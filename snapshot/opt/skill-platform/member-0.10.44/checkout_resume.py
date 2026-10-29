"""Resume an existing pet login only from an unexpired, unrevoked device cookie."""
import json,time,os,ipaddress
from http.cookies import SimpleCookie
from urllib.parse import urlsplit,parse_qs
PATH='/platform-api/pet/membership-api/resume'
def wrap(parent,store,server):
    class Handler(parent):
        def run_request(self):
            if urlsplit(self.path).path!=PATH:return super().run_request()
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
                if self.headers.get('Origin')!='https://myplanestore.com' or self.headers.get('X-Membership-Request')!='1':raise server.Problem(403,'请从本站操作')
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式无效')
                if not isinstance(json.loads(self.rfile.read(size)),dict):raise server.Problem(400,'请求格式无效')
                cookies=SimpleCookie(self.headers.get('Cookie',''));device=cookies.get('mps_device')
                uid=store.device_links.lookup(device.value if device else None)
                if not uid:raise server.Problem(401,'当前浏览器还没有登录，请先确认账户')
                # Never register/enroll a new pet user, link a new device, or issue trials.
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
