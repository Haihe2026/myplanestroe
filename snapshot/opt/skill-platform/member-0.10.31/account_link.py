"""Scheme A: recognise a merchant's signed-in browser when a new WorkBuddy conversation asks to link.

Problem: every new conversation (rebuilt sandbox) gets a new install secret, so confirming the
registration link created a second account and a second free trial.

What this layer adds (Temu only by default; nothing else changes):
* After a skill-issued link signs a browser in (registration confirm, or the membership-page
  redeem used by 我的账户/充值), the browser gets a long-lived ``mps_device`` cookie.
  Only its SHA-256 is stored. HttpOnly, Secure, SameSite=Strict, Path=/platform-api/.
* ``GET  membership-api/remembered``  -> which account this browser remembers (label + uses).
* ``POST membership-api/link-entry``   -> after explicit consent on the page, attach the pending
  registration (the new conversation) to that remembered account. No new account, no new trial.
* ``POST membership-api/forget-device``-> sign this browser out (revoke the remembered login).
* ``/register`` adds ``linked_existing: true`` for credentials attached this way.

Unchanged: plans, prices, quota and trial policy tables, payments, orders, idempotency, the
existing confirm-entry/new-account path, the 30-minute platform_member session.
"""
from contextvars import ContextVar
from http.cookies import SimpleCookie
import json
import os
import secrets
import time
import urllib.parse

VERSION = '0.10.31'
COOKIE = 'mps_device'
ROUTES = ('remembered', 'link-entry', 'forget-device')
REQUEST = ContextVar('device_link_request', default=None)
TOKEN_CHARS = frozenset('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')
MAX_DEVICE_BODY = 4096


def remember_days():
    try:
        days = int(os.environ.get('MYPLANESTORE_DEVICE_DAYS', '180'))
    except ValueError:
        days = 180
    return min(400, max(1, days))  # browsers cap cookie lifetime at 400 days


def enabled_products():
    raw = os.environ.get('MYPLANESTORE_DEVICE_LINK_PRODUCTS', 'temu')
    return {p.strip() for p in raw.split(',') if p.strip() in ('gemini', 'temu')}


def valid_token(value):
    return isinstance(value, str) and len(value) == 43 and set(value) <= TOKEN_CHARS


def cookie_header(token, max_age):
    return '%s=%s; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=%d' % (COOKIE, token, max_age)


