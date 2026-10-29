"""Compatibility adapter on the existing shared server, preserving other routes."""
import json,os,re,secrets,time,uuid
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
from trade_store import Trade,Error,digest
from trade_config import config,mock_identity,COUNTRIES
from trade_mapping import slug
from trade_provider import MockProvider,RockApis

PREFIX='/api/trade-leads/v1'
WEB='/platform-api/trade-leads/web'

def install(store,parent):
    config()
    trade=Trade(store);trade.recover();store.trade=trade
    class Handler(parent):
        def log_message(self,*args):
            # URLs may include browser link codes; never log request lines.
            if urlsplit(self.path).path.startswith((PREFIX,WEB)):return
            return super().log_message(*args)
        def run_request(self):
            path=urlsplit(self.path).path
            if not path.startswith((PREFIX+'/',WEB+'/')):return super().run_request()
            self.connection.settimeout(30)
            try:
                if self.command not in ('GET','POST'):raise Error(405,'INVALID_PARAMS','请求方式无效')
                ip=self.client_address[0]
                if ip in ('127.0.0.1','::1'):
                    import ipaddress
                    try:ip=str(ipaddress.ip_address(self.headers.get('X-Real-IP',ip)))
                    except ValueError:pass
                body={}
                if self.command=='POST':
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=16384 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Error(400,'INVALID_PARAMS','请提交 JSON 对象')
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict):raise Error(400,'INVALID_PARAMS','请提交 JSON 对象')
                if path==PREFIX+'/health' and self.command=='GET':return self.send(200,dict(status='ok',version='0.10.41'))
                if path.startswith(WEB+'/'):return self.trade_web(path[len(WEB):],body,ip)
                if path==PREFIX+'/pricing' and self.command=='GET':
                    trade.rate('pricing:'+ip,120)
                    return self.send(200,dict(currency='CNY',price_fen=config()['price_list'],daily_free_trial=config()['daily_free_trial'],tiers_yuan=[x/100 for x in config()['tiers']],tiers_fen=config()['tiers'],tier_details=config().get('tier_details',[])))
                device=self.headers.get('X-Device-Id','')
                try:
                    if str(uuid.UUID(device))!=device.lower():raise ValueError()
                except (ValueError,TypeError):raise Error(400,'INVALID_PARAMS','请提供有效 X-Device-Id')
                token=self.headers.get('Authorization','')
                uid=trade.token_user(token[7:],device) if token.startswith('Bearer ') else None
                if token and not uid:raise Error(401,'INVALID_TOKEN','关联已失效')
                trade.rate('account:'+uid if uid else 'device:'+device,30 if uid else 10)
                # A second bounded IP throttle protects anonymous link-code guessing.
                trade.rate('ip:'+ip,600)
                route=path[len(PREFIX):]
                if route=='/pricing' and self.command=='GET':return self.send(200,dict(currency='CNY',price_fen=config()['price_list'],daily_free_trial=config()['daily_free_trial'],tiers_yuan=[x/100 for x in config()['tiers']],tiers_fen=config()['tiers'],tier_details=config().get('tier_details',[])))
                if route=='/auth/start' and self.command=='POST':
                    if body.get('device_id')!=device or body.get('skill')!='trade-leads':raise Error(400,'INVALID_PARAMS','设备或技能标识不符')
                    trade.rate('start:'+ip,30,600);return self.send(200,trade.start(device))
                if route=='/auth/poll' and self.command=='POST':
                    if body.get('device_id')!=device or not re.fullmatch('[A-Z2-9]{8}',body.get('link_code','')):raise Error(400,'INVALID_PARAMS','关联参数无效')
                    return self.send(200,trade.poll(body['link_code'],device))
                if route=='/me' and self.command=='GET':
                    if not uid:raise Error(401,'AUTH_REQUIRED','请先关联账户')
                    with store.connect() as c:free=trade.free_available(c,trade.free_keys(uid,device,ip))
                    return self.send(200,dict(account=dict(display='账户 · '+uid[:8]),balance_fen=trade.balance(uid),trial_remaining_today=int(free),recharge_url='https://myplanestore.com/pay?skill=trade-leads'))
                if route not in ('/search','/company','/contacts') or self.command!='POST':raise Error(404,'INVALID_PARAMS','接口不存在')
                if route!='/search' and not uid:raise Error(401,'AUTH_REQUIRED','请先关联账户')
                if route=='/search':
                    keywords=body.get('keywords');country=body.get('country');page=body.get('page',1)
                    if not isinstance(keywords,list) or not 1<=len(keywords)<=5 or any(not isinstance(k,str) or not 1<=len(k.strip())<=64 for k in keywords) or country not in COUNTRIES or type(page) is not int or page!=1:raise Error(400,'INVALID_PARAMS','请填写1–5个关键词、支持的国家代码及第1页')
                    body=dict(keywords=[k.strip() for k in keywords[:max(1,min(5,int(os.environ.get('MAX_KEYWORDS_PER_SEARCH','2'))))]],country=country,page=page)
                else:
                    cid=slug(body.get('company_id') or body.get('linkedin_url',''))
                    if not cid:raise Error(400,'INVALID_PARAMS','公司标识无效')
                    limit=body.get('max',3)
                    if type(limit) is not int or not 1<=limit<=10:raise Error(400,'INVALID_PARAMS','联系人数量应为1–10')
                    body=dict(company_id=cid,**({'max':limit} if route=='/contacts' else {}))
                ref=secrets.token_hex(12)
                # No global mock switch can accidentally make real users pay for test data.
                provider=(MockProvider if mock_identity(uid,device) else RockApis)(store,uid,ref)
                status,payload=trade.execute(route[1:],body,uid,device,ip,self.headers.get('Idempotency-Key'),provider)
                return self.send(status,payload)
            except Error as e:
                if e.status==429:self.trade_retry=True
                return self.send(e.status,e.body())
            except (ValueError,TypeError,UnicodeError):return self.send(400,Error(400,'INVALID_PARAMS','参数格式无效').body())
            except Exception:return self.send(503,Error(503,'UPSTREAM_ERROR','服务暂不可用，本次未扣费').body())
        def trade_web(self,route,body,ip):
            cookies=SimpleCookie()
            try:cookies.load(self.headers.get('Cookie',''))
            except Exception:pass
            cookie=lambda k:cookies[k].value if k in cookies else ''
            uid=store.device_links.lookup(cookie('mps_device'))
            if not uid:
                try:uid=store.membership.web_user(cookie('platform_member'))
                except Exception:pass
            trade.rate('browser:'+ip,120)
            if self.command=='POST' and (self.headers.get('Origin')!='https://myplanestore.com' or self.headers.get('X-Membership-Request')!='1'):raise Error(403,'INVALID_PARAMS','请从本站操作')
            if route=='/account' and self.command=='GET':return self.send(200,dict(remembered=bool(uid),account_label='账户 · '+uid[:8] if uid else '',balance_fen=trade.balance(uid) if uid else 0,**config()))
            if route=='/approve' and self.command=='POST':
                if body.get('accepted') is not True or not re.fullmatch('[A-Z2-9]{8}',body.get('code','')):raise Error(400,'INVALID_PARAMS','请确认关联并同意账户条款')
                if not uid:
                    # New website identity follows the existing zero-balance shared-user
                    # schema, never image/pet registration or a grant/trial insertion.
                    if body.get('new_account') is not True:raise Error(401,'AUTH_REQUIRED','请先选择创建账户或使用浏览器已记住的账户')
                    trade.rate('register:'+ip,10,86400)
                uid=trade.approve(body['code'],uid)
                self.trade_cookie=store.device_links.issue(uid,cookie('mps_device'),'trade-leads')
                return self.send(200,dict(status='approved',account=dict(display='账户 · '+uid[:8])))
            if not uid:raise Error(401,'AUTH_REQUIRED','请从技能关联后打开充值页')
            if route=='/orders' and self.command=='POST':
                return self.send(200,trade.order(uid,body.get('amount_fen'),uid in __import__('trade_config').ids('SMOKE_TEST_ACCOUNT_IDS')))
            if route=='/report-payment' and self.command=='POST':return self.send(200,trade.report(uid,body.get('order_id')))
            if route.startswith('/orders/') and self.command=='GET':
                with store.connect() as c:r=c.execute('SELECT id,amount_fen,status FROM trade_orders WHERE id=? AND account_id=?',(route.rsplit('/',1)[-1],uid)).fetchone()
                if not r:raise Error(404,'INVALID_PARAMS','订单不存在')
                return self.send(200,dict(r))
            raise Error(404,'INVALID_PARAMS','接口不存在')
        def end_headers(self):
            if getattr(self,'trade_cookie',None):self.send_header('Set-Cookie',self.trade_cookie);self.trade_cookie=None
            if getattr(self,'trade_retry',False):self.send_header('Retry-After','60');self.trade_retry=False
            if urlsplit(self.path).path.startswith((PREFIX,WEB)):self.send_header('Cache-Control','no-store')
            return super().end_headers()
        do_GET=run_request
        do_POST=run_request
    return Handler
