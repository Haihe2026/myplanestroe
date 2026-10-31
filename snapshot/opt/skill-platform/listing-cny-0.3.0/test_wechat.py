"""Existing WeChat/device-link code with synthetic identity approvals, zero OAuth calls."""
import unittest,sys,types,importlib.util,tempfile,threading,json,secrets,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from http.cookies import SimpleCookie
from test_http import Parent,Problem
from test_listing import Database
from listing_store import sha
from listing_gateway import wrap,PREFIX

ROOT=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.db=Database(str(Path(cls.tmp.name)/'synthetic.db'))
  with cls.db.connect() as c:
   c.executescript("CREATE TABLE users(id PRIMARY KEY,balance);CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id,amount,kind,created);CREATE TABLE trial_claims(hash PRIMARY KEY,user_id,created);CREATE TABLE sessions(hash PRIMARY KEY,user_id,expires);INSERT INTO users VALUES('synthetic-original',0);")
  cls.server=types.SimpleNamespace(Problem=Problem,digest=sha)
  def user(secret):
   with cls.db.connect() as c:r=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(sha(secret),)).fetchone()
   if not r:raise Problem(401,'unknown')
   return r[0]
  cls.db.user=user;cls.db.register_product=lambda *a:None
  cls.db.registration_entries=types.SimpleNamespace(lock=threading.RLock(),pending={},prepare=lambda *a:{'status':'registration'})
  cls.web={};cls.tickets={};cls.existing=secrets.token_urlsafe(32);cls.web[cls.existing]='synthetic-original'
  def handoff(uid):
   t=secrets.token_urlsafe(32);cls.tickets[t]=uid;return {'url':'https://myplanestore.com/membership/#ticket='+t}
  def redeem(t):
   uid=cls.tickets.pop(t);v=secrets.token_urlsafe(32);cls.web[v]=uid;return v
  def web_user(token):
   if token not in cls.web:raise Problem(401,'unknown')
   return cls.web[token]
  cls.db.membership=types.SimpleNamespace(handoff=handoff,redeem=redeem,web_user=web_user)
  device=load('synthetic_device_module',ROOT/'tests-fixtures/account_link.py');cls.db.device_links=device.DeviceLinks(cls.db,cls.server)
  cls.saved=sys.modules.get('wechat_binding');wechat=load('synthetic_wechat_module',ROOT/'tests-fixtures/wechat_binding.py');cls.wechat=wechat
  wechat.config=lambda:dict(appid='synthetic-appid')
  sys.modules['wechat_binding']=wechat
  parent=wechat.handler(Parent,cls.db,cls.server);handler=wrap(parent,cls.db,cls.server)
  with cls.db.connect() as c:c.execute('INSERT INTO wechat_identities VALUES(?,?,0)',('synthetic-known-wechat','synthetic-original'))
  cls.http=ThreadingHTTPServer(('127.0.0.1',0),handler);cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls):
  cls.http.shutdown();cls.http.server_close();cls.thread.join();cls.tmp.cleanup()
  if cls.saved:sys.modules['wechat_binding']=cls.saved
  else:sys.modules.pop('wechat_binding',None)
 def post(self,path,body,secret=None,cookie=None):
  h={'Origin':'https://myplanestore.com','Content-Type':'application/json','X-Membership-Request':'1','Idempotency-Key':secrets.token_hex(16)}
  if secret:h['Authorization']='Bearer '+secret
  if cookie:h['Cookie']=cookie
  req=urllib.request.Request(self.url+path,data=json.dumps(body).encode(),headers=h)
  try:
   with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.load(r),r.headers
  except urllib.error.HTTPError as e:return e.code,json.load(e),e.headers
 def test_existing_bound_account_reused_without_scan(self):
  secret=secrets.token_urlsafe(32);status,entry,_=self.post(PREFIX+'/entry',{'accepted':True},secret)
  self.assertEqual(status,200);ticket=parse_qs(urlsplit(entry['url']).fragment)['entry'][0]
  status,result,headers=self.post('/platform-api/wechat/start',dict(product='listing-optimizer',entry=ticket,accepted=True),cookie='platform_member='+self.existing)
  self.assertEqual(status,200);self.assertEqual(result['url'],'/membership/listing/');self.assertEqual(result['status'],'linked');self.assertEqual(self.db.user(secret),'synthetic-original')
  self.assertTrue(any('HttpOnly; Secure; SameSite=Strict' in v for v in headers.get_all('Set-Cookie')))
 def test_new_wechat_identity_creates_listing_only(self):
  secret=secrets.token_urlsafe(32);_,entry,_=self.post(PREFIX+'/entry',{'accepted':True},secret);ticket=parse_qs(urlsplit(entry['url']).fragment)['entry'][0]
  status,start,_=self.post('/platform-api/wechat/start',dict(product='listing-optimizer',entry=ticket,accepted=True))
  self.assertEqual(status,200);self.assertIn('state',start)
  # Synthetic substitute for the user's WeChat approval; no real exchange request.
  with self.db.connect() as c:c.execute("UPDATE wechat_login_states SET identity='synthetic-new-wechat',status='approved' WHERE hash=?",(sha(start['state']),))
  status,result,_=self.post('/platform-api/wechat/finish',dict(state=start['state'],verifier=start['verifier']))
  self.assertEqual(status,200);self.assertEqual(result['url'],'/membership/listing/')
  uid=self.db.user(secret)
  with self.db.connect() as c:
   self.assertEqual(c.execute('SELECT balance FROM users WHERE id=?',(uid,)).fetchone()[0],0)
   self.assertEqual(c.execute('SELECT trial_state FROM listing_accounts WHERE account_id=?',(uid,)).fetchone()[0],'available')
 def test_old_product_enums_retained(self):
  self.assertTrue({'gemini','temu','pet','trade-leads','listing-optimizer'}<=set(self.wechat.PRODUCTS))

if __name__=='__main__':unittest.main()
