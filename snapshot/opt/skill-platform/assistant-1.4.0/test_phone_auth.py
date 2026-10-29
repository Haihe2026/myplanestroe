import importlib.util
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / 'service'))
import server
from phone_auth import PhoneAuth


class Sms:
    ready = True
    def __init__(self): self.sent = []
    def send(self, phone, code): self.sent.append((phone, code))


class Provider:
    ready = edit_ready = True
    def __call__(self, *args): raise AssertionError('No paid calls allowed')


class PhoneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'IMAGE_PUBLIC_TRIAL_ENABLED':'yes', 'IMAGE_TRIAL_HMAC_KEY':'test-key',
            'IMAGE_PILOT_MAX_IMAGES':'120', 'IMAGE_ASSISTANT_TRIAL_POOL_UNITS':'100'})
        self.env.start()
        self.store = server.Store(Path(self.temp.name) / 'ledger.db', Provider())
        self.sms = Sms()
        self.auth = PhoneAuth(self.store, server.Problem, self.sms, 'test-private-key-with-thirty-two-characters')
        self.phone = '13800000000'

    def tearDown(self): self.env.stop(); self.temp.cleanup()

    def begin(self, token=None, ip='192.0.2.1'):
        result = self.auth.create({'existing_credential':token} if token else {}, ip)
        cookie = self.auth.redeem(result['url'].split('#ticket=')[1])
        return result, cookie

    def complete(self, result, cookie, phone=None):
        self.auth.send_code(cookie, {'phone':phone or self.phone, 'accepted':True}, '192.0.2.1')
        self.auth.verify(cookie, {'code':self.sms.sent[-1][1]}, '192.0.2.1')
        return self.auth.poll({'id':result['id'], 'poll_secret':result['poll_secret']}, '192.0.2.1')

    def test_disabled_is_truthful_no_session(self):
        self.sms.ready = False
        self.assertFalse(self.auth.create({}, '192.0.2.1')['ready'])
        with self.store.connect() as c: self.assertEqual(c.execute('SELECT count(*) FROM phone_auth_sessions').fetchone()[0], 0)

    def test_new_phone_once_other_device_same_account(self):
        result, cookie = self.begin()
        first = self.complete(result, cookie)
        uid = self.store.user(first['token'])
        self.assertTrue(first['granted'])
        self.assertEqual(first['balance_points'], 10000)
        # Advance beyond the resend cooldown for this synthetic phone.
        with self.store.connect() as c: c.execute('UPDATE phone_auth_limits SET last=0')
        result2, cookie2 = self.begin()
        second = self.complete(result2, cookie2)
        self.assertEqual(self.store.user(second['token']), uid)
        self.assertFalse(second['granted'])
        self.assertNotEqual(first['token'], second['token'])

    def test_binding_keeps_old_balance(self):
        old = self.store.register(secrets.token_urlsafe(32), '192.0.2.5', True, 5)
        uid = self.store.user(old['token'])
        result, cookie = self.begin(old['token'])
        verified = self.complete(result, cookie)
        self.assertEqual(self.store.user(verified['token']), uid)
        self.assertEqual(verified['balance_points'], 5000)
        self.assertFalse(verified['granted'])

    def test_conflicting_account_not_merged(self):
        result, cookie = self.begin()
        first = self.complete(result, cookie)
        other = self.store.register(secrets.token_urlsafe(32), '192.0.2.6', True, 5)
        with self.store.connect() as c: c.execute('UPDATE phone_auth_limits SET last=0')
        result2, cookie2 = self.begin(other['token'])
        self.auth.send_code(cookie2, {'phone':self.phone, 'accepted':True}, '192.0.2.1')
        with self.assertRaises(server.Problem) as error:
            self.auth.verify(cookie2, {'code':self.sms.sent[-1][1]}, '192.0.2.1')
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.store.balance(self.store.user(other['token'])), 5)
        self.assertEqual(self.store.balance(self.store.user(first['token'])), 10)

    def test_wrong_attempts_persist_and_lock(self):
        result, cookie = self.begin()
        self.auth.send_code(cookie, {'phone':self.phone, 'accepted':True}, '192.0.2.1')
        correct = self.sms.sent[-1][1]
        wrong = '000000' if correct != '000000' else '111111'
        for _ in range(5):
            with self.assertRaises(server.Problem): self.auth.verify(cookie, {'code':wrong}, '192.0.2.1')
        with self.assertRaises(server.Problem): self.auth.verify(cookie, {'code':correct}, '192.0.2.1')
        self.assertEqual(self.auth.poll({'id':result['id'], 'poll_secret':result['poll_secret']}, '192.0.2.1')['status'], 'waiting')

    def test_expired_code_does_not_credit(self):
        result, cookie = self.begin()
        self.auth.send_code(cookie, {'phone':self.phone, 'accepted':True}, '192.0.2.1')
        with self.store.connect() as c: c.execute('UPDATE phone_auth_sessions SET code_expires=0')
        with self.assertRaises(server.Problem): self.auth.verify(cookie, {'code':self.sms.sent[-1][1]}, '192.0.2.1')
        with self.store.connect() as c: self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0], 0)

    def test_consent_and_phone_format_no_sms(self):
        _, cookie = self.begin()
        for body in ({'phone':self.phone}, {'phone':'12345','accepted':True}):
            with self.assertRaises(server.Problem): self.auth.send_code(cookie, body, '192.0.2.1')
        self.assertFalse(self.sms.sent)

    def test_resend_cooldown(self):
        _, cookie = self.begin()
        self.auth.send_code(cookie, {'phone':self.phone,'accepted':True}, '192.0.2.1')
        with self.assertRaises(server.Problem) as error: self.auth.send_code(cookie, {'phone':self.phone,'accepted':True}, '192.0.2.1')
        self.assertEqual(error.exception.status,429)
        self.assertEqual(len(self.sms.sent), 1)

    def test_send_failure_not_verifyable_or_free_retry(self):
        _, cookie = self.begin()
        with patch.object(self.sms, 'send', side_effect=TimeoutError):
            with self.assertRaises(server.Problem): self.auth.send_code(cookie, {'phone':self.phone,'accepted':True}, '192.0.2.1')
        with self.assertRaises(server.Problem) as error: self.auth.send_code(cookie, {'phone':self.phone,'accepted':True}, '192.0.2.1')
        self.assertEqual(error.exception.status,429)

    def test_ticket_one_use_wrong_poll_secret(self):
        result, _ = self.begin()
        with self.assertRaises(server.Problem): self.auth.redeem(result['url'].split('#ticket=')[1])
        with self.assertRaises(server.Problem): self.auth.poll({'id':result['id'],'poll_secret':'x'*43}, '192.0.2.1')

    def test_no_plain_phone_code_or_secret_in_database(self):
        result, cookie = self.begin()
        self.complete(result, cookie)
        with self.store.connect() as c:
            values = [tuple(row) for row in c.execute('SELECT * FROM phone_auth_sessions')]
            values += [tuple(row) for row in c.execute('SELECT * FROM phone_accounts')]
        text = repr(values)
        for private in (self.phone, self.sms.sent[-1][1], result['poll_secret'], cookie):
            self.assertNotIn(private, text)


if __name__ == '__main__': unittest.main()
