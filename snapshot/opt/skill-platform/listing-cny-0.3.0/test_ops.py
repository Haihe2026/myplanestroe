import sys,types,unittest,secrets,json,io
import test_http as fixture
from test_http import Parent
from test_listing import Database
from listing_ops import extend

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  fixture.Tests.setUpClass();cls.api=fixture.Tests.db.listing;cls.db=fixture.Tests.db
  cls.saved=sys.modules.get('pet_ops');sys.modules['pet_ops']=types.SimpleNamespace(Database=lambda path:cls.db)
  cls.Handler=extend(lambda:Parent,cls.db.path)()
  cls.api.enroll('synthetic',secrets.token_hex(16),True)
 @classmethod
 def tearDownClass(cls):
  fixture.Tests.tearDownClass()
  if cls.saved:sys.modules['pet_ops']=cls.saved
  else:sys.modules.pop('pet_ops',None)
 def handler(self,route,body=None,auth=True,origin='https://myplanestore.com'):
  h=object.__new__(self.Handler);h.path=route;h.headers={'Cookie':'synthetic-ops=authenticated' if auth else '', 'Origin':origin,'Content-Type':'application/json','Idempotency-Key':secrets.token_hex(16)};h.client_address=('synthetic',1)
  raw=json.dumps(body or {}).encode();h.headers['Content-Length']=str(len(raw));h.rfile=io.BytesIO(raw)
  h.send=lambda status,result,*a,**kw:(status,result);return h
 def test_auth_and_origin(self):
  self.assertEqual(self.handler('/ops/api/listing/summary',auth=False).do_GET()[0],401)
  self.assertEqual(self.handler('/ops/api/listing/settle',origin='https://evil.invalid').do_POST()[0],403)
 def test_confirm_requires_real_verification_and_is_idempotent(self):
  o=self.api.order('synthetic',secrets.token_hex(16),'listing_cny_39_v1','synthetic-listing','workbuddy_skill');self.api.report('synthetic',secrets.token_hex(16),o['id'])
  b=dict(order_id=o['id'],amount_fen=3900,transaction_id='synthetic-ops-receipt',verified=False)
  self.assertEqual(self.handler('/ops/api/listing/settle',b).do_POST()[0],400)
  b['verified']=True
  self.assertEqual(self.handler('/ops/api/listing/settle',b).do_POST()[0],200)
  self.assertEqual(self.handler('/ops/api/listing/settle',b).do_POST()[0],200)
  self.assertEqual(self.api.me('synthetic')['balance_fen'],3900)

if __name__=='__main__':unittest.main()
