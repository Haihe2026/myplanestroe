"""First-party Skill credentials; separate from optional external customer API keys."""
import base64
import hashlib
import hmac
import os
import re
import time


class SkillAccess:
    def __init__(self, store, problem):
        self.store, self.problem = store, problem
        with store.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS skill_credentials(
                    user_id TEXT PRIMARY KEY,id TEXT UNIQUE NOT NULL,nonce TEXT NOT NULL,
                    created INTEGER NOT NULL,revoked INTEGER,bound_at INTEGER);
                CREATE TRIGGER IF NOT EXISTS paid_skill_credential_update
                AFTER UPDATE OF status ON member_orders
                WHEN NEW.status='paid' AND OLD.status!='paid'
                BEGIN
                    INSERT OR IGNORE INTO skill_credentials(user_id,id,nonce,created)
                    VALUES(NEW.user_id,lower(hex(randomblob(16))),lower(hex(randomblob(32))),
                           cast(strftime('%s','now') as integer));
                END;
                CREATE TRIGGER IF NOT EXISTS paid_skill_credential_insert
                AFTER INSERT ON member_orders WHEN NEW.status='paid'
                BEGIN
                    INSERT OR IGNORE INTO skill_credentials(user_id,id,nonce,created)
                    VALUES(NEW.user_id,lower(hex(randomblob(16))),lower(hex(randomblob(32))),
                           cast(strftime('%s','now') as integer));
                END;
                INSERT OR IGNORE INTO skill_credentials(user_id,id,nonce,created)
                SELECT DISTINCT user_id,lower(hex(randomblob(16))),lower(hex(randomblob(32))),
                       cast(strftime('%s','now') as integer)
                FROM member_orders WHERE status='paid';
            ''')

    @staticmethod
    def configured():
        return len(os.environ.get('IMAGE_TRIAL_HMAC_KEY', '')) >= 16

    def row(self, uid):
        with self.store.connect() as c:
            return c.execute('SELECT * FROM skill_credentials WHERE user_id=?', (uid,)).fetchone()

    def public(self, uid):
        row = self.row(uid)
        if not row:
            return dict(state='pending_payment', required=False)
        return dict(state='revoked' if row['revoked'] else 'ready' if self.configured() else 'unavailable',
                    required=True, id=row['id'], fingerprint=row['id'][-8:], bound=bool(row['bound_at']))

    def token(self, row):
        if not self.configured():
            raise self.problem(503, '专属服务正在连接，请稍后继续原任务')
        message = ('myplanestore:gemini-skill:v1:' + row['user_id'] + ':' + row['id'] + ':' + row['nonce']).encode()
        digest = hmac.new(os.environ['IMAGE_TRIAL_HMAC_KEY'].encode(), message, hashlib.sha256).digest()
        return 'mpskill_' + row['id'] + '_' + base64.urlsafe_b64encode(digest).decode().rstrip('=')

    def binding(self, uid):
        public = self.public(uid)
        if public['state'] != 'ready':
            return public
        return dict(public, key=self.token(self.row(uid)), scope='gemini:images')

    def authenticate(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'mpskill_[0-9a-f]{32}_[A-Za-z0-9_-]{43}', key):
            raise self.problem(401, '专属Key需要重新绑定，请在Skill中刷新账户')
        with self.store.connect() as c:
            row = c.execute('SELECT * FROM skill_credentials WHERE id=?', (key[8:40],)).fetchone()
        if not row or row['revoked'] or not hmac.compare_digest(key, self.token(row)):
            raise self.problem(401, '专属Key需要重新绑定，请在Skill中刷新账户')
        return row['user_id'], row['id']

    def acknowledge(self, uid, key):
        owner, kid = self.authenticate(key)
        if owner != uid:
            raise self.problem(403, '专属Key与原账户不匹配')
        with self.store.connect() as c:
            updated = c.execute('UPDATE skill_credentials SET bound_at=? WHERE user_id=? AND id=? AND revoked IS NULL',
                                (int(time.time()), uid, kid))
            if updated.rowcount != 1:
                raise self.problem(401, '专属Key状态已更新，请在Skill中刷新账户')
        return dict(bound=True, id=kid)

    def manage(self, uid, action):
        if action not in ('revoke', 'rotate'):
            raise self.problem(400, 'Key操作无效')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM skill_credentials WHERE user_id=?', (uid,)).fetchone():
                raise self.problem(403, '核款到账后即可开通专属Key')
            if action == 'revoke':
                c.execute('UPDATE skill_credentials SET revoked=coalesce(revoked,?) WHERE user_id=?', (int(time.time()), uid))
            else:
                c.execute('UPDATE skill_credentials SET id=lower(hex(randomblob(16))),nonce=lower(hex(randomblob(32))),revoked=NULL,bound_at=NULL WHERE user_id=?', (uid,))
        return self.public(uid)
