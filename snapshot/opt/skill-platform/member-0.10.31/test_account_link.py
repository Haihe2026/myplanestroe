"""Offline end-to-end test of scheme A on the real service chain (0.10.31 -> 0.10.29 -> ... -> 0.10.14).

Starts run_shared.py on loopback with fresh synthetic SQLite files from ../../../../schema, no provider key,
no SMTP. A cookie-keeping "phone browser" and cookie-less "skill client" talk to it over HTTP.
Requires the dev-container path layout (/opt/skill-platform, /opt/temu-image-assistant).

    python3 test_account_link.py            # exit 0 = all passed
"""
import http.cookies
import json
import os
import secrets
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = Path(os.environ.get('MYPLANESTORE_SCHEMA_DIR') or
              (HERE.parents[3] / 'schema' if (HERE.parents[3] / 'schema').is_dir() else '/workspace/schema'))
ENTRY = Path('/opt/skill-platform/member-0.10.31/run_shared.py')
PORT = int(os.environ.get('ACCOUNT_LINK_TEST_PORT', '18931'))
ORIGIN = 'https://myplanestore.com'
T = '/platform-api/temu'
RESULTS = []


class Browser:
    def __init__(self, origin=ORIGIN):
        self.jar, self.origin, self.raw_cookies = {}, origin, []

    def call(self, method, path, body=None, web=True):
        headers = {}
        data = None
        if body is not None:
            data, headers['Content-Type'] = json.dumps(body).encode(), 'application/json'
        if web:
            headers.update({'Origin': self.origin, 'X-Membership-Request': '1'})
            if self.jar:
                headers['Cookie'] = '; '.join('%s=%s' % kv for kv in self.jar.items())
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (PORT, path), data=data, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            status = resp.status
        except urllib.error.HTTPError as error:
            resp, status = error, error.code
        raw = resp.read()
        for header in resp.headers.get_all('Set-Cookie') or []:
            self.raw_cookies.append(header)
            parsed = http.cookies.SimpleCookie()
            parsed.load(header)
            for name, morsel in parsed.items():
                if morsel['max-age'] == '0' or not morsel.value:
                    self.jar.pop(name, None)
                else:
                    self.jar[name] = morsel.value
        try:
            return status, json.loads(raw)
        except ValueError:
            return status, raw


def skill(method, path, body=None):
    return Browser().call(method, path, body, web=False)


def entry_of(result):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(result['url']).fragment)['entry'][0]


def new_conversation():
    secret = secrets.token_urlsafe(32)
    status, result = skill('POST', T + '/quick-entry', {'install_secret': secret})
    assert status == 200 and result['status'] == 'registration', (status, result)
    return secret, entry_of(result)


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok), detail))


