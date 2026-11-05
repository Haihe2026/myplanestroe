from contextlib import closing
import os,sys,types,sqlite3,tempfile,unittest,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'snapshot/opt/skill-platform/ops-2026-10-28-journey'
sys.path.insert(0,str(ROOT))
report=types.ModuleType('journey.report')
class Report:
 def __init__(self,*a):pass
 def quota(self,*a):return dict(shared=0,legacy=dict(gemini=0,temu=0),available=dict(temu=1),temu_trial=1)
report.Report=Report;sys.modules['journey']=types.ModuleType('journey');sys.modules['journey.report']=report
from unified_users import Directory
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'shared.db';self.fd=Path(self.tmp.name)/'first.db';self.old=os.environ.get('FIRST_DIALOGUES_DB');os.environ['FIRST_DIALOGUES_DB']=str(self.fd)
  with closing(sqlite3.connect(self.db)) as c, c:c.executescript("CREATE TABLE users(id);CREATE TABLE ledger(user_id,created,kind);INSERT INTO users VALUES('synthetic-account'),('unknown');INSERT INTO ledger VALUES('synthetic-account',10,'account_created');")
  with closing(sqlite3.connect(self.fd)) as c, c:
   c.execute('CREATE TABLE first_dialogues(event_id,skill_id,skill_name,skill_version,channel,received_at,client_occurred_at,user_id,is_test)')
   for i in range(30):c.execute('INSERT INTO first_dialogues VALUES(?,?,?,?,?,?,?,?,?)',(f'event-{i:02}','synthetic','合成技能','1','skillhub',100+i,999999,None,0))
   c.execute('INSERT INTO first_dialogues VALUES(?,?,?,?,?,?,?,?,?)',('linked','synthetic','合成技能','1','skillhub',115,999999,'synthetic-account',0))
   c.execute('INSERT INTO first_dialogues VALUES(?,?,?,?,?,?,?,?,?)',('test','synthetic','测试','1','skillhub',999999,1,None,1))
  self.before=self.db.read_bytes(),self.fd.read_bytes()
 def tearDown(self):
  if self.old is None:os.environ.pop('FIRST_DIALOGUES_DB',None)
  else:os.environ['FIRST_DIALOGUES_DB']=self.old
  self.tmp.cleanup()
 def test_sort_and_pagination(self):
  d=Directory(self.db);a=d.listing();b=d.listing(2);rows=a['users']+b['users'];self.assertEqual(a['total'],32);self.assertEqual(len(rows),32);self.assertEqual(len({r['id'] for r in rows}),32);self.assertEqual(rows[0]['id'],'event-29');self.assertEqual(rows[-1]['id'],'unknown');stamps=[r['observed_at'] for r in rows if r['observed_at'] is not None];self.assertEqual(stamps,sorted(stamps,reverse=True));self.assertEqual(self.before,(self.db.read_bytes(),self.fd.read_bytes()))
 def test_link_collapses_anonymous(self):
  with closing(sqlite3.connect(self.fd)) as c, c:c.execute("UPDATE first_dialogues SET user_id='synthetic-account' WHERE event_id='event-29'")
  rows=Directory(self.db).listing()['users'];self.assertFalse(any(r['id']=='event-29' for r in rows));self.assertEqual(Directory(self.db).listing()['total'],31)
 def test_search(self):
  self.assertEqual(Directory(self.db).listing(query='event-29')['total'],1);self.assertEqual(Directory(self.db).listing(query='合成')['total'],30)
 def test_failure_not_silent(self):
  self.fd.unlink()
  with self.assertRaises(sqlite3.OperationalError):Directory(self.db).listing()
 def test_validation(self):
  for p,q in [(0,''),(1,'x'*65)]:
   with self.assertRaises(ValueError):Directory(self.db).listing(p,q)
 def test_auth_gate(self):
  sys.modules['overview_data']=types.SimpleNamespace(overview=lambda *a:{})
  import manual_admin
  class Parent:
   path='/ops/api/users-activity'
   def authenticated(self):return False
   def send(self,s,r,mime='',cookie=None):return s,r
  h=manual_admin.extend(lambda:Parent,self.db)()();self.assertEqual(h.do_GET()[0],401)
if __name__=='__main__':unittest.main()
