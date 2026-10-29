import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from server import Problem, Store
from server import Provider, MAX_IMAGE
from unittest.mock import patch, MagicMock
import base64
import os
import secrets


class ProviderResponseTests(unittest.TestCase):
    def test_base64_png(self):
        image = b'\x89PNG\r\n\x1a\nTEST'
        self.assertEqual(Provider.decode_response({'data': [{'b64_json': base64.b64encode(image).decode()}]}), image)

    def test_url_png_without_key(self):
        image = b'\x89PNG\r\n\x1a\nTEST'
        response = MagicMock()
        response.__enter__.return_value.read.return_value = image
        opener = MagicMock()
        opener.open.return_value = response
        with patch('server.urllib.request.build_opener', return_value=opener):
            self.assertEqual(Provider.decode_response({'data': [{'url': 'https://file.hfsyapi.cn/test.png?signature=synthetic'}]}), image)
        req = opener.open.call_args.args[0]
        self.assertIsNone(req.get_header('Authorization'))

    def test_untrusted_urls_blocked(self):
        for url in ('http://file.hfsyapi.cn/a', 'https://localhost/a', 'https://file.hfsyapi.cn.attacker.test/a',
                    'https://user:example@redacted.invalid/a', 'https://file.hfsyapi.cn:1234/a'):
            with self.assertRaises(ValueError), patch('server.urllib.request.build_opener') as opener:
                Provider.decode_response({'data': [{'url': url}]})
            opener.assert_not_called()

    def test_invalid_images_blocked(self):
        for image in (b'not png', b'\x89PNG\r\n\x1a\n' + b'x' * MAX_IMAGE):
            with self.assertRaises(ValueError):
                Provider.decode_response({'data': [{'b64_json': base64.b64encode(image).decode()}]})


