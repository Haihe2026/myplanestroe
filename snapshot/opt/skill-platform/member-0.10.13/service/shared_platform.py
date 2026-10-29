"""Shared paid image wallet. Existing product databases remain independent and intact."""
import base64
from contextvars import ContextVar
from contextlib import closing
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import urllib.parse
import uuid

import server
from manual_payments import ManualMembership
from membership import PLANS
from paid_registration import install
from registration_entries import RegistrationEntries
from skill_access import SkillAccess
from enterprise import Enterprise, PLANS as ENTERPRISE_PLANS, LEGACY_PLANS as ENTERPRISE_LEGACY_PLANS

PRODUCTS = ('gemini', 'temu', 'xhs')
CURRENT_PRODUCT = ContextVar('product', default='gemini')
TEMU_IMAGES = ContextVar('temu_images', default=())


def payment_status(store, uid, product, since):
    if type(since) is not int or not 0 <= since <= int(time.time()) + 300:
        raise server.Problem(400, '付款查询时间无效')
    with store.connect() as c:
        row = c.execute('''SELECT id,status,units,plan FROM member_orders WHERE user_id=?
            AND (status='reported' OR created>=? OR paid_at>=?)
            ORDER BY coalesce(paid_at,created) DESC,id DESC LIMIT 1''', (uid, since, since)).fetchone()
    return dict(store.quota(uid, product), order=dict(row) if row else None)


class SharedProvider(server.Provider):
    def __call__(self, prompt, size):
        images = TEMU_IMAGES.get()
        return self.edit(prompt, size, images) if images else super().__call__(prompt, size)


class SharedMembership(ManualMembership):
    def plans(self):
        data = super().plans()
        data.update(audience='shared', shared=True)
        if CURRENT_PRODUCT.get() == 'temu':
            data.update(trial_images=3, trial_product='temu', monthly_valid_days=None)
        return data

    def order(self, uid, plan, product='gemini'):
        from permanent_plans import SHARED_PLANS
        if product in PRODUCTS and isinstance(plan, str) and plan in SHARED_PLANS:
            result = super().order(uid, plan, 'gemini-image-assistant')
            with self.store.connect() as c:
                c.execute('INSERT OR IGNORE INTO order_sources VALUES(?,?)', (result['id'], product))
            return self.get_order(uid, result['id'])
        if product == 'temu':
            plans={**ENTERPRISE_LEGACY_PLANS,**ENTERPRISE_PLANS}
            if not isinstance(plan,str) or plan not in plans:
                raise server.Problem(400, '请选择Temu企业套餐')
            if not self.payment_ready:
                raise server.Problem(503, '扫码收款暂未开放')
            now = int(time.time())
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                old = c.execute("SELECT id FROM member_orders WHERE user_id=? AND plan=? AND status IN ('pending','reported') AND created>? ORDER BY created DESC LIMIT 1", (uid,plan,now-86400)).fetchone()
                if old:
                    oid = old[0]
                else:
                    if c.execute('SELECT count(*) FROM member_orders WHERE user_id=? AND created>?', (uid,now-86400)).fetchone()[0] >= 12:
                        raise server.Problem(429,'今天的订单创建次数已达上限，请联系客服')
                    oid, p = uuid.uuid4().hex, plans[plan]
                    c.execute("INSERT INTO member_orders(id,user_id,plan,amount_fen,units,status,created,product) VALUES(?,?,?,?,?,'pending',?,?)", (oid,uid,plan,p['price_fen'],p['images'],now,'gemini-image-assistant'))
                    c.execute('INSERT INTO order_sources VALUES(?,?)', (oid,product))
            return self.get_order(uid,oid)
        if product not in PRODUCTS or plan not in PLANS:
            raise server.Problem(400, '产品或套餐无效')
        # Reuse the proven QR order writer, then record the actual acquisition source.
        result = super().order(uid, plan, 'gemini-image-assistant')
        with self.store.connect() as c:
            c.execute('INSERT OR IGNORE INTO order_sources VALUES(?,?)', (result['id'], product))
        return self.get_order(uid, result['id'])

    def get_order(self, uid, oid):
        result = super().get_order(uid, oid)
        with self.store.connect() as c:
            source = c.execute('SELECT product FROM order_sources WHERE order_id=?', (oid,)).fetchone()
        product = source[0] if source else 'gemini'
        result.update(source_product=product, shared=True,
                      qr_url='/membership/' + ('temu' if product == 'temu' else 'gemini') + '/payment-qr.png')
        return result

    def account(self, uid):
        product = CURRENT_PRODUCT.get()
        data = self.store.quota(uid, product)
        return dict(data, account_label='创作账户 · ' + uid[:8])


