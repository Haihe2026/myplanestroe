"""Read-only budget check and safe authenticated video transport; no model fallback."""
import json,time,re,threading,ipaddress,socket,http.client,ssl
from decimal import Decimal
from urllib.request import Request,build_opener
from urllib.error import HTTPError
from urllib.parse import urlsplit,urljoin
from grok_provider import Provider as Base,Fault,ORIGIN,NoRedirect,cost

class PinnedHTTPS(http.client.HTTPSConnection):
 def __init__(self,host,address):super().__init__(host,timeout=30,context=ssl.create_default_context());self.address=address
 def connect(self):
  sock=socket.create_connection((self.address,443),timeout=self.timeout)
  self.sock=self._context.wrap_socket(sock,server_hostname=self.host)

class Provider(Base):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.cached=None;self.checked=0;self.budget_lock=threading.Lock()
 def budget(self):
  with self.budget_lock:
   if time.monotonic()-self.checked<20 and self.cached is not None:return self.cached
   if not super().ready:raise Fault('PROVIDER_NOT_CONFIGURED')
   try:
    req=Request(ORIGIN+'/v1/balance',headers={'Authorization':'Bearer '+self.key_file.read_text().strip()})
    with build_opener(NoRedirect()).open(req,timeout=3) as r:o=json.loads(r.read(65536))
    if o.get('currency')!='USD':raise ValueError()
    amount=Decimal(str(o['available']))
    if not amount.is_finite() or amount<0:raise ValueError()
    self.cached=amount;self.checked=time.monotonic();return amount
   except Exception:raise Fault('PROVIDER_BUDGET_UNAVAILABLE') from None
 @property
 def ready(self):
  if self.requester:return True
  try:return self.budget()>=Decimal('0.0672')
  except Fault:return False
 def can_afford(self,spec):
  if self.requester:return True
  return self.budget()>=Decimal(cost(spec))
 def request(self,method,path,body=None,idem=None,binary=False):
  if self.requester:return self.requester(method,path,body,idem,binary)
  if binary:return self.download(path)
  if method!='POST':return Base(self.key_file).request(method,path,body,idem,binary)
  if path!='/v1/videos' or not super().ready:raise Fault('PROVIDER_NOT_CONFIGURED')
  h={'Authorization':'Bearer '+self.key_file.read_text().strip(),'Content-Type':'application/json','Idempotency-Key':idem}
  try:
   req=Request(ORIGIN+path,method='POST',headers=h,data=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode())
   with build_opener(NoRedirect()).open(req,timeout=30) as r:o=json.loads(r.read(1024*1024))
   if not isinstance(o,dict):raise Fault('INVALID_RESPONSE')
   self.checked=0
   return o
  except HTTPError as e:
   if e.code==402:
    try:code=json.loads(e.read(65536)).get('code')
    except Exception:code=None
    if code in ('insufficient_user_quota','insufficient_key_quota'):
     self.checked=0;raise Fault('PROVIDER_BALANCE_INSUFFICIENT') from None
   raise Fault('UPSTREAM_UNCERTAIN') from None
  except Fault:raise
  except Exception:raise Fault('UPSTREAM_UNCERTAIN') from None
 def download(self,path):
  if not re.fullmatch(r'/v1/videos/[A-Za-z0-9_-]{1,180}/content',path):raise Fault('INVALID_PATH')
  url=ORIGIN+path
  for hop in range(4):
   u=urlsplit(url)
   if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):raise Fault('INVALID_VIDEO_LOCATION')
   try:addresses=list(dict.fromkeys(x[4][0] for x in socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)))
   except Exception:raise Fault('VIDEO_UNAVAILABLE') from None
   if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses):raise Fault('INVALID_VIDEO_LOCATION')
   conn=PinnedHTTPS(u.hostname,addresses[0])
   try:
    # Bearer is only sent to the configured origin, never a redirected CDN.
    headers={'Authorization':'Bearer '+self.key_file.read_text().strip()} if u.netloc==urlsplit(ORIGIN).netloc else {}
    conn.request('GET',u.path+('?'+u.query if u.query else ''),headers=headers);r=conn.getresponse()
    if r.status in (301,302,303,307,308):
     target=r.getheader('Location')
     if not target:raise Fault('VIDEO_UNAVAILABLE')
     url=urljoin(url,target);continue
    if r.status!=200:raise Fault('VIDEO_UNAVAILABLE')
    raw=r.read(128*1024*1024+1)
    if len(raw)>128*1024*1024 or len(raw)<12 or raw[4:8]!=b'ftyp':raise Fault('INVALID_VIDEO')
    return raw
   except Fault:raise
   except Exception:raise Fault('VIDEO_UNAVAILABLE') from None
   finally:conn.close()
  raise Fault('VIDEO_UNAVAILABLE')
