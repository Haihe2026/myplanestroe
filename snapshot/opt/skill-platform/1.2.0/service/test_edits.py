import base64
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image, PngImagePlugin
import server
from image_inputs import references


def photo(color='red', meta=False):
    output=io.BytesIO()
    info=PngImagePlugin.PngInfo();info.add_text('private','synthetic secret')
    Image.new('RGB',(256,256),color).save(output,'PNG',pnginfo=info if meta else None)
    return output.getvalue()


def ref(color='red',meta=False):
    return {'mime':'image/png','content':base64.b64encode(photo(color,meta)).decode()}


class Fake:
    ready=True
    edit_ready=True
    calls=0
    text_calls=0
    fail=False
    def __call__(self,prompt,size):self.text_calls+=1;return photo()
    def edit(self,prompt,size,images):
        self.calls+=1;self.last=(prompt,size,images)
        if self.fail:raise TimeoutError()
        return photo()


class EditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.provider=Fake()
        self.store=server.Store(Path(self.tmp.name)/'db.sqlite',self.provider)
        self.uid=self.store.user(self.store.activate(self.store.invite())['token'])
        self.job={'prompt':'Synthetic product scene','slot':'scene','confirmed':True,'reference_consent':True,'references':[ref()]}
    def tearDown(self):self.tmp.cleanup()
    def runjob(self,key='a'*32):return self.store.generate(self.uid,self.job,key)
    def test_edit_receives_real_bytes(self):
        result=self.runjob();self.assertEqual(result['status'],'succeeded');self.assertEqual(self.provider.calls,1)
        self.assertEqual(self.provider.text_calls,0);self.assertTrue(self.provider.last[2][0].startswith(b'\x89PNG'))
        self.assertEqual(self.store.balance(self.uid),4)
    def test_idempotent(self):
        a=self.runjob();b=self.runjob();self.assertEqual(a['id'],b['id']);self.assertEqual(self.provider.calls,1)
        self.assertEqual(self.store.balance(self.uid),4)
    def test_change_ref_same_key_conflicts(self):
        self.runjob();self.job['references']=[ref('blue')]
        with self.assertRaises(server.Problem) as error:self.runjob()
        self.assertEqual(error.exception.status,409);self.assertEqual(self.provider.calls,1)
    def test_metadata_stripped(self):
        self.job['references']=[ref(meta=True)]
        images,_=references(self.job,server.Problem)
        with Image.open(io.BytesIO(images[0])) as im:self.assertNotIn('private',im.info)
    def test_no_consent(self):
        self.job['reference_consent']=False
        with self.assertRaises(server.Problem):self.runjob()
        self.assertEqual(self.store.balance(self.uid),5)
    def test_no_reference_main(self):
        self.job.pop('references');self.job['slot']='main'
        with self.assertRaises(server.Problem):self.runjob()
        self.assertEqual(self.store.balance(self.uid),5)
    def test_main_with_reference(self):
        self.job['slot']='main';self.assertEqual(self.runjob()['status'],'succeeded')
    def test_sku_with_reference(self):
        self.job['slot']='sku';self.assertEqual(self.runjob()['status'],'succeeded')
    def test_feature_gate(self):
        self.provider.edit_ready=False
        with self.assertRaises(server.Problem) as error:self.runjob()
        self.assertEqual(error.exception.status,503);self.assertEqual(self.store.balance(self.uid),5);self.assertEqual(self.provider.calls,0)
    def test_timeout_no_retry(self):
        self.provider.fail=True
        self.assertEqual(self.runjob()['status'],'pending');self.assertTrue(self.runjob()['replayed'])
        self.assertEqual(self.provider.calls,1);self.assertEqual(self.store.balance(self.uid),4)
    def test_bad_refs(self):
        for refs in [[],[ref()]*4,[{'url':'http://127.0.0.1/private'}],[{'mime':'image/png','content':'bad'}],[dict(ref(),mime='image/jpeg')]]:
            with self.subTest(refs=str(refs)[:30]):
                self.job['references']=refs
                with self.assertRaises(server.Problem):self.runjob()
                self.assertEqual(self.store.balance(self.uid),5)
    def test_text_unchanged(self):
        self.job.pop('references');self.runjob();self.assertEqual(self.provider.text_calls,1);self.assertEqual(self.provider.calls,0)
    def test_reference_order_changes_identity(self):
        self.job['references']=[ref(),ref('blue')];self.runjob();self.job['references'].reverse()
        with self.assertRaises(server.Problem):self.runjob()
    def test_edit_multipart(self):
        reply=MagicMock();reply.__enter__.return_value.read.return_value=json.dumps({'data':[{'b64_json':base64.b64encode(photo()).decode()}]}).encode()
        opener=MagicMock();opener.open.return_value=reply
        with patch.dict(os.environ,{'IMAGE_PROVIDER_KEY':'synthetic-not-a-key'}),patch('server.urllib.request.build_opener',return_value=opener):
            server.Provider().edit('prompt','1024x1024',[photo(),photo('blue')])
        req=opener.open.call_args.args[0]
        self.assertEqual(req.full_url,'https://token.q14.cn/v1/images/edits')
        self.assertEqual(req.data.count(b'name="image[]"'),2)
        self.assertIn(photo('blue'),req.data)


if __name__=='__main__':unittest.main()