class FakeProvider:
    ready = True
    calls = 0
    fail = False

    def __call__(self, prompt, size):
        self.calls += 1
        if self.fail:
            raise TimeoutError('mock timeout')
        # Synthetic header fixture, not an actual generated or visually validated image.
        return b'\x89PNG\r\n\x1a\nTEST'


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.provider = FakeProvider()
        self.s = Store(Path(self.tmp.name) / 'test.db', self.provider)
        self.uid = self.s.user(self.s.activate(self.s.invite())['token'])
        self.job = {'prompt': '合成测试：办公封面，无文字', 'confirmed': True}

    def tearDown(self):
        self.tmp.cleanup()

    def test_grant(self):
        self.assertEqual(self.s.balance(self.uid), 5)

    def trial_env(self, **kwargs):
        return patch.dict(os.environ, dict(IMAGE_PUBLIC_TRIAL_ENABLED='yes', IMAGE_TRIAL_HMAC_KEY='synthetic-hmac-test-secret', **kwargs))

    def test_public_trial_new_and_repeat(self):
        secret = secrets.token_urlsafe(32)
        with self.trial_env():
            a = self.s.register(secret, '192.0.2.1', True)
            b = self.s.register(secret, '192.0.2.1', True)
        self.assertEqual(a['balance_points'], 5000)
        self.assertTrue(a['granted'])
        self.assertFalse(b['granted'])
        self.assertEqual(self.s.user(a['token']), self.s.user(b['token']))
        with self.s.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM ledger WHERE user_id=? AND kind=?', (self.s.user(a['token']), 'trial_grant')).fetchone()[0], 1)

    def test_public_trial_concurrent_single_grant(self):
        secret = secrets.token_urlsafe(32)
        with self.trial_env(), concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            values = list(pool.map(lambda _: self.s.register(secret, '192.0.2.1', True), range(6)))
        self.assertEqual(sum(v['granted'] for v in values), 1)

    def test_trial_existing_invite_account(self):
        token = self.s.activate(self.s.invite())['token']
        uid = self.s.user(token)
        self.s.generate(uid, self.job, 'legacy-task'.ljust(32, '0'))
        with self.trial_env():
            result = self.s.register(token, '192.0.2.1', True)
        self.assertFalse(result['granted'])
        self.assertEqual(result['balance_points'], 4000)
        self.assertEqual(self.s.user(result['token']), uid)

    def test_trial_expiry_renew_no_grant(self):
        secret = secrets.token_urlsafe(32)
        with self.trial_env():
            self.s.register(secret, '192.0.2.1', True)
            with self.s.connect() as c:
                c.execute('UPDATE sessions SET expires=0')
            result = self.s.register(secret, '192.0.2.1', True)
        self.assertFalse(result['granted'])
        self.assertTrue(self.s.user(secret))

    def test_trial_ip_limit(self):
        with self.trial_env(IMAGE_TRIAL_IP_DAILY_LIMIT='1'):
            self.s.register(secrets.token_urlsafe(32), '192.0.2.1', True)
            with self.assertRaises(Problem) as error:
                self.s.register(secrets.token_urlsafe(32), '192.0.2.1', True)
        self.assertEqual(error.exception.status, 429)

    def test_trial_parallel_budget_not_oversold(self):
        def register(index):
            try:
                return self.s.register(secrets.token_urlsafe(32), '192.0.2.' + str(index), True)['granted']
            except Problem as e:
                return e.status
        with self.trial_env(), concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            result = list(pool.map(register, range(8)))
        self.assertEqual(result.count(True), 3)
        self.assertEqual(result.count(429), 5)
        with self.s.connect() as c:
            self.assertEqual(c.execute('SELECT sum(balance) FROM users').fetchone()[0], 20)

    def test_trial_budget_reserves_all_promised_images(self):
        with self.trial_env(IMAGE_PILOT_MAX_IMAGES='5'):
            with self.assertRaises(Problem) as error:
                self.s.register(secrets.token_urlsafe(32), '192.0.2.1', True)
        self.assertEqual(error.exception.status, 429)
        with self.s.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0], 1)

    def test_trial_disabled_and_provider_off(self):
        with patch.dict(os.environ, {'IMAGE_PUBLIC_TRIAL_ENABLED': 'no'}), self.assertRaises(Problem):
            self.s.register(secrets.token_urlsafe(32), '192.0.2.1', True)
        self.provider.ready = False
        with self.trial_env(), self.assertRaises(Problem) as error:
            self.s.register(secrets.token_urlsafe(32), '192.0.2.1', True)
        self.assertEqual(error.exception.status, 503)

    def test_trial_notice_required(self):
        with self.trial_env(), self.assertRaises(Problem):
            self.s.register(secrets.token_urlsafe(32), '192.0.2.1', False)

    def test_trial_invalid_identity(self):
        for value in ('a', 'a' * 44, '!' * 43, None):
            with self.trial_env(), self.assertRaises(Problem):
                self.s.register(value, '192.0.2.1', True)

    def test_all_specific_roles_accepted(self):
        from server import CATALOG
        for role in CATALOG['roles']:
            self.provider.ready = False
            with self.assertRaises(Problem) as e:
                self.s.generate(self.uid, dict(self.job, role=role), role.ljust(32, '0'))
            self.assertEqual(e.exception.status, 503)
        self.assertEqual(self.s.balance(self.uid), 5)

    def test_invite_once(self):
        code = self.s.invite()
        self.s.activate(code)
        with self.assertRaises(Problem):
            self.s.activate(code)

    def test_no_provider_no_charge(self):
        self.provider.ready = False
        with self.assertRaises(Problem):
            self.s.generate(self.uid, self.job, 'a' * 32)
        self.assertEqual(self.s.balance(self.uid), 5)

    def test_success_and_replay(self):
        a = self.s.generate(self.uid, self.job, 'a' * 32)
        b = self.s.generate(self.uid, self.job, 'a' * 32)
        self.assertEqual(a['id'], b['id'])
        self.assertEqual(self.provider.calls, 1)
        self.assertEqual(self.s.balance(self.uid), 4)

    def test_replay_changed_body(self):
        self.s.generate(self.uid, self.job, 'a' * 32)
        with self.assertRaises(Problem):
            self.s.generate(self.uid, dict(self.job, prompt='changed'), 'a' * 32)

    def test_quota_concurrent(self):
        def run(i):
            try:
                return self.s.generate(self.uid, self.job, str(i).zfill(32))['status']
            except Problem as e:
                return e.status
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            result = list(pool.map(run, range(8)))
        self.assertEqual(result.count('succeeded'), 5)
        self.assertEqual(result.count(402), 3)
        self.assertEqual(self.s.balance(self.uid), 0)

    def test_timeout_refund_once(self):
        self.provider.fail = True
        a = self.s.generate(self.uid, self.job, 'a' * 32)
        self.assertEqual(a['status'], 'pending')
        self.assertEqual(self.s.balance(self.uid), 4)
        self.s.refund_confirmed_failure(a['id'])
        self.assertEqual(self.s.balance(self.uid), 5)
        with self.assertRaises(Problem):
            self.s.refund_confirmed_failure(a['id'])

    def test_ownership(self):
        a = self.s.generate(self.uid, self.job, 'a' * 32)
        other = self.s.user(self.s.activate(self.s.invite())['token'])
        with self.assertRaises(Problem):
            self.s.get_job(other, a['id'])

    def test_confirmation(self):
        with self.assertRaises(Problem):
            self.s.generate(self.uid, {'prompt': 'test'}, 'a' * 32)
        self.assertEqual(self.s.balance(self.uid), 5)

    def test_main_not_faked(self):
        with self.assertRaises(Problem):
            self.s.generate(self.uid, dict(self.job, slot='main'), 'a' * 32)
        self.assertEqual(self.s.balance(self.uid), 5)

    def test_expired_session(self):
        with self.s.connect() as c:
            c.execute('UPDATE sessions SET expires=0')
        with self.assertRaises(Problem):
            self.s.user('invalid')


if __name__ == '__main__':
    unittest.main()