def start(work):
    dbs = {k: work / (k + '.db') for k in ('shared', 'events', 'gemini-legacy', 'temu-legacy')}
    for label, path in dbs.items():
        db = sqlite3.connect(path)
        db.executescript((SCHEMA / (label + '.sql')).read_text())
        db.commit()
        db.close()
    env = dict(os.environ, IMAGE_TRIAL_HMAC_KEY=secrets.token_urlsafe(32), IMAGE_PUBLIC_TRIAL_ENABLED='yes',
               SKILL_EVENTS_DB=str(dbs['events']), SKILL_JOURNEY_DB=str(work / 'journey.db'),
               GEMINI_PERSONAL_TRIAL_POOL_IMAGES='20', IMAGE_MANUAL_QR_ENABLED='yes')
    for key in ('IMAGE_PROVIDER_KEY', 'IMAGE_PROVIDER_CONFIRMED', 'MYPLANESTORE_DEVICE_DAYS', 'MYPLANESTORE_DEVICE_LINK_PRODUCTS'):
        env.pop(key, None)
    log = open(work / 'service.log', 'w')
    proc = subprocess.Popen([sys.executable, str(ENTRY), '--db', str(dbs['shared']), '--gemini-db', str(dbs['gemini-legacy']),
                             '--temu-db', str(dbs['temu-legacy']), '--temu-source', '/opt/temu-image-assistant/0.2.2/service',
                             '--port', str(PORT)], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(80):
        try:
            urllib.request.urlopen('http://127.0.0.1:%d%s/health' % (PORT, T), timeout=2).read()
            return proc, dbs['shared']
        except Exception:
            if proc.poll() is not None:
                break
            time.sleep(0.25)
    raise SystemExit('service did not start:\n' + (work / 'service.log').read_text()[-3000:])


def main():
    work = Path(tempfile.mkdtemp(prefix='account-link-'))
    proc, shared_db = start(work)
    try:
        phone = Browser()

        # 1. First conversation, new merchant: unchanged path, but the browser is now remembered.
        s1, e1 = new_conversation()
        status, r = phone.call('GET', T + '/membership-api/remembered')
        check('01 unknown browser: remembered=false', status == 200 and r == {'remembered': False}, r)
        status, r = phone.call('POST', T + '/membership-api/confirm-entry', {'ticket': e1, 'accepted': True})
        device_headers = [h for h in phone.raw_cookies if h.startswith('mps_device=')]
        check('02 new-account confirm still works and sets a remembered-browser cookie',
              status == 200 and r.get('ok') is True and len(device_headers) == 1, (status, r))
        flags = device_headers[0] if device_headers else ''
        check('03 cookie flags: HttpOnly, Secure, SameSite=Strict, Path=/platform-api/, 180 days',
              all(f in flags for f in ('HttpOnly', 'Secure', 'SameSite=Strict', 'Path=/platform-api/', 'Max-Age=15552000')), flags)
        status, reg1 = skill('POST', T + '/register', {'install_secret': s1, 'accepted': True})
        uid1_label = phone.call('GET', T + '/membership-api/account')[1].get('account_label')
        check('04 first account: 1 Temu trial, no linked_existing flag',
              reg1.get('trial_total') == 1 and reg1.get('trial_remaining') == 1 and 'linked_existing' not in reg1, reg1)
        with sqlite3.connect(shared_db) as c:
            stored = [r[0] for r in c.execute('SELECT hash FROM remembered_devices')]
        check('05 only the SHA-256 of the cookie is stored', stored and phone.jar['mps_device'] not in stored and len(stored[0]) == 64)

        # Paid merchant: give the account 5 shared uses directly in the synthetic DB.
        with sqlite3.connect(shared_db) as c:
            uid1 = c.execute('SELECT user_id FROM trial_claims').fetchone()[0]
            c.execute('UPDATE users SET balance=5 WHERE id=?', (uid1,))
        status, r = phone.call('GET', T + '/membership-api/remembered')
        check('06 remembered browser: same account label and real remaining uses',
              status == 200 and r.get('remembered') is True and r.get('account_label') == uid1_label and r.get('remaining_uses') == 6, r)

        # 2. New WorkBuddy conversation (rebuilt sandbox), same phone browser -> link instead of new account.
        s2, e2 = new_conversation()
        phone.jar.pop('platform_member', None)  # 30-minute web session long gone
        status, r = phone.call('POST', T + '/membership-api/link-entry', {'ticket': e2, 'accepted': False})
        check('07 link requires explicit consent', status == 400, (status, r))
        status, r = phone.call('POST', T + '/membership-api/link-entry', {'ticket': e2, 'accepted': True})
        check('08 link-entry attaches the new conversation', status == 200 and r == {'ok': True, 'linked': True}, (status, r))
        status, r = skill('POST', T + '/quick-entry/status', {'install_secret': s2})
        check('09 skill sees registered', r.get('status') == 'registered', r)
        status, reg2 = skill('POST', T + '/register', {'install_secret': s2, 'accepted': True})
        check('10 /register: same account, linked_existing=true, uses kept, no second trial',
              reg2.get('linked_existing') is True and reg2.get('created') is False and reg2.get('remaining_uses') == 6
              and reg2.get('trial_total') == 1, reg2)
        with sqlite3.connect(shared_db) as c:
            users = c.execute('SELECT count(*) FROM users').fetchone()[0]
            uid2 = c.execute('SELECT user_id FROM trial_claims WHERE hash=(SELECT identity_hash FROM device_entry_links)').fetchone()[0]
            trials = c.execute('SELECT count(*) FROM temu_enterprise_trials').fetchone()[0]
            audit = [r[0] for r in c.execute('SELECT kind FROM device_link_audit ORDER BY id')]
        check('11 still exactly one account and one trial row; mapped to the original account',
              users == 1 and trials == 1 and uid2 == uid1, (users, trials))
        status, r = phone.call('GET', T + '/membership-api/account')
        check('12 page can read the account right after linking (web session issued)', status == 200 and r.get('remaining_uses') == 6, r)
        check('13 audit trail: remembered, then conversation_linked',
              audit[:1] == ['device_remembered'] and 'conversation_linked' in audit, audit)
        status, r = phone.call('POST', T + '/membership-api/link-entry', {'ticket': e2, 'accepted': True})
        check('14 the same link cannot be used twice', status == 401, (status, r))

        # 3. Abuse / safety checks
        s3, e3 = new_conversation()
        stranger = Browser()
        status, r = stranger.call('POST', T + '/membership-api/link-entry', {'ticket': e3, 'accepted': True})
        check('15 browser without remembered login cannot link', status == 401, (status, r))
        evil = Browser(origin='https://evil.example')
        evil.jar = dict(phone.jar)
        status, r = evil.call('POST', T + '/membership-api/link-entry', {'ticket': e3, 'accepted': True})
        check('16 cross-site POST rejected (Origin check)', status == 403, (status, r))
        forged = Browser()
        forged.jar = {'mps_device': secrets.token_urlsafe(32)}
        status, r = forged.call('GET', T + '/membership-api/remembered')
        check('17 forged cookie is not recognised', r == {'remembered': False}, r)
        status, r = phone.call('GET', '/platform-api/gemini/membership-api/remembered')
        check('18 Gemini pages unchanged by default (feature scoped to Temu)', status == 404, (status, r))

        # 4. "不是我，用新账户" on a remembered browser: existing new-account path, browser now remembers the new account.
        s4, e4 = new_conversation()
        friend_phone = Browser()
        friend_phone.jar = dict(phone.jar)
        status, r = friend_phone.call('POST', T + '/membership-api/confirm-entry', {'ticket': e4, 'accepted': True})
        status, r = friend_phone.call('GET', T + '/membership-api/remembered')
        check('19 choosing a new account switches the remembered account (old cookie revoked)',
              r.get('remembered') is True and r.get('account_label') != uid1_label, r)
        status, r = phone.call('GET', T + '/membership-api/remembered')
        check('20 the replaced cookie no longer works anywhere', r == {'remembered': False}, r)

        # 5. Sign this browser out
        phone2 = Browser()
        s5, e5 = new_conversation()
        phone2.call('POST', T + '/membership-api/confirm-entry', {'ticket': e5, 'accepted': True})
        status, r = phone2.call('POST', T + '/membership-api/forget-device', {})
        status2, r2 = phone2.call('GET', T + '/membership-api/remembered')
        check('21 forget-device signs the browser out', status == 200 and 'mps_device' not in phone2.jar and r2 == {'remembered': False}, (r, r2))

        # 6. Membership page opened from the skill (我的账户/充值) also remembers the browser.
        status, r = skill('POST', T + '/register', {'install_secret': s5, 'accepted': True})
        req = urllib.request.Request('http://127.0.0.1:%d%s/membership-link' % (PORT, T), data=b'{}', method='POST',
                                     headers={'Authorization': 'Bearer ' + s5, 'Content-Type': 'application/json'})
        link = json.loads(urllib.request.urlopen(req, timeout=15).read())
        ticket = urllib.parse.parse_qs(urllib.parse.urlsplit(link['url']).fragment)['ticket'][0]
        laptop = Browser()
        status, r = laptop.call('POST', T + '/membership-api/redeem', {'ticket': ticket})
        status2, r2 = laptop.call('GET', T + '/membership-api/remembered')
        check('22 opening 我的账户 from the skill remembers that browser too',
              status == 200 and r2.get('remembered') is True, (status, r, r2))

        # 7. Existing regressions on the same process
        status, r = skill('POST', T + '/quick-entry', {'install_secret': s1})
        check('23 known conversation still gets ready/checkout, not a registration link',
              r.get('status') in ('ready', 'checkout'), r.get('status'))
        status, r = skill('GET', T + '/render-info')
        check('24 Temu async delivery route still served by 0.10.28', status == 200 and r.get('contract') == 'temu-render-v1', r)
    finally:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    width = max(len(n) for n, _, _ in RESULTS)
    for name, ok, detail in RESULTS:
        print(('PASS ' if ok else 'FAIL ') + name.ljust(width) + ('' if ok else '   ' + str(detail)[:300]))
    passed = sum(ok for _, ok, _ in RESULTS)
    print('\n%d/%d passed (offline synthetic test; no real accounts, payments or provider)' % (passed, len(RESULTS)))
    return 0 if passed == len(RESULTS) else 1


if __name__ == '__main__':
    sys.exit(main())
