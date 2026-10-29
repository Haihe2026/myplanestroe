"""Outer PET-only handler. Other paths keep the original final handler unchanged."""
import json,re
from urllib.parse import urlsplit
from pet_photo import MAX_BODY,execute

def wrap(parent,store,server,vision):
    billing=store.pet_billing
    class Handler(parent):
        def run_request(self):
            path=urlsplit(self.path).path
            if path=='/platform-api/pet/membership-api/plans' and self.command=='GET':
                from product_config import settings
                import os
                cfg=settings()
                return self.send(200,dict(plans=cfg['plans'],display=cfg.get('display',{}),payment_ready=os.environ.get('PET_PAYMENT_CONFIRMED')=='yes',photo_analysis_ready=vision.ready))
            photo=path=='/platform-api/pet/photo-analysis'
            query=path.startswith('/platform-api/pet/photo-analysis/')
            if not (photo or query):return super().run_request()
            self.connection.settimeout(20);ip=self.client_address[0]
            if ip in ('127.0.0.1','::1'):
                import ipaddress
                try:ip=str(ipaddress.ip_address(self.headers.get('X-Real-IP',ip)))
                except ValueError:pass
            try:
                # Existing failed-only pet throttle; successful users behind CGNAT don't count.
                key=server.digest(ip+':pet')
                import os,time
                now=int(time.time());window=int(os.environ.get('PET_FAILURE_WINDOW_SECONDS','600'))
                with store.connect() as c:
                    r=c.execute('SELECT count FROM pet_rate_limits WHERE key=? AND window>?',(key,now-window)).fetchone()
                    if r and r[0]>=int(os.environ.get('PET_FAILURE_LIMIT','600')):raise server.Problem(429,'失败请求过多，请稍后重试')
                auth=self.headers.get('Authorization','')
                if not auth.startswith('Bearer '):raise server.Problem(401,'请先关联宠物账户')
                uid=store.user(auth[7:])
                with store.connect() as c:billing.require(c,uid)
                if query and self.command=='GET':
                    jid=path.rsplit('/',1)[-1]
                    if not re.fullmatch(r'[a-f0-9]{32}',jid):raise server.Problem(404,'照片任务不存在')
                    return self.send(200,billing.analysis(uid,jid))
                if not photo or self.command!='POST':raise server.Problem(405,'请求方式无效')
                if not vision.ready:
                    billing.unavailable();self.close_connection=True
                    return self.send(503,{'error':'照片分析暂未开放','code':'PHOTO_NOT_READY'})
                idem=self.headers.get('Idempotency-Key','')
                if not re.fullmatch(r'[A-Za-z0-9_-]{16,100}',idem):raise server.Problem(400,'请提供16至100位任务编号')
                size=int(self.headers.get('Content-Length','0'))
                if size>MAX_BODY:raise server.Problem(413,'照片须在5 MiB以内')
                if size<=0 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式无效')
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict):raise server.Problem(400,'请求内容应为对象')
                return self.send(200,execute(billing,vision,uid,idem,body))
            except server.Problem as e:
                if e.status in (400,401,403,404,405):
                    with store.connect() as c:
                        c.execute('INSERT INTO pet_rate_limits VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET window=CASE WHEN window<=? THEN excluded.window ELSE window END,count=CASE WHEN window<=? THEN 1 ELSE count+1 END',(key,now,now-window,now-window))
                self.close_connection=True
                return self.send(e.status,{'error':e.message})
            except (ValueError,TypeError,UnicodeError):
                with store.connect() as c:
                    c.execute('INSERT INTO pet_rate_limits VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET window=CASE WHEN window<=? THEN excluded.window ELSE window END,count=CASE WHEN window<=? THEN 1 ELSE count+1 END',(key,now,now-window,now-window))
                self.close_connection=True;return self.send(400,{'error':'请求格式无效'})
            except Exception:
                self.close_connection=True;return self.send(503,{'error':'照片分析暂不可用'})
        do_GET=run_request
        do_POST=run_request
    return Handler
