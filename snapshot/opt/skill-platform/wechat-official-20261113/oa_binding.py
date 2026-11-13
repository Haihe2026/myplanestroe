"""Official-account OAuth, additive identities and one-use cross-host handoff.

Old website-application states continue through the unmodified legacy handler.
OAuth secrets, raw openids and code exchange URLs never enter responses/logs.
"""
import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import secrets
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie

ORIGINS = ('https://myplanestore.com', 'https://aistore.zhaopintong.com')
CALLBACK_ORIGIN = 'https://www.myplanestore.com'
CALLBACK = CALLBACK_ORIGIN + '/platform-api/wechat/callback'
PRODUCTS = ('gemini', 'temu', 'pet', 'trade-leads')
OAUTH_TTL = 900
LEGACY_PATH = '/opt/skill-platform/trade-link-fix-20261111/wechat_binding.py'
LOCK = threading.RLock()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def valid(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{43}', value) is not None


def cookie(headers, name):
    try:
        item = SimpleCookie(headers.get('Cookie', '')).get(name)
        return item.value if item else None
    except Exception:
        return None


def config():
    p = Path(os.environ.get('WECHAT_OFFICIAL_CONFIG_FILE', '/etc/skill-platform/wechat-official.json'))
    if os.name != 'nt' and p.stat().st_mode & 0o077:
        raise RuntimeError('Private official-account configuration required')
    value = json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or not re.fullmatch(r'wx[A-Za-z0-9]{16}', value.get('appid', '')) or not re.fullmatch(r'[A-Za-z0-9]{32}', value.get('secret', '')):
        raise RuntimeError('Invalid official-account configuration')
    return value


def exchange(code, expected_app_tag):
    cfg = config()
    if not hmac.compare_digest(digest(cfg['appid']), expected_app_tag):
        raise ValueError('Authorization application changed')
    target = 'https://api.weixin.qq.com/sns/oauth2/access_token?' + urllib.parse.urlencode(dict(
        appid=cfg['appid'], secret=cfg['secret'], code=code, grant_type='authorization_code'))
    try:
        with urllib.request.urlopen(target, timeout=10) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError()
        result = json.loads(raw)
        if result.get('errcode') or not isinstance(result.get('openid'), str) or not 1 <= len(result['openid']) <= 128:
            raise ValueError()
        # AppID scoped: there is no safe implicit migration from another app's
        # OpenID, and the old service never recorded UnionID.
        return digest('official:' + cfg['appid'] + ':' + result['openid'])
    except Exception:
        raise ValueError('Official-account authorization rejected') from None


def load_legacy():
    name = '_mps_legacy_website_wechat_binding'
    if name not in sys.modules:
        path = os.environ.get('WECHAT_LEGACY_MODULE', LEGACY_PATH)
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def official_bound(store, uid):
    if not uid:
        return False
    tag = digest(config()['appid'])
    with store.connect() as c:
        return c.execute('SELECT 1 FROM wechat_oa_identities WHERE app_tag=? AND user_id=?', (tag, uid)).fetchone() is not None


def install_metered_compat():
    module = sys.modules.get('metered')
    if module is None or getattr(module, '_official_wechat_bound_installed', False):
        return
    previous = module.bound
    def bound(store, uid):
        return previous(store, uid) or official_bound(store, uid)
    module.bound = bound
    module._official_wechat_bound_installed = True


class OfficialService:
    def __init__(self, store, server, lock=LOCK):
        self.store, self.Problem, self.server, self.lock = store, server.Problem, server, lock
        from wechat_entries import EntryCache
        self.cache = EntryCache(store)
        with store.connect() as c:
            c.executescript('''
              CREATE TABLE IF NOT EXISTS wechat_oa_identities(
                app_tag TEXT NOT NULL, identity TEXT NOT NULL, user_id TEXT NOT NULL,
                created INTEGER NOT NULL, PRIMARY KEY(app_tag,identity), UNIQUE(app_tag,user_id));
              CREATE TABLE IF NOT EXISTS wechat_oa_states(
                hash TEXT PRIMARY KEY, verifier TEXT NOT NULL, scan_hash TEXT NOT NULL,
                mobile_hash TEXT, app_tag TEXT NOT NULL, product TEXT NOT NULL,
                entry_hash TEXT, source_uid TEXT, identity TEXT, status TEXT NOT NULL,
                expires INTEGER NOT NULL, created INTEGER NOT NULL, origin TEXT NOT NULL,
                return_path TEXT NOT NULL, context BLOB);
              CREATE TABLE IF NOT EXISTS wechat_oa_handoffs(
                hash TEXT PRIMARY KEY, state_hash TEXT NOT NULL, expires INTEGER NOT NULL,
                used INTEGER NOT NULL DEFAULT 0);
            ''')

    def row(self, state):
        if not valid(state):
            return None
        with self.store.connect() as c:
            return c.execute('SELECT * FROM wechat_oa_states WHERE hash=?', (digest(state),)).fetchone()

    def require_row(self, state):
        row = self.row(state)
        if row is None or row['expires'] <= time.time():
            raise self.Problem(401, '二维码已过期，请重新扫码')
        return row

    def current(self, headers):
        try:
            return self.store.membership.web_user(cookie(headers, 'platform_member'))
        except self.Problem:
            return self.store.device_links.lookup(cookie(headers, 'mps_device'))

    def session(self, uid):
        handoff = self.store.membership.handoff(uid)
        ticket = urllib.parse.parse_qs(urllib.parse.urlsplit(handoff['url']).fragment)['ticket'][0]
        return self.store.membership.redeem(ticket)

    def return_path(self, product, raw):
        default = '/pay?skill=trade-leads' if product == 'trade-leads' else '/membership/listing/' if product == 'listing-optimizer' else '/membership/' + product + '/'
        if raw is None:
            return default
        if not isinstance(raw, str) or len(raw) > 250 or any(ch in raw for ch in ('\\', '\r', '\n')):
            raise self.Problem(400, '请使用对应服务的付款入口')
        value = urllib.parse.urlsplit(raw)
        if value.scheme or value.netloc or value.fragment:
            raise self.Problem(400, '请使用对应服务的付款入口')
        if product != 'listing-optimizer':
            allowed = [default] + (['/membership/'] if product == 'gemini' else [])
            if raw not in allowed:
                raise self.Problem(400, '请使用对应服务的付款入口')
            return raw
        if value.path != '/membership/listing/':
            raise self.Problem(400, '请使用对应服务的付款入口')
        if not value.query:
            return default
        query = urllib.parse.parse_qs(value.query, strict_parsing=True)
        if set(query) != {'skill'} or len(query['skill']) != 1:
            raise self.Problem(400, '请使用对应服务的付款入口')
        sid = query['skill'][0]
        if not re.fullmatch(r'[a-z][a-z0-9_-]{2,63}', sid):
            raise self.Problem(400, '请选择有效的服务')
        module = sys.modules.get('metered')
        services = module.services() if module else {}
        if sid != 'listing-optimizer' and sid not in services:
            raise self.Problem(400, '请选择已开通的服务')
        return '/membership/listing/?skill=' + sid

    def _seal(self, key, context):
        nonce = os.urandom(12)
        return nonce + self.cache.cipher.encrypt(nonce, json.dumps(context).encode(), ('oa:' + key).encode())

    def _unseal(self, row):
        data = row['context']
        if not data:
            return {}
        return json.loads(self.cache.cipher.decrypt(data[:12], data[12:], ('oa:' + row['hash']).encode()))

    def observe_trade(self, event, row, uid):
        """Best-effort parity with the existing funnel, never an auth decision."""
        if row['product'] != 'trade-leads' or not isinstance(row['entry_hash'], str) or not re.fullmatch(r'trade:[0-9a-f]{64}', row['entry_hash']):
            return
        module = sys.modules.get('trade_funnel_gateway')
        if module is None:
            return
        try:
            observer = module.runtime(self.store)
            if event == 'oauth_started':
                observer.oauth_started(row['entry_hash'][6:], uid)
            elif event == 'identity_confirmed':
                observer.identity_confirmed(row['entry_hash'][6:], uid)
        except Exception:
            pass

    def known(self, uid, app_tag):
        with self.store.connect() as c:
            new = c.execute('SELECT 1 FROM wechat_oa_identities WHERE app_tag=? AND user_id=?', (app_tag, uid)).fetchone()
            old = c.execute('SELECT 1 FROM wechat_identities WHERE user_id=?', (uid,)).fetchone()
        return bool(new or old)

    def start(self, body, headers, ip):
        if body.get('accepted') is not True:
            raise self.Problem(400, '请先同意隐私政策与账户绑定')
        product = body.get('product', 'gemini')
        if product not in PRODUCTS:
            raise self.Problem(400, '请选择对应技能')
        origin = headers.get('Origin')
        if origin not in ORIGINS:
            raise self.Problem(403, '请从本站操作')
        target = self.return_path(product, body.get('return_path'))
        cfg = config()
        app_tag = digest(cfg['appid'])
        uid = browser_uid = self.current(headers)
        entry, trade_code = body.get('entry') or None, body.get('code') or None
        if entry and trade_code:
            raise self.Problem(400, '请使用一种有效的账户入口')
        entries = self.store.registration_entries
        if entry:
            if not valid(entry):
                raise self.Problem(401, '请从原技能重新打开')
            with entries.lock:
                row = entries.pending.get(self.server.digest(entry))
                if row and row['product'] != product:
                    raise self.Problem(401, '请使用对应服务的账户入口')
                if row:
                    self.cache.remember(self.server.digest(entry), row)
                restored = self.cache.restore(self.server.digest(entry), product)
                if restored:
                    row = restored
                    entries.pending[self.server.digest(entry)] = row
                if row and row['expires'] > time.time():
                    try:
                        original = self.store.user(row['secret'])
                    except self.Problem:
                        original = None
                    if uid and original and uid != original and body.get('force_scan') is not True:
                        raise self.Problem(409, '账户不一致，请保留原账户联系客服')
                    uid = original or uid
                else:
                    uid = self.cache.linked(self.server.digest(entry), product) or uid
                    entry = None
        elif trade_code:
            if product != 'trade-leads' or not re.fullmatch(r'[A-Z2-9]{8}', trade_code):
                raise self.Problem(400, '外贸获客入口无效')
            with self.store.connect() as c:
                row = c.execute('SELECT account_id FROM trade_links WHERE code_hash=? AND expires>?', (digest(trade_code), time.time())).fetchone()
            if row is None:
                raise self.Problem(401, '关联入口已过期，请从原技能重新打开')
            if uid and row[0] and uid != row[0] and body.get('force_scan') is not True:
                raise self.Problem(409, '账户不一致，请联系客服')
            uid = row[0] or uid
        # Already authenticated browsers retain device memory, even for a
        # historical website-app binding. This does not migrate an unknown ID.
        if body.get('force_scan') is not True and uid and uid == browser_uid and self.known(uid, app_tag):
            if trade_code:
                self.store.trade.approve(trade_code, uid)
            if entry:
                device = self.store.device_links.issue(uid, cookie(headers, 'mps_device'), product)
                raw = SimpleCookie(device)['mps_device'].value
                token = self.store.device_links.link_entry(product, entry, True, raw)
                self.cache.consume(self.server.digest(entry), uid)
                return dict(status='linked', product=product, url=target, return_path=target), [device, self.member_cookie(token)]
            return dict(status='linked', product=product, url=target, return_path=target), self.account_cookies(uid, product, headers)
        state, verifier, scan = (secrets.token_urlsafe(32) for _ in range(3))
        now, ttl = int(time.time()), OAUTH_TTL
        key = digest(state)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('DELETE FROM wechat_oa_handoffs WHERE expires<?', (now,))
            c.execute('DELETE FROM wechat_oa_states WHERE expires<?', (now,))
            if c.execute('SELECT count(*) FROM wechat_oa_states').fetchone()[0] >= 2048:
                raise self.Problem(429, '登录请求较多，请稍后重试')
            c.execute('INSERT INTO wechat_oa_states VALUES(?,?,?,NULL,?,?,?,?,NULL,?,?,?,?,?,?)', (
                key, digest(verifier), digest(scan), app_tag, product,
                self.server.digest(entry) if entry else ('trade:' + digest(trade_code) if trade_code else None), uid,
                'pending', now + ttl, now, origin, target, self._seal(key, {'trade_code': trade_code})))
        query = urllib.parse.urlencode(dict(state=state, scan=scan))
        authorize = CALLBACK_ORIGIN + '/platform-api/wechat/oa/authorize?' + query
        self.observe_trade('oauth_started', self.row(state), uid)
        return dict(mode='official_account', state=state, verifier=verifier,
                    qr_url='/platform-api/wechat/oa/qr?' + query,
                    authorize_url=authorize, url=authorize, expires_in=ttl), []

    def member_cookie(self, token):
        return 'platform_member=' + token + '; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800'

    def account_cookies(self, uid, product, headers):
        token = self.session(uid)
        return [self.store.device_links.issue(uid, cookie(headers, 'mps_device'), product), self.member_cookie(token)]

    def scan(self, state, scan):
        row = self.require_row(state)
        if not valid(scan) or not hmac.compare_digest(row['scan_hash'], digest(scan)) or row['status'] != 'pending':
            raise self.Problem(401, '二维码已失效，请重新扫码')
        return row

    def authorize(self, state, scan):
        with self.lock:
            row = self.scan(state, scan)
            cfg = config()
            if digest(cfg['appid']) != row['app_tag']:
                raise self.Problem(401, '二维码已更新，请重新扫码')
            mobile = secrets.token_urlsafe(32)
            with self.store.connect() as c:
                c.execute("UPDATE wechat_oa_states SET mobile_hash=? WHERE hash=? AND status='pending'", (digest(mobile), row['hash']))
        name = 'mps_oa_' + row['hash'][:24]
        ttl = min(OAUTH_TTL, max(0, int(row['expires'] - time.time())))
        proof = name + '=' + mobile + '; HttpOnly; Secure; SameSite=Lax; Path=/platform-api/wechat/; Max-Age=' + str(ttl)
        url = 'https://open.weixin.qq.com/connect/oauth2/authorize?' + urllib.parse.urlencode(dict(
            appid=cfg['appid'], redirect_uri=CALLBACK, response_type='code', scope='snsapi_base', state=state)) + '#wechat_redirect'
        return url, proof

    def complete(self, row, ip):
        if row['status'] == 'used':
            return row['source_uid']
        if row['status'] != 'approved' or not row['identity']:
            raise self.Problem(401, '扫码未完成，请重新扫码')
        with self.store.connect() as c:
            known = c.execute('SELECT user_id FROM wechat_oa_identities WHERE app_tag=? AND identity=?', (row['app_tag'], row['identity'])).fetchone()
        uid = row['source_uid']
        if uid and known and uid != known[0]:
            raise self.Problem(409, '该微信已绑定其他账户，不会合并或替换余额')
        uid = uid or (known[0] if known else None)
        if uid:
            with self.store.connect() as c:
                other = c.execute('SELECT identity FROM wechat_oa_identities WHERE app_tag=? AND user_id=?', (row['app_tag'], uid)).fetchone()
            if other and other[0] != row['identity']:
                raise self.Problem(409, '原账户已绑定其他微信，请联系客服')
        entries = self.store.registration_entries
        with entries.lock:
            trade = bool(row['entry_hash'] and row['entry_hash'].startswith('trade:'))
            pending = None
            if row['entry_hash'] and not trade:
                pending = self.cache.restore(row['entry_hash'], row['product'])
                if pending is None:
                    pending = entries.pending.get(row['entry_hash'])
                if pending and (pending['product'] != row['product'] or pending['expires'] <= time.time()):
                    raise self.Problem(401, '请重新打开对应服务的账户入口')
                if pending is None:
                    linked = self.cache.linked(row['entry_hash'], row['product'])
                    if linked is None:
                        # A verified scan must not silently abandon the original
                        # Skill credential and create an unrelated web account.
                        raise self.Problem(401, '原账户入口已失效，请从原技能重新打开')
                    if uid and linked != uid:
                        raise self.Problem(409, '原对话关联了其他账户，请联系客服')
                    uid = linked
            if trade:
                code = self._unseal(row).get('trade_code')
                if not isinstance(code, str) or not re.fullmatch(r'[A-Z2-9]{8}', code) or 'trade:' + digest(code) != row['entry_hash']:
                    raise self.Problem(401, '请从原外贸获客入口继续')
                uid = self.store.trade.approve(code, uid)
            if pending:
                if uid:
                    with self.store.connect() as c:
                        c.execute('BEGIN IMMEDIATE')
                        prior = c.execute('SELECT user_id FROM trial_claims WHERE hash=?', (self.server.digest(pending['secret']),)).fetchone()
                        if prior and prior[0] != uid:
                            raise self.Problem(409, '原对话关联了其他账户，请联系客服')
                        c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)', (self.server.digest(pending['secret']), uid, int(time.time())))
                self.store.register_product(row['product'], pending['secret'], pending['ip'], True)
                uid = self.store.user(pending['secret'])
            if not uid:
                secret = self.cache.registration_secret('official:' + row['app_tag'] + ':' + row['identity'])
                product = 'gemini' if row['product'] == 'trade-leads' else row['product']
                self.store.register_product(product, secret, ip[:64], True)
                uid = self.store.user(secret)
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                other = c.execute('SELECT identity FROM wechat_oa_identities WHERE app_tag=? AND user_id=?', (row['app_tag'], uid)).fetchone()
                known = c.execute('SELECT user_id FROM wechat_oa_identities WHERE app_tag=? AND identity=?', (row['app_tag'], row['identity'])).fetchone()
                if (other and other[0] != row['identity']) or (known and known[0] != uid):
                    raise self.Problem(409, '该微信或原账户已存在绑定，请联系客服')
                c.execute('INSERT OR IGNORE INTO wechat_oa_identities VALUES(?,?,?,?)', (row['app_tag'], row['identity'], uid, int(time.time())))
                c.execute("UPDATE wechat_oa_states SET source_uid=?,status='used',context=NULL WHERE hash=? AND status='approved'", (uid, row['hash']))
                # Keep the existing audit vocabulary so older journey readers
                # continue to observe completed bindings. Provider proof remains
                # in the separate, app-scoped official-account identity table.
                c.execute('INSERT INTO wechat_login_audit(kind,product,created) VALUES(?,?,?)', ('wechat_bound', row['product'], int(time.time())))
            if pending:
                self.cache.consume(row['entry_hash'], uid)
                entries.pending.pop(row['entry_hash'], None)
        self.observe_trade('identity_confirmed', row, uid)
        return uid

    def callback(self, state, code, headers, ip):
        with self.lock:
            row = self.require_row(state)
            proof = cookie(headers, 'mps_oa_' + row['hash'][:24])
            if not valid(proof) or not row['mobile_hash'] or not hmac.compare_digest(digest(proof), row['mobile_hash']):
                raise self.Problem(401, '请使用手机微信重新扫码')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', code or ''):
                raise self.Problem(400, '微信授权已取消，请重新扫码')
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                updated = c.execute("UPDATE wechat_oa_states SET status='exchanging' WHERE hash=? AND status='pending' AND expires>?", (row['hash'], time.time()))
                if updated.rowcount != 1:
                    raise self.Problem(401, '授权已使用或过期，请重新扫码')
        try:
            identity = exchange(code, row['app_tag'])
        except Exception:
            with self.store.connect() as c:
                c.execute("UPDATE wechat_oa_states SET status='failed' WHERE hash=? AND status='exchanging'", (row['hash'],))
            raise self.Problem(503, '微信授权未完成，请在原页面重新扫码') from None
        with self.lock:
            with self.store.connect() as c:
                updated = c.execute("UPDATE wechat_oa_states SET identity=?,status='approved' WHERE hash=? AND status='exchanging' AND expires>?", (identity, row['hash'], time.time()))
                if updated.rowcount != 1:
                    raise self.Problem(401, '二维码已过期，请重新扫码')
            row = self.require_row(state)
            self.complete(row, ip)
            ticket = secrets.token_urlsafe(32)
            with self.store.connect() as c:
                c.execute('INSERT INTO wechat_oa_handoffs VALUES(?,?,?,0)', (digest(ticket), row['hash'], min(row['expires'], int(time.time()) + 120)))
        return row['origin'] + '/auth/wechat/oa-complete.html#ticket=' + ticket

    def finish(self, state, verifier, headers, ip):
        with self.lock:
            row = self.require_row(state)
            if not valid(verifier) or not hmac.compare_digest(row['verifier'], digest(verifier)):
                raise self.Problem(401, '请重新扫码')
            if row['status'] in ('pending', 'exchanging'):
                return dict(status='pending'), []
            uid = self.complete(row, ip)
            return dict(status='linked', product=row['product'], url=row['return_path'], return_path=row['return_path']), self.account_cookies(uid, row['product'], headers)

    def redeem(self, ticket, headers):
        if not valid(ticket):
            raise self.Problem(401, '登录链接已过期，请重新扫码')
        with self.lock:
            with self.store.connect() as c:
                handoff = c.execute('SELECT * FROM wechat_oa_handoffs WHERE hash=? AND expires>? AND used=0', (digest(ticket), time.time())).fetchone()
                if handoff is None:
                    raise self.Problem(401, '登录链接已使用或过期，请重新扫码')
                row = c.execute("SELECT * FROM wechat_oa_states WHERE hash=? AND status='used' AND expires>?", (handoff['state_hash'], time.time())).fetchone()
                if row is None or headers.get('Origin') != row['origin']:
                    raise self.Problem(403, '请从原账户页面继续')
            # Session/device issuance owns its own transactions. Complete it
            # before consuming the one-use ticket so a transient internal
            # failure leaves the mobile handoff retryable. No Cookie is sent
            # until the final guarded consume succeeds.
            cookies = self.account_cookies(row['source_uid'], row['product'], headers)
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                updated = c.execute('UPDATE wechat_oa_handoffs SET used=1 WHERE hash=? AND used=0 AND expires>?', (digest(ticket), time.time()))
                if updated.rowcount != 1:
                    raise self.Problem(401, '登录链接已使用或过期，请重新扫码')
            return dict(status='linked', product=row['product'], url=row['return_path'], return_path=row['return_path']), cookies


