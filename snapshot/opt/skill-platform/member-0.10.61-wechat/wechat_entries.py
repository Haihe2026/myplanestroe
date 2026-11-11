"""Short-lived, encrypted registration context across QR refreshes and restarts."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EntryCache:
    def __init__(self, store):
        self.store = store
        path = Path(os.environ.get('WECHAT_ENTRY_KEY_FILE', '/etc/skill-platform/wechat-entry.key'))
        if os.name != 'nt' and path.stat().st_mode & 0o077:
            raise RuntimeError('Private entry key required')
        key = path.read_bytes()
        if len(key) != 32:
            raise RuntimeError('Invalid entry key')
        self.cipher = AESGCM(key)
        self.registration_key = hmac.new(key, b'wechat-browser-credential-key:v1', hashlib.sha256).digest()
        with store.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS wechat_entry_cache(
                hash TEXT PRIMARY KEY, product TEXT NOT NULL, payload BLOB,
                expires INTEGER NOT NULL, linked_uid TEXT)''')

    def remember(self, key, row):
        expires = int(row['expires']) + 1800
        if expires <= time.time():
            return
        nonce = os.urandom(12)
        payload = nonce + self.cipher.encrypt(nonce, json.dumps(row).encode(), key.encode())
        with self.store.connect() as c:
            c.execute('DELETE FROM wechat_entry_cache WHERE expires<?', (time.time(),))
            c.execute('INSERT OR IGNORE INTO wechat_entry_cache VALUES(?,?,?,?,NULL)',
                      (key, row['product'], payload, expires))

    def restore(self, key, product):
        with self.store.connect() as c:
            cached = c.execute('SELECT * FROM wechat_entry_cache WHERE hash=? AND product=? AND expires>?',
                               (key, product, time.time())).fetchone()
        if not cached or not cached['payload']:
            return None
        payload = cached['payload']
        row = json.loads(self.cipher.decrypt(payload[:12], payload[12:], key.encode()))
        row['expires'] = cached['expires']
        return row

    def linked(self, key, product):
        with self.store.connect() as c:
            row = c.execute('SELECT linked_uid FROM wechat_entry_cache WHERE hash=? AND product=? AND expires>?',
                            (key, product, time.time())).fetchone()
        return row[0] if row else None

    def consume(self, key, uid):
        with self.store.connect() as c:
            c.execute('UPDATE wechat_entry_cache SET payload=NULL,linked_uid=? WHERE hash=?', (uid, key))

    def registration_secret(self, identity):
        # A retry after partial registration resolves the same account, even with
        # a fresh QR state. This credential is retained only on the server.
        value = hmac.new(self.registration_key, identity.encode(), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(value).decode().rstrip('=')
