from pathlib import Path
from urllib.parse import urlsplit
import json,hashlib,time,threading
LIMIT_LOCK=threading.Lock()
LIMITS={}
def allowed(actor,write=False):
 now=int(time.time())//60;key=(actor,write)
 with LIMIT_LOCK:
  for k in list(LIMITS):
   if LIMITS[k][0]!=now:LIMITS.pop(k,None)
  window,count=LIMITS.get(key,(now,0))
  if count>=(30 if write else 120):return False
  LIMITS[key]=(now,count+1);return True
from asset_registry import Registry,Invalid
ROOT=Path(__file__).resolve().parent
def extend(factory,path):
 def build(*args,**kwargs):
  parent=factory(*args,**kwargs);registry=Registry()
  class Handler(parent):
   def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
    if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=result.replace(b'</head>',b'<link rel="stylesheet" href="/ops/upstream-assets.css?v=0.10.52"><script defer src="/ops/upstream-assets.js?v=0.10.52"></script></head>',1)
    return super().send(status,result,mime,cookie=cookie)
   def do_GET(self):
    route=urlsplit(self.path).path
    if route in ('/ops/upstream-assets.js','/ops/upstream-assets.css'):
     name=route.rsplit('/',1)[-1];return self.send(200,(ROOT/name).read_bytes(),('application/javascript' if name.endswith('.js') else 'text/css')+'; charset=utf-8')
    if route!='/ops/api/upstream-assets':return super().do_GET()
    if not self.authenticated():return self.send(401,{'error':'请登录管理后台'})
    actor=hashlib.sha256(self.headers.get('Cookie','').encode()).hexdigest()
    if not allowed(actor):return self.send(429,{'error':'操作较频繁，请稍后重试'})
    try:return self.send(200,registry.listing())
    except Exception:return self.send(503,{'error':'资产读取暂未完成'})
   def do_POST(self):
    route=urlsplit(self.path).path
    if route not in ('/ops/api/upstream-assets/save','/ops/api/upstream-assets/archive'):return super().do_POST()
    if not self.authenticated():return self.send(401,{'error':'请登录管理后台'})
    if self.headers.get('Origin')!='https://myplanestore.com' or self.headers.get('X-Membership-Request')!='1':return self.send(403,{'error':'请从本站管理后台操作'})
    try:
     size=int(self.headers.get('Content-Length','0'))
     if not 0<size<=24576 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Invalid('请求格式无效')
     body=json.loads(self.rfile.read(size))
     if not isinstance(body,dict):raise Invalid('请求格式无效')
     actor='admin:'+hashlib.sha256(self.headers.get('Cookie','').encode()).hexdigest()[:16]
     if not allowed(actor,True):return self.send(429,{'error':'操作较频繁，请稍后重试'})
     if route.endswith('/archive'):result=registry.archive(body.get('id'),body.get('revision'),actor)
     else:result=registry.save(body,actor)
     return self.send(200,result)
    except Invalid as e:return self.send(400,{'error':str(e)})
    except (ValueError,TypeError):return self.send(400,{'error':'资产参数无效，请核对表单'})
    except Exception:return self.send(503,{'error':'资产操作未完成，密钥未回显，请刷新核对'})
  return Handler
 return build
