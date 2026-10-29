import json,re,time,threading,ipaddress
from urllib.parse import urlsplit
from dialogue_store import Dialogues,Invalid,Conflict
PREFIX='/platform-api/telemetry/v1'
LOCK=threading.Lock();RATES={}
def allowed(key,limit):
 window=int(time.time())//60
 with LOCK:
  for k in list(RATES):
   if RATES[k][0]!=window:RATES.pop(k,None)
  old,count=RATES.get(key,(window,0))
  if count>=limit:return False
  RATES[key]=(window,count+1);return True
def install(parent,store):
 events=Dialogues()
 class Handler(parent):
  def log_message(self,*a):
   if urlsplit(self.path).path.startswith(PREFIX+'/'):return
   return super().log_message(*a)
  def run_request(self):
   path=urlsplit(self.path).path
   if not path.startswith(PREFIX+'/'):return super().run_request()
   if path==PREFIX+'/health' and self.command=='GET':return self.send(200,dict(status='ok',version='0.10.58',event='first_dialogue'))
   if path not in (PREFIX+'/first-dialogue',PREFIX+'/first-dialogue/link'):return self.send(404,dict(error='not_found'))
   if self.command!='POST':return self.send(405,dict(error='method_not_allowed'))
   try:
    self.connection.settimeout(5)
    origin=self.headers.get('Origin')
    if origin and origin!='https://myplanestore.com':return self.send(403,dict(error='origin_not_allowed'))
    ip=self.client_address[0]
    if ip in ('127.0.0.1','::1'):
     try:ip=str(ipaddress.ip_address(self.headers.get('X-Real-IP',ip)))
     except ValueError:pass
    if not allowed(events.digest('rate:'+ip),300):return self.send(429,dict(error='rate_limited'))
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(400,dict(error='invalid_json_request'))
    body=json.loads(self.rfile.read(size))
    if not isinstance(body,dict):raise Invalid('请提交元数据对象')
    if path.endswith('/link'):
     if set(body)-{'event_id','receipt','product'}:raise Invalid('关联字段无效')
     product=body.get('product');authorization=self.headers.get('Authorization','')
     if product not in ('gemini','temu','pet','trade-leads') or not re.fullmatch(r'Bearer [A-Za-z0-9_-]{43}',authorization):return self.send(401,dict(error='account_auth_required'))
     try:
      uid=store.trade.token_user(authorization[7:],self.headers.get('X-Device-Id','')) if product=='trade-leads' else store.user(authorization[7:])
      if not uid:raise ValueError()
     except Exception:return self.send(401,dict(error='invalid_account_credential'))
     if not allowed(events.digest('account:'+uid),60):return self.send(429,dict(error='rate_limited'))
     return self.send(200,events.link(body.get('event_id'),body.get('receipt'),uid))
    if not allowed(events.digest('client:'+str(body.get('installation_id',''))),10):return self.send(429,dict(error='rate_limited'))
    return self.send(200,events.record(body))
   except Conflict as error:return self.send(409,dict(error=str(error)))
   except Invalid as error:return self.send(400,dict(error=str(error)))
   except (ValueError,UnicodeError,TypeError):return self.send(400,dict(error='invalid_metadata'))
   except Exception:return self.send(503,dict(error='event_recording_unavailable'))
 return Handler
