"""Actual inherited HTTP route factory; synthetic SQLite; localhost only."""
import sys,types,threading,secrets,unittest,json,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'listing-cny-0.4.0'))
import test_http as base
import metered,listing_gateway
from listing_store import sha
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from listing_store import Listing
  cls.saved_methods=(Listing.enroll,Listing.quote,Listing.me)
  import listing_trial_gate
  base.Tests.setUpClass()
  cls.db=base.Tests.db;cls.token=base.Tests.token
  with cls.db.connect() as c:c.executescript("CREATE TABLE wechat_identities(identity PRIMARY KEY,user_id UNIQUE,created);INSERT INTO wechat_identities VALUES('synthetic-wx','synthetic',1);")
  cfg={s:dict(name='合成按次服务',unit_scope='一次合成服务',enabled=True) for s in ['synthetic-alpha','synthetic-beta']}
  with patch.object(metered,'services',return_value=cfg):handler=metered.install(base.Tests.Handler,cls.db,types.SimpleNamespace(Problem=base.Problem,digest=sha))
  cls.http=base.ThreadingHTTPServer(('127.0.0.1',0),handler);cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start();cls.url='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls):
  cls.http.shutdown();cls.http.server_close();cls.thread.join();base.Tests.tearDownClass()
  from listing_store import Listing
  Listing.enroll,Listing.quote,Listing.me=cls.saved_methods
 call=base.Tests.call
 p='/platform-api/metered/v1/synthetic-alpha'
 def test_01_pricing_and_legacy_delegation(self):
  status,d=self.call(self.p+'/pricing',auth=False);self.assertEqual(status,200);self.assertEqual(d['unit_price_fen'],30);self.assertTrue(d['requires_wechat']);self.assertNotIn('platform_fields',d)
  self.assertIn('listing',self.call('/platform-api/listing/v1/pricing',auth=False)[1]['display_name'].lower())
  self.assertTrue(self.call('/platform-api/temu/health')[1]['delegated'])
 def test_02_auth_origin_idem(self):
  self.assertEqual(self.call(self.p+'/me',auth=False)[0],401)
  self.assertEqual(self.call(self.p+'/enroll',{'accepted':True},headers={'Origin':'https://evil.invalid'})[0],403)
  self.assertEqual(self.call(self.p+'/enroll',{'accepted':True},headers={'Idempotency-Key':''})[0],400)
 def test_03_entry_carries_skill_and_original_ticket(self):
  _,d=self.call(self.p+'/entry',{'accepted':True});self.assertIn('/membership/listing/?skill=synthetic-alpha#product=listing-optimizer&entry=',d['url']);self.assertNotIn(self.token,d['url'])
  ticket=d['url'].split('entry=')[1];self.assertEqual(self.db.registration_entries.pending[sha(ticket)]['secret'],self.token)
 def test_04_enrollment_and_full_http_delivery(self):
  self.assertEqual(self.call(self.p+'/enroll',{'accepted':True})[0],200)
  self.assertEqual(self.call(self.p+'/me')[1]['trial_state'],'available')
  status,q=self.call(self.p+'/quotes',{'request_id':secrets.token_hex(16)});self.assertEqual(status,200)
  status,t=self.call(self.p+'/tasks/reserve',{'quote_id':q['id'],'confirmed':True});self.assertEqual(status,200)
  evidence={'scope_hash':q['scope_hash'],'deliveries':[{'target':q['scope']['targets'][0],'content':{'result':'完整合成结果'}}]}
  self.assertEqual(self.call(self.p+'/tasks/'+t['id']+'/complete',{'evidence':evidence})[0],200)
  self.assertEqual(self.call(self.p+'/me')[1]['trial_state'],'used')
  self.call(self.p+'/enroll',{'accepted':True});self.assertEqual(self.call(self.p+'/me')[1]['trial_state'],'used')
  _,q=self.call(self.p+'/quotes',{'request_id':secrets.token_hex(16)});self.assertEqual(self.call(self.p+'/tasks/reserve',{'quote_id':q['id'],'confirmed':True})[0],402)
 def test_05_other_skill_has_independent_trial(self):
  p='/platform-api/metered/v1/synthetic-beta';self.assertEqual(self.call(p+'/enroll',{'accepted':True})[0],200);self.assertEqual(self.call(p+'/me')[1]['trial_state'],'available')
 def test_06_listing_free_trial_needs_wechat(self):
  with self.db.connect() as c:c.execute("INSERT INTO listing_accounts(account_id,created) VALUES('unbound',1)")
  from listing_store import Error
  with self.assertRaises(Error) as e:self.db.listing.me('unbound')
  self.assertEqual(e.exception.code,'WECHAT_REQUIRED')
  with self.db.connect() as c:c.execute("UPDATE listing_accounts SET trial_state='used',balance_fen=99 WHERE account_id='unbound'")
  self.assertEqual(self.db.listing.me('unbound')['balance_fen'],99)
 def test_07_body_limit(self):
  self.assertEqual(self.call(self.p+'/quotes',{'request_id':'x'*17000})[0],400)
if __name__=='__main__':unittest.main()
