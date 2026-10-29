"""Allowlisted metadata only. No request bodies, credentials, hashes of credentials or PII."""
from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3
import time
import uuid

SOURCES = frozenset(('gemini-image-assistant', 'amazon-image-assistant', 'temu-image-master',
    'shein-image-assistant', 'shopee-image-assistant', 'shopify-image-assistant',
    'independent-site-image-assistant', 'tiktokshop-image-assistant', 'facebook-image-assistant',
    'pinterest-image-assistant', 'ebay-image-assistant', 'etsy-image-assistant', 'wayfair-image-assistant'))
CHANNELS = frozenset(('workbuddy_skill', 'workbuddy_expert', 'skillhub'))
PRODUCTS = frozenset(('gemini', 'temu', 'xhs'))
EVENTS = frozenset(('invitation_created', 'registration_page_entered', 'recharge_page_entered',
    'account_linked', 'order_created', 'payment_reported', 'image_succeeded', 'activity', 'return_visit'))
IDENTIFIER = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

def source(value):
    return value if isinstance(value, str) and value in SOURCES else 'unknown'

def channel(value):
    return value if isinstance(value, str) and value in CHANNELS else 'unknown'

def identifier(value):
    return isinstance(value, str) and bool(IDENTIFIER.fullmatch(value))

@contextmanager
def database(path, readonly=False):
    path = Path(path).resolve()
    c = sqlite3.connect(path.as_uri() + '?mode=ro' if readonly else str(path),
                        uri=readonly, timeout=0.15)
    c.row_factory = sqlite3.Row
    try:
        if readonly:
            c.execute('PRAGMA query_only=ON')
        with c:
            yield c
    finally:
        c.close()