class SharedStore(server.Store):
    def __init__(self, path, legacy, provider=None):
        super().__init__(path, provider or SharedProvider())
        self.legacy = legacy
        with self.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS legacy_links(product TEXT NOT NULL,legacy_uid TEXT NOT NULL,
                  user_id TEXT NOT NULL,PRIMARY KEY(product,legacy_uid),UNIQUE(product,user_id));
                CREATE TABLE IF NOT EXISTS product_accounts(product TEXT NOT NULL,user_id TEXT NOT NULL,
                  created INTEGER NOT NULL,PRIMARY KEY(product,user_id));
                CREATE TABLE IF NOT EXISTS job_products(job_id TEXT PRIMARY KEY,product TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS order_sources(order_id TEXT PRIMARY KEY,product TEXT NOT NULL);
            ''')
        self.membership = SharedMembership(self, server.Problem, server.digest, server.points)
        install(self)
        self.registration_entries = RegistrationEntries(self)
        self.skill_access = SkillAccess(self, server.Problem)
        self.enterprise = Enterprise(self, server.Problem)

    def old_identity(self, product, secret):
        path = self.legacy.get(product)
        if not path:
            return None
        with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=10)) as c:
            row = c.execute('SELECT user_id FROM trial_claims WHERE hash=? UNION SELECT user_id FROM sessions WHERE hash=? LIMIT 1',
                            (server.digest(secret), server.digest(secret))).fetchone()
        return row[0] if row else None

    def register_product(self, product, secret, ip, accepted):
        if product not in PRODUCTS:
            raise server.Problem(400, '产品无效')
        if (not isinstance(secret, str) or len(secret) != 43
                or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in secret)):
            raise server.Problem(400, '账户凭证格式错误')
        # A legacy identity may already be attached by redeeming an old membership ticket.
        known = {p: self.old_identity(p, secret) for p in self.legacy}
        if accepted is not True:
            raise server.Problem(400, '请先同意账户与图片处理说明')
        if not self.public_trial_enabled():
            raise server.Problem(503, '账户开通暂不可用')
        now = int(time.time())
        identity = server.digest(secret)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            mapped = {r[0] for p, old in known.items() if old for r in c.execute(
                'SELECT user_id FROM legacy_links WHERE product=? AND legacy_uid=?', (p, old))}
            current = c.execute('SELECT user_id FROM trial_claims WHERE hash=?', (server.digest(secret),)).fetchone()
            if current:
                mapped.add(current[0])
            if len(mapped) > 1:
                raise server.Problem(409, '原账户关联冲突，请保留凭证联系客服，不会合并余额')
            created = not mapped
            if created:
                day = time.strftime('%Y-%m-%d', time.gmtime(now))
                ip_hash = hmac.new(os.environ['IMAGE_TRIAL_HMAC_KEY'].encode(), ip.encode(), hashlib.sha256).hexdigest()
                limit = c.execute('SELECT count FROM claim_limits WHERE ip_hash=? AND day=?', (ip_hash,day)).fetchone()
                if limit and limit[0] >= int(os.environ.get('IMAGE_ASSISTANT_ACCOUNT_IP_DAILY_LIMIT','10')):
                    raise server.Problem(429,'账户开通频率过高，请稍后重试；已有账户可恢复')
                uid = str(uuid.uuid4())
                c.execute('INSERT INTO users VALUES(?,0)',(uid,))
                c.execute('INSERT INTO claim_limits VALUES(?,?,1) ON CONFLICT(ip_hash,day) DO UPDATE SET count=count+1',(ip_hash,day))
                c.execute("INSERT INTO ledger(user_id,amount,kind,created) VALUES(?,0,'account_created',?)",(uid,now))
            else:
                uid = next(iter(mapped))
            self.membership.expire(c,uid)
            c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)',(identity,uid,now))
            c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',(identity,uid,now+7*86400))
            for p, old in known.items():
                if old:
                    prior = c.execute('SELECT legacy_uid FROM legacy_links WHERE product=? AND user_id=?', (p, uid)).fetchone()
                    if prior and prior[0] != old:
                        raise server.Problem(409, '该产品已有另一原账户，不会替换或合并余额')
                    c.execute('INSERT INTO legacy_links VALUES(?,?,?) ON CONFLICT(product,legacy_uid) DO NOTHING', (p, old, uid))
            c.execute('INSERT OR IGNORE INTO product_accounts VALUES(?,?,?)', (product, uid, int(time.time())))
        if product == 'temu':
            self.enterprise.start(uid)
        quota = self.quota(uid, product)
        return dict(token=secret,granted=False,created=created,purchase_required=quota['remaining_uses']<1,**quota)

    def link_legacy(self, uid, product, secret):
        if product not in self.legacy or not isinstance(secret, str) or len(secret) != 43:
            raise server.Problem(400, '原账户凭证格式错误')
        old = self.old_identity(product, secret)
        if not old:
            raise server.Problem(401, '未找到原账户，原余额未修改')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            by_old = c.execute('SELECT user_id FROM legacy_links WHERE product=? AND legacy_uid=?', (product, old)).fetchone()
            by_user = c.execute('SELECT legacy_uid FROM legacy_links WHERE product=? AND user_id=?', (product, uid)).fetchone()
            if (by_old and by_old[0] != uid) or (by_user and by_user[0] != old):
                raise server.Problem(409, '原账户已有关联，请保留两个凭证联系客服；不会合并或替换余额')
            c.execute('INSERT OR IGNORE INTO legacy_links VALUES(?,?,?)', (product, old, uid))
        return self.quota(uid, product)

    def legacy_remaining(self, uid, product):
        with self.connect() as c:
            row = c.execute('SELECT legacy_uid FROM legacy_links WHERE product=? AND user_id=?', (product, uid)).fetchone()
        if not row:
            return 0
        with closing(sqlite3.connect(Path(self.legacy[product]).resolve().as_uri() + '?mode=ro', uri=True, timeout=10)) as c:
            balance = c.execute('SELECT balance FROM users WHERE id=?', (row[0],)).fetchone()
            expired = c.execute('SELECT coalesce(sum(remaining),0) FROM member_grants WHERE user_id=? AND expires IS NOT NULL AND expires<=?',
                                (row[0], time.time())).fetchone()[0]
        return max(0, balance[0] - expired) if balance else 0

    def quota(self, uid, product):
        shared = self.balance(uid)
        old = self.legacy_remaining(uid, product) if product in self.legacy else 0
        access = self.skill_access.public(uid)
        trial = self.enterprise.quota(uid) if product == 'temu' else {}
        return dict(remaining_uses=shared + old + trial.get('trial_remaining',0), shared_uses=shared, legacy_uses=old,
                    skill_key=access, skill_key_required=access['required'],
                    balance_points=(shared + old) * 1000, balance=shared + old,
                    point_scale=1000, image_cost_points=1000, **trial)

    def redeem_product(self, product, ticket):
        try:
            return self.membership.redeem(ticket)
        except server.Problem as error:
            if error.status != 401 or product not in self.legacy or not isinstance(ticket, str) or len(ticket) != 43:
                raise
        # Old links are consumed once in the old DB; no old quota is transferred.
        with closing(sqlite3.connect(self.legacy[product], timeout=10)) as c, c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT user_id FROM web_tickets WHERE hash=? AND used=0 AND expires>?', (server.digest(ticket), time.time())).fetchone()
            if not row:
                raise server.Problem(401, '链接已使用或过期，请从 Skill 重新打开')
            c.execute('UPDATE web_tickets SET used=1 WHERE hash=?', (server.digest(ticket),))
        now = int(time.time())
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT user_id FROM legacy_links WHERE product=? AND legacy_uid=?', (product, row[0])).fetchone()
            uid = old[0] if old else str(uuid.uuid4())
            if not old:
                c.execute('INSERT INTO users VALUES(?,0)', (uid,))
                c.execute('INSERT INTO legacy_links VALUES(?,?,?)', (product, row[0], uid))
                c.execute("INSERT INTO ledger(user_id,amount,kind,created) VALUES(?,0,'account_created',?)", (uid, now))
            c.execute('INSERT OR IGNORE INTO product_accounts VALUES(?,?,?)', (product, uid, now))
            session = secrets.token_urlsafe(32)
            c.execute('INSERT INTO web_sessions VALUES(?,?,?)', (server.digest(session), uid, now + 1800))
        return session

    def generate_product(self, uid, product, body, idem, temu_validator=None):
        if product not in ('gemini', 'temu'):
            raise server.Problem(400, '该产品不消耗生图次数')
        if not isinstance(idem, str) or not 16 <= len(idem) <= 100:
            raise server.Problem(400, '任务标识无效')
        images = ()
        if product == 'temu':
            if not self.provider.edit_ready:
                raise server.Problem(503, '商品图编辑暂不可用，本次未消耗次数')
            if not temu_validator:
                raise server.Problem(503, '商品图编辑暂不可用')
            body, images = temu_validator(body)
            body = dict(body)
            body['prompt'] += '\nverified-reference-sha256:' + ','.join(hashlib.sha256(x).hexdigest() for x in images)
        key = hashlib.sha256((product + ':' + idem).encode()).hexdigest()
        context = CURRENT_PRODUCT.set(product)
        refs = TEMU_IMAGES.set(tuple(images))
        try:
            # Product attribution is inserted in the same transaction as the quota reservation.
            result = super().generate(uid, body, key)
            return dict(result, **self.quota(uid, product))
        finally:
            TEMU_IMAGES.reset(refs)
            CURRENT_PRODUCT.reset(context)


def handler(store, temu_validator=None):
    class Handler(server.handler(store)):
        def run_request(self):
            self.connection.settimeout(15)
            product = None
            context = None
            try:
                parts = urllib.parse.urlsplit(self.path).path.split('/')
                if len(parts) < 4 or parts[1] != 'platform-api' or parts[2] not in PRODUCTS:
                    raise server.Problem(404, '接口不存在')
                product, route = parts[2], '/' + '/'.join(parts[3:])
                context = CURRENT_PRODUCT.set(product)
                body = {}
                if route == '/skill-jobs' and self.command == 'POST':
                    if product not in ('gemini', 'temu'):
                        raise server.Problem(403, '专属Key用于已开通的生图技能')
                    store.skill_access.authenticate(self.headers.get('Authorization','').removeprefix('Bearer '))
                if route == '/jobs' and self.command == 'POST':
                    # Reject unknown accounts before accepting a large photo upload.
                    store.user(self.headers.get('Authorization','').removeprefix('Bearer '))
                if self.command == 'POST':
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= (server.MAX_EDIT_BODY if route in ('/jobs', '/skill-jobs') else server.MAX_BODY):
                        raise server.Problem(413, '请求体过大或缺少长度')
                    if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                        raise server.Problem(400, '请求须为JSON')
                    body = json.loads(self.rfile.read(size))
                    if not isinstance(body, dict):
                        raise server.Problem(400, '请求须为JSON对象')
                if route == '/health' and self.command == 'GET':
                    return self.send(200, dict(status='ok', version='0.10.13', shared_wallet=True,
                        automatic_skill_keys=store.skill_access.configured(),
                        new_user_uses=3 if product=='temu' else 0, provider_configured=store.provider.ready,
                        reference_editing=store.provider.edit_ready, sms_required=False))
                if route == '/register' and self.command == 'POST':
                    ip = self.headers.get('X-Real-IP', self.client_address[0]) if self.client_address[0] == '127.0.0.1' else self.client_address[0]
                    return self.send(200, store.register_product(product, body.get('install_secret'), ip[:64], body.get('accepted')))
                if route == '/quick-entry' and self.command == 'POST':
                    ip = self.headers.get('X-Real-IP', self.client_address[0]) if self.client_address[0] == '127.0.0.1' else self.client_address[0]
                    return self.send(200, store.registration_entries.prepare(product, body.get('install_secret'), ip[:64]))
                if route == '/quick-entry/status' and self.command == 'POST':
                    return self.send(200, store.registration_entries.status(product, body.get('install_secret')))
                if route == '/membership-api/plans' and self.command == 'GET':
                    return self.send(200, store.membership.plans())
                if route == '/membership-api/catalog' and self.command == 'GET':
                    return self.send(200, store.platform_catalog.catalog())
                if route.startswith('/membership-api/'):
                    if self.command == 'POST' and (self.headers.get('Origin') != 'https://myplanestore.com'
                            or self.headers.get('X-Membership-Request') != '1'):
                        raise server.Problem(403, '请从本站操作')
                    if route == '/membership-api/redeem' and self.command == 'POST':
                        session = store.redeem_product(product, body.get('ticket'))
                        return self.send(200, {'ok': True}, cookie='platform_member=' + session + '; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800')
                    if route == '/membership-api/confirm-entry' and self.command == 'POST':
                        session = store.registration_entries.confirm(product, body.get('ticket'), body.get('accepted'))
                        return self.send(200, {'ok': True}, cookie='platform_member=' + session + '; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800')
                    cookie = SimpleCookie(self.headers.get('Cookie', '')).get('platform_member')
                    uid = store.membership.web_user(cookie.value if cookie else '')
                    if route == '/membership-api/account' and self.command == 'GET':
                        data = store.membership.account(uid)
                        return self.send(200, dict(data, label=data['account_label']))
                    if product=='temu' and route=='/membership-api/enterprise-history' and self.command=='GET':
                        return self.send(200,store.enterprise.history(uid))
                    if product=='temu' and route=='/membership-api/feedback' and self.command=='POST':
                        return self.send(200,store.enterprise.feedback(uid,body))
                    if route == '/membership-api/skill-key' and self.command == 'GET':
                        return self.send(200, store.skill_access.public(uid))
                    if route == '/membership-api/skill-key/manage' and self.command == 'POST':
                        return self.send(200, store.skill_access.manage(uid, body.get('action')))
                    if route == '/membership-api/orders' and self.command == 'POST':
                        return self.send(200, store.membership.order(uid, body.get('plan'), product))
                    if route == '/membership-api/orders' and self.command == 'GET':
                        return self.send(200, store.membership.orders(uid))
                    if route == '/membership-api/report-payment' and self.command == 'POST':
                        return self.send(200, store.membership.report_paid(uid, body.get('order_id')))
                    if route.startswith('/membership-api/orders/') and self.command == 'GET':
                        return self.send(200, store.membership.get_order(uid, route.rsplit('/', 1)[-1]))
                    if route == '/membership-api/gifts' and self.command == 'GET':
                        gifts = store.platform_catalog.gifts(uid)
                        for gift in gifts.get('items', []):
                            if gift.get('download_url'):
                                gift['download_url'] = '/platform-api/' + product + gift['download_url']
                        return self.send(200, gifts)
                    if route == '/membership-api/gifts/360/download' and self.command == 'GET':
                        return self.send(200, store.platform_catalog.download(uid), 'application/zip', download='360-scam-check-free-workbuddy.zip')
                    if route == '/membership-api/keys' and self.command == 'GET':
                        return self.send(200, store.api_access.listing(uid))
                    if route == '/membership-api/keys' and self.command == 'POST':
                        return self.send(200, store.api_access.issue(uid))
                    if route == '/membership-api/keys/revoke' and self.command == 'POST':
                        return self.send(200, store.api_access.revoke(uid, body.get('id')))
                    raise server.Problem(404, '接口不存在')
                token = self.headers.get('Authorization', '').removeprefix('Bearer ')
                api_key_id = None
                skill_key_id = None
                if token.startswith('mpskill_'):
                    uid, skill_key_id = store.skill_access.authenticate(token)
                    if product not in ('gemini', 'temu') or not (route == '/balance' and self.command == 'GET'
                            or route == '/skill-jobs' and self.command == 'POST'
                            or route.startswith('/jobs/') and self.command == 'GET'):
                        raise server.Problem(403, '专属Key仅用于本技能生图和查询结果')
                elif token.startswith('mpimg_'):
                    uid, api_key_id = store.api_access.authenticate(token)
                    if product != 'gemini' or not (route in ('/v1/images/generations', '/balance') or route.startswith('/jobs/') and self.command == 'GET'):
                        raise server.Problem(403, '该Key仅支持生图、查询任务与次数')
                else:
                    uid = store.user(token)
                if product=='temu' and skill_key_id is None and api_key_id is None:
                    if route=='/enterprise-trial/start' and self.command=='POST':
                        store.enterprise.start(uid)
                        return self.send(200,store.quota(uid,product))
                    if route=='/enterprise-history' and self.command=='GET':
                        return self.send(200,store.enterprise.history(uid))
                    if route=='/feedback' and self.command=='POST':
                        return self.send(200,store.enterprise.feedback(uid,body))
                if route == '/skill-key' and self.command == 'POST':
                    if product not in ('gemini', 'temu'):
                        raise server.Problem(403, '专属Key用于已开通的生图技能')
                    return self.send(200, store.skill_access.binding(uid, product))
                if route == '/skill-key/bound' and self.command == 'POST':
                    if product not in ('gemini', 'temu'):
                        raise server.Problem(403, '专属Key用于已开通的生图技能')
                    return self.send(200, store.skill_access.acknowledge(uid, body.get('key')))
                if route == '/skill-jobs' and self.command == 'POST':
                    if skill_key_id is None:
                        raise server.Problem(403, '请使用Skill自动绑定的专属Key')
                    if not server.EDIT_SLOTS.acquire(blocking=False):
                        raise server.Problem(429, '当前任务较多，未提交生成，请稍后继续')
                    try:
                        return self.send(200, store.generate_product(uid, product, body, self.headers.get('Idempotency-Key'), temu_validator))
                    finally:
                        server.EDIT_SLOTS.release()
                if route == '/v1/images/generations' and self.command == 'POST':
                    if api_key_id is None or body.get('model', 'gpt-image-2') != 'gpt-image-2' or type(body.get('n',1)) is not int or body.get('n', 1) != 1 or body.get('response_format', 'b64_json') != 'b64_json' or set(body) - {'model','prompt','n','size','response_format','role','platform','slot'}:
                        raise server.Problem(400, '请使用生图Key和单张b64_json参数')
                    payload = {k: body[k] for k in ('prompt','size','role','platform','slot') if k in body}
                    payload['confirmed'] = True
                    key = hashlib.sha256(('gemini:' + str(self.headers.get('Idempotency-Key', ''))).encode()).hexdigest()
                    if not 16 <= len(self.headers.get('Idempotency-Key', '')) <= 100:
                        raise server.Problem(400, '任务标识无效')
                    if not server.EDIT_SLOTS.acquire(blocking=False):
                        raise server.Problem(429,'当前任务较多，未提交生成，请稍后继续')
                    try:
                        result = server.Store.generate(store, uid, payload, key, api_key_id)
                    finally:
                        server.EDIT_SLOTS.release()
                    if result['status'] != 'succeeded':
                        return self.send(202, dict(job_id=result['id'], status=result['status']))
                    job = store.get_job(uid, result['id'])
                    return self.send(200, dict(created=int(time.time()), job_id=result['id'], data=[{'b64_json':base64.b64encode(job['image']).decode()}], remaining_uses=store.balance(uid)))
                if route == '/balance' and self.command == 'GET':
                    return self.send(200, store.quota(uid, product))
                if route == '/payment-status' and self.command == 'GET':
                    query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                    return self.send(200, payment_status(store, uid, product, int(query.get('since', ['0'])[0])))
                if route == '/link-legacy' and self.command == 'POST':
                    return self.send(200, store.link_legacy(uid, product, body.get('legacy_credential')))
                if route == '/membership-link' and self.command == 'POST':
                    result = store.membership.handoff(uid)
                    result['url'] = result['url'].replace('/membership/', '/membership/' + product + '/')
                    return self.send(200, result)
                if route == '/jobs' and self.command == 'POST':
                    if not server.EDIT_SLOTS.acquire(blocking=False):
                        raise server.Problem(429, '当前任务较多，未提交生成，请稍后继续')
                    try:
                        return self.send(200, store.generate_product(uid, product, body, self.headers.get('Idempotency-Key'), temu_validator))
                    finally:
                        server.EDIT_SLOTS.release()
                if route.startswith('/jobs/by-key/') and self.command == 'GET':
                    idem = route.rsplit('/', 1)[-1]
                    if not 16 <= len(idem) <= 100:
                        raise server.Problem(400, '任务标识无效')
                    key = hashlib.sha256((product + ':' + idem).encode()).hexdigest()
                    with store.connect() as c:
                        row = c.execute('SELECT id,status FROM jobs WHERE user_id=? AND idem=?', (uid, key)).fetchone()
                    if not row:
                        raise server.Problem(404, '任务未查到，请保留任务等待核查，不要重新生成')
                    return self.send(200, dict(row))
                if route.startswith('/jobs/') and self.command == 'GET':
                    jid = route.split('/')[2]
                    with store.connect() as c:
                        row = c.execute('SELECT product FROM job_products WHERE job_id=?', (jid,)).fetchone()
                    if not row or row[0] != product:
                        raise server.Problem(404, '任务不存在')
                    job = store.get_job(uid, jid)
                    image = job.pop('image')
                    if route == '/jobs/' + jid:
                        return self.send(200, job)
                    if route == '/jobs/' + jid + '/image' and image:
                        return self.send(200, image, 'image/png')
                    raise server.Problem(409, '图片尚未可用')
                raise server.Problem(404, '接口不存在')
            except server.Problem as error:
                cookie = 'platform_member=; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=0' if product and route == '/membership-api/redeem' else None
                return self.send(error.status, {'error': error.message}, cookie=cookie)
            except (ValueError, TypeError, UnicodeError):
                return self.send(400, {'error': '请求格式错误'})
            except Exception:
                return self.send(503, {'error': '服务暂不可用，请保留账户与任务文件'})
            finally:
                if context is not None:
                    CURRENT_PRODUCT.reset(context)

        do_GET = run_request
        do_POST = run_request
    return Handler
