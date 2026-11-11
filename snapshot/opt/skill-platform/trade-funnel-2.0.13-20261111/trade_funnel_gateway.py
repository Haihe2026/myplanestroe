"""Optional observations around existing successful handlers; no auth replacement."""
import atexit
import hashlib
from http.cookies import SimpleCookie
import ipaddress
import json
import os
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit,parse_qs

from trade_funnel import CONTRACT, SKILL, Funnel, Invalid, Limited, Conflict, identity

TRIGGER = '/api/v1/telemetry/skill-trigger'
PAGE = '/platform-api/telemetry/v2/trade-page-view'
HEALTH = '/platform-api/telemetry/v2/trade-funnel/health'
ORIGINS = ('https://aistore.zhaopintong.com','https://myplanestore.com')
_LOCK = threading.RLock()
_MAINTENANCE = {}


def start_retention(funnel, interval=6*3600):
    """One bounded sidecar cleanup daemon per path; no new consumer/service."""
    key=str(funnel.path.resolve())
    with _LOCK:
        old=_MAINTENANCE.get(key)
        if old and old[1].is_alive():return old
        stop=threading.Event()
        def maintain():
            while not stop.is_set():
                try:funnel.prune()
                except Exception:pass
                if stop.wait(interval):break
        thread=threading.Thread(target=maintain,name='trade-funnel-retention',daemon=True)
        _MAINTENANCE[key]=(stop,thread)
        atexit.register(stop.set)
        thread.start()
        return stop,thread


def sha(value): return hashlib.sha256(value.encode()).hexdigest()


def peer_ip(handler):
    peer = str(ipaddress.ip_address(handler.client_address[0]))
    if peer in ('127.0.0.1','::1'):
        try: return str(ipaddress.ip_address(handler.headers.get('X-Real-IP',peer)))
        except ValueError: pass
    return peer


def test_request(handler):
    requested = handler.headers.get('X-MPS-Telemetry-Test')
    if requested is None: return False
    # Nginx sets X-Real-IP for Internet traffic. A forwarded/spoofed request can
    # never opt out of normal reporting by claiming to be an internal test.
    if requested != '1' or handler.client_address[0] not in ('127.0.0.1','::1') or handler.headers.get('X-Real-IP') or handler.headers.get('X-Forwarded-For'):
        raise Invalid('test_header_not_allowed')
    return True


def browser_user(store, headers):
    try: cookies=SimpleCookie(headers.get('Cookie',''))
    except Exception: return None
    value=lambda name:cookies[name].value if name in cookies else ''
    try:
        uid=store.device_links.lookup(value('mps_device'))
        if uid:return uid
    except Exception:pass
    try:return store.membership.web_user(value('platform_member'))
    except Exception:return None


def runtime(store, dialogues=None, path=None):
    if dialogues is None:
        from dialogue_store import Dialogues
        dialogues=Dialogues()
    return Funnel(path or os.environ.get('TRADE_FUNNEL_DB','/var/lib/skill-monitor/trade-funnel.sqlite3'),
                  dialogues.key,dialogues=dialogues,shared_path=getattr(store,'path',None) or '/var/lib/skill-platform/shared.db')


def ensure_approve_observer(store, funnel):
    """Observe the real Trade.approve fact, preserving args, return and errors.

    The captured member-0.10.54 implementation inserts a new users UUID only in
    its uid=None branch; known WeChat identities are resolved before that call.
    No timestamp guess or phone identity is used to create the new-account fact.
    """
    if funnel is None or not hasattr(store,'trade'):return
    with _LOCK:
        trade=store.trade
        if getattr(trade,'trade_funnel_observer_installed',False):return
        original=trade.approve
        def approve(code,uid=None):
            before=None; observed=False
            try:
                with store.connect() as c:
                    row=c.execute('SELECT account_id,device_hash FROM trade_links WHERE code_hash=?',(sha(code),)).fetchone()
                observed=bool(row); before=row[0] if row else None
            except Exception:pass
            result=original(code,uid)
            if observed and before is None:
                try:
                    with store.connect() as c:
                        wallet=c.execute('SELECT is_test FROM trade_wallets WHERE account_id=?',(result,)).fetchone()
                    funnel.approved(sha(code),result,new_account=uid is None,is_test=bool(wallet and wallet[0]),device_hash=row['device_hash'])
                except Exception:pass
            return result
        trade.approve=approve
        trade.trade_funnel_observer_installed=True


