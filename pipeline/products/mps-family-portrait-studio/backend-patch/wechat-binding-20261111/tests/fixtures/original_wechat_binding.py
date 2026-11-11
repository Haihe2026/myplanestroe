"""WeChat website OAuth; host-only cookies, browser verifier and one-use state.

No provider credentials, user text or photos are handled here. Existing product
registration/account-link functions own all trial/ledger policy. OAuth identities
are hashes scoped to this app; credentials are loaded only on the server.
"""
import hashlib,json,os,re,secrets,threading,time,urllib.parse,urllib.request
from pathlib import Path
from http.cookies import SimpleCookie
ORIGINS=('https://myplanestore.com','https://aistore.zhaopintong.com')
CALLBACK=ORIGINS[1]+'/platform-api/wechat/callback'
PRODUCTS=('gemini','temu','pet','trade-leads')
LOCK=threading.RLock()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def valid(s):return isinstance(s,str) and re.fullmatch(r'[A-Za-z0-9_-]{43}',s) is not None
def cookie(headers,name):
    try:v=SimpleCookie(headers.get('Cookie','')).get(name);return v.value if v else None
    except Exception:return None
def config():
    p=Path(os.environ.get('WECHAT_CONFIG_FILE','/etc/skill-platform/wechat-login.json'))
    if p.stat().st_mode&0o077:raise RuntimeError('Private configuration required')
    v=json.loads(p.read_text())
    if not re.fullmatch(r'wx[a-zA-Z0-9]{16}',v['appid']) or not re.fullmatch(r'[a-zA-Z0-9]{32}',v['secret']):raise RuntimeError('Invalid configuration')
    return v
def exchange(code):
    cfg=config()
    url='https://api.weixin.qq.com/sns/oauth2/access_token?'+urllib.parse.urlencode(dict(appid=cfg['appid'],secret=cfg['secret'],code=code,grant_type='authorization_code'))
    # Never log this URL, the HTTP exception, response token, or raw openid.
    with urllib.request.urlopen(url,timeout=10) as r:
        raw=r.read(65537)
    if len(raw)>65536:raise ValueError('Invalid response')
    d=json.loads(raw)
    if d.get('errcode') or not isinstance(d.get('openid'),str) or not 1<=len(d['openid'])<=128:raise ValueError('Authorization rejected')
    return digest(cfg['appid']+':'+d['openid'])

