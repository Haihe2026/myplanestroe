"""Listing namespace adapter; existing routes and machine identities delegate unchanged."""
import json,re,secrets,time,threading,hashlib,uuid
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
from listing_store import Listing,Error
from hosted_delivery import HostedDelivery,FIELDS
PREFIX='/platform-api/listing/v1'
PRODUCT='listing-optimizer'
ORIGINS=('https://myplanestore.com','https://aistore.zhaopintong.com')
LOCK=threading.Lock();RATES={}

def rate(key,limit=180):
 key=hashlib.sha256(key.encode()).hexdigest();now=int(time.time())//60
 with LOCK:
  for k in list(RATES):
   if RATES[k][0]!=now:del RATES[k]
  n=RATES.get(key,(now,0))[1]
  if n>=limit:raise Error(429,'RATE_LIMITED')
  RATES[key]=(now,n+1)

def cook(headers,name):
 try:r=SimpleCookie(headers.get('Cookie','')).get(name);return r.value if r else None
 except Exception:return None

def public(api):
 c=api.config
 return {**{k:c[k] for k in ('product_id','display_name','currency','price_version','unit_price_fen','trial_policy','tiers','terms')},
   'service_ready':api.ready(),'payment_methods':['微信','支付宝'],'qr_url':'/membership/payment-qr.png',
   'platform_fields':FIELDS,'client_skill_integration_verified':False}

