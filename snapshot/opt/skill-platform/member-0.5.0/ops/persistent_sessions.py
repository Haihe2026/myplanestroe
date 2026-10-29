"""Durable hashed admin sessions; the browser never stores the admin password."""
import hashlib
from contextlib import contextmanager
import hmac
import os
from pathlib import Path
import secrets
import sqlite3

SESSION_SECONDS = 90 * 24 * 60 * 60


class SessionStore:
    def __init__(self, path, password):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.path.chmod(0o600)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS sessions (key TEXT PRIMARY KEY, expires REAL NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT value FROM meta WHERE name='secret'").fetchone()
            secret = row[0] if row else secrets.token_hex(32)
            db.execute("INSERT OR IGNORE INTO meta VALUES ('secret', ?)", (secret,))
            marker = hmac.new(bytes.fromhex(secret), password.encode(), hashlib.sha256).hexdigest()
            row = db.execute("SELECT value FROM meta WHERE name='password_marker'").fetchone()
            if row is None or not hmac.compare_digest(row[0], marker):
                db.execute('DELETE FROM sessions')
                db.execute("INSERT OR REPLACE INTO meta VALUES ('password_marker', ?)", (marker,))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key, default=None):
        with self.connection() as db:
            row = db.execute('SELECT expires FROM sessions WHERE key=?', (key,)).fetchone()
            return row[0] if row else default

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, expires):
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?)', (key, expires))

    def __iter__(self):
        with self.connection() as db:
            return iter([row[0] for row in db.execute('SELECT key FROM sessions')])

    def pop(self, key, default=None):
        with self.connection() as db:
            row = db.execute('SELECT expires FROM sessions WHERE key=?', (key,)).fetchone()
            db.execute('DELETE FROM sessions WHERE key=?', (key,))
            return row[0] if row else default
