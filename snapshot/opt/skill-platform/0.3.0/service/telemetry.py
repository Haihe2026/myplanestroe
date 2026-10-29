"""Minimal operational events, isolated from the billing databases."""
import hashlib
from contextlib import contextmanager
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

CHANNELS = {'workbuddy_skill', 'workbuddy_expert', 'skillhub'}
DEVICES = {'desktop', 'mobile', 'cloud'}


@contextmanager
def connect(path):
    c = sqlite3.connect(str(path), timeout=2)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as c:
        c.executescript('''PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,created INTEGER NOT NULL,
          product TEXT NOT NULL,user_id TEXT,event TEXT NOT NULL,status INTEGER NOT NULL,
          channel TEXT NOT NULL,device TEXT NOT NULL,duration_ms INTEGER NOT NULL);
          CREATE INDEX IF NOT EXISTS events_time ON events(created);
          CREATE INDEX IF NOT EXISTS events_user ON events(product,user_id,created);
          CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
        c.execute("INSERT OR IGNORE INTO metadata VALUES('collection_started',?)", (str(int(time.time())),))


def record(path, product, uid, event, status, channel, device, duration):
    with connect(path) as c:
        c.execute('INSERT INTO events(created,product,user_id,event,status,channel,device,duration_ms) VALUES(?,?,?,?,?,?,?,?)',
                  (int(time.time()), product, uid, event, status,
                   channel if channel in CHANNELS else 'unknown', device if device in DEVICES else 'unknown', max(0, int(duration))))


def event_name(path, method):
    if path.startswith('/temu/'):
        path = path[5:]
    return {('/register', 'POST'): 'activation_attempt', ('/activate', 'POST'): 'activation_attempt',
            ('/jobs', 'POST'): 'generation_request', ('/v1/images/generations', 'POST'): 'generation_request',
            ('/balance', 'GET'): 'balance_view', ('/membership-link', 'POST'): 'legacy_membership_link',
            ('/membership-api/redeem', 'POST'): 'legacy_membership_open',
            ('/membership-api/orders', 'POST'): 'legacy_order_create',
            ('/skill-pay/offer', 'GET'): 'purchase_offer_fetch', ('/skill-pay/orders', 'POST'): 'native_order_attempt'}.get((path, method))


def resolve_user(store, headers, result):
    token = headers.get('Authorization', '').removeprefix('Bearer ')
    if isinstance(result, dict) and isinstance(result.get('token'), str):
        token = result['token']
    with store.connect() as c:
        if token:
            hashed = hashlib.sha256(token.encode()).hexdigest()
            row = c.execute('SELECT user_id FROM sessions WHERE hash=? AND expires>?', (hashed, time.time())).fetchone()
            if not row and token.startswith('mpimg_'):
                row = c.execute('SELECT user_id FROM customer_keys WHERE hash=? AND revoked IS NULL', (hashed,)).fetchone()
            if row:
                return row['user_id']
        cookies = SimpleCookie(headers.get('Cookie', ''))
        for name in ('image_member', 'temu_member'):
            if name in cookies:
                row = c.execute('SELECT user_id FROM web_sessions WHERE hash=? AND expires>?',
                                (hashlib.sha256(cookies[name].value.encode()).hexdigest(), time.time())).fetchone()
                if row:
                    return row['user_id']
    return None


def observed_handler(parent, store, product, event_db):
    class Observed(parent):
        def send(self, status, result, *args, **kwargs):
            self.event_status = status
            name = event_name(getattr(self, 'original_path', self.path), self.command)
            if name and not getattr(self, 'event_recorded', False):
                self.event_recorded = True
                try:
                    uid = resolve_user(store, self.headers, result)
                    if name == 'activation_attempt' and status == 200 and isinstance(result, dict):
                        name = 'activation_created' if result.get('granted') else 'activation_restored'
                    record(event_db, product, uid, name, status,
                           self.headers.get('X-Skill-Channel'), self.headers.get('X-Skill-Device'),
                           (time.monotonic() - self.event_start) * 1000)
                except Exception:
                    print('operational_event_write_failed', file=sys.stderr)
            return super().send(status, result, *args, **kwargs)

        def run_request(self):
            self.event_start = time.monotonic()
            self.original_path = self.path
            self.event_recorded = False
            if product == 'gemini' and self.path in ('/skill-pay/offer', '/skill-pay/orders'):
                try:
                    token = self.headers.get('Authorization', '').removeprefix('Bearer ')
                    store.user(token)
                except Exception:
                    return self.send(401, {'error': '请恢复原账户后重试'})
                if self.path == '/skill-pay/offer' and self.command == 'GET':
                    return self.send(200, {'ready': False, 'mode': 'wechat_ai', 'product': 'gemini-image-assistant',
                      'notice': '应用内购买暂未开放，已有额度可继续使用。',
                      'offer': {'id': 'gemini-32-v1', 'title': '32次生图包', 'amount_fen': 2900,
                                'images': 32, 'valid_days': 30, 'auto_renew': False}})
                return self.send(503, {'error': '应用内支付接入尚未完成，未创建订单、未扣款。'})
            return super().run_request()

        do_GET = run_request
        do_POST = run_request
    return Observed
