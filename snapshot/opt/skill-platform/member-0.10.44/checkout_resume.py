"""Resume an existing pet login only from an unexpired, unrevoked device cookie."""
import json,time,os,ipaddress
from http.cookies import SimpleCookie
from urllib.parse import urlsplit,parse_qs
PATH='/platform-api/pet/membership-api/resume'
ACTIVATE='/platform-api/pet/membership-api/activate'
def wrap(parent,store,server):
    class Handler(parent):
        def run_request(self):
            route=urlsplit(self.path).path
            if route not in (PATH,ACTIVATE):return super().run_request()
            self.close_connection=True;self.connection.settimeout(15)
            ip=self.client_address[0]
            if ip in ('127.0.0.1','::1'):
                try:ip=str(ipaddress.ip_address(self.headers.get('X-Real-IP',ip)))
                except ValueError:pass
            key=server.digest(ip+':pet');now=int(time.time());window=int(os.environ.get('PET_FAILURE_WINDOW_SECONDS','600'))
            try:
                with store.connect() as c:
                    r=c.execute('SELECT count FROM pet_rate_limits WHERE key=? AND window>?',(key,now-window)).fetchone()
                    if r and r[0]>=int(os.environ.get('PET_FAILURE_LIMIT','600')):raise server.Problem(429,'操作较频繁，请稍后再试')
                if self.command!='POST':raise server.Problem(405,'请从付款页面继续')
                origins=('https://myplanestore.com','https://aistore.zhaopintong.com') if route==ACTIVATE else ('https://myplanestore.com',)
                if self.headers.get('Origin') not in origins or self.headers.get('X-Membership-Request')!='1':raise server.Problem(403,'请从本站操作')
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式无效')
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict):raise server.Problem(400,'请求格式无效')
                if route==ACTIVATE and body.get('accepted') is not True:raise server.Problem(400,'请确认开通宠物账户')
                cookies=SimpleCookie(self.headers.get('Cookie',''));device=cookies.get('mps_device')
                uid=None
                if route==ACTIVATE:
                    member=cookies.get('platform_member')
                    if member:
                        try:uid=store.membership.web_user(member.value)
                        except server.Problem as e:
                            if e.status!=401:raise
                if not uid:uid=store.device_links.lookup(device.value if device else None)
                if not uid:raise server.Problem(401,'请先微信扫码登录')
                if route==ACTIVATE:
                    # Explicit checkout action only. A read/resume never creates eligibility.
                    # Identity comes solely from verified server sessions, never a body uid.
                    with store.connect() as c:
                        c.execute('BEGIN IMMEDIATE')
                        if not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():raise server.Problem(401,'账户登录已失效')
                        store.pet_billing.enroll(c,uid,False)
                        store.pet_billing.audit(c,'pet_checkout_account_confirmed',uid)
                else:
                    # Resume preserves the historical read-only eligibility boundary.
                    with store.connect() as c:store.pet_billing.require(c,uid)
                link=store.membership.handoff(uid)
                ticket=parse_qs(urlsplit(link['url']).fragment)['ticket'][0]
                session=store.membership.redeem(ticket)
                if store.membership.web_user(session)!=uid:raise server.Problem(503,'账户状态需要重新确认')
                with store.connect() as c:store.pet_billing.audit(c,'pet_checkout_session_resumed',uid)
                return self.send(200,{'ok':True},cookie='platform_member='+session+'; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800')
            except server.Problem as e:
                if e.status in (400,401,403,405):
                    with store.connect() as c:
                        c.execute('INSERT INTO pet_rate_limits VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET window=CASE WHEN window<=? THEN excluded.window ELSE window END,count=CASE WHEN window<=? THEN 1 ELSE count+1 END',(key,now,now-window,now-window))
                return self.send(e.status,{'error':e.message})
            except (ValueError,TypeError):return self.send(400,{'error':'请求格式无效'})
            except Exception:return self.send(503,{'error':'暂时无法确认账户，请稍后重试'})
        do_GET=run_request
        do_POST=run_request
    return Handler
