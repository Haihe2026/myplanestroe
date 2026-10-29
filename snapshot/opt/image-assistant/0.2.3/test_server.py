import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from server import Problem, Store


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
