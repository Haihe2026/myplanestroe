"""Loopback HTTP regression tests. Only synthetic SQLite accounts and OAuth identities.

RegistrationEntries and DeviceLinks are unmodified fixed-source fixtures. Only the
account/financial store and OAuth exchange are synthetic; no production imports.
"""
import concurrent.futures
import contextlib
import hashlib
import importlib.util
import json
import os
import secrets
import sqlite3
import sys
import tempfile
import threading
import time
import types
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
MODULE = Path(os.environ.get('WECHAT_TEST_MODULE', HERE.parent / 'wechat_binding.py'))
BASELINE = bool(os.environ.get('WECHAT_TEST_BASELINE'))


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class Store:
    def __init__(self, database):
        self.database = str(database)
        self.registration_calls = 0
        self.web, self.tickets = {}, {}
        with self.connect() as c:
            c.executescript('''
                CREATE TABLE users(id TEXT PRIMARY KEY,balance INTEGER);
                CREATE TABLE trial_claims(hash TEXT PRIMARY KEY,user_id TEXT,created INTEGER);
                CREATE TABLE orders(id TEXT PRIMARY KEY,status TEXT,amount INTEGER);
                CREATE TABLE paid_wallets(user_id TEXT PRIMARY KEY,remaining INTEGER);
                CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id TEXT,amount INTEGER,kind TEXT);
                CREATE TABLE trade_links(code_hash TEXT PRIMARY KEY,account_id TEXT,expires INTEGER);
                INSERT INTO users VALUES('synthetic-customer-sentinel',41);
                INSERT INTO paid_wallets VALUES('synthetic-customer-sentinel',41);
                INSERT INTO orders VALUES('synthetic-order','paid',2900);
                INSERT INTO ledger VALUES(1,'synthetic-customer-sentinel',41,'synthetic-fixture');
            ''')
        self.membership = types.SimpleNamespace(handoff=self.handoff, redeem=self.redeem, web_user=self.web_user)
        self.trade = types.SimpleNamespace(approve=lambda code, uid: uid or 'synthetic-trade-user')

    @contextlib.contextmanager
    def connect(self):
        c = sqlite3.connect(self.database, timeout=5)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def user(self, secret):
        with self.connect() as c:
            row = c.execute('SELECT user_id FROM trial_claims WHERE hash=?', (sha(secret or ''),)).fetchone()
        if not row:
            raise Problem(401, '模拟：尚未关联')
        return row[0]

    def register_product(self, product, secret, ip, accepted):
        assert accepted is True
        self.registration_calls += 1
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT user_id FROM trial_claims WHERE hash=?', (sha(secret),)).fetchone()
            if not old:
                uid = 'synthetic-' + secrets.token_hex(8)
                c.execute('INSERT INTO users VALUES(?,0)', (uid,))
                c.execute('INSERT INTO trial_claims VALUES(?,?,0)', (sha(secret), uid))
        return {'registered': True}

    def quota(self, uid, product):
        with self.connect() as c:
            row = c.execute('SELECT balance FROM users WHERE id=?', (uid,)).fetchone()
        return dict(remaining_uses=row[0] if row else 0)

    def handoff(self, uid):
        ticket = secrets.token_urlsafe(32)
        self.tickets[ticket] = uid
        return dict(url='https://myplanestore.com/membership/#ticket=' + ticket)

    def redeem(self, ticket):
        token = secrets.token_urlsafe(32)
        self.web[token] = self.tickets.pop(ticket)
        return token

    def web_user(self, token):
        if token not in self.web:
            raise Problem(401, '模拟：无网页会话')
        return self.web[token]

    def finances(self):
        with self.connect() as c:
            return {name: [tuple(r) for r in c.execute('SELECT * FROM ' + name + ' ORDER BY 1')]
                    for name in ('orders', 'paid_wallets', 'ledger')}, c.execute(
                        "SELECT balance FROM users WHERE id='synthetic-customer-sentinel'").fetchone()[0]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'synthetic.sqlite3')
        self.money_before = self.store.finances()
        self.clock = [int(time.time())]
        self.server = types.SimpleNamespace(Problem=Problem, digest=sha)
        with patch.dict(sys.modules, {'server': self.server}):
            registration = load('synthetic_registration', HERE / 'fixtures' / 'registration_entries.py')
        device = load('synthetic_device', HERE / 'fixtures' / 'account_link.py')
        fake_time = types.SimpleNamespace(time=lambda: self.clock[0])
        registration.time = fake_time
        device.time = fake_time
        self.store.registration_entries = registration.RegistrationEntries(self.store)
        self.store.device_links = device.DeviceLinks(self.store, self.server)
        self.wechat = load('synthetic_wechat', MODULE)
        self.wechat.time = fake_time
        self.wechat.config = lambda: dict(appid='synthetic-appid')
        self.identities = {}
        self.exchange_calls = 0

        def exchange(code):
            self.exchange_calls += 1
            return self.identities[code]
        self.wechat.exchange = exchange
        store = self.store

        class Parent(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(self, status, data):
                raw = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def run_request(self):
                if self.path == '/sentinel':
                    return self.send(200, dict(unchanged=True))
                try:
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    if self.path == '/platform-api/gemini/quick-entry':
                        data = store.registration_entries.prepare('gemini', body['install_secret'], '127.0.0.1')
                    elif self.path == '/platform-api/gemini/quick-entry/status':
                        data = store.registration_entries.status('gemini', body['install_secret'])
                    else:
                        raise Problem(404, '模拟：未实现的测试路由')
                    self.send(200, data)
                except Problem as error:
                    self.send(error.status, dict(error=error.message))
            do_GET = run_request
            do_POST = run_request

        handler = self.wechat.handler(Parent, store, self.server)
        if BASELINE:
            # Match the deployed outer listing wrapper's lifecycle dispatch; do
            # not confuse that pre-existing method-name collision with this bug.
            class Lifecycle(handler):
                def finish(self, *args):
                    return super().finish(*args) if args else BaseHTTPRequestHandler.finish(self)
            handler = Lifecycle
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.http.server_port)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.assertEqual(self.money_before, self.store.finances(), 'Synthetic pre-existing finances changed')
        self.tmp.cleanup()

    def request(self, path, body=None, cookie=None, origin='https://aistore.zhaopintong.com', marker='1'):
        headers = {'Origin': origin, 'X-Membership-Request': marker}
        if cookie:
            headers['Cookie'] = cookie
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(self.url + path, headers=headers,
                                     data=None if body is None else json.dumps(body).encode())
        try:
            response = self.opener.open(req, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read()
            data = json.loads(raw) if 'application/json' in response.headers.get('Content-Type', '') else raw.decode()
            return response.status, data, response.headers

    def entry(self, secret=None):
        secret = secret or secrets.token_urlsafe(32)
        status, data, _ = self.request('/platform-api/gemini/quick-entry', dict(install_secret=secret))
        self.assertEqual(status, 200)
        ticket = urllib.parse.parse_qs(urllib.parse.urlsplit(data['url']).fragment)['entry'][0]
        return secret, ticket, data

    def start(self, ticket, cookie=None, product='gemini', **fields):
        return self.request('/platform-api/wechat/start', dict(product=product, entry=ticket, accepted=True, **fields), cookie)

    def callback(self, start, identity='synthetic-wechat-A', cookie=None):
        code = secrets.token_hex(8)
        self.identities[code] = identity
        return self.request('/platform-api/wechat/callback?' + urllib.parse.urlencode(dict(state=start['state'], code=code)), cookie=cookie)

    def status(self, secret):
        status, data, _ = self.request('/platform-api/gemini/quick-entry/status', dict(install_secret=secret))
        self.assertEqual(status, 200)
        return data['status']

    def finish(self, start, **fields):
        return self.request('/platform-api/wechat/finish', dict(state=start['state'], verifier=start['verifier'], **fields))

    def begin(self):
        secret, ticket, _ = self.entry()
        status, start, headers = self.start(ticket)
        self.assertEqual(status, 200)
        return secret, ticket, start, headers

    def test_01_desktop_kept_open(self):
        secret, _, start, _ = self.begin()
        self.assertEqual(self.finish(start)[1]['status'], 'pending')
        self.assertEqual(self.callback(start)[0], 302)
        self.assertEqual(self.status(secret), 'registered')
        status, data, _ = self.finish(start)
        self.assertEqual((status, data['status'], data['url']), (200, 'linked', '/membership/gemini/'))

    def test_02_desktop_closed_no_finish_call(self):
        secret, _, start, _ = self.begin()
        status, _, headers = self.callback(start)
        self.assertEqual(status, 302)
        self.assertEqual(headers['Location'], '/membership/gemini/')
        self.assertTrue(any('platform_member=' in v for v in headers.get_all('Set-Cookie')))
        self.assertEqual(self.status(secret), 'registered')

    def test_03_same_browser_mobile_sets_session_and_redirects(self):
        secret, _, start, headers = self.begin()
        self.assertIsNone(headers.get('Set-Cookie'))
        status, _, result = self.callback(start)
        self.assertEqual(status, 302)
        self.assertEqual(result['Location'], '/membership/gemini/')
        cookies = result.get_all('Set-Cookie')
        self.assertTrue(any('platform_member=' in v and 'HttpOnly; Secure; SameSite=Strict' in v for v in cookies))
        self.assertFalse(any('Domain=' in v for v in cookies))
        self.assertEqual(self.status(secret), 'registered')

    def test_04_scan_in_sixth_minute_after_link_issue(self):
        secret, ticket, _ = self.entry()
        self.clock[0] += 360
        status, start, _ = self.start(ticket)
        self.assertEqual(status, 200)
        self.assertEqual(self.callback(start)[0], 302)
        self.assertEqual(self.status(secret), 'registered')

    def test_05_repeat_same_identity_is_idempotent(self):
        secret, _, start, _ = self.begin()
        self.assertEqual(self.callback(start)[0], 302)
        self.assertEqual(self.status(secret), 'registered')
        uid = self.store.user(secret)
        for _ in range(3):
            self.assertEqual(self.finish(start)[1]['status'], 'linked')
        second, _, again, _ = self.begin()
        self.assertEqual(self.callback(again)[0], 302)
        self.assertEqual(self.status(second), 'registered')
        self.assertEqual(self.store.user(second), uid)
        with self.store.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM wechat_identities').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM users WHERE balance=0').fetchone()[0], 1)
        self.assertEqual(self.store.registration_calls, 2)  # one per original install, not per finish

    def test_start_cannot_issue_a_member_session_before_oauth(self):
        _, _, _, headers = self.begin()
        self.assertIsNone(headers.get('Set-Cookie'))

    def test_callback_in_sixth_minute_after_qr_start(self):
        secret, _, start, _ = self.begin()
        self.clock[0] += 360
        self.assertEqual(self.callback(start)[0], 302)
        self.assertEqual(self.status(secret), 'registered')
        self.assertEqual(self.finish(start)[1]['status'], 'linked')

    def test_existing_bound_browser_reuses_original_account_without_scan(self):
        with self.store.connect() as c:
            c.execute('INSERT INTO wechat_identities VALUES(?,?,0)', ('synthetic-known', 'synthetic-customer-sentinel'))
        token = self.store.redeem(urllib.parse.parse_qs(urllib.parse.urlsplit(
            self.store.handoff('synthetic-customer-sentinel')['url']).fragment)['ticket'][0])
        secret, ticket, _ = self.entry()
        status, result, _ = self.start(ticket, cookie='platform_member=' + token)
        self.assertEqual((status, result['status']), (200, 'linked'))
        self.assertEqual(self.status(secret), 'registered')
        self.assertEqual(self.store.user(secret), 'synthetic-customer-sentinel')
        self.assertEqual(self.exchange_calls, 0)

    def test_scanner_browser_needs_no_initiator_cookie(self):
        secret, _, start, _ = self.begin()
        unrelated = self.store.redeem(urllib.parse.parse_qs(urllib.parse.urlsplit(
            self.store.handoff('synthetic-customer-sentinel')['url']).fragment)['ticket'][0])
        status, _, headers = self.callback(start, cookie='platform_member=' + unrelated)
        self.assertEqual(status, 302)
        jar = SimpleCookie()
        for value in headers.get_all('Set-Cookie'):
            jar.load(value)
        scanner_token = jar['platform_member'].value
        self.assertNotEqual(scanner_token, unrelated)
        self.assertEqual(self.store.web_user(scanner_token), self.store.user(secret))
        self.assertEqual(self.store.web_user(unrelated), 'synthetic-customer-sentinel')
        self.assertEqual(self.status(secret), 'registered')

    def test_phone_and_desktop_get_separate_sessions_for_same_identity(self):
        secret, _, start, _ = self.begin()
        status, _, phone = self.callback(start)
        self.assertEqual(status, 302)
        status, data, desktop = self.finish(start)
        self.assertEqual((status, data['status']), (200, 'linked'))
        tokens = []
        for headers in (phone, desktop):
            jar = SimpleCookie()
            for value in headers.get_all('Set-Cookie'):
                jar.load(value)
                self.assertNotIn('Domain=', value)
            tokens.append(jar['platform_member'].value)
        self.assertNotEqual(*tokens)
        self.assertTrue(all(self.store.web_user(token) == self.store.user(secret) for token in tokens))
        self.assertNotIn(tokens[0], phone['Location'])
        self.assertNotIn(tokens[1], data['url'])

    def test_finish_wrong_verifier_and_callback_replay(self):
        secret, _, start, _ = self.begin()
        bad = dict(start, verifier=secrets.token_urlsafe(32))
        self.assertEqual(self.finish(bad)[0], 401)
        self.assertEqual(self.callback(start)[0], 302)
        self.assertEqual(self.callback(start)[0], 401)
        self.assertEqual(self.exchange_calls, 1)
        self.assertEqual(self.finish(bad)[0], 401)
        self.assertEqual(self.store.registration_calls, 1)
        self.assertEqual(self.status(secret), 'registered')

    def test_finish_used_state_needs_no_pending_entry_and_audits_once(self):
        _, _, start, _ = self.begin()
        self.callback(start)
        self.store.registration_entries.pending.clear()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.finish(start), range(4)))
        self.assertTrue(all(r[0] == 200 and r[1]['status'] == 'linked' for r in results))
        self.assertEqual(self.store.registration_calls, 1)
        with self.store.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM wechat_login_audit').fetchone()[0], 1)

    def test_start_reserves_entry_until_oauth_deadline(self):
        secret, ticket, _ = self.entry()
        self.clock[0] += 1790
        status, start, _ = self.start(ticket)
        self.assertEqual(status, 200)
        self.clock[0] += 400
        self.entry()  # normal cleanup must retain the reserved entry
        self.assertEqual(self.callback(start)[0], 302)
        self.assertEqual(self.status(secret), 'registered')

    def test_expired_entry_and_state_are_rejected(self):
        _, ticket, _ = self.entry()
        self.clock[0] += 1801
        self.assertEqual(self.start(ticket)[0], 401)
        secret, _, start, _ = self.begin()
        self.clock[0] += 901
        self.assertEqual(self.callback(start)[0], 401)
        self.assertEqual(self.finish(start)[0], 401)
        self.assertEqual(self.status(secret), 'registration_pending')
        self.assertEqual(self.store.registration_calls, 0)

    def test_missing_entry_fails_closed(self):
        secret, _, start, _ = self.begin()
        self.store.registration_entries.pending.clear()
        self.assertEqual(self.callback(start)[0], 401)
        self.assertEqual(self.status(secret), 'registration_pending')

    def test_conflicting_identity_does_not_merge_accounts(self):
        secret = secrets.token_urlsafe(32)
        with self.store.connect() as c:
            c.execute("INSERT INTO users VALUES('synthetic-other',0)")
            c.execute('INSERT INTO trial_claims VALUES(?,?,0)', (sha(secret), 'synthetic-customer-sentinel'))
            c.execute("INSERT INTO wechat_identities VALUES('synthetic-wechat-B','synthetic-other',0)")
        _, ticket, _ = self.entry(secret)
        _, start, _ = self.start(ticket)
        self.assertEqual(self.callback(start, identity='synthetic-wechat-B')[0], 409)
        self.assertEqual(self.finish(start)[0], 409)
        self.assertEqual(self.store.user(secret), 'synthetic-customer-sentinel')
        self.assertEqual(self.store.registration_calls, 0)

    def test_account_already_bound_to_different_wechat(self):
        secret, ticket, _ = self.entry()
        self.store.register_product('gemini', secret, '127.0.0.1', True)
        uid = self.store.user(secret)
        with self.store.connect() as c:
            c.execute('INSERT INTO wechat_identities VALUES(?,?,0)', ('synthetic-first', uid))
        _, start, _ = self.start(ticket)
        self.assertEqual(self.callback(start, identity='synthetic-second')[0], 409)
        self.assertEqual(self.store.registration_calls, 1)

    def test_poll_while_exchange_in_progress_then_callback_completes(self):
        secret, _, start, _ = self.begin()
        entered, release = threading.Event(), threading.Event()
        def exchange(code):
            entered.set()
            self.assertTrue(release.wait(3))
            return 'synthetic-wechat-A'
        self.wechat.exchange = exchange
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            task = pool.submit(self.callback, start)
            self.assertTrue(entered.wait(3))
            self.assertEqual(self.finish(start)[1]['status'], 'pending')
            release.set()
            self.assertEqual(task.result()[0], 302)
        self.assertEqual(self.status(secret), 'registered')
        self.assertEqual(self.store.registration_calls, 1)

    def test_origin_consent_and_state_checks_remain(self):
        _, ticket, _ = self.entry()
        body = dict(product='gemini', entry=ticket, accepted=True)
        for origin in ('null', 'https://evil.example', 'https://sub.myplanestore.com'):
            self.assertEqual(self.request('/platform-api/wechat/start', body, origin=origin)[0], 403)
        self.assertEqual(self.request('/platform-api/wechat/start', body, marker='0')[0], 403)
        self.assertEqual(self.request('/platform-api/wechat/start', dict(body, accepted=False))[0], 400)
        self.assertEqual(self.request('/platform-api/wechat/callback?state=invalid&code=none')[0], 400)
        self.assertEqual(self.exchange_calls, 0)
        self.assertEqual(self.store.registration_calls, 0)

    def test_exchange_error_is_generic_and_no_registration(self):
        secret, _, start, _ = self.begin()
        def reject(code):
            raise RuntimeError('synthetic-secret-must-not-leak')
        self.wechat.exchange = reject
        status, body, _ = self.callback(start)
        self.assertEqual(status, 503)
        self.assertNotIn('synthetic-secret', json.dumps(body))
        self.assertEqual(self.finish(start)[0], 401)
        self.assertEqual(self.status(secret), 'registration_pending')

    def test_trade_still_requires_original_browser_code_at_finish(self):
        code = 'ABCD2345'
        with self.store.connect() as c:
            c.execute('INSERT INTO trade_links VALUES(?,NULL,?)', (sha(code), self.clock[0] + 300))
        status, start, _ = self.start(None, product='trade-leads', code=code)
        self.assertEqual((status, start['expires_in']), (200, 300))
        self.assertEqual(self.callback(start)[0], 200)
        self.assertEqual(self.finish(start)[0], 401)
        result = self.finish(start, code=code)
        self.assertEqual((result[0], result[1]['url']), (200, '/pay?skill=trade-leads'))
        self.assertEqual(self.store.registration_calls, 0)

    def test_unrelated_route_still_delegates(self):
        self.assertEqual(self.request('/sentinel')[:2], (200, dict(unchanged=True)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
