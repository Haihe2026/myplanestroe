import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('task_client', Path(__file__).parent / 'skill/scripts/client.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'IMAGE_CREDENTIAL_FILE':str(self.root / 'private/credential')})
        self.env.start()
        self.security = patch.object(client, 'secure_local')
        self.security.start()
        self.job = {'prompt':'Synthetic scene', 'confirmed':True, 'role':'general', 'platform':'general', 'slot':'scene'}

    def tearDown(self): self.security.stop(); self.env.stop(); self.tmp.cleanup()

    def test_prepare_offline_no_secret(self):
        with patch.object(client,'request') as req:
            path = client.create_task(self.job,self.root)
        req.assert_not_called()
        self.assertEqual(json.loads(path.read_text())['status'],'draft')
        self.assertNotIn('token', path.read_text())

    def test_no_account_preserves_before_authorization(self):
        path = client.create_task(self.job,self.root)
        with patch.object(client,'request',return_value={'ready':True}) as req,redirect_stdout(io.StringIO()): client.execute_task(path)
        self.assertEqual(req.call_count,1)
        self.assertEqual(req.call_args.args[0],'/phone-auth/status')
        self.assertEqual(json.loads(path.read_text())['status'],'needs_authorization')

    def test_low_balance_preserves_task_no_generation(self):
        client.credential_path().parent.mkdir()
        client.credential_path().write_text('synthetic-only')
        path = client.create_task(self.job,self.root)
        with patch.object(client,'account_request',return_value={'balance_points':0}),patch.object(client,'request') as req,patch.object(client,'show_purchase_notice'),redirect_stdout(io.StringIO()): client.execute_task(path)
        req.assert_not_called()
        self.assertEqual(json.loads(path.read_text())['status'],'needs_credits')

    def test_unknown_only_queries_original_never_resubmits(self):
        path = client.create_task(self.job,self.root)
        state = json.loads(path.read_text()); state['status']='submitting'; client.save_private_json(path,state)
        with patch.object(client,'finish') as finish,patch.object(client,'request') as req,redirect_stdout(io.StringIO()): client.execute_task(path)
        req.assert_not_called(); finish.assert_called_once()
        self.assertEqual(finish.call_args.args[0]['idem'],state['idem'])

    def test_changed_photo_blocked(self):
        photo=self.root/'product.png'; photo.write_bytes(b'first')
        job=dict(self.job,reference_files=[str(photo)],reference_consent=True)
        path=client.create_task(job,self.root); photo.write_bytes(b'changed')
        with patch.object(client,'request') as req, self.assertRaises(client.UserProblem), redirect_stdout(io.StringIO()): client.execute_task(path)
        req.assert_not_called()

    def test_lock_refuses_duplicate(self):
        path=client.create_task(self.job,self.root); path.with_name('task.lock').write_text('locked')
        with patch.object(client,'request') as req,self.assertRaises(client.UserProblem): client.execute_task(path)
        req.assert_not_called()

    def test_authorization_completion_keeps_raw_compatible_token(self):
        token='x'*43
        client.save_private_json(client.auth_path(),{'id':'synthetic','poll_secret':'test-only'})
        with patch.object(client,'request',return_value={'status':'verified','token':token,'balance_points':5000}),redirect_stdout(io.StringIO()): client.authorization_finish()
        self.assertEqual(client.credential_path().read_text(), token)
        self.assertFalse(client.auth_path().exists())

    def test_waiting_never_claims_verified(self):
        client.save_private_json(client.auth_path(),{'id':'synthetic','poll_secret':'test-only'})
        out=io.StringIO()
        with patch.object(client,'request',return_value={'status':'waiting'}),redirect_stdout(out): client.authorization_finish()
        self.assertFalse(client.credential_path().exists())
        self.assertIn('等待',out.getvalue())


if __name__ == '__main__': unittest.main()
