from pathlib import Path
from contextlib import contextmanager
import sys,sqlite3,tempfile,unittest,uuid
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'listing-cny-0.4.0'))
from metered import Service,bound
from listing_store import Error
class DB:
 def __init__(self,p):self.p=p
 @contextmanager
 def connect(self):
  c=sqlite3.connect(self.p);c.row_factory=sqlite3.Row
  try:
   with c:yield c
  finally:c.close()
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=DB(str(Path(self.tmp.name)/'synthetic.sqlite3'))
  with self.db.connect() as c:
   c.executescript('CREATE TABLE wechat_identities(identity TEXT PRIMARY KEY,user_id TEXT UNIQUE,created INTEGER);CREATE TABLE users(id TEXT PRIMARY KEY,balance INTEGER);CREATE TABLE paid_wallets(user_id TEXT PRIMARY KEY,remaining INTEGER);INSERT INTO wechat_identities VALUES(\'synthetic-wx\',\'u\',1);INSERT INTO users VALUES(\'u\',77);INSERT INTO paid_wallets VALUES(\'u\',77);')
  cfg=dict(name='合成技能A',unit_scope='一次合成服务',enabled=True)
  self.a=Service(self.db,'synthetic-alpha',cfg);self.b=Service(self.db,'synthetic-beta',{**cfg,'name':'合成技能B'})
 def tearDown(self):self.tmp.cleanup()
 def key(self):return uuid.uuid4().hex
 def enroll(self,a=None,uid='u'):return (a or self.a).enroll(uid,self.key(),True)
 def quote(self,a=None):return (a or self.a).quote('u',self.key(),{'request_id':self.key()})
 def finish(self,a=None):
  a=a or self.a;q=self.quote(a);t=a.reserve('u',self.key(),q['id'],True);a.complete('u',self.key(),t['id'],{'scope_hash':q['scope_hash'],'deliveries':[{'target':q['scope']['targets'][0],'content':{'result':'合成完整交付结果'}}]});return q,t
 def test_wechat_required(self):
  with self.assertRaises(Error) as e:self.enroll(uid='anonymous')
  self.assertEqual(e.exception.code,'WECHAT_REQUIRED')
 def test_get_does_not_create_trial(self):
  with self.assertRaises(Error):self.a.me('u')
  with self.a.store.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM listing_accounts').fetchone()[0],0)
 def test_enroll_once(self):
  self.enroll();self.enroll();self.assertEqual(self.a.me('u')['trial_state'],'available')
 def test_trial_success_once(self):
  self.enroll();self.finish();self.assertEqual(self.a.me('u')['trial_state'],'used')
 def test_recover_does_not_reissue(self):
  self.enroll();self.finish();self.enroll();self.assertEqual(self.a.me('u')['trial_state'],'used')
 def test_one_trial_per_skill(self):
  self.enroll();self.enroll(self.b);self.finish();self.assertEqual(self.b.me('u')['trial_state'],'available')
 def test_unfinished_trial_blocks_second_reserve(self):
  self.enroll();q=self.quote();self.a.reserve('u',self.key(),q['id'],True)
  with self.assertRaises(Error):self.quote()
 def test_paid_402(self):
  self.enroll();self.finish();q=self.quote()
  with self.assertRaises(Error) as e:self.a.reserve('u',self.key(),q['id'],True)
  self.assertEqual(e.exception.status,402)
 def test_customer_report_not_receipt(self):
  self.enroll();o=self.a.order('u',self.key(),'metered-39','website','website');self.a.report('u',self.key(),o['id']);self.assertEqual(self.a.me('u')['balance_fen'],0)
 def test_confirm_and_charge_30(self):
  self.enroll();self.finish();o=self.a.order('u',self.key(),'metered-39','website','website');self.a.report('u',self.key(),o['id']);self.a.confirm_receipt('u',self.key(),o['id'],3900,'SYNTHETIC-TX-001','synthetic-operator',True);self.finish();self.assertEqual(self.a.me('u')['balance_fen'],3870)
 def test_receipt_not_reusable_between_skills(self):
  for a in [self.a,self.b]:self.enroll(a)
  orders=[]
  for a in [self.a,self.b]:
   o=a.order('u',self.key(),'metered-39','website','website');a.report('u',self.key(),o['id']);orders.append(o)
  self.a.confirm_receipt('u',self.key(),orders[0]['id'],3900,'SYNTHETIC-TX-002','operator',True)
  with self.assertRaises(Error):self.b.confirm_receipt('u',self.key(),orders[1]['id'],3900,'SYNTHETIC-TX-002','operator',True)
 def test_wrong_amount(self):
  self.enroll();o=self.a.order('u',self.key(),'metered-39','website','website');self.a.report('u',self.key(),o['id'])
  with self.assertRaises(Error):self.a.confirm_receipt('u',self.key(),o['id'],2900,'SYNTHETIC-TX-003','operator',True)
 def test_no_converting_image_quota(self):
  self.enroll();self.finish()
  with self.db.connect() as c:self.assertEqual(c.execute('SELECT balance FROM users').fetchone()[0],77);self.assertEqual(c.execute('SELECT remaining FROM paid_wallets').fetchone()[0],77)
 def test_wrong_pricing_rejected(self):
  with self.assertRaises(ValueError):Service(self.db,'synthetic-bad',dict(name='错误价格',unit_scope='一次',enabled=True,unit_price_fen=1))
 def test_idempotent_task_complete(self):
  self.enroll();q,t=self.finish();r=self.a.complete('u',self.key(),t['id'],{})
  self.assertTrue(r['artifact_id'].startswith('metered-'));self.assertEqual(self.a.me('u')['trial_state'],'used')
 def test_invalid_delivery_cannot_consume(self):
  self.enroll();q=self.quote();t=self.a.reserve('u',self.key(),q['id'],True)
  with self.assertRaises(Error):self.a.complete('u',self.key(),t['id'],{'success':True})
  self.assertEqual(self.a.me('u')['trial_state'],'held')
 def test_unknown_keeps_hold(self):
  self.enroll();q=self.quote();t=self.a.reserve('u',self.key(),q['id'],True);self.a.release_confirmed_failure('u',self.key(),t['id'],'unknown');self.assertEqual(self.a.me('u')['trial_state'],'held')
 def test_confirmed_failure_releases(self):
  self.enroll();q=self.quote();t=self.a.reserve('u',self.key(),q['id'],True);self.a.release_confirmed_failure('u',self.key(),t['id'],'confirmed_failure');self.assertEqual(self.a.me('u')['trial_state'],'available')
if __name__=='__main__':unittest.main()
