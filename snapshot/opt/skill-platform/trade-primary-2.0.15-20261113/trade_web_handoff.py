"""Purpose-scoped Trade credential -> main-domain browser handoff.

Only the existing authenticated GET /me response can mint an entry. Existing
Membership and DeviceLinks own sessions; no account, trial, order or Trade
approval is created here. Official-account OAuth remains unchanged.
"""
import io
import json
from pathlib import Path
import re
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from urllib.parse import parse_qs,urlsplit

CONTRACT='trade-web-handoff-v1'
ORIGIN='https://myplanestore.com'
LANDING='/auth/wechat/oa-complete.html'
REDEEM='/platform-api/wechat/oa/redeem'
HEALTH='/platform-api/wechat/trade-handoff/health'
ME='/api/trade-leads/v1/me'
TARGET='/pay?skill=trade-leads'
TTL=120
FIELDS={'token_hash','account_id','scope','expires','created','used'}
SCHEMA="""CREATE TABLE trade_web_handoffs(
token_hash TEXT PRIMARY KEY,account_id TEXT NOT NULL,
scope TEXT NOT NULL CHECK(scope='trade-leads'),
expires INTEGER NOT NULL,created INTEGER NOT NULL,
used INTEGER NOT NULL DEFAULT 0 CHECK(used IN (0,1)))"""


class Fault(Exception):
    def __init__(self,status,message):self.status,self.message=status,message


def token(value):return isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{43}',value) is not None


def migrate_shared(path):
    """Explicit migration of only the new scope table in an existing shared DB."""
    path=Path(path)
    if path.is_symlink():raise ValueError('symlink_database')
    c=sqlite3.connect(path.resolve().as_uri()+'?mode=rw',uri=True,timeout=3)
    try:
        with c:
            c.execute('BEGIN IMMEDIATE')
            names={row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'users','web_tickets','web_sessions','remembered_devices'}<=names:
                raise ValueError('existing_membership_database_required')
            if 'trade_web_handoffs' not in names:c.execute(SCHEMA)
            columns={row[1] for row in c.execute('PRAGMA table_info(trade_web_handoffs)')}
            if columns!=FIELDS:raise ValueError('unexpected_handoff_schema')
    finally:c.close()


class Handoffs:
    def __init__(self,store,server,clock=time.time):
        self.store,self.server,self.clock=store,server,clock

    def ready(self):
        with self.store.connect() as c:
            columns={row[1] for row in c.execute('PRAGMA table_info(trade_web_handoffs)')}
        return columns==FIELDS

    def issue(self,uid):
        # The public ticket exists only in this purpose table. In particular,
        # it must not be accepted by any older generic membership redeem route.
        ticket=secrets.token_urlsafe(32);key=self.server.digest(ticket);now=int(self.clock())
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            user=c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone()
            if not user:
                raise Fault(401,'请保留原账户，在原技能重新打开账户页面')
            expires=now+TTL
            c.execute("INSERT INTO trade_web_handoffs VALUES(?,?,'trade-leads',?,?,0)",(key,uid,expires,now))
            # Keep used/expired tombstones for a day, so replay cannot fall back
            # to another authentication mechanism during its useful lifetime.
            c.execute('DELETE FROM trade_web_handoffs WHERE expires<?',(now-86400,))
        return ORIGIN+LANDING+'#ticket='+ticket

    def lookup(self,ticket):
        if not token(ticket):return None
        with self.store.connect() as c:
            row=c.execute('SELECT * FROM trade_web_handoffs WHERE token_hash=?',(self.server.digest(ticket),)).fetchone()
        return dict(row) if row else None

    def browser_accounts(self,headers):
        try:values=SimpleCookie(headers.get('Cookie',''))
        except Exception:return set()
        result=set()
        if 'platform_member' in values:
            try:result.add(self.store.membership.web_user(values['platform_member'].value))
            except self.server.Problem as error:
                if error.status!=401:raise Fault(503,'暂时无法确认浏览器账户，请稍后重新打开') from None
            except Exception:raise Fault(503,'暂时无法确认浏览器账户，请稍后重新打开') from None
        if 'mps_device' in values:
            try:
                uid=self.store.device_links.lookup(values['mps_device'].value)
                if uid:result.add(uid)
            except self.server.Problem as error:
                if error.status!=401:raise Fault(503,'暂时无法确认浏览器账户，请稍后重新打开') from None
            except Exception:raise Fault(503,'暂时无法确认浏览器账户，请稍后重新打开') from None
        return result

    def redeem(self,ticket,headers):
        # This is deliberately main-domain only. No existing Cookie is copied
        # across hosts; the main-domain HTTP response issues a fresh session.
        if headers.get('Origin')!=ORIGIN or headers.get('Host','').lower() not in ('myplanestore.com','myplanestore.com:443') or headers.get('X-Membership-Request')!='1':
            raise Fault(403,'请从原技能提供的主站账户页面继续')
        row=self.lookup(ticket);now=int(self.clock())
        if not row or row['scope']!='trade-leads' or row['used'] or row['expires']<=now:
            raise Fault(401,'账户链接已使用或过期，请在原技能重新打开')
        accounts=self.browser_accounts(headers)
        if any(uid!=row['account_id'] for uid in accounts):
            raise Fault(409,'浏览器当前是其他账户，请使用原账户的浏览器或无痕窗口重新打开')
        key=self.server.digest(ticket)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            changed=c.execute("UPDATE trade_web_handoffs SET used=1 WHERE token_hash=? AND scope='trade-leads' AND used=0 AND expires>?",(key,now)).rowcount
            if changed!=1:raise Fault(401,'账户链接已使用或过期，请在原技能重新打开')
        # Separate original transactions, never nested on the same SQLite DB.
        # If issuance fails after consumption, no Cookie is returned; the
        # authenticated Skill can obtain another fresh /me handoff safely.
        internal=self.store.membership.handoff(row['account_id'])
        values=parse_qs(urlsplit(internal['url']).fragment,keep_blank_values=True)
        if set(values)!={'ticket'} or len(values['ticket'])!=1 or not token(values['ticket'][0]):
            raise Fault(503,'账户页面暂未准备好，请稍后从原技能重试')
        session=self.store.membership.redeem(values['ticket'][0])
        if self.store.membership.web_user(session)!=row['account_id']:
            raise Fault(401,'账户归属未能确认，请从原技能重新打开')
        try:current=SimpleCookie(headers.get('Cookie','')).get('mps_device')
        except Exception:current=None
        remembered=self.store.device_links.issue(row['account_id'],current.value if current else '', 'trade-leads')
        cookies=[remembered,'platform_member='+session+'; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800']
        return dict(status='linked',product='trade-leads',url=TARGET,return_path=TARGET),cookies


