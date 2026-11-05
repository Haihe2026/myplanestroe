"""Observe existing transport results without changing requests, retries, or billing."""
import urllib.request,urllib.parse,json,uuid,re,threading,http.client
from cost_store import Costs
KNOWN={};LOCK=threading.Lock()
def safe_text(x):return x if isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,180}',x) else None
def observe(url,method,body,headers,status,data):
 try:
  path=urllib.parse.urlsplit(url).path
  if not path.startswith(('/v1/images','/v1/videos','/v1/chat/completions','/v1/responses','/v1/audio','/v1/3d')):return
  model=safe_text(body.get('model')) if isinstance(body,dict) else None
  response=data if isinstance(data,dict) else {}
  rid=safe_text(response.get('task_id') or response.get('id'))
  part=path.rstrip('/').split('/')[-1]
  if method=='GET' and part not in ('videos','images','content'):rid=rid or safe_text(part)
  if rid:
   prior=Costs().lookup('task:'+rid)
   with LOCK:
    model=model or KNOWN.get(rid) or (prior or {}).get('model')
    if model:KNOWN[rid]=model
  if not model:return
  state=response.get('status')
  if status>=400:out='failed' if status in (400,401,402,403,404,422) else 'unknown'
  elif state in ('completed','succeeded','success'):out='succeeded'
  elif state in ('failed','cancelled','canceled'):out='failed'
  elif state in ('queued','pending','in_progress','processing','running'):out='pending'
  elif 'choices' in response or ('data' in response and isinstance(response['data'],list)):out='succeeded'
  else:out='unknown'
  idem=next((v for k,v in headers.items() if k.lower()=='idempotency-key'),None)
  key='task:'+rid if rid else 'request:'+(safe_text(idem) or uuid.uuid4().hex)
  usage=response.get('usage',{});inp=usage.get('prompt_tokens',usage.get('input_tokens'));output=usage.get('completion_tokens',usage.get('output_tokens'))
  if type(inp)is not int or inp<0:inp=None
  if type(output)is not int or output<0:output=None
  quantity=body.get('duration',body.get('seconds',body.get('n',1))) if isinstance(body,dict) else 1
  params={k:body[k] for k in ('resolution','size','quality') if k in body} if isinstance(body,dict) else {}
  if method=='GET' and rid and prior:
   quantity=prior['quantity'];params=json.loads(prior['params'] or '{}')
  Costs().record(key,model,out,quantity,inp,output,params)
 except Exception:pass # Cost telemetry never changes service delivery or customer charges.
class Response:
 def __init__(self,response,info):self.response=response;self.info=info;self.done=False
 def __getattr__(self,name):return getattr(self.response,name)
 def __enter__(self):return self
 def __exit__(self,*args):return self.response.__exit__(*args)
 def read(self,*args,**kwargs):
  raw=self.response.read(*args,**kwargs)
  if not self.done:
   self.done=True
   try:obj=json.loads(raw) if len(raw)<=32*1024*1024 else None
   except Exception:obj=None
   observe(*self.info,getattr(self.response,'status',200),obj)
  return raw
def install():
 # Both current image adapters (direct HTTPSConnection) and video adapters
 # (urllib) pass through this boundary. Do not patch both and double count.
 cls=http.client.HTTPConnection
 if getattr(cls,'_mps_cost_observer',False):return
 putrequest,putheader,endheaders,getresponse=cls.putrequest,cls.putheader,cls.endheaders,cls.getresponse
 def start(self,method,url,*a,**kw):
  host=str(self.host).split(':')[0]
  path=urllib.parse.urlsplit(url).path
  self._mps_info=None
  if host in ('www.aisplice.store','aisplice.store') and method in ('GET','POST') and path not in ('/v1/balance','/v1/models') and not path.endswith('/content'):
   self._mps_info=['https://'+host+url,method,{},{}]
  return putrequest(self,method,url,*a,**kw)
 def header(self,name,*values):
  info=getattr(self,'_mps_info',None)
  if info is not None and name.lower()=='idempotency-key':info[3]['Idempotency-Key']=str(values[0]) if values else ''
  return putheader(self,name,*values)
 def finish(self,message_body=None,*a,**kw):
  info=getattr(self,'_mps_info',None)
  if info is not None and isinstance(message_body,(bytes,bytearray,str)) and len(message_body)<=32*1024*1024:
   try:info[2]=json.loads(message_body)
   except Exception:pass
  return endheaders(self,message_body,*a,**kw)
 def receive(self,*a,**kw):
  info=getattr(self,'_mps_info',None)
  try:
   result=getresponse(self,*a,**kw)
   return Response(result,info) if info is not None else result
  except Exception:
   if info is not None:observe(*info,599,None)
   raise
 cls.putrequest=start;cls.putheader=header;cls.endheaders=finish;cls.getresponse=receive;cls._mps_cost_observer=True