def wrap(parent,store,server):
 api=Listing(store,verifier=HostedDelivery());store.listing=api
 import wechat_binding
 if PRODUCT not in wechat_binding.PRODUCTS:wechat_binding.PRODUCTS=(*wechat_binding.PRODUCTS,PRODUCT)
 original=store.register_product
 def register(product,secret,ip,accepted):
  if product!=PRODUCT:return original(product,secret,ip,accepted)
  if accepted is not True or not re.fullmatch('[A-Za-z0-9_-]{43}',secret or ''):raise server.Problem(400,'请确认账户关联')
  now=int(time.time());identity=server.digest(secret)
  with store.connect() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(identity,)).fetchone()
   if row:uid=row[0]
   else:
    uid=str(uuid.uuid4());c.execute('INSERT INTO users VALUES(?,0)',(uid,))
    c.execute("INSERT INTO ledger(user_id,amount,kind,created) VALUES(?,0,'account_created',?)",(uid,now))
    c.execute('INSERT INTO trial_claims VALUES(?,?,?)',(identity,uid,now))
   c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',(identity,uid,now+7*86400))
   c.execute('INSERT OR IGNORE INTO listing_accounts(account_id,created) VALUES(?,?)',(uid,now))
  return dict(registered=True)
 store.register_product=register

 class Handler(parent):
  def finish(self,*args):
   # Existing WeChat names its OAuth completion method finish(body), which
   # collides with socketserver's no-argument lifecycle cleanup. Preserve both.
   if args:return super().finish(*args)
   from http.server import BaseHTTPRequestHandler
   return BaseHTTPRequestHandler.finish(self)
  def log_message(self,*args):
   if urlsplit(self.path).path.startswith(PREFIX):return
   return super().log_message(*args)
  def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
   if isinstance(result,dict) and result.get('product')==PRODUCT and result.get('status')=='linked':
    result=dict(result,url='/membership/listing/')
   return super().send(status,result,mime,cookie=cookie)
  def run_request(self):
   path=urlsplit(self.path).path
   if path=='/platform-api/telemetry/v1/first-dialogue/link' and self.command=='POST':
    import io
    try:
     self.connection.settimeout(5)
     n=int(self.headers.get('Content-Length','0'))
     if not 0<n<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Error(400,'INVALID_JSON')
     raw=self.rfile.read(n);b=json.loads(raw)
     if isinstance(b,dict) and b.get('product')==PRODUCT:
      if set(b)!={'event_id','receipt','product'}:raise Error(400,'INVALID_FIELDS')
      if self.headers.get('Origin') not in (None,*ORIGINS):raise Error(403,'ORIGIN_NOT_ALLOWED')
      token=self.headers.get('Authorization','')
      if not re.fullmatch('Bearer [A-Za-z0-9_-]{43}',token):raise Error(401,'ACCOUNT_REQUIRED')
      try:uid=store.user(token[7:])
      except Exception:raise Error(401,'ACCOUNT_REQUIRED')
      rate('listing-event-link:'+uid,60)
      from dialogue_store import Dialogues,Invalid,Conflict
      try:return self.send(200,Dialogues().link(b['event_id'],b['receipt'],uid))
      except Conflict:raise Error(409,'EVENT_ALREADY_LINKED')
      except Invalid:raise Error(400,'INVALID_RECEIPT')
     self.rfile=io.BytesIO(raw)
     return super().run_request()
    except Error as e:return self.send(e.status,dict(error=e.code))
    except (ValueError,TypeError):return self.send(400,dict(error='INVALID_REQUEST'))
    except Exception:return self.send(503,dict(error='EVENT_LINK_UNAVAILABLE'))
   if not path.startswith(PREFIX+'/'):return super().run_request()
   self.connection.settimeout(15)
   try:
    ip=self.client_address[0]
    if ip in ('127.0.0.1','::1'):
     import ipaddress
     try:ip=str(ipaddress.ip_address(self.headers.get('X-Real-IP',ip)))
     except ValueError:pass
    origin=self.headers.get('Origin')
    if origin and origin not in ORIGINS:raise Error(403,'ORIGIN_NOT_ALLOWED')
    if self.command not in ('GET','POST'):raise Error(405,'METHOD_NOT_ALLOWED')
    route=path[len(PREFIX):];b={}
    if self.command=='GET' and route in ('/health','/pricing'):
     rate('public:'+ip,300)
     return self.send(200,dict(status='ok',contract='listing-cny-bundle-v1',payment_ready=api.ready(),host_integration_verified=False) if route=='/health' else public(api))
    auth=self.headers.get('Authorization','');uid=None
    if auth:
     if not re.fullmatch('Bearer [A-Za-z0-9_-]{43}',auth):raise Error(401,'ACCOUNT_REQUIRED')
     try:uid=store.user(auth[7:])
     except Exception:pass
    else:
     try:uid=store.membership.web_user(cook(self.headers,'platform_member'))
     except Exception:uid=store.device_links.lookup(cook(self.headers,'mps_device'))
    if self.command=='POST':
     if not auth and (origin not in ORIGINS or self.headers.get('X-Membership-Request')!='1'):raise Error(403,'SITE_REQUEST_REQUIRED')
     n=int(self.headers.get('Content-Length','0'));limit=262144 if re.fullmatch('/tasks/[a-f0-9]{32}/(complete|revise)',route) else 16384
     if not 0<n<=limit or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Error(400,'INVALID_JSON')
     b=json.loads(self.rfile.read(n))
     if not isinstance(b,dict):raise Error(400,'INVALID_JSON')
    rate('account:'+uid if uid else 'credential:'+auth if auth else 'anonymous:'+ip,180)
    key=self.headers.get('Idempotency-Key','')
    if self.command=='POST' and not re.fullmatch('[A-Za-z0-9_.:-]{16,100}',key):raise Error(400,'IDEMPOTENCY_KEY_REQUIRED')
    if route=='/entry' and self.command=='POST':
     if b!={'accepted':True}:raise Error(400,'ACCEPTANCE_REQUIRED')
     secret=auth[7:] if auth else secrets.token_urlsafe(32)
     if not re.fullmatch('[A-Za-z0-9_-]{43}',secret):raise Error(400,'INVALID_CREDENTIAL')
     entries=store.registration_entries;now=time.time()
     with entries.lock:
      entries.pending={k:r for k,r in entries.pending.items() if r['expires']>now}
      # Short-lived idempotent entry envelope only; never persist/log machine secrets.
      marker=server.digest('listing-entry:'+(secret if auth else 'anonymous')+':'+key)
      old=next((r for r in entries.pending.values() if r.get('listing_marker')==marker),None)
      if old:ticket=old['listing_ticket']
      else:
       if len(entries.pending)>=2048 or sum(r.get('ip')==ip for r in entries.pending.values())>=100:raise Error(429,'RATE_LIMITED')
       ticket=secrets.token_urlsafe(32);entries.pending[server.digest(ticket)]=dict(product=PRODUCT,secret=secret,ip=ip,expires=now+300,listing_marker=marker,listing_ticket=ticket)
     return self.send(200,dict(url=(origin if origin in ORIGINS else ORIGINS[0])+'/auth/wechat/listing.html#product='+PRODUCT+'&entry='+ticket,expires_in=300))
    if route=='/entry/status' and self.command=='GET':
     if not re.fullmatch('Bearer [A-Za-z0-9_-]{43}',auth):raise Error(401,'ACCOUNT_REQUIRED')
     if not uid:return self.send(200,dict(status='pending'))
     try:return self.send(200,dict(status='ready',account=api.me(uid)))
     except Error as e:
      if e.status==403:return self.send(200,dict(status='recognized',requires_enroll=True))
      raise
    if not uid:raise Error(401,'ACCOUNT_REQUIRED')
    if route=='/me' and self.command=='GET':return self.send(200,dict(api.me(uid),account_tag=hashlib.sha256(uid.encode()).hexdigest()[:16]))
    if route=='/enroll' and self.command=='POST':
     if set(b)!={'accepted'}:raise Error(400,'INVALID_FIELDS')
     return self.send(200,api.enroll(uid,key,b.get('accepted')))
    if route=='/orders':
     if self.command=='POST':
      if set(b)!={'tier_id','source','channel'}:raise Error(400,'INVALID_FIELDS')
      return self.send(200,api.order(uid,key,b['tier_id'],b['source'],b['channel']))
     with store.connect() as c:rows=[dict(r) for r in c.execute('SELECT * FROM listing_orders WHERE account_id=? ORDER BY created DESC LIMIT 50',(uid,))]
     return self.send(200,dict(items=rows))
    m=re.fullmatch('/orders/([a-f0-9]{32})(/report)?',route)
    if m:
     if m[2] and self.command=='POST':
      if b:raise Error(400,'INVALID_FIELDS')
      return self.send(200,api.report(uid,key,m[1]))
     if not m[2] and self.command=='GET':
      with store.connect() as c:return self.send(200,dict(api.owned(c,'listing_orders',uid,m[1])))
    if route=='/quotes' and self.command=='POST':return self.send(200,api.quote(uid,key,b))
    if route=='/tasks/reserve' and self.command=='POST':
     if set(b)!={'quote_id','confirmed'}:raise Error(400,'INVALID_FIELDS')
     return self.send(200,api.reserve(uid,key,b['quote_id'],b['confirmed']))
    m=re.fullmatch('/tasks/([a-f0-9]{32})(/(complete|revise|release))?',route)
    if m:
     if not m[2] and self.command=='GET':return self.send(200,api.task(uid,m[1]))
     if self.command=='POST' and m[3] in ('complete','revise'):
      if set(b)!={'evidence'}:raise Error(400,'INVALID_FIELDS')
      return self.send(200,getattr(api,m[3])(uid,key,m[1],b['evidence']))
     # A readable host cannot attest its own execution failure. No public refund
     # of an in-flight task; trusted ops must verify before releasing the hold.
     if m[3]=='release':raise Error(409,'REQUIRES_CONFIRMED_FAILURE_REVIEW')
    raise Error(404,'NOT_FOUND')
   except Error as e:return self.send(e.status,dict(error=e.code))
   except (ValueError,TypeError,KeyError):return self.send(400,dict(error='INVALID_REQUEST'))
   except Exception:return self.send(503,dict(error='LISTING_UNAVAILABLE'))
  def end_headers(self):
   if urlsplit(self.path).path.startswith(PREFIX+'/'):self.send_header('Cache-Control','no-store')
   return super().end_headers()
  do_GET=run_request
  do_POST=run_request
 return Handler
