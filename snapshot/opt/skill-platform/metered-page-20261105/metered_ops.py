from pathlib import Path
from urllib.parse import urlsplit
import json,hashlib
from metered import Service,services
from listing_store import Error
from listing_gateway import rate
ROOT=Path(__file__).resolve().parent
def wrap(parent):
 from pet_ops import Database
 db=Database('/var/lib/skill-platform/shared.db')
 apis={sid:Service(db,sid,cfg) for sid,cfg in services().items() if cfg.get('bridge')!='listing'}
 class Handler(parent):
  def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
   if status==200 and isinstance(result,dict) and urlsplit(self.path).path=='/ops/api/listing/summary':
    result={**result,'orders':list(result.get('orders',[])),'tasks':list(result.get('tasks',[]))}
    for sid,api in apis.items():
     with api.store.connect() as c:
      result['orders'] += [{**dict(r),'service_id':sid} for r in c.execute('SELECT * FROM listing_orders ORDER BY created DESC LIMIT 200')]
      result['tasks'] += [{**dict(r),'service_id':sid} for r in c.execute('SELECT id,account_id,state,funding,amount_fen,created FROM listing_tasks ORDER BY created DESC LIMIT 200')]
    result['orders'].sort(key=lambda x:x['created'],reverse=True);result['tasks'].sort(key=lambda x:x['created'],reverse=True)
   return super().send(status,result,mime,cookie=cookie)
  def do_GET(self):
   if urlsplit(self.path).path=='/ops/listing-admin.js':return self.send(200,(ROOT/'listing-admin.js').read_bytes(),'application/javascript; charset=utf-8')
   return super().do_GET()
  def do_POST(self):
   path=urlsplit(self.path).path
   if path not in ('/ops/api/metered/settle','/ops/api/metered/release'):return super().do_POST()
   if not self.authenticated():return self.send(401,{'error':'OPS_LOGIN_REQUIRED'})
   if self.headers.get('Origin')!='https://myplanestore.com' or self.headers.get('X-Membership-Request')!='1':return self.send(403,{'error':'SITE_REQUEST_REQUIRED'})
   try:
    rate('metered-ops:'+self.client_address[0],30)
    if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Error(400,'INVALID_JSON')
    n=int(self.headers.get('Content-Length','0'))
    if not 0<n<=4096:raise Error(400,'INVALID_JSON')
    b=json.loads(self.rfile.read(n))
    if not isinstance(b,dict):raise Error(400,'INVALID_JSON')
    api=apis.get(b.get('service_id'))
    if not api:raise Error(404,'SERVICE_NOT_CONFIGURED')
    if b.get('verified') is not True:raise Error(400,'VERIFICATION_REQUIRED')
    key=self.headers.get('Idempotency-Key','');table='listing_orders' if path.endswith('/settle') else 'listing_tasks';rid=b.get('order_id') if path.endswith('/settle') else b.get('task_id')
    with api.store.connect() as c:r=c.execute('SELECT account_id FROM '+table+' WHERE id=?',(rid,)).fetchone()
    if not r:raise Error(404,'NOT_FOUND')
    actor='operator:'+hashlib.sha256(self.headers.get('Cookie','').encode()).hexdigest()[:16]
    value=api.confirm_receipt(r[0],key,rid,b.get('amount_fen'),b.get('transaction_id'),actor,True) if path.endswith('/settle') else api.release_confirmed_failure(r[0],key,rid,'confirmed_failure')
    return self.send(200,value)
   except Error as e:return self.send(e.status,{'error':e.code})
   except Exception:return self.send(503,{'error':'METERED_OPERATION_UNAVAILABLE'})
 return Handler
