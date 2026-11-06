import io,json,unittest,urllib.error
from client import Client,GatewayError,text_job,temporary_link,ORIGIN
ACCOUNT='A'*43;KEY='mpskill_'+'a'*32+'_'+'B'*43;JID='11111111-1111-4111-8111-111111111111'
class Reply(io.BytesIO):
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
class Spy:
 def __init__(self,values):self.values=list(values);self.requests=[]
 def open(self,req,timeout):
  self.requests.append(req);v=self.values.pop(0)
  if isinstance(v,Exception):raise v
  return Reply(v if isinstance(v,bytes) else json.dumps(v).encode())
class Tests(unittest.TestCase):
 def client(self,values):
  c=Client('synthetic-skill','skillhub',ACCOUNT,KEY,device='cloud');c.opener=Spy(values);return c
 def test_health_no_credential(self):
  c=self.client([{'status':'ok'}]);c.health();r=c.opener.requests[0];self.assertEqual(r.full_url,ORIGIN+'/platform-api/gemini/health');self.assertIsNone(r.get_header('Authorization'))
 def test_balance_same_account(self):
  c=self.client([{'remaining_uses':4}]);self.assertEqual(c.balance()['remaining_uses'],4);self.assertEqual(c.opener.requests[0].get_header('Authorization'),'Bearer '+ACCOUNT)
 def test_browser_link_preserves_ticket(self):
  url='https://myplanestore.com/membership/gemini/#ticket='+'x'*43;self.assertEqual(temporary_link(url),url.replace('https://myplanestore.com',ORIGIN))
 def test_foreign_site_and_arbitrary_api_rejected(self):
  for u in ['https://evil.invalid/membership/#ticket=x','https://myplanestore.com/platform-api/gemini/jobs']:
   with self.assertRaises(ValueError):temporary_link(u)
 def test_confirmation_and_stable_key(self):
  with self.assertRaises(ValueError):text_job('synthetic','x'*32)
  body=text_job('synthetic','x'*32,True);self.assertEqual(body['gemini_trial_intent'],'paid');self.assertEqual(body['image_retention']['policy'],'gateway-delivery-delete/1')
 def test_bind_saves_before_ack(self):
  c=self.client([{'state':'ready','key':KEY},{'bound':True}]);saved=[];result=c.bind_skill_key(saved.append);self.assertEqual(saved,[KEY]);self.assertEqual(result,{'bound':True});self.assertEqual(json.loads(c.opener.requests[1].data),{'key':KEY})
 def test_submit_uses_skill_key_and_original_idem(self):
  c=self.client([{'id':JID,'status':'pending'}]);key='synthetic-task-00000001';c.submit(text_job('synthetic',key,True),key);r=c.opener.requests[0];self.assertEqual(r.get_header('Authorization'),'Bearer '+KEY);self.assertEqual(r.get_header('Idempotency-key'),key)
 def test_no_automatic_post_retry_or_secret_in_error(self):
  c=self.client([TimeoutError(KEY)])
  with self.assertRaises(GatewayError) as e:c.submit({'confirmed':True},'x'*32)
  self.assertEqual(len(c.opener.requests),1);self.assertNotIn(KEY,str(e.exception))
 def test_http_402_preserved(self):
  c=self.client([urllib.error.HTTPError(ORIGIN,402,'secret detail',{},None)])
  with self.assertRaises(GatewayError) as e:c.balance()
  self.assertEqual(e.exception.status,402);self.assertNotIn('secret detail',str(e.exception))
 def test_download_png_and_ownership_path(self):
  c=self.client([b'\x89PNG\r\n\x1a\nsynthetic']);self.assertTrue(c.image(JID).startswith(b'\x89PNG'));self.assertTrue(c.opener.requests[0].full_url.endswith('/jobs/'+JID+'/image'))
 def test_bad_download_and_traversal_rejected(self):
  with self.assertRaises(ValueError):self.client([]).image('../other-user')
  with self.assertRaises(GatewayError):self.client([b'<html>not an image</html>']).image(JID)
 def test_no_supplier_host_or_plaintext_remote(self):
  for origin in ['https://www.aisplice.store','http://evil.invalid']:
   with self.assertRaises(ValueError):Client('synthetic-skill','skillhub',ACCOUNT,origin=origin)
if __name__=='__main__':unittest.main()