class DeviceLinks:
    def __init__(self, store, server):
        self.store, self.server = store, server
        with store.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS remembered_devices(hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                  created INTEGER NOT NULL, expires INTEGER NOT NULL, last_used INTEGER NOT NULL,
                  revoked INTEGER NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS remembered_devices_user ON remembered_devices(user_id);
                CREATE TABLE IF NOT EXISTS device_entry_links(identity_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                  device_hash TEXT NOT NULL, product TEXT NOT NULL, created INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS device_link_audit(id INTEGER PRIMARY KEY, kind TEXT NOT NULL,
                  user_id TEXT, product TEXT, created INTEGER NOT NULL);''')

    # ---- remembered browsers
    def lookup(self, token):
        if not valid_token(token):
            return None
        now = int(time.time())
        with self.store.connect() as c:
            row = c.execute('''SELECT d.user_id FROM remembered_devices d JOIN users u ON u.id=d.user_id
                               WHERE d.hash=? AND d.revoked=0 AND d.expires>?''', (self.server.digest(token), now)).fetchone()
            if row:
                c.execute('UPDATE remembered_devices SET last_used=? WHERE hash=?', (now, self.server.digest(token)))
        return row[0] if row else None

    def issue(self, uid, current, product):
        """Remember this browser for uid. Same account -> roll the expiry; other account -> replace."""
        now, days = int(time.time()), remember_days()
        expires = now + days * 86400
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT user_id FROM remembered_devices WHERE hash=? AND revoked=0 AND expires>?',
                            (self.server.digest(current), now)).fetchone() if valid_token(current) else None
            if row and row[0] == uid:
                c.execute('UPDATE remembered_devices SET expires=?,last_used=? WHERE hash=?',
                          (expires, now, self.server.digest(current)))
                return cookie_header(current, days * 86400)
            if row:
                c.execute('UPDATE remembered_devices SET revoked=1 WHERE hash=?', (self.server.digest(current),))
            token = secrets.token_urlsafe(32)
            c.execute('INSERT INTO remembered_devices VALUES(?,?,?,?,?,0)', (self.server.digest(token), uid, now, expires, now))
            c.execute('INSERT INTO device_link_audit(kind,user_id,product,created) VALUES(?,?,?,?)',
                      ('device_remembered', uid, product, now))
        return cookie_header(token, days * 86400)

    def forget(self, token, product):
        if not valid_token(token):
            return
        now = int(time.time())
        with self.store.connect() as c:
            row = c.execute('SELECT user_id FROM remembered_devices WHERE hash=? AND revoked=0', (self.server.digest(token),)).fetchone()
            if row:
                c.execute('UPDATE remembered_devices SET revoked=1 WHERE hash=?', (self.server.digest(token),))
                c.execute('INSERT INTO device_link_audit(kind,user_id,product,created) VALUES(?,?,?,?)',
                          ('device_forgotten', row[0], product, now))

    def remember_session(self, session):
        """Called after a skill-issued ticket became a web session: remember this browser."""
        ctx = REQUEST.get()
        if ctx is None or ctx.get('product') not in enabled_products():
            return
        try:
            uid = self.store.membership.web_user(session)
        except self.server.Problem:
            return
        ctx['cookies'].append(self.issue(uid, ctx.get('device'), ctx['product']))

    # ---- attaching a new conversation
    def was_linked(self, secret):
        if not valid_token(secret):
            return False
        with self.store.connect() as c:
            return c.execute('SELECT 1 FROM device_entry_links WHERE identity_hash=?',
                             (self.server.digest(secret),)).fetchone() is not None

    def link_entry(self, product, ticket, accepted, device):
        Problem, digest = self.server.Problem, self.server.digest
        if accepted is not True:
            raise Problem(400, '请勾选账户与图片处理说明后继续')
        if not valid_token(ticket):
            raise Problem(401, '链接需要更新，请从原技能重新打开')
        uid = self.lookup(device)
        if not uid:
            raise Problem(401, '这个浏览器没有已登录的账户，请按新账户继续')
        entries = self.store.registration_entries
        key = digest(ticket)
        with entries.lock:  # same lock as confirm(): one pending entry is consumed exactly once
            row = entries.pending.get(key)
            if not row or row['expires'] <= time.time():
                entries.pending.pop(key, None)
                raise Problem(401, '链接已使用或过期，请从原技能重新打开')
            if product != row['product']:
                raise Problem(401, '请从对应技能的入口继续')
            identity, now = digest(row['secret']), int(time.time())
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                current = c.execute('SELECT user_id FROM trial_claims WHERE hash=?', (identity,)).fetchone()
                if current and current[0] != uid:
                    raise Problem(409, '这个对话已关联其他账户，不会合并或替换余额，请联系客服')
                c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)', (identity, uid, now))
                c.execute('INSERT OR IGNORE INTO device_entry_links VALUES(?,?,?,?,?)', (identity, uid, digest(device), product, now))
                c.execute('INSERT INTO device_link_audit(kind,user_id,product,created) VALUES(?,?,?,?)',
                          ('conversation_linked', uid, product, now))
            # The existing registration code now finds the mapping and reuses the account:
            # created=False, no IP account limit, no new account, enterprise.start() is idempotent.
            self.store.register_product(product, row['secret'], row['ip'], True)
            if self.store.user(row['secret']) != uid:
                raise Problem(409, '账户关联需要核对，请联系客服；余额未改变')
            link = self.store.membership.handoff(uid)
            web_ticket = urllib.parse.parse_qs(urllib.parse.urlsplit(link['url']).fragment)['ticket'][0]
            session = self.store.membership.redeem(web_ticket)
            del entries.pending[key]
        return session

    def public(self, uid, product):
        quota = self.store.quota(uid, product)
        keys = ('remaining_uses', 'trial_total', 'trial_used', 'trial_pending', 'trial_remaining')
        return dict(remembered=True, account_label='创作账户 · ' + uid[:8], **{k: quota[k] for k in keys if k in quota})


def install(server, shared):
    old = shared.handler

    def handler(store, validator=None):
        parent = old(store, validator)
        links = DeviceLinks(store, server)
        store.device_links = links

        original_redeem = store.membership.redeem
        def redeem(ticket):
            session = original_redeem(ticket)
            links.remember_session(session)
            return session
        store.membership.redeem = redeem

        original_register = store.register_product
        def register_product(product, secret, ip, accepted):
            result = original_register(product, secret, ip, accepted)
            return dict(result, linked_existing=True) if links.was_linked(secret) else result
        store.register_product = register_product

        class Handler(parent):
            def device_cookie(self):
                try:
                    cookie = SimpleCookie(self.headers.get('Cookie', '')).get(COOKIE)
                except Exception:
                    return None
                return cookie.value if cookie else None

            def run_request(self):
                parts = urllib.parse.urlsplit(self.path).path.split('/')
                product = parts[2] if len(parts) > 2 and parts[1] == 'platform-api' else None
                token = REQUEST.set(dict(product=product, device=self.device_cookie(), cookies=[]))
                try:
                    if (len(parts) == 5 and product in ('gemini', 'temu') and parts[3] == 'membership-api'
                            and parts[4] in ROUTES):
                        return self.device_route(product, parts[4])
                    return super().run_request()
                finally:
                    REQUEST.reset(token)

            def end_headers(self):
                ctx = REQUEST.get()
                if ctx:
                    for value in ctx['cookies']:
                        self.send_header('Set-Cookie', value)
                    ctx['cookies'] = []
                return super().end_headers()

            def device_route(self, product, route):
                self.connection.settimeout(15)
                ctx = REQUEST.get()
                try:
                    if product not in enabled_products():
                        raise server.Problem(404, '接口不存在')
                    if route == 'remembered':
                        if self.command != 'GET':
                            raise server.Problem(405, '请求方式无效')
                        uid = links.lookup(ctx['device'])
                        return self.send(200, links.public(uid, product) if uid else dict(remembered=False))
                    if self.command != 'POST':
                        raise server.Problem(405, '请求方式无效')
                    if (self.headers.get('Origin') != 'https://myplanestore.com'
                            or self.headers.get('X-Membership-Request') != '1'):
                        raise server.Problem(403, '请从本站操作')
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= MAX_DEVICE_BODY or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                        raise server.Problem(400, '请求格式错误')
                    body = json.loads(self.rfile.read(size))
                    if not isinstance(body, dict):
                        raise server.Problem(400, '请求格式错误')
                    if route == 'forget-device':
                        links.forget(ctx['device'], product)
                        ctx['cookies'].append(cookie_header('', 0))
                        return self.send(200, {'ok': True})
                    session = links.link_entry(product, body.get('ticket'), body.get('accepted'), ctx['device'])
                    return self.send(200, {'ok': True, 'linked': True},
                                     cookie='platform_member=' + session + '; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800')
                except server.Problem as error:
                    return self.send(error.status, {'error': error.message})
                except (ValueError, TypeError, UnicodeError):
                    return self.send(400, {'error': '请求格式错误'})
                except Exception:
                    return self.send(503, {'error': '服务暂不可用，请稍后重试；余额未改变'})

            do_GET = run_request
            do_POST = run_request
        return Handler

    shared.handler = handler