def handler(parent, store, server):
    legacy = load_legacy()
    Legacy = legacy.handler(parent, store, server)
    service = OfficialService(store, server, lock=legacy.LOCK)
    store.official_wechat = service
    install_metered_compat()
    Problem = server.Problem

    class Handler(Legacy):
        def oa_ip(self):
            return self.headers.get('X-Real-IP', self.client_address[0]) if self.client_address[0] in ('127.0.0.1', '::1') else self.client_address[0]

        def oa_body(self):
            if self.headers.get('Origin') not in ORIGINS or self.headers.get('X-Membership-Request') != '1':
                raise Problem(403, '请从本站操作')
            n = int(self.headers.get('Content-Length', '0'))
            if not 0 < n <= 4096 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise Problem(400, '请求格式无效')
            value = json.loads(self.rfile.read(n))
            if not isinstance(value, dict):
                raise Problem(400, '请求格式无效')
            return value

        def run_request(self):
            path = urllib.parse.urlsplit(self.path).path
            if path not in ('/platform-api/wechat/oa/qr', '/platform-api/wechat/oa/authorize', '/platform-api/wechat/oa/redeem', '/platform-api/wechat/status'):
                return super().run_request()
            try:
                self.connection.settimeout(15)
                if path == '/platform-api/wechat/status' and self.command == 'GET':
                    uid = service.current(self.headers)
                    return self.send(200, dict(logged_in=bool(uid), wechat_bound=bool(uid and service.known(uid, digest(config()['appid']))), mode='official_account'))
                if path == '/platform-api/wechat/oa/redeem':
                    if self.command != 'POST':
                        raise Problem(405, '请求方式无效')
                    result, self.wechat_cookies = service.redeem(self.oa_body().get('ticket'), self.headers)
                    return self.send(200, result)
                if self.command != 'GET':
                    raise Problem(405, '请求方式无效')
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                if set(query) != {'state', 'scan'} or any(len(v) != 1 for v in query.values()):
                    raise Problem(400, '二维码地址无效')
                state, scan = query['state'][0], query['scan'][0]
                service.scan(state, scan)
                if path.endswith('/authorize'):
                    target, proof = service.authorize(state, scan)
                    self.wechat_cookies = [proof]
                    return self.oa_redirect(target)
                import qrcode
                from qrcode.image.svg import SvgPathImage
                qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
                qr.add_data(CALLBACK_ORIGIN + '/platform-api/wechat/oa/authorize?' + urllib.parse.urlencode(dict(state=state, scan=scan)))
                qr.make(fit=True)
                image = qr.make_image(image_factory=SvgPathImage)
                output = io.BytesIO()
                image.save(output)
                return self.oa_raw(200, output.getvalue(), 'image/svg+xml')
            except Problem as e:
                return self.send(e.status, dict(error=e.message))
            except (ValueError, TypeError, KeyError):
                return self.send(400, dict(error='请核对信息，重新扫码'))
            except Exception:
                return self.send(503, dict(error='微信登录暂不可用，请稍后重新扫码'))

        def start(self, body):
            result, self.wechat_cookies = service.start(body, self.headers, self.oa_ip())
            return self.send(200, result)

        def callback(self):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            state, code = query.get('state', [''])[0], query.get('code', [''])[0]
            if service.row(state) is None:
                return super().callback()
            if self.command != 'GET':
                raise Problem(405, '请求方式无效')
            target = service.callback(state, code, self.headers, self.oa_ip())
            return self.oa_redirect(target)

        def finish(self, body=None):
            if body is None:
                return super().finish()
            if service.row(body.get('state')) is None:
                return super().finish(body)
            result, self.wechat_cookies = service.finish(body.get('state'), body.get('verifier'), self.headers, self.oa_ip())
            return self.send(200, result)

        def oa_raw(self, status, data, mime):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def oa_redirect(self, target):
            self.send_response(302)
            self.send_header('Location', target)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Length', '0')
            self.end_headers()

        do_GET = run_request
        do_POST = run_request
    return Handler