def install(parent,store,server,service=None):
    service=service or Handoffs(store,server)
    class Handler(parent):
        def run_request(self):
            path=urlsplit(self.path).path
            if path==HEALTH:
                if self.command!='GET':return self.send(405,dict(error='请求方式无效'))
                try:ready=service.ready()
                except Exception:ready=False
                return self.send(200 if ready else 503,dict(status='ok' if ready else 'unavailable',contract=CONTRACT,
                    primary_host_valid=self.headers.get('Host','').lower() in ('myplanestore.com','myplanestore.com:443')))
            if path!=REDEEM or self.command!='POST':return super().run_request()
            # Preserve the complete existing official-account redeem route for
            # tickets that are not in this narrowly scoped handoff table.
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':return super().run_request()
                raw=self.rfile.read(size)
                try:body=json.loads(raw)
                except (ValueError,UnicodeError):body=None
                value=body.get('ticket') if isinstance(body,dict) else None
                try:owned=service.lookup(value)
                except Exception:raise Fault(503,'账户页面暂不可用，请从原技能重新打开') from None
                if not owned:
                    original=self.rfile;self.rfile=io.BytesIO(raw)
                    try:return super().run_request()
                    finally:self.rfile=original
                if set(body)!={'ticket'}:raise Fault(400,'账户链接格式无效，请从原技能重新打开')
                result,cookies=service.redeem(value,self.headers)
                self.wechat_cookies=cookies
                return self.send(200,result)
            except Fault as error:return self.send(error.status,dict(error=error.message))
            except Exception:return self.send(503,dict(error='账户页面暂不可用，请从原技能重新打开；原账户和余额保持'))

        def send(self,status,result,*args,**kwargs):
            if self.command=='GET' and urlsplit(self.path).path==ME and status==200 and isinstance(result,dict) and 'error' not in result:
                try:
                    authorization=self.headers.get('Authorization','')
                    if not re.fullmatch(r'Bearer [A-Za-z0-9_-]{43}',authorization):raise ValueError('account_auth_required')
                    uid=store.trade.token_user(authorization[7:],self.headers.get('X-Device-Id',''))
                    result=dict(result,web_login_url=service.issue(uid))
                except Exception:
                    # Account reads and existing credentials keep working; the
                    # new client must not replace this with unproven re-login.
                    result=dict(result,web_login_unavailable=True)
            return super().send(status,result,*args,**kwargs)

        do_GET=run_request
        do_POST=run_request
    return Handler
