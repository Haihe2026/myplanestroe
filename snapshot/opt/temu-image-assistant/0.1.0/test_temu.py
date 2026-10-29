import base64
import concurrent.futures
import importlib.util
import io
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'service'))
sys.path.insert(0, str(ROOT / 'skill/scripts'))
import server
import client


def photo(color='blue'):
    image = Image.new('RGB', (512, 512), 'lightgray')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((175, 100, 335, 420), 24, fill=color)
    draw.rectangle((212, 60, 298, 100), fill='black')
    draw.rectangle((175, 260, 335, 295), fill='red')
    data = io.BytesIO()
    image.save(data, 'PNG')
    return data.getvalue()


class FakeProvider:
    ready = True
    def __init__(self):
        self.calls = 0
        self.seen = []
    def __call__(self, prompt, size):
        self.calls += 1
        self.seen.append(server.REFERENCES.get())
        return photo()


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'TEMU_CREDENTIAL_FILE': str(self.root / 'private/credential'),
            'IMAGE_PUBLIC_TRIAL_ENABLED': 'yes', 'IMAGE_TRIAL_HMAC_KEY': 'synthetic-test-secret',
            'IMAGE_TRIAL_IP_DAILY_LIMIT': '3', 'IMAGE_PILOT_MAX_IMAGES': '100'})
        self.env.start()
        self.provider = FakeProvider()
        self.store = server.Store(self.root / 'test.db', self.provider)
        self.identity = secrets.token_urlsafe(32)
        self.store.register(self.identity, '192.0.2.1', True)
        self.uid = self.store.user(self.identity)
        self.body = {'references': [{'mime': 'image/png', 'content': base64.b64encode(photo()).decode()}],
                     'countries': ['US', 'DE'], 'slot': 'main', 'confirmed': True}
        (self.root / 'source.png').write_bytes(photo())
        self.job = self.root / 'job.json'
        self.job.write_text(json.dumps({'photos': ['source.png'], 'countries': ['US','DE'],
                                        'slots': ['main', 'sku', 'detail'], 'confirmed': True}))
    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()
    def test_reference_uploaded_and_main_allowed(self):
        result = self.store.generate(self.uid, self.body, 'a' * 32)
        self.assertEqual(result['balance_points'], 4000)
        self.assertEqual(len(self.provider.seen[0]), 1)
    def test_no_reference_no_charge(self):
        self.body['references'] = []
        with self.assertRaises(server.pilot.Problem): self.store.generate(self.uid, self.body, 'a' * 32)
        self.assertEqual(self.store.balance(self.uid), 5)
    def test_text_disallowed(self):
        self.body['text'] = 'promotion'
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_invalid_country(self):
        self.body['countries'] = ['INVALID']
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_invalid_slot(self):
        self.body['slot'] = 'fabricate_back'
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_base64_invalid(self):
        self.body['references'][0]['content'] = 'bad!'
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_corrupt_image(self):
        self.body['references'][0]['content'] = base64.b64encode(b'not a photo').decode()
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_mime_mismatch(self):
        self.body['references'][0]['mime'] = 'image/jpeg'
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_tiny_image(self):
        data = io.BytesIO(); Image.new('RGB',(10,10)).save(data,'PNG')
        self.body['references'][0]['content'] = base64.b64encode(data.getvalue()).decode()
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_confirm_required(self):
        self.body['confirmed'] = False
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_repeat_grant(self):
        self.assertFalse(self.store.register(self.identity, '192.0.2.1', True)['granted'])
        self.assertEqual(self.store.balance(self.uid), 5)
    def test_replay_one_charge(self):
        self.store.generate(self.uid, self.body, 'a' * 32)
        result = self.store.generate(self.uid, self.body, 'a' * 32)
        self.assertTrue(result['replayed']); self.assertEqual(self.provider.calls, 1)
        self.assertEqual(self.store.balance(self.uid), 4)
    def test_changed_photo_conflicts(self):
        self.store.generate(self.uid, self.body, 'a' * 32)
        self.body['references'][0]['content'] = base64.b64encode(photo('green')).decode()
        with self.assertRaises(server.pilot.Problem) as raised: self.store.generate(self.uid, self.body, 'a' * 32)
        self.assertEqual(raised.exception.status, 409)
    def test_parallel_replay_one_charge(self):
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            list(pool.map(lambda _: self.store.generate(self.uid, self.body, 'b' * 32), range(4)))
        self.assertEqual(self.provider.calls, 1)
    def test_uncertain_no_auto_refund(self):
        self.provider.__class__.__call__, old = self.fail, self.provider.__class__.__call__
        try:
            result = self.store.generate(self.uid, self.body, 'a' * 32)
            self.assertEqual(result['status'], 'pending'); self.assertEqual(self.store.balance(self.uid), 4)
        finally: self.provider.__class__.__call__ = old
    @staticmethod
    def fail(*args): raise TimeoutError()
    def test_known_rejection_refund(self):
        def reject(*args):
            server.REJECTED.set(True); raise server.ConfirmedRejected()
        old = self.provider.__class__.__call__
        self.provider.__class__.__call__ = reject
        try:
            result = self.store.generate(self.uid, self.body, 'a' * 32)
            self.assertEqual(result['status'], 'failed'); self.assertEqual(result['balance_points'], 5000)
        finally: self.provider.__class__.__call__ = old
    def test_local_plan_no_network(self):
        with patch.object(client, 'request', side_effect=AssertionError('network')):
            jobs = client.prepare(self.job)
        self.assertEqual(len(jobs), 3); self.assertEqual(jobs[0]['countries'], ['US','DE'])
    def test_multiple_countries_no_duplicate_cost(self):
        self.assertEqual(len(client.prepare(self.job)), 3)
    def test_selection_deduplicates(self):
        self.assertEqual(client.selection(['US','DE','US'])['countries'], ['US','DE'])
        self.assertEqual(client.selection()['countries'], ['US','DE'])
    def test_skip(self):
        self.assertEqual(client.selection(skip=True)['countries'], ['OTHER'])
    def test_menu_covers_all(self):
        items=[]
        for page in range(1, client.menu()['pages']+1): items.extend(client.menu(page)['options'])
        self.assertEqual({v['id'] for v in items}, set(client.CATALOG['markets']))
    def test_missing_file(self):
        (self.root/'source.png').unlink()
        with self.assertRaises(FileNotFoundError): client.prepare(self.job)
    def test_invalid_slots_client(self):
        job=json.loads(self.job.read_text()); job['slots']=['main','main']; self.job.write_text(json.dumps(job))
        with self.assertRaises(client.transport.UserProblem): client.prepare(self.job)
    def test_context_is_reset(self):
        self.store.generate(self.uid, self.body, 'a' * 32)
        self.assertEqual(server.REFERENCES.get(), ())
    def test_edit_disabled_not_claimed(self):
        with patch.dict(os.environ, {'IMAGE_PROVIDER_CONFIRMED':'yes','IMAGE_PROVIDER_KEY':'synthetic','TEMU_EDIT_CONFIRMED':'no'}):
            self.assertFalse(server.EditProvider().ready)
    def test_full_pool_preserves_promised_capacity(self):
        with patch.dict(os.environ, {'IMAGE_PILOT_MAX_IMAGES':'5'}):
            with self.assertRaises(server.pilot.Problem) as raised:
                self.store.register(secrets.token_urlsafe(32),'192.0.2.2',True)
            self.assertEqual(raised.exception.status,429)
        self.assertEqual(self.store.balance(self.uid),5)
    def test_signup_network_limit(self):
        self.store.register(secrets.token_urlsafe(32),'192.0.2.1',True)
        self.store.register(secrets.token_urlsafe(32),'192.0.2.1',True)
        with self.assertRaises(server.pilot.Problem):
            self.store.register(secrets.token_urlsafe(32),'192.0.2.1',True)
    def test_more_than_three_references(self):
        self.body['references'] *= 4
        with self.assertRaises(server.pilot.Problem): server.validate(self.body)
    def test_metadata_removed(self):
        data=io.BytesIO()
        from PIL.PngImagePlugin import PngInfo
        metadata=PngInfo(); metadata.add_text('private','sensitive-test-marker')
        Image.new('RGB',(512,512),'blue').save(data,'PNG',pnginfo=metadata)
        self.body['references'][0]['content']=base64.b64encode(data.getvalue()).decode()
        _,images=server.validate(self.body)
        self.assertNotIn(b'sensitive-test-marker',images[0])
    def test_detail_prompt_is_not_scene(self):
        self.body['slot']='detail'
        normalized,_=server.validate(self.body)
        self.assertIn('不做生活场景',normalized['prompt'])
    def test_provider_uses_multipart_reference_not_generations(self):
        from contextlib import contextmanager
        captured=[]
        class Response:
            def read(self,limit): return json.dumps({'data':[{'b64_json':base64.b64encode(photo()).decode()}]}).encode()
            def __enter__(self): return self
            def __exit__(self,*args): pass
        class Opener:
            def open(self,request,timeout):
                captured.append(request)
                return Response()
        context=server.REFERENCES.set((photo(),))
        try:
            with patch.dict(os.environ, {'IMAGE_PROVIDER_CONFIRMED':'yes','IMAGE_PROVIDER_KEY':'synthetic','TEMU_EDIT_CONFIRMED':'yes'}), patch.object(server.urllib.request,'build_opener',return_value=Opener()):
                output=server.EditProvider()('preserve real product','1024x1024')
            self.assertTrue(output.startswith(b'\x89PNG'))
            self.assertTrue(captured[0].full_url.endswith('/images/edits'))
            self.assertIn(b'name="image"',captured[0].data)
            self.assertNotIn(b'synthetic',captured[0].data)
        finally: server.REFERENCES.reset(context)


if __name__ == '__main__': unittest.main()