class Journey:
    def __init__(self, path):
        self.path = str(path)

    def initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with database(self.path) as c:
            c.executescript('''
              PRAGMA journal_mode=WAL;
              CREATE TABLE IF NOT EXISTS journey_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS journey_invitations(
                id TEXT PRIMARY KEY,source TEXT NOT NULL,channel TEXT NOT NULL,
                product TEXT NOT NULL,created INTEGER NOT NULL,user_id TEXT);
              CREATE TABLE IF NOT EXISTS journey_accounts(
                user_id TEXT PRIMARY KEY,source TEXT NOT NULL,channel TEXT NOT NULL,
                evidence TEXT NOT NULL,first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL);
              CREATE TABLE IF NOT EXISTS journey_events(
                id INTEGER PRIMARY KEY,event TEXT NOT NULL,created INTEGER NOT NULL,
                user_id TEXT,invitation_id TEXT,source TEXT NOT NULL,channel TEXT NOT NULL,
                product TEXT NOT NULL,object_id TEXT,dedupe TEXT NOT NULL UNIQUE);
              CREATE INDEX IF NOT EXISTS journey_event_user ON journey_events(user_id,created);
              CREATE INDEX IF NOT EXISTS journey_event_time ON journey_events(created);
              CREATE TABLE IF NOT EXISTS journey_objects(
                kind TEXT NOT NULL,id TEXT NOT NULL,user_id TEXT NOT NULL,source TEXT NOT NULL,
                channel TEXT NOT NULL,product TEXT NOT NULL,PRIMARY KEY(kind,id));
              CREATE TABLE IF NOT EXISTS journey_test_accounts(
                user_id TEXT PRIMARY KEY,evidence TEXT NOT NULL,marked_at INTEGER NOT NULL);
              CREATE TABLE IF NOT EXISTS journey_contexts(
                id TEXT PRIMARY KEY,user_id TEXT NOT NULL,invitation_id TEXT NOT NULL,
                source TEXT NOT NULL,channel TEXT NOT NULL,product TEXT NOT NULL,expires INTEGER NOT NULL);
              CREATE TABLE IF NOT EXISTS journey_activity(
                user_id TEXT NOT NULL,product TEXT NOT NULL,last_seen INTEGER NOT NULL,
                PRIMARY KEY(user_id,product));
            ''')
            c.execute("INSERT OR IGNORE INTO journey_meta VALUES('collection_started',?)", (str(int(time.time())),))
            c.execute("INSERT OR REPLACE INTO journey_meta VALUES('schema_version','1')")

    def invitation(self, product, src, ch):
        invitation = uuid.uuid4().hex
        with database(self.path) as c:
            c.execute('INSERT INTO journey_invitations VALUES(?,?,?,?,?,NULL)',
                      (invitation, source(src), channel(ch), product, int(time.time())))
        self.event('invitation_created', product, src, ch, invitation=invitation,
                   dedupe='invite:' + invitation)
        return invitation

    def attribution(self, uid):
        with database(self.path, True) as c:
            row = c.execute('SELECT source,channel FROM journey_accounts WHERE user_id=?', (uid,)).fetchone()
        return (row['source'], row['channel']) if row else ('unknown', 'unknown')

    def touch(self, uid, src, ch, evidence='observed_request', now=None, product='gemini', activity=True):
        if not identifier(uid):
            return
        now = int(time.time()) if now is None else int(now)
        with database(self.path) as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT last_seen FROM journey_activity WHERE user_id=? AND product=?', (uid, product)).fetchone()
            c.execute('''INSERT INTO journey_accounts VALUES(?,?,?,?,?,?) ON CONFLICT(user_id)
                         DO UPDATE SET last_seen=max(last_seen,excluded.last_seen)''',
                      (uid, source(src), channel(ch), evidence, now, now))
            # A return is an authenticated, successful observation >=30 minutes after prior activity.
            if activity:
                c.execute('''INSERT INTO journey_activity VALUES(?,?,?) ON CONFLICT(user_id,product)
                    DO UPDATE SET last_seen=max(last_seen,excluded.last_seen)''', (uid, product, now))
                if row and now - row['last_seen'] >= 1800:
                    self._event(c, 'return_visit', product, src, ch, uid, None, None,
                                'return:' + uid + ':' + product + ':' + str(now // 1800), now)

    def link(self, invitation, uid):
        with database(self.path) as c:
            row = c.execute('SELECT * FROM journey_invitations WHERE id=?', (invitation,)).fetchone()
            if not row or (row['user_id'] and row['user_id'] != uid):
                return
            c.execute('UPDATE journey_invitations SET user_id=? WHERE id=?', (uid, invitation))
            c.execute('UPDATE journey_events SET user_id=? WHERE invitation_id=? AND user_id IS NULL', (uid, invitation))
        self.touch(uid, row['source'], row['channel'], 'existing_invitation_request', product=row['product'], activity=False)
        self.event('account_linked', row['product'], row['source'], row['channel'], uid,
                   invitation=invitation, dedupe='linked:' + invitation)

    def context(self, invitation, uid):
        row = self.invitation_row(invitation)
        if not row or row['user_id'] != uid:
            return None
        cid = uuid.uuid4().hex
        with database(self.path) as c:
            c.execute('DELETE FROM journey_contexts WHERE expires<?', (int(time.time()),))
            c.execute('INSERT INTO journey_contexts VALUES(?,?,?,?,?,?,?)',
                (cid, uid, invitation, row['source'], row['channel'], row['product'], int(time.time()) + 1800))
        return cid

    def context_row(self, cid, uid, product):
        if not identifier(cid):
            return None
        with database(self.path, True) as c:
            row = c.execute('SELECT source,channel FROM journey_contexts WHERE id=? AND user_id=? AND product=? AND expires>?',
                            (cid, uid, product, int(time.time()))).fetchone()
        return dict(row) if row else None

    def invitation_row(self, invitation):
        with database(self.path, True) as c:
            row = c.execute('SELECT * FROM journey_invitations WHERE id=?', (invitation,)).fetchone()
        return dict(row) if row else None

    def object(self, kind, oid, uid, product, src, ch):
        if kind not in ('order', 'job') or not identifier(oid) or not identifier(uid):
            return
        with database(self.path) as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute('INSERT OR IGNORE INTO journey_objects VALUES(?,?,?,?,?,?)',
                      (kind, oid, uid, source(src), channel(ch), product))
            old = c.execute('SELECT source,channel FROM journey_objects WHERE kind=? AND id=? AND user_id=?', (kind,oid,uid)).fetchone()
            if old and (old['source'],old['channel']) != (source(src),channel(ch)):
                # The QR writer has no "newly created" flag. Concurrent creators with conflicting
                # declarations are ambiguous; conservative unknown is preferable to picking a winner.
                c.execute("UPDATE journey_objects SET source='unknown',channel='unknown' WHERE kind=? AND id=? AND user_id=?", (kind,oid,uid))
                c.execute("UPDATE journey_events SET source='unknown',channel='unknown' WHERE object_id=? AND user_id=?", (oid,uid))
            return dict(c.execute('SELECT source,channel,product FROM journey_objects WHERE kind=? AND id=? AND user_id=?', (kind,oid,uid)).fetchone())

    def object_row(self, kind, oid, uid):
        with database(self.path, True) as c:
            row = c.execute('SELECT source,channel,product FROM journey_objects WHERE kind=? AND id=? AND user_id=?',
                            (kind, oid, uid)).fetchone()
        return dict(row) if row else None

    def health(self):
        with database(self.path, True) as c:
            required = ('journey_meta','journey_invitations','journey_accounts','journey_events',
                        'journey_objects','journey_test_accounts','journey_contexts','journey_activity')
            present = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            meta = dict(c.execute('SELECT key,value FROM journey_meta'))
            c.execute('SELECT event,created,source,channel,product,object_id FROM journey_events LIMIT 0')
            ok = all(name in present for name in required) and meta.get('schema_version') == '1'
        return dict(ok=ok, schema_version=meta.get('schema_version'), collection_started=meta.get('collection_started'),
                    missing_tables=[name for name in required if name not in present], read_only_check=True)

    def _event(self, c, name, product, src, ch, uid, invitation, oid, dedupe, now):
        written = c.execute('''INSERT OR IGNORE INTO journey_events(event,created,user_id,invitation_id,
                     source,channel,product,object_id,dedupe) VALUES(?,?,?,?,?,?,?,?,?)''',
                  (name, now, uid, invitation, source(src), channel(ch), product, oid, dedupe))
        return written.rowcount == 1

    def event(self, name, product, src='unknown', ch='unknown', uid=None, invitation=None,
              oid=None, dedupe=None, now=None):
        if name not in EVENTS or product not in PRODUCTS or (uid is not None and not identifier(uid)):
            return
        now = int(time.time()) if now is None else int(now)
        if oid is not None and not identifier(oid):
            return
        with database(self.path) as c:
            return self._event(c, name, product, src, ch, uid, invitation, oid,
                               dedupe or uuid.uuid4().hex, now)

    def mark_test(self, uid, marked, evidence):
        if not identifier(uid) or evidence not in ('operator_confirmed_test_account', 'synthetic_offline_fixture'):
            raise ValueError('Explicit test evidence required')
        with database(self.path) as c:
            if marked:
                c.execute('INSERT OR REPLACE INTO journey_test_accounts VALUES(?,?,?)',
                          (uid, evidence, int(time.time())))
            else:
                c.execute('DELETE FROM journey_test_accounts WHERE user_id=?', (uid,))
