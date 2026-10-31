"""Real local HTTP, synthetic SQLite and credentials, no outside network."""
import unittest,tempfile,types,sys,threading,json,secrets,urllib.request,urllib.error,hashlib,copy,io
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from test_listing import Database
from listing_gateway import wrap,PREFIX
from listing_ops import extend
from hosted_delivery import FIELDS
from listing_store import sha,canonical

class Problem(Exception):
 def __init__(self,status,message):self.status,self.message=status,message

class Parent(BaseHTTPRequestHandler):
 def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
  b=result if isinstance(result,bytes) else json.dumps(result,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',mime);self.end_headers();self.wfile.write(b)
 def run_request(self):return self.send(200,{'delegated':self.path})
 def authenticated(self):return self.headers.get('Cookie')=='synthetic-ops=authenticated'
 def log_message(self,*args):pass
 do_GET=run_request
 do_POST=run_request

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.db=Database(str(Path(cls.tmp.name)/'synthetic.db'))
  cls.token=secrets.token_urlsafe(32)
  with cls.db.connect() as c:
   c.executescript('CREATE TABLE users(id PRIMARY KEY,balance);CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id,amount,kind,created);CREATE TABLE trial_claims(hash PRIMARY KEY,user_id,created);CREATE TABLE sessions(hash PRIMARY KEY,user_id,expires);')
   c.execute("INSERT INTO users VALUES('synthetic',0)");c.execute('INSERT INTO trial_claims VALUES(?,?,0)',(sha(cls.token),'synthetic'))
  cls.db.user=lambda s:'synthetic' if s==cls.token else (_ for _ in ()).throw(Problem(401,'unknown'))
  cls.db.register_product=lambda *a:None
  cls.db.membership=types.SimpleNamespace(web_user=lambda s:'synthetic' if s=='synthetic-member' else (_ for _ in ()).throw(Problem(401,'unknown')))
  cls.db.device_links=types.SimpleNamespace(lookup=lambda s:None)
  cls.db.registration_entries=types.SimpleNamespace(lock=threading.RLock(),pending={})
  cls.saved=sys.modules.get('wechat_binding');sys.modules['wechat_binding']=types.SimpleNamespace(PRODUCTS=('gemini','temu','pet','trade-leads'))
  cls.Handler=wrap(Parent,cls.db,types.SimpleNamespace(Problem=Problem,digest=sha))
  cls.http=ThreadingHTTPServer(('127.0.0.1',0),cls.Handler);cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls):
  cls.http.shutdown();cls.http.server_close();cls.thread.join();cls.tmp.cleanup()
  if cls.saved:sys.modules['wechat_binding']=cls.saved
  else:sys.modules.pop('wechat_binding',None)
 def call(self,path,body=None,auth=True,headers=None):
  h={'Authorization':'Bearer '+self.token} if auth else {}
  if body is not None:h.update({'Content-Type':'application/json','Idempotency-Key':secrets.token_hex(16)})
  h.update(headers or {});req=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
  try:
   with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_01_health_auth_origin_fields(self):
  self.assertEqual(self.call(PREFIX+'/pricing',auth=False)[0],200)
  self.assertEqual(self.call(PREFIX+'/me',auth=False)[0],401)
  self.assertEqual(self.call(PREFIX+'/enroll',{'accepted':True},headers={'Origin':'https://evil.invalid'})[0],403)
  self.assertEqual(self.call(PREFIX+'/enroll',{'accepted':True,'account_id':'other'})[0],400)
  self.assertEqual(self.call(PREFIX+'/enroll',{'accepted':True})[0],200)
  self.assertEqual(self.call(PREFIX+'/me')[1]['trial_state'],'available')
 def test_02_entry_no_secret_url_and_product_scope(self):
  token=secrets.token_urlsafe(32)
  status,d=self.call(PREFIX+'/entry',{'accepted':True},auth=False,headers={'Origin':'https://myplanestore.com','X-Membership-Request':'1','Authorization':'Bearer '+token})
  self.assertEqual(status,200);self.assertIn('/auth/wechat/listing.html#product=listing-optimizer&entry=',d['url']);self.assertNotIn(token,d['url'])
  self.assertEqual(list(self.db.registration_entries.pending.values())[-1]['product'],'listing-optimizer')
 def test_03_pending_report_paid_and_complete(self):
  status,o=self.call(PREFIX+'/orders',dict(tier_id='listing_cny_39_v1',source='synthetic-listing',channel='workbuddy_skill'))
  self.assertEqual(status,200);oid=o['id']
  self.assertEqual(self.call(PREFIX+'/orders/'+oid+'/report',{})[1]['status'],'reported')
  self.assertEqual(self.call(PREFIX+'/me')[1]['balance_fen'],0)
  self.db.listing.confirm_receipt('synthetic',secrets.token_hex(16),oid,3900,'synthetic-only-transaction','synthetic-ops',True)
  self.assertEqual(self.call(PREFIX+'/orders/'+oid)[1]['status'],'paid')
  status,q=self.call(PREFIX+'/quotes',dict(sku='synthetic-sku',targets=[dict(platform='amazon',country='US'),dict(platform='temu',country='GB')]))
  self.assertEqual(status,200);self.assertEqual(q['reserve_fen'],0)
  tid=self.call(PREFIX+'/tasks/reserve',dict(quote_id=q['id'],confirmed=True))[1]['id']
  self.assertEqual(self.call(PREFIX+'/tasks/'+tid+'/complete',dict(success=True))[0],400)
  evidence=dict(scope_hash=q['scope_hash'],deliveries=[dict(target=t,content={f:['合成检查/字段'] if f in ('bullets','keywords','checks') else '合成内容' for f in FIELDS[t['platform']]}) for t in q['scope']['targets']])
  partial=copy.deepcopy(evidence);partial['deliveries'].pop()
  self.assertEqual(self.call(PREFIX+'/tasks/'+tid+'/complete',dict(evidence=partial))[0],409)
  self.assertEqual(self.call(PREFIX+'/tasks/'+tid+'/complete',dict(evidence=evidence))[0],200)
  self.assertEqual(self.call(PREFIX+'/tasks/'+tid+'/revise',dict(evidence=evidence))[1]['charged_fen'],0)
  self.assertEqual(self.call(PREFIX+'/tasks/'+tid+'/release',{})[0],409)
  self.assertEqual(self.call(PREFIX+'/me')[1]['balance_fen'],3900)
 def test_04_new_identity_no_image_credit(self):
  secret=secrets.token_urlsafe(32);self.db.register_product('listing-optimizer',secret,'synthetic-ip',True)
  with self.db.connect() as c:
   uid=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(sha(secret),)).fetchone()[0]
   self.assertEqual(c.execute('SELECT balance FROM users WHERE id=?',(uid,)).fetchone()[0],0)
   self.assertEqual(c.execute('SELECT trial_state FROM listing_accounts WHERE account_id=?',(uid,)).fetchone()[0],'available')
 def test_05_delegate_old_route(self):
  self.assertTrue(self.call('/platform-api/gemini/health')[1]['delegated'])
 def test_06_oversize_rejected(self):
  self.assertEqual(self.call(PREFIX+'/quotes',{'oversize':'x'*17000})[0],400)

if __name__=='__main__':unittest.main()
