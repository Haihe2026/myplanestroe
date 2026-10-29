"""Customer keys for the image gateway, never upstream supplier credentials."""
import os
import secrets
import time
import uuid

class ApiAccess:
    def __init__(self, store, problem, digest):
        self.store, self.problem, self.digest = store, problem, digest
        with store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS customer_keys(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,
                hash TEXT UNIQUE NOT NULL,prefix TEXT NOT NULL,created INTEGER NOT NULL,revoked INTEGER,
                last_used INTEGER);
            CREATE TABLE IF NOT EXISTS api_jobs(key_id TEXT NOT NULL,job_id TEXT PRIMARY KEY,day TEXT NOT NULL);
            ''')

    def enabled(self):
        return os.environ.get('IMAGE_API_RESALE_CONFIRMED') == 'yes'

    @staticmethod
    def eligible(c, uid):
        return bool(c.execute("""SELECT 1 FROM member_orders o LEFT JOIN member_grants g ON o.id=g.order_id
            WHERE o.user_id=? AND o.status='paid' AND (o.plan='business' OR g.expires>?) LIMIT 1""", (uid,time.time())).fetchone())

    def listing(self, uid):
        with self.store.connect() as c:
            keys = [dict(row) for row in c.execute('SELECT id,prefix,created,revoked,last_used FROM customer_keys WHERE user_id=? ORDER BY created DESC LIMIT 50', (uid,))]
            eligible = self.eligible(c, uid)
        return {'enabled': self.enabled(), 'eligible': eligible, 'keys': keys,
                'base_url': 'https://myplanestore.com/v1', 'model': 'gpt-image-2',
                'scope': 'images', 'daily_limit': int(os.environ.get('IMAGE_API_DAILY_LIMIT', '100'))}

    def issue(self, uid):
        if not self.enabled():
            raise self.problem(503, '生图 API 发放暂未开放')
        key = 'mpimg_' + secrets.token_urlsafe(32)
        kid, now = uuid.uuid4().hex, int(time.time())
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not self.eligible(c, uid):
                raise self.problem(403, '请先完成会员支付；免费账户不能领取 API Key')
            count = c.execute('SELECT count(*) FROM customer_keys WHERE user_id=? AND revoked IS NULL', (uid,)).fetchone()[0]
            if count >= 2:
                raise self.problem(409, '最多保留两个有效 Key，请先撤销旧 Key')
            c.execute('INSERT INTO customer_keys(id,user_id,hash,prefix,created) VALUES(?,?,?,?,?)',
                      (kid, uid, self.digest(key), key[:12], now))
        return {'id': kid, 'key': key, 'prefix': key[:12], 'created': now}

    def revoke(self, uid, kid):
        if not isinstance(kid, str):
            raise self.problem(400, 'Key 标识无效')
        with self.store.connect() as c:
            row = c.execute('SELECT id FROM customer_keys WHERE id=? AND user_id=?', (kid, uid)).fetchone()
            if not row:
                raise self.problem(404, 'Key 不存在')
            c.execute('UPDATE customer_keys SET revoked=coalesce(revoked,?) WHERE id=?', (int(time.time()), kid))
        return {'revoked': True}

    def authenticate(self, token):
        if not self.enabled() or not isinstance(token, str) or len(token) != 49:
            raise self.problem(401, '生图 API Key 无效或服务未开放')
        with self.store.connect() as c:
            row = c.execute('SELECT id,user_id FROM customer_keys WHERE hash=? AND revoked IS NULL', (self.digest(token),)).fetchone()
            if not row or not self.eligible(c, row['user_id']):
                raise self.problem(401, '生图 API Key 无效或会员权限失效')
        return row['user_id'], row['id']

    def reserve(self, c, uid, kid, jid):
        row = c.execute('SELECT id FROM customer_keys WHERE id=? AND user_id=? AND revoked IS NULL', (kid, uid)).fetchone()
        if not self.enabled() or not row or not self.eligible(c, uid):
            raise self.problem(401, 'Key 已撤销或会员权限失效')
        day = time.strftime('%Y-%m-%d', time.gmtime())
        used = c.execute("SELECT count(*) FROM api_jobs a JOIN jobs j ON a.job_id=j.id WHERE j.user_id=? AND a.day=? AND j.status IN ('pending','succeeded')", (uid, day)).fetchone()[0]
        if used >= int(os.environ.get('IMAGE_API_DAILY_LIMIT', '100')):
            raise self.problem(429, '当日 API 生图上限已到，请次日再试')
        pending = c.execute("SELECT count(*) FROM jobs WHERE user_id=? AND status='pending'", (uid,)).fetchone()[0]
        if pending >= 2:
            raise self.problem(429, '已有待处理任务，请先核查结果，不要重复生成')
        c.execute('INSERT INTO api_jobs VALUES(?,?,?)', (kid, jid, day))
        c.execute('UPDATE customer_keys SET last_used=? WHERE id=?', (int(time.time()), kid))
