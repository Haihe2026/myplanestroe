"""Baby studio phone+KEY identity layer over the EXISTING shared wallet.

No SMS, quota grants, payment settlement, image upload, or new balance table.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from urllib.parse import parse_qs, urlsplit

PREFIX='/platform-api/gemini'

class PhoneKeys:
    def __init__(self,store,server,master):
        if not isinstance(master,str) or len(master)<32: raise ValueError('Phone KEY secret not configured')
        self.store,self.server,self.master=store,server,master.encode()
        self.lock=threading.RLock()
        with store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS album_phone_keys(phone_hash TEXT PRIMARY KEY,user_id TEXT UNIQUE NOT NULL,
                last4 TEXT NOT NULL,salt TEXT NOT NULL,key_hash TEXT NOT NULL,created INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS album_login_limits(scope TEXT PRIMARY KEY,attempts INTEGER NOT NULL,expires INTEGER NOT NULL);
            ''')
    def phone(self,phone):
        if not isinstance(phone,str): raise self.server.Problem(400,'请填写手机号')
        phone=phone.strip().removeprefix('+86')
        if not re.fullmatch(r'1[3-9][0-9]{9}',phone): raise self.server.Problem(400,'首版支持中国大陆手机号')
        return hmac.new(self.master,phone.encode(),hashlib.sha256).hexdigest(),phone[-4:]
    def hash_key(self,key,salt):return hashlib.scrypt(key.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    def limit(self,scope):
        now=int(time.time())
        scope=hmac.new(self.master,scope.encode(),hashlib.sha256).hexdigest()
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('DELETE FROM album_login_limits WHERE expires<?',(now,))
            old=c.execute('SELECT attempts FROM album_login_limits WHERE scope=?',(scope,)).fetchone()
            if old and old[0]>=10:raise self.server.Problem(429,'尝试较多，请15分钟后再试')
            c.execute('INSERT INTO album_login_limits VALUES(?,1,?) ON CONFLICT(scope) DO UPDATE SET attempts=attempts+1',(scope,now+900))
    def complete(self,body,ip,login=False):
        if body.get('accepted') is not True:raise self.server.Problem(400,'请同意手机号仅用于账户关联与登录')
        self.limit('ip:'+ip)
        ph,last4=self.phone(body.get('phone'));self.limit('phone:'+ph)
        ticket=body.get('entry')
        if not isinstance(ticket,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',ticket): raise self.server.Problem(401,'请从技能重新打开账户入口')
        entries=self.store.registration_entries
        with self.lock,entries.lock:
            row=entries.pending.get(self.server.digest(ticket))
            if not row or row['product']!='gemini' or row['expires']<=time.time():raise self.server.Problem(401,'入口已过期或使用，请从技能重新打开')
            with self.store.connect() as c:
                account=c.execute('SELECT * FROM album_phone_keys WHERE phone_hash=?',(ph,)).fetchone()
            if login:
                key=body.get('key')
                if not isinstance(key,str) or not 1<=len(key)<=128:raise self.server.Problem(401,'手机号或KEY不匹配')
                expected=account['key_hash'] if account else '0'*128
                actual=self.hash_key(key,account['salt'] if account else '00'*16)
                if not account or not hmac.compare_digest(actual,expected):raise self.server.Problem(401,'手机号或KEY不匹配')
                uid=account['user_id'];identity=self.server.digest(row['secret'])
                with self.store.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    prior=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(identity,)).fetchone()
                    if prior and prior[0]!=uid:raise self.server.Problem(409,'当前对话已有其他账户，请保留原账户，不自动合并余额')
                    c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)',(identity,uid,int(time.time())))
                session=entries.confirm('gemini',ticket,True)
                return {'ok':True,'linked_existing':True},session
            if account:raise self.server.Problem(409,'该号码已建账户，请使用原KEY登录，不会重新赠送体验')
            # Registration is the established shared-account transaction; no balance duplication.
            # Retain the ticket until binding succeeds, so a transient failure can resume same identity.
            self.store.register_product('gemini',row['secret'],row['ip'],True)
            uid=self.store.user(row['secret'])
            with self.store.connect() as c:
                prior=c.execute('SELECT 1 FROM album_phone_keys WHERE user_id=?',(uid,)).fetchone()
            if prior:raise self.server.Problem(409,'原账户已绑定其他号码，不替换、不重置KEY')
            key=secrets.token_urlsafe(12)+last4;salt=secrets.token_bytes(16).hex()
            with self.store.connect() as c:
                c.execute('INSERT INTO album_phone_keys VALUES(?,?,?,?,?,?)',(ph,uid,last4,salt,self.hash_key(key,salt),int(time.time())))
            session=entries.confirm('gemini',ticket,True)
            return {'ok':True,'key_once':key,'last4':last4,'phone_verified':False},session

def install(server,shared):
    previous=shared.handler
    def handler(store,validator=None):
        parent=previous(store,validator)
        keys=PhoneKeys(store,server,os.environ.get('IMAGE_TRIAL_HMAC_KEY',''))
        class Handler(parent):
            def run_request(self):
                if self.path not in (PREFIX+'/album-entry',PREFIX+'/album-register',PREFIX+'/album-login'):
                    return super().run_request()
                try:
                    if self.command!='POST':raise server.Problem(405,'请求方式无效')
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式错误')
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict):raise server.Problem(400,'请求格式错误')
                    ip=self.headers.get('X-Real-IP',self.client_address[0]) if self.client_address[0]=='127.0.0.1' else self.client_address[0]
                    if self.path.endswith('/album-entry'):
                        result=store.registration_entries.prepare('gemini',body.get('install_secret'),ip[:64])
                        if result['status']=='registration':result['url']=result['url'].replace('/membership/gemini/register/','/membership/baby-photo/')
                        return self.send(200,result)
                    if self.headers.get('Origin')!='https://myplanestore.com' or self.headers.get('X-Membership-Request')!='1':raise server.Problem(403,'请从本站操作')
                    result,session=keys.complete(body,ip[:64],login=self.path.endswith('/album-login'))
                    return self.send(200,result,cookie='platform_member='+session+'; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800')
                except server.Problem as error:return self.send(error.status,{'error':error.message})
                except (ValueError,TypeError):return self.send(400,{'error':'参数无效，请核对后重试'})
                except Exception:return self.send(503,{'error':'账户关联暂不可用，请保留原需求与KEY后核对'})
            do_GET=run_request
            do_POST=run_request
        return Handler
    shared.handler=handler