def install(parent, store, funnel=None, make_runtime=runtime):
    managed=funnel is None
    if funnel is None:
        try:funnel=make_runtime(store)
        except Exception:funnel=None
    if managed and funnel is not None:
        try:start_retention(funnel)
        except Exception:pass

    class Handler(parent):
        def __init__(self,*args,**kwargs):
            try:ensure_approve_observer(store,funnel)
            except Exception:pass
            super().__init__(*args,**kwargs)

        def log_message(self,*args):
            if urlsplit(self.path).path in (TRIGGER,PAGE,HEALTH):return
            return super().log_message(*args)

        def _empty(self,status):
            self.send_response(status)
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length','0')
            self.end_headers()

        def _body(self):
            self.connection.settimeout(4)
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=1024 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Invalid('invalid_json_request')
            body=json.loads(self.rfile.read(size))
            if not isinstance(body,dict):raise Invalid('json_object_required')
            return body

        def run_request(self):
            path=urlsplit(self.path).path
            if path not in (TRIGGER,PAGE,HEALTH):return super().run_request()
            try:
                if path==HEALTH:
                    if self.command!='GET':return self._empty(405)
                    if funnel is None:return self._empty(503)
                    with funnel.connect():pass
                    return self.send(200,dict(status='ok',contract=CONTRACT,skill_code=SKILL))
                if self.command!='POST':return self._empty(405)
                if funnel is None:return self._empty(503)
                origin=self.headers.get('Origin')
                if origin and origin not in ORIGINS:return self._empty(403)
                is_test=test_request(self)
                body=self._body()
                if path==TRIGGER:
                    funnel.trigger(body,peer_ip(self),self.headers.get('X-Skill-Channel','workbuddy_expert'),self.headers.get('X-Skill-Version',''),is_test=is_test)
                else:
                    if origin not in ORIGINS or self.headers.get('X-Membership-Request')!='1':return self._empty(403)
                    if set(body)-{'page','code'} or 'page' not in body:raise Invalid('invalid_page_fields')
                    uid=browser_user(store,self.headers)
                    if body['page']=='recharge' and not uid:return self._empty(401)
                    if uid:
                        with store.connect() as c:wallet=c.execute('SELECT is_test FROM trade_wallets WHERE account_id=?',(uid,)).fetchone()
                        is_test=bool(is_test or (wallet and wallet[0]))
                    funnel.page(body['page'],peer_ip(self),uid,body.get('code'),is_test=is_test)
                return self._empty(204)
            except Limited:return self._empty(429)
            except Conflict:return self._empty(409)
            except (Invalid,ValueError,TypeError,UnicodeError):return self._empty(400)
            except Exception:return self._empty(503)

        def send(self,status,result,*args,**kwargs):
            if funnel is not None and status==200 and isinstance(result,dict):
                try:
                    path=urlsplit(self.path).path
                    if path=='/api/trade-leads/v1/auth/start':
                        funnel.remember_link(result.get('link_code'),self.headers.get('X-Device-Id'),self.headers.get('X-Skill-Instance'))
                    elif path=='/platform-api/wechat/start' and isinstance(result.get('state'),str):
                        with store.connect() as c:
                            row=c.execute('SELECT product,entry_hash,source_uid FROM wechat_login_states WHERE hash=?',(sha(result['state']),)).fetchone()
                        if row and row['product']=='trade-leads' and isinstance(row['entry_hash'],str) and row['entry_hash'].startswith('trade:'):
                            funnel.oauth_started(row['entry_hash'][6:],row['source_uid'])
                    elif path=='/platform-api/telemetry/v1/first-dialogue/link' and result.get('linked') is True:
                        funnel.link_from_dialogue(result.get('event_id'))
                except Exception:pass
            return super().send(status,result,*args,**kwargs)

        def send_response(self,status,*args,**kwargs):
            if funnel is not None and urlsplit(self.path).path=='/platform-api/wechat/callback':
                try:
                    state=parse_qs(urlsplit(self.path).query).get('state',[''])[0]
                    if re.fullmatch('[A-Za-z0-9_-]{43}',state):
                        with store.connect() as c:
                            row=c.execute("SELECT s.entry_hash,w.user_id FROM wechat_login_states s JOIN wechat_identities w ON w.identity=s.identity WHERE s.hash=? AND s.product='trade-leads' AND s.status IN ('approved','used')",(sha(state),)).fetchone()
                        if row and isinstance(row['entry_hash'],str) and row['entry_hash'].startswith('trade:'):
                            funnel.identity_confirmed(row['entry_hash'][6:],row['user_id'])
                except Exception:pass
            return super().send_response(status,*args,**kwargs)

        do_GET=run_request
        do_POST=run_request
    return Handler


def install_telemetry(telemetry):
    """Install before the existing chain; avoid eager trade/config imports."""
    previous=telemetry.observed_handler
    def observed(parent,store,product,event_db):
        return install(previous(parent,store,product,event_db),store)
    telemetry.observed_handler=observed
