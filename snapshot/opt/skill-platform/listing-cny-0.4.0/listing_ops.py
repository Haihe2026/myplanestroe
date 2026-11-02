import json,hashlib,re
from pathlib import Path
from urllib.parse import urlsplit
from listing_store import Listing,Error
from hosted_delivery import HostedDelivery
from listing_gateway import rate,ORIGINS

def extend(factory,path):
 def build(*args,**kwargs):
  parent=factory(*args,**kwargs)
  from pet_ops import Database
  db=Database(path);api=Listing(db,verifier=HostedDelivery())
  class Handler(parent):
   def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
    if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=result.replace(b'</head>',b'<script defer src="/ops/listing-admin.js?v=20261031"></script></head>',1)
    return super().send(status,result,mime,cookie=cookie)
   def do_GET(self):
    route=urlsplit(self.path).path
    if route=='/ops/listing-admin.js':return self.send(200,Path(__file__).with_name('listing-admin.js').read_bytes(),'application/javascript; charset=utf-8')
    if route!='/ops/api/listing/summary':return super().do_GET()
    if not self.authenticated():return self.send(401,dict(error='OPS_LOGIN_REQUIRED'))
    with db.connect() as c:
     rows=[dict(r) for r in c.execute('SELECT * FROM listing_orders ORDER BY created DESC LIMIT 200')]
     tasks=[dict(r) for r in c.execute('SELECT id,account_id,state,funding,amount_fen,created FROM listing_tasks ORDER BY created DESC LIMIT 200')]
    return self.send(200,dict(orders=rows,tasks=tasks))
   def do_POST(self):
    route=urlsplit(self.path).path
    if route not in ('/ops/api/listing/settle','/ops/api/listing/release'):return super().do_POST()
    if not self.authenticated():return self.send(401,dict(error='OPS_LOGIN_REQUIRED'))
    if self.headers.get('Origin') not in ORIGINS:return self.send(403,dict(error='ORIGIN_NOT_ALLOWED'))
    try:
     rate('listing-ops:'+self.client_address[0],30)
     n=int(self.headers.get('Content-Length','0'))
     if not 0<n<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Error(400,'INVALID_JSON')
     b=json.loads(self.rfile.read(n));key=self.headers.get('Idempotency-Key','')
     actor='operator:'+hashlib.sha256(self.headers.get('Cookie','').encode()).hexdigest()[:16]
     if route.endswith('/release'):
      if b.get('verified') is not True:raise Error(400,'VERIFICATION_REQUIRED')
      with db.connect() as c:r=c.execute('SELECT account_id FROM listing_tasks WHERE id=?',(b.get('task_id'),)).fetchone()
      if not r:raise Error(404,'NOT_FOUND')
      return self.send(200,api.release_confirmed_failure(r[0],key,b['task_id'],'confirmed_failure'))
     with db.connect() as c:r=c.execute('SELECT account_id FROM listing_orders WHERE id=?',(b.get('order_id'),)).fetchone()
     if not r:raise Error(404,'NOT_FOUND')
     return self.send(200,api.confirm_receipt(r[0],key,b['order_id'],b.get('amount_fen'),b.get('transaction_id'),actor,b.get('verified')))
    except Error as e:return self.send(e.status,dict(error=e.code))
    except (ValueError,TypeError,KeyError):return self.send(400,dict(error='INVALID_REQUEST'))
    except Exception:return self.send(503,dict(error='CONFIRMATION_UNAVAILABLE'))
  return Handler
 return build
