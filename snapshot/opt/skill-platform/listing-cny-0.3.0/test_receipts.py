import ast,sys,types,tempfile,unittest,time,textwrap
from pathlib import Path
from test_listing import Database
from test_http import Problem

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=Database(str(Path(self.tmp.name)/'synthetic.db'))
  with self.db.connect() as c:c.executescript("""
   CREATE TABLE users(id PRIMARY KEY,balance);INSERT INTO users VALUES('synthetic',0);
   CREATE TABLE member_orders(id PRIMARY KEY,user_id,plan,amount_fen,units,status,created,product,provider,transaction_id,paid_at);
   INSERT INTO member_orders VALUES('synthetic-order','synthetic','synthetic-plan',2900,150,'reported',0,'gemini-image-assistant',NULL,NULL,NULL);
   CREATE TABLE member_grants(order_id PRIMARY KEY,user_id,remaining,expires);
   CREATE TABLE paid_wallets(user_id PRIMARY KEY,remaining);
   CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id,job_id,amount,kind,created);
   CREATE TABLE member_gifts(user_id,product,kind,created,UNIQUE(user_id,product,kind));
   CREATE TABLE settlement_receipts(transaction_id PRIMARY KEY,product,order_id,amount_fen,actor,state,created);
  """)
  source=Path(__file__).parent/'tests-fixtures/manual_payments.py'
  s=source.read_text(encoding='utf8');tree=ast.parse(s);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ManualMembership');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='confirm_manual')
  scope={'time':time,'order_permanent':lambda c,row:True};exec(textwrap.dedent(ast.get_source_segment(s,fn)),scope)
  Legacy=type('ManualMembership',(),{'confirm_manual':scope['confirm_manual']})
  self.saved=sys.modules.get('manual_payments');sys.modules['manual_payments']=types.SimpleNamespace(ManualMembership=Legacy)
  import listing_receipts;listing_receipts.install();self.api=Legacy();self.api.store=self.db;self.api.problem=Problem
 def tearDown(self):
  if self.saved:sys.modules['manual_payments']=self.saved
  else:sys.modules.pop('manual_payments',None)
  self.tmp.cleanup()
 def test_old_shared_confirmation_and_replay_preserved(self):
  self.assertTrue(self.api.confirm_manual('synthetic-order',2900,'synthetic-transaction'))
  self.assertFalse(self.api.confirm_manual('synthetic-order',2900,'synthetic-transaction'))
  with self.db.connect() as c:
   self.assertEqual(c.execute('SELECT balance FROM users').fetchone()[0],150)
   self.assertEqual(c.execute('SELECT count(*) FROM member_grants').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT state FROM settlement_receipts').fetchone()[0],'paid')
 def test_listing_receipt_cannot_credit_shared(self):
  with self.db.connect() as c:c.execute("INSERT INTO settlement_receipts VALUES('synthetic-used','listing-optimizer','listing-order',3900,'synthetic-ops','paid',0)")
  with self.assertRaises(Problem):self.api.confirm_manual('synthetic-order',2900,'synthetic-used')
  with self.db.connect() as c:self.assertEqual(c.execute('SELECT balance FROM users').fetchone()[0],0)
 def test_wrong_amount_never_reserves_receipt(self):
  with self.assertRaises(Problem):self.api.confirm_manual('synthetic-order',2901,'synthetic-wrong')
  with self.db.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM settlement_receipts').fetchone()[0],0)

if __name__=='__main__':unittest.main()