def handler(parent,store,server):
    Problem=server.Problem
    with store.connect() as c:
        c.executescript('''
          CREATE TABLE IF NOT EXISTS wechat_identities(identity TEXT PRIMARY KEY,user_id TEXT UNIQUE NOT NULL,created INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS wechat_login_states(hash TEXT PRIMARY KEY,verifier TEXT NOT NULL,product TEXT NOT NULL,entry_hash TEXT,source_uid TEXT,identity TEXT,status TEXT NOT NULL,expires INTEGER NOT NULL,created INTEGER NOT NULL);
          CREATE TABLE IF NOT EXISTS wechat_login_audit(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,product TEXT,created INTEGER NOT NULL);
        ''')
    def entry_for(product,secret,ip):
        if product not in ('gemini','temu','pet') or not valid(secret):raise Problem(400,'请从原技能打开账户入口')
        entries=store.registration_entries;now=time.time()
        with entries.lock:
            entries.pending={k:r for k,r in entries.pending.items() if r['expires']>now}
            if len(entries.pending)>=2048 or sum(r['ip']==ip for r in entries.pending.values())>=12:raise Problem(429,'账户入口较多，请稍后重试')
            ticket=secrets.token_urlsafe(32);entries.pending[server.digest(ticket)]=dict(product=product,secret=secret,ip=ip,expires=now+300)
        return dict(status='registration',url=ORIGINS[0]+'/membership/'+product+'/register/#entry='+ticket,expires_in=300)
    if not getattr(store,'wechat_prepare_installed',False):
        original_prepare=store.registration_entries.prepare
        def prepare(product,secret,ip):
            result=original_prepare(product,secret,ip)
            if result.get('status') in ('ready','checkout'):
                uid=store.user(secret)
                with store.connect() as c:bound=c.execute('SELECT 1 FROM wechat_identities WHERE user_id=?',(uid,)).fetchone()
                if not bound:return entry_for(product,secret,ip)
            return result
        store.registration_entries.prepare=prepare;store.wechat_prepare_installed=True
    def current(headers):
        try:return store.membership.web_user(cookie(headers,'platform_member'))
        except Problem:return store.device_links.lookup(cookie(headers,'mps_device'))
    def session(uid):
        h=store.membership.handoff(uid)
        t=urllib.parse.parse_qs(urllib.parse.urlsplit(h['url']).fragment)['ticket'][0]
        return store.membership.redeem(t)
    class Handler(parent):
        def log_message(self,*a):pass
        def end_headers(self):
            for h in getattr(self,'wechat_cookies',[]):self.send_header('Set-Cookie',h)
            self.wechat_cookies=[]
            return super().end_headers()
        def run_request(self):
            path=urllib.parse.urlsplit(self.path).path
            if not path.startswith('/platform-api/wechat/'):
                # Two exact first-party Origins. No wildcard, subdomain or null Origin.
                if self.headers.get('Origin')==ORIGINS[1]:self.headers.replace_header('Origin',ORIGINS[0])
                return super().run_request()
            try:
                self.connection.settimeout(15)
                route=path.rsplit('/',1)[-1]
                if route=='callback':return self.callback()
                if self.command=='GET' and route=='status':
                    uid=current(self.headers)
                    with store.connect() as c:r=c.execute('SELECT 1 FROM wechat_identities WHERE user_id=?',(uid,)).fetchone() if uid else None
                    return self.send(200,dict(logged_in=bool(uid),wechat_bound=bool(r)))
                if self.command!='POST':raise Problem(405,'请求方式无效')
                if self.headers.get('Origin') not in ORIGINS or self.headers.get('X-Membership-Request')!='1':raise Problem(403,'请从本站操作')
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Problem(400,'请求格式无效')
                b=json.loads(self.rfile.read(n))
                if not isinstance(b,dict):raise Problem(400,'请求格式无效')
                if route=='start':return self.start(b)
                if route=='finish':return self.finish(b)
                raise Problem(404,'页面不存在')
            except Problem as e:return self.send(e.status,dict(error=e.message))
            except (ValueError,TypeError,KeyError):return self.send(400,dict(error='请核对信息，重新扫码'))
            except Exception:return self.send(503,dict(error='微信登录暂不可用，请稍后重新扫码'))
        def start(self,b):
            if b.get('accepted') is not True:raise Problem(400,'请先同意隐私政策与账户绑定')
            product=b.get('product','gemini');entry=b.get('entry') or None;trade_code=b.get('code') or None
            if product not in PRODUCTS:raise Problem(400,'请选择对应技能')
            uid=current(self.headers)
            if entry:
                if not valid(entry):raise Problem(401,'请从原技能重新打开')
                with store.registration_entries.lock:
                    row=store.registration_entries.pending.get(server.digest(entry))
                    if not row or row['expires']<=time.time() or row['product']!=product:raise Problem(401,'请从原技能重新打开')
                    try:original=store.user(row['secret'])
                    except Problem:original=None
                    if uid and original and uid!=original:raise Problem(409,'账户不一致，请保留原账户联系客服')
                    uid=original or uid
            elif trade_code:
                if product!='trade-leads' or not re.fullmatch('[A-Z2-9]{8}',trade_code):raise Problem(400,'外贸获客入口无效')
                with store.connect() as c:row=c.execute('SELECT account_id FROM trade_links WHERE code_hash=? AND expires>?',(digest(trade_code),time.time())).fetchone()
                if not row:raise Problem(401,'请从原技能重新打开')
                if uid and row[0] and uid!=row[0]:raise Problem(409,'账户不一致，请联系客服')
                uid=row[0] or uid
            elif not uid:
                # Account-free login is only meaningful for an existing WeChat identity;
                # creation still requires a real skill entry (and its original product).
                pass
            # Retain scheme A: an already authenticated, WeChat-bound browser can
            # explicitly reuse its account. A new sandbox does not force a new scan.
            if uid and current(self.headers)==uid:
                with store.connect() as c:bound=c.execute('SELECT 1 FROM wechat_identities WHERE user_id=?',(uid,)).fetchone()
                if bound:
                    if trade_code:store.trade.approve(trade_code,uid)
                    device=store.device_links.issue(uid,cookie(self.headers,'mps_device'),product)
                    raw=SimpleCookie(device)['mps_device'].value
                    token=store.device_links.link_entry(product,entry,True,raw) if entry else session(uid)
                    self.wechat_cookies=[device,'platform_member='+token+'; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800']
                    return self.send(200,dict(status='linked',product=product,url='/pay?skill=trade-leads' if product=='trade-leads' else '/membership/'+product+'/'))
            cfg=config();state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(32);now=int(time.time())
            with store.connect() as c:
                c.execute('BEGIN IMMEDIATE');c.execute('DELETE FROM wechat_login_states WHERE expires<?',(now,))
                if c.execute('SELECT count(*) FROM wechat_login_states').fetchone()[0]>=2048:raise Problem(429,'登录请求较多，请稍后重试')
                c.execute('INSERT INTO wechat_login_states VALUES(?,?,?,?,?,NULL,?,?,?)',(digest(state),digest(verifier),product,server.digest(entry) if entry else ('trade:'+digest(trade_code) if trade_code else None),uid,'pending',now+300,now))
            url='https://open.weixin.qq.com/connect/qrconnect?'+urllib.parse.urlencode(dict(appid=cfg['appid'],redirect_uri=CALLBACK,response_type='code',scope='snsapi_login',state=state))+'#wechat_redirect'
            return self.send(200,dict(state=state,verifier=verifier,url=url,expires_in=300))
        def callback(self):
            if self.command!='GET':raise Problem(405,'请求方式无效')
            q=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query);state=q.get('state',[''])[0];code=q.get('code',[''])[0]
            if not valid(state) or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',code):raise Problem(400,'微信授权已取消或已过期')
            with store.connect() as c:
                c.execute('BEGIN IMMEDIATE');r=c.execute("UPDATE wechat_login_states SET status='exchanging' WHERE hash=? AND status='pending' AND expires>?",(digest(state),time.time()))
                if r.rowcount!=1:raise Problem(401,'授权已使用或过期，请重新扫码')
            try:identity=exchange(code)
            except Exception:
                with store.connect() as c:c.execute("UPDATE wechat_login_states SET status='failed' WHERE hash=?",(digest(state),))
                raise Problem(503,'微信授权未完成，请在原页面重新扫码') from None
            with store.connect() as c:c.execute("UPDATE wechat_login_states SET identity=?,status='approved' WHERE hash=?",(identity,digest(state)))
            data='<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>微信授权完成</title><p>微信授权完成。请回到刚才的账户页面继续，随后回原 Skill 对话。</p>'.encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def finish(self,b):
            state=b.get('state');verifier=b.get('verifier')
            if not valid(state) or not valid(verifier):raise Problem(401,'请重新扫码')
            with LOCK:
                with store.connect() as c:r=c.execute('SELECT * FROM wechat_login_states WHERE hash=? AND verifier=? AND expires>?',(digest(state),digest(verifier),time.time())).fetchone()
                if not r:raise Problem(401,'扫码已过期，请重新扫码')
                if r['status'] in ('pending','exchanging'):return self.send(200,dict(status='pending'))
                if r['status'] not in ('approved','used'):raise Problem(401,'扫码未完成，请重新扫码')
                with store.connect() as c:identity=c.execute('SELECT user_id FROM wechat_identities WHERE identity=?',(r['identity'],)).fetchone()
                uid=r['source_uid'];known=identity[0] if identity else None
                if uid and known and uid!=known:raise Problem(409,'该微信已绑定其他账户，不会合并或替换余额')
                uid=uid or known
                if uid:
                    with store.connect() as c:other=c.execute('SELECT identity FROM wechat_identities WHERE user_id=?',(uid,)).fetchone()
                    if other and other[0]!=r['identity']:raise Problem(409,'原账户已绑定其他微信，请联系客服')
                entries=store.registration_entries
                with entries.lock:
                    trade_entry=bool(r['entry_hash'] and r['entry_hash'].startswith('trade:'))
                    pending=entries.pending.get(r['entry_hash']) if r['entry_hash'] and not trade_entry and r['status']!='used' else None
                    if r['entry_hash'] and not trade_entry and r['status']!='used' and (not pending or pending['expires']<=time.time() or pending['product']!=r['product']):raise Problem(401,'原技能入口已过期，请重新打开')
                    if trade_entry and r['status']!='used':
                        code=b.get('code','')
                        if not re.fullmatch('[A-Z2-9]{8}',code) or 'trade:'+digest(code)!=r['entry_hash']:raise Problem(401,'请从原外贸获客入口继续')
                        uid=store.trade.approve(code,uid)
                    if pending:
                        if uid:
                            with store.connect() as c:
                                c.execute('BEGIN IMMEDIATE');prior=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(server.digest(pending['secret']),)).fetchone()
                                if prior and prior[0]!=uid:raise Problem(409,'原对话关联了其他账户，请联系客服')
                                c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)',(server.digest(pending['secret']),uid,int(time.time())))
                        store.register_product(r['product'],pending['secret'],pending['ip'],True)
                        uid=store.user(pending['secret'])
                    if not uid:raise Problem(401,'首次使用请从对应 Skill 打开账户入口')
                    with store.connect() as c:
                        c.execute('BEGIN IMMEDIATE');other=c.execute('SELECT identity FROM wechat_identities WHERE user_id=?',(uid,)).fetchone()
                        if other and other[0]!=r['identity']:raise Problem(409,'原账户已绑定其他微信，请联系客服')
                        c.execute('INSERT OR IGNORE INTO wechat_identities VALUES(?,?,?)',(r['identity'],uid,int(time.time())))
                        c.execute("UPDATE wechat_login_states SET status='used',source_uid=? WHERE hash=? AND status='approved'",(uid,r['hash']))
                        if r['status']!='used':c.execute('INSERT INTO wechat_login_audit(kind,product,created) VALUES(?,?,?)',('wechat_bound',r['product'],int(time.time())))
                    if pending:del entries.pending[r['entry_hash']]
                token=session(uid);remember=store.device_links.issue(uid,cookie(self.headers,'mps_device'),r['product'])
                self.wechat_cookies=[remember,'platform_member='+token+'; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800']
                return self.send(200,dict(status='linked',product=r['product'],url='/pay?skill=trade-leads' if r['product']=='trade-leads' else '/membership/'+r['product']+'/'))
        do_GET=run_request
        do_POST=run_request
    return Handler
