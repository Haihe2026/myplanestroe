"""Pet routes wrap the actual final handler; all other prefixes delegate unchanged."""
import hashlib,hmac,json,os,re,secrets,time,uuid
from http.cookies import SimpleCookie
from urllib.parse import urlsplit,parse_qs
from pet_billing import PetBilling
from product_config import settings,PRODUCT_PREFIXES

def install(store,server,shared,parent):
    import account_link,platform_catalog
    from pet_vision import Vision,execute
    vision=Vision()
    billing=PetBilling(store,server.Problem);store.pet_billing=billing
    old_register=store.register_product;old_quota=store.quota
    def register(product,secret,ip,accepted):
        if product!='pet':return old_register(product,secret,ip,accepted)
        if accepted is not True or not account_link.valid_token(secret):raise server.Problem(400,'请确认宠物账户条款并从原技能打开')
        identity=server.digest(secret);now=int(time.time())
        with store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(identity,)).fetchone();created=row is None
            if created:
                day=time.strftime('%Y-%m-%d',time.gmtime(now));iph=hmac.new(os.environ['IMAGE_TRIAL_HMAC_KEY'].encode(),ip.encode(),hashlib.sha256).hexdigest()
                n=c.execute('SELECT count FROM claim_limits WHERE ip_hash=? AND day=?',(iph,day)).fetchone()
                if n and n[0]>=int(os.environ.get('IMAGE_ASSISTANT_ACCOUNT_IP_DAILY_LIMIT','10')):raise server.Problem(429,'账户开通频率过高')
                uid=str(uuid.uuid4());c.execute('INSERT INTO users VALUES(?,0)',(uid,))
                c.execute('INSERT INTO claim_limits VALUES(?,?,1) ON CONFLICT(ip_hash,day) DO UPDATE SET count=count+1',(iph,day))
                c.execute('INSERT INTO trial_claims VALUES(?,?,?)',(identity,uid,now))
            else:uid=row[0]
            billing.enroll(c,uid,created)
            c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',(identity,uid,now+7*86400))
        return {'created':created,'registered':True,'granted':False,**billing.account(uid)}
    store.register_product=register
    store.quota=lambda uid,product:billing.account(uid) if product=='pet' else old_quota(uid,product)
    # One registry replaces the old enabled-products helper without editing its file.
    previous_enabled=account_link.enabled_products
    account_link.enabled_products=lambda:set(p for p in (*previous_enabled(),'pet') if p in PRODUCT_PREFIXES)
    if not any(p['id']=='pet' for p in platform_catalog.PRODUCTS):
        platform_catalog.PRODUCTS=[*platform_catalog.PRODUCTS,{'id':'pet','name':'宠物养护','tag':'宠物 / 养护','description':'宠物照片分析、养护档案与提醒','membership_ready':True,'quota_policy':'独立额度，不与通用次数通兑','status':'独立宠物通道'}]
    with store.connect() as c:c.execute('CREATE TABLE IF NOT EXISTS pet_rate_limits(key TEXT PRIMARY KEY,window INTEGER NOT NULL,count INTEGER NOT NULL)')
    def failure_limit(key,record=False):
        # Only invalid requests count; successful users behind CGNAT do not consume it.
        now=int(time.time());key=server.digest(key);window=int(os.environ.get('PET_FAILURE_WINDOW_SECONDS','600'));maximum=int(os.environ.get('PET_FAILURE_LIMIT','600'))
        with store.connect() as c:
            c.execute('BEGIN IMMEDIATE');c.execute('DELETE FROM pet_rate_limits WHERE window<=?',(now-window,))
            r=c.execute('SELECT count FROM pet_rate_limits WHERE key=?',(key,)).fetchone()
            if record:
                c.execute('INSERT INTO pet_rate_limits VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1',(key,now))
            elif r and r[0]>=maximum:raise server.Problem(429,'失败请求过多，请稍后重试')
    def cookie_value(headers,name):
        try:r=SimpleCookie(headers.get('Cookie','')).get(name);return r.value if r else None
        except Exception:return None
    def session_for(uid):
        link=store.membership.handoff(uid);ticket=parse_qs(urlsplit(link['url']).fragment)['ticket'][0]
        return store.membership.redeem(ticket)
    class Handler(parent):
        def run_request(self):
            path=urlsplit(self.path).path
            if not path.startswith('/platform-api/pet/'):return super().run_request()
            self.connection.settimeout(15);route=path[len('/platform-api/pet'):];ctx=None
            try:
                ip=self.client_address[0]
                if ip in ('127.0.0.1','::1'):
                    import ipaddress
                    try:ip=str(ipaddress.ip_address(self.headers.get('X-Real-IP',ip)))
                    except ValueError:pass
                failure_limit(ip+':pet')
                if route=='/health' and self.command=='GET':return self.send(200,{'status':'ok','version':'0.10.39','isolated_quota':True})
                if self.command not in ('POST','GET'):raise server.Problem(405,'请求方式无效')
                browser=route.startswith('/membership-api/')
                if self.command=='POST':
                    if browser and (self.headers.get('Origin')!='https://myplanestore.com' or self.headers.get('X-Membership-Request')!='1'):raise server.Problem(403,'请从本站操作')
                    if route=='/photo-analysis':
                        store.user(self.headers.get('Authorization','').removeprefix('Bearer '))
                        if not vision.ready:raise server.Problem(503,'照片分析暂未开放')
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=(12*1024*1024 if route=='/photo-analysis' else 16384) or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式无效')
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict):raise server.Problem(400,'JSON对象必填')
                else:body={}
                def reply(data,session=None):
                    if session:
                        uid=store.membership.web_user(session)
                        self.send_header_cookie=store.device_links.issue(uid,cookie_value(self.headers,'mps_device'),'pet')
                    return self.send(200,data,cookie=('platform_member='+session+'; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800') if session else None)
                if route=='/register' and self.command=='POST':return reply(register('pet',body.get('install_secret'),ip,body.get('accepted')))
                if route=='/quick-entry' and self.command=='POST':
                    secret=body.get('install_secret')
                    if not account_link.valid_token(secret):raise server.Problem(400,'账户参数无效')
                    try:uid=store.user(secret)
                    except server.Problem as e:
                        if e.status!=401:raise
                    else:
                        # Reads never enroll an existing shared identity or create a trial.
                        try:q=billing.account(uid)
                        except server.Problem:q={}
                        if q:
                            result=store.membership.handoff(uid)
                            u=urlsplit(result['url'])
                            if u.scheme!='https' or u.netloc!='myplanestore.com' or not u.path.startswith('/membership/'):raise server.Problem(503,'账户入口需要核对')
                            result['url']=u._replace(path='/membership/pet/').geturl()
                            return reply(dict(result,status='checkout',**q))
                    entries=store.registration_entries
                    with entries.lock:
                        now=time.time();entries.pending={k:v for k,v in entries.pending.items() if v['expires']>now}
                        if len(entries.pending)>=2048 or sum(r['ip']==ip for r in entries.pending.values())>=12:raise server.Problem(429,'入口过多')
                        ticket=secrets.token_urlsafe(32);entries.pending[server.digest(ticket)]={'product':'pet','secret':secret,'ip':ip,'expires':now+300}
                    return reply({'status':'registration','url':'https://myplanestore.com/membership/pet/register/#entry='+ticket,'expires_in':300})
                if route=='/membership-api/plans' and self.command=='GET':return reply({'plans':settings()['plans'],'payment_ready':os.environ.get('PET_PAYMENT_CONFIRMED')=='yes','photo_analysis_ready':vision.ready})
                if route=='/membership-api/remembered' and self.command=='GET':
                    uid=store.device_links.lookup(cookie_value(self.headers,'mps_device'))
                    return reply({'remembered':bool(uid),'account_label':('宠物账户 · '+uid[:8]) if uid else None})
                if route=='/membership-api/forget-device' and self.command=='POST':
                    store.device_links.forget(cookie_value(self.headers,'mps_device'),'pet');self.send_header_cookie=account_link.cookie_header('',0);return reply({'ok':True})
                if route=='/membership-api/link-entry' and self.command=='POST':
                    session=store.device_links.link_entry('pet',body.get('ticket'),body.get('accepted'),cookie_value(self.headers,'mps_device'));return reply({'ok':True},session)
                if route=='/membership-api/confirm-entry' and self.command=='POST':
                    if body.get('accepted') is not True:raise server.Problem(400,'请明确同意后继续')
                    entries=store.registration_entries;ticket=body.get('ticket')
                    if not account_link.valid_token(ticket):raise server.Problem(401,'入口无效')
                    with entries.lock:
                        row=entries.pending.get(server.digest(ticket))
                        if not row or row['expires']<=time.time() or row['product']!='pet':raise server.Problem(401,'请从对应宠物技能重新打开')
                        register('pet',row['secret'],row['ip'],True);uid=store.user(row['secret']);session=session_for(uid);del entries.pending[server.digest(ticket)]
                    return reply({'ok':True},session)
                if route=='/membership-api/redeem' and self.command=='POST':
                    session=store.redeem_product('pet',body.get('ticket'));uid=store.membership.web_user(session);billing.account(uid);return reply({'ok':True},session)
                if route=='/quick-entry/status' and self.command=='POST':
                    try:uid=store.user(body.get('install_secret'))
                    except server.Problem:return reply({'status':'registration_pending'})
                    return reply(dict(status='registered',**billing.account(uid)))
                if browser:uid=store.membership.web_user(cookie_value(self.headers,'platform_member') or '')
                else:uid=store.user(self.headers.get('Authorization','').removeprefix('Bearer '))
                if route in ('/balance','/membership-api/account') and self.command=='GET':return reply(dict(billing.account(uid),photo_analysis_ready=vision.ready))
                if route=='/quick-entry/status' and self.command=='POST':return reply(dict(status='registered',**billing.account(uid)))
                if route=='/membership-api/orders' and self.command=='POST':
                    if os.environ.get('PET_PAYMENT_CONFIRMED')!='yes':raise server.Problem(503,'宠物支付尚未开放')
                    return reply(billing.order(uid,body.get('plan')))
                if route.startswith('/membership-api/orders/') and self.command=='GET':return reply(billing.get_order(uid,route.rsplit('/',1)[-1]))
                if route=='/membership-api/report-payment' and self.command=='POST':return reply(billing.report_payment(uid,body.get('order_id')))
                if route=='/profiles' and self.command=='GET':
                    with store.connect() as c:
                        billing.require(c,uid);items=[dict(r) for r in c.execute('SELECT id,body,created FROM pet_profiles WHERE user_id=? ORDER BY created',(uid,))]
                    return reply({'items':items})
                if route=='/profiles' and self.command=='POST':return reply(billing.profile(uid,body.get('profile'),body.get('id')))
                if route=='/reminders' and self.command in ('GET','POST'):return reply(billing.reminders(uid,body if self.command=='POST' else None))
                if route.startswith('/report-pdf/') and self.command=='GET':return self.send(200,billing.report_pdf(uid,route.rsplit('/',1)[-1]),'application/pdf')
                # No client-callable reserve/finish: only a trusted vision adapter may meter
                # and execute analysis. Host models cannot mark their own calls as paid.
                if route=='/photo-analysis' and self.command=='POST':
                    if not vision.ready:raise server.Problem(503,'照片分析暂未开放')
                    import base64
                    return reply(execute(billing,vision,uid,base64.b64decode(body.get('image_base64',''),validate=True),body.get('prompt')))
                raise server.Problem(404,'接口不存在')
            except server.Problem as e:
                if e.status in (400,401,403,404,405):failure_limit(ip+':pet',True)
                return self.send(e.status,{'error':e.message})
            except (ValueError,TypeError,UnicodeError):
                failure_limit(ip+':pet',True);return self.send(400,{'error':'请求格式无效'})
            except Exception:return self.send(503,{'error':'服务暂不可用，请稍后重试'})
        def end_headers(self):
            value=getattr(self,'send_header_cookie',None)
            if value:self.send_header('Set-Cookie',value);self.send_header_cookie=None
            return super().end_headers()
        do_GET=run_request
        do_POST=run_request
    return Handler
