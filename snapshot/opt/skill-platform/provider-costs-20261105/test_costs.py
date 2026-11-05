import tempfile,os,json,sqlite3,unittest
from pathlib import Path
from contextlib import closing
from cost_store import Costs,catalog
from usage_capture import observe,KNOWN
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=os.environ.get('PROVIDER_COSTS_DB');os.environ['PROVIDER_COSTS_DB']=str(Path(self.temp.name)/'costs.db');self.s=Costs();self.s.initialize();KNOWN.clear()
 def tearDown(self):
  if self.old is None:os.environ.pop('PROVIDER_COSTS_DB',None)
  else:os.environ['PROVIDER_COSTS_DB']=self.old
  self.temp.cleanup()
 def test_catalog(self):self.assertEqual(len(catalog()['models']),36)
 def test_image(self):self.assertEqual(self.s.estimate('gpt-image-2.5-ext',1),'0.0065')
 def test_token(self):self.assertEqual(self.s.estimate('gpt-6-sol',input_tokens=1000000,output_tokens=1000000),'1.20')
 def test_missing_token(self):self.assertIsNone(self.s.estimate('gpt-6-sol',1))
 def test_video(self):self.assertEqual(self.s.estimate('grok-imagine-1.5-video',6,params={'resolution':'720p'}),'0.126')
 def test_unverified_video(self):self.assertIsNone(self.s.estimate('kling-v3',6,params={'resolution':'720p'}))
 def test_unknown_model(self):self.assertIsNone(self.s.estimate('invented',1))
 def test_dedup(self):
  self.s.record('a','gpt-image-2.5-ext','succeeded',1);self.s.record('a','gpt-image-2.5-ext','succeeded',1);self.assertEqual(self.s.report()['estimated_usd'],'0.0065')
 def test_failed_unknown(self):
  for i,state in enumerate(['failed','unknown','pending']):self.s.record(str(i),'gpt-image-2.5-ext',state,1)
  self.assertEqual(self.s.report()['estimated_usd'],'0')
 def test_terminal_preserved(self):
  self.s.record('x','gpt-image-2.5-ext','succeeded',1);self.s.record('x','gpt-image-2.5-ext','pending',1);self.assertEqual(self.s.report()['groups'][0]['status'],'succeeded')
 def test_async(self):
  observe('https://www.aisplice.store/v1/videos','POST',{'model':'grok-imagine-1.5-video','duration':6,'resolution':'480p','prompt':'DO_NOT_STORE'}, {'Authorization':'SECRET_DO_NOT_STORE'},200,{'task_id':'synthetic-video','status':'queued'})
  KNOWN.clear();observe('https://www.aisplice.store/v1/videos/synthetic-video','GET',{}, {},200,{'status':'completed','id':'synthetic-video'})
  self.assertEqual(self.s.report()['estimated_usd'],'0.0672');self.assertEqual(len(self.s.report()['items']),1)
  raw=self.s.path.read_bytes();self.assertNotIn(b'DO_NOT_STORE',raw)
 def test_snapshot(self):
  self.s.snapshot({'currency':'USD','balance':12,'available':5,'key':{'used':3}});self.assertEqual(self.s.report()['snapshot']['key_used'],'3');self.assertEqual(self.s.report()['estimated_usd'],'0')
 def test_bad_snapshot(self):
  with self.assertRaises(ValueError):self.s.snapshot({'currency':'CNY'})
 def test_fx(self):
  self.s.record('fx','gpt-image-2.5-ext','succeeded',1);self.assertEqual(self.s.report()['estimated_cny'],'0.0455')
 def test_nonmodel(self):
  observe('https://www.aisplice.store/v1/balance','GET',{}, {},200,{'available':3});self.assertEqual(self.s.report()['items'],[])
 def test_direct_https_transport(self):
  import io,http.client
  from usage_capture import install
  class Socket:
   def sendall(self,data):pass
   def makefile(self,*a):return io.BytesIO(b'HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\n'+b'{"data":[]}')
   def close(self):pass
  class Connection(http.client.HTTPSConnection):
   def connect(self):self.sock=Socket()
  install();c=Connection('www.aisplice.store')
  raw=json.dumps({'model':'gpt-image-2.5-ext','prompt':'NEVER_STORE_PROMPT','n':1})
  c.request('POST','/v1/images/generations',body=raw,headers={'Authorization':'SECRET_KEY','Idempotency-Key':'synthetic-transport-id'})
  result=c.getresponse();result.read();c.close()
  self.assertEqual(self.s.report()['estimated_usd'],'0.0065');self.assertNotIn(b'NEVER_STORE_PROMPT',self.s.path.read_bytes());self.assertNotIn(b'SECRET_KEY',self.s.path.read_bytes())
if __name__=='__main__':unittest.main()
