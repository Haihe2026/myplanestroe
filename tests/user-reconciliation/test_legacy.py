import os,sys,types,sqlite3,tempfile,unittest,json
from pathlib import Path
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'snapshot/opt/skill-platform/ops-2026-10-28-journey'))
report=types.ModuleType('journey.report')
class Report:
 def __init__(self,*args):pass
 def quota(self,*args):return dict(shared=0,legacy={'gemini':0,'temu':0},available={'gemini':0,'temu':1},temu_trial=1)
report.Report=Report;sys.modules['journey']=types.ModuleType('journey');sys.modules['journey.report']=report
sys.modules['overview_data']=types.SimpleNamespace(overview=lambda *args:{})
from unified_users import Directory
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();r=Path(self.tmp.name);self.shared=r/'shared.db';self.fd=r/'first.db';self.paths={x:r/(x+'.db') for x in ['gemini','temu']};self.old=os.environ.get('FIRST_DIALOGUES_DB');os.environ['FIRST_DIALOGUES_DB']=str(self.fd)
  with closing(sqlite3.connect(self.shared)) as c,c:c.executescript("CREATE TABLE users(id);CREATE TABLE ledger(user_id,kind,created);CREATE TABLE legacy_links(product,user_id,legacy_uid);INSERT INTO users VALUES('u'),('same-id');INSERT INTO ledger VALUES('u','account_created',20),('same-id','account_created',10);INSERT INTO legacy_links VALUES('temu','u','linked-old');")
  with closing(sqlite3.connect(self.fd)) as c,c:c.executescript("CREATE TABLE first_dialogues(event_id,skill_id,skill_name,skill_version,channel,received_at,client_occurred_at,user_id,is_test);INSERT INTO first_dialogues VALUES('anon','synthetic','Synthetic','1','skillhub',50,50,NULL,0),('linked','synthetic','Synthetic','1','skillhub',30,30,'u',0),('test','synthetic','TEST','1','skillhub',99,99,NULL,1);")
  for p,path in self.paths.items():
   with closing(sqlite3.connect(path)) as c,c:
    c.executescript("CREATE TABLE users(id,balance);CREATE TABLE ledger(id,user_id,job_id,amount,kind,created);CREATE TABLE member_grants(order_id,user_id,remaining,expires);CREATE TABLE jobs(id,user_id,created,status,image,request_hash);")
    users=[('g',7),('same-id',9)] if p=='gemini' else [('linked-old',4),('t',2)]
    for i,(uid,balance) in enumerate(users):
     c.execute('INSERT INTO users VALUES(?,?)',(uid,balance));c.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(i,uid,None,balance,'account_created',5+i));c.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?)',('job'+uid,uid,15,'succeeded','DO-NOT-EXPORT-IMAGE','DO-NOT-EXPORT-HASH'))
    if p=='gemini':c.execute("INSERT INTO member_grants VALUES('expired','g',3,1)")
  self.d=Directory(self.shared,self.paths)
 def tearDown(self):
  if self.old is None:os.environ.pop('FIRST_DIALOGUES_DB',None)
  else:os.environ['FIRST_DIALOGUES_DB']=self.old
  self.tmp.cleanup()
 def test_all_sources_and_counts(self):
  a=self.d.listing();self.assertEqual(a['total'],6);self.assertEqual(a['counts'],dict(accounts=2,interactions=1,legacy_accounts=3))
 def test_linked_legacy_not_duplicated(self):
  self.assertFalse(any(x['id']=='linked-old' for x in self.d.listing()['users']))
 def test_same_uuid_not_merged_without_link(self):
  a=[x for x in self.d.listing()['users'] if x['id']=='same-id'];self.assertEqual(len(a),2);self.assertEqual({x['record_type'] for x in a},{'account','legacy_account'})
 def test_expired_not_granted(self):
  self.assertEqual(self.d.legacy_account('gemini','g')['image']['available']['gemini'],4)
 def test_detail_current_status_and_no_images_or_secrets(self):
  a=self.d.legacy_detail('gemini','g');self.assertEqual(a['historical_succeeded_jobs'],1);self.assertEqual(len(a['legacy']['gemini']['jobs']),1);self.assertNotIn('DO-NOT-EXPORT',json.dumps(a));self.assertEqual(a['first_dialogues'],[])
 def test_readonly(self):
  files=[self.shared,self.fd,*self.paths.values()];before=[p.read_bytes() for p in files];self.d.listing();self.d.legacy_detail('gemini','g');self.assertEqual(before,[p.read_bytes() for p in files])
 def test_bad_product_and_unknown_id(self):
  with self.assertRaises(ValueError):self.d.legacy_detail('../outside','g')
  with self.assertRaises(LookupError):self.d.legacy_detail('gemini','missing')
 def test_search_exact_source(self):
  a=self.d.listing(query='g');self.assertTrue(any(x['id']=='g' for x in a['users']));self.assertEqual(self.d.listing(query="' OR 1=1 --")['total'],0)
 def test_pagination_and_dates(self):
  with closing(sqlite3.connect(self.paths['gemini'])) as c,c:
   for i in range(30):c.execute('INSERT INTO users VALUES(?,0)',('more-'+str(i),))
  a=self.d.listing();b=self.d.listing(2);self.assertEqual(a['total'],36);self.assertEqual(len(a['users'])+len(b['users']),36);dates=[x['observed_at'] for x in a['users']+b['users'] if x['observed_at'] is not None];self.assertEqual(dates,sorted(dates,reverse=True))
 def test_legacy_route_auth_and_query(self):
  import manual_admin
  class Parent:
   path='/ops/api/user-journey/legacy?product=gemini&uid=g'
   allowed=False
   def authenticated(self):return self.allowed
   def send(self,status,data,*args,**kwargs):return status,data
  H=manual_admin.extend(lambda *args:Parent,self.shared)(types.SimpleNamespace(products=self.paths));h=H();self.assertEqual(h.do_GET()[0],401);h.allowed=True;self.assertEqual(h.do_GET()[0],200);h.path='/ops/api/user-journey/legacy?product=invalid&uid=g';self.assertEqual(h.do_GET()[0],400)
if __name__=='__main__':unittest.main()
