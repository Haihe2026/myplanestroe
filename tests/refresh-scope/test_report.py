from pathlib import Path
from contextlib import contextmanager,closing
import sqlite3,tempfile,types,sys,importlib.util,unittest
from unittest.mock import patch
@contextmanager
def database(path,readonly=False):
 c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
 try:yield c
 finally:c.close()
sys.modules['journey']=types.ModuleType('journey');store=types.ModuleType('journey.store');store.database=database;store.identifier=lambda x:True;store.SOURCES=set();sys.modules['journey.store']=store
spec=importlib.util.spec_from_file_location('journey.report',Path(__file__).resolve().parents[2]/'snapshot/opt/skill-platform/member-0.10.16/journey/report.py');mod=importlib.util.module_from_spec(spec);sys.modules['journey.report']=mod;spec.loader.exec_module(mod)
class View(mod.Report):
 def user(self,uid):return dict(id=uid,first_observed_source='unknown',source_evidence='not_collected',last_active={'a-old':11,'b-active':40}.get(uid),quota={},key={},test_account=None)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();r=Path(self.tmp.name);self.shared=r/'shared.db';self.journey=r/'journey.db'
  with closing(sqlite3.connect(self.shared)) as c,c:c.executescript("CREATE TABLE users(id);CREATE TABLE ledger(user_id,created,kind);INSERT INTO users VALUES('a-old'),('z-new'),('b-active'),('no-clock');INSERT INTO ledger VALUES('a-old',10,'account_created'),('z-new',30,'account_created'),('b-active',10,'account_created');")
  with closing(sqlite3.connect(self.journey)) as c,c:c.executescript("CREATE TABLE journey_accounts(user_id,first_seen,last_seen);INSERT INTO journey_accounts VALUES('a-old',10,11),('b-active',10,40);")
  self.v=View(types.SimpleNamespace(path=self.journey),self.shared)
 def tearDown(self):self.tmp.cleanup()
 def test_latest_before_alphabetical_and_unknown_last(self):self.assertEqual([x['id'] for x in self.v.users()['users']],['b-active','z-new','a-old','no-clock'])
 def test_registration_is_not_authentication(self):
  a=next(x for x in self.v.users()['users'] if x['id']=='z-new');self.assertEqual(a['registered_at'],30);self.assertIsNone(a['last_active'])
 def test_actual_auth_time_preserved(self):self.assertEqual(next(x for x in self.v.users()['users'] if x['id']=='a-old')['last_active'],11)
 def test_fresh_read_time(self):
  with patch.object(mod.time,'time',return_value=1000):a=self.v.users()
  with patch.object(mod.time,'time',return_value=1001):b=self.v.users()
  self.assertEqual((a['generated_at'],b['generated_at']),(1000,1001));self.assertEqual(a['users'],b['users'])
 def test_readonly(self):
  before=[p.read_bytes() for p in [self.shared,self.journey]];self.v.users();self.assertEqual(before,[p.read_bytes() for p in [self.shared,self.journey]])
 def test_search_and_injection(self):
  self.assertEqual(self.v.users(query='z-new')['total'],1);self.assertEqual(self.v.users(query="' OR 1=1 --")['total'],0)
 def test_pagination_stable(self):
  with closing(sqlite3.connect(self.shared)) as c,c:
   for i in range(31):c.execute('INSERT INTO users VALUES(?)',('extra-'+str(i),))
  a=self.v.users();b=self.v.users(2);self.assertEqual(len(a['users'])+len(b['users']),35);self.assertEqual(len({x['id'] for x in a['users']+b['users']}),35)
 def test_bad_query_rejected(self):
  with self.assertRaises(ValueError):self.v.users(0)
if __name__=='__main__':unittest.main()
