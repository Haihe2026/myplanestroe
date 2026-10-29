"""Trust the host usage gate; do not claim independent payment verification."""
import hashlib
import hmac
import json
import os
import re
import time
import uuid


class AnnualAccounts:
    def __init__(self, store, quota, problem):
        self.store, self.quota, self.problem = store, quota, problem
        with store.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS annual_claim_limits(
                ip_hash TEXT NOT NULL,day TEXT NOT NULL,count INTEGER NOT NULL,
                PRIMARY KEY(ip_hash,day));''')

    def account(self, secret, accepted, ip):
        if accepted is not True:
            raise self.problem(400, '请先确认账户与素材发送说明')
        if not isinstance(secret, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', secret):
            raise self.problem(400, '账户标识格式错误')
        if os.environ.get('IMAGE_ANNUAL_ENABLED') != 'yes':
            raise self.problem(503, '一年额度激活暂未开放')
        key = os.environ.get('IMAGE_TRIAL_HMAC_KEY')
        if not key or not self.store.provider.ready:
            raise self.problem(503, '账户或生图服务暂不可用')
        hashed = hashlib.sha256(secret.encode()).hexdigest()
        now = int(time.time())
        day = time.strftime('%Y-%m-%d', time.gmtime(now))
        iphash = hmac.new(key.encode(), ip.encode(), hashlib.sha256).hexdigest()
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT user_id FROM trial_claims WHERE hash=?', (hashed,)).fetchone()
            if not row:
                row = c.execute('SELECT user_id FROM sessions WHERE hash=?', (hashed,)).fetchone()
            uid = row['user_id'] if row else str(uuid.uuid4())
            claimed = c.execute('SELECT 1 FROM annual_activations WHERE user_id=?', (uid,)).fetchone()
            pending = c.execute('SELECT 1 FROM annual_activation_requests WHERE user_id=?', (uid,)).fetchone()
            if not claimed and not pending:
                limit = c.execute('SELECT count FROM annual_claim_limits WHERE ip_hash=? AND day=?', (iphash, day)).fetchone()
                if limit and limit[0] >= int(os.environ.get('IMAGE_ANNUAL_IP_DAILY_LIMIT', '3')):
                    raise self.problem(429, '当前网络激活次数已达上限，请稍后再试')
                c.execute('INSERT INTO annual_claim_limits VALUES(?,?,1) ON CONFLICT(ip_hash,day) DO UPDATE SET count=count+1', (iphash, day))
                c.execute('INSERT INTO annual_activation_requests VALUES(?,?)', (uid, now))
            if not row:
                c.execute('INSERT INTO users VALUES(?,0)', (uid,))
            c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)', (hashed, uid, now))
            c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)', (hashed, uid, now + 7*86400))
        grant = self.quota.activate_authorized_account(uid)
        return dict(grant, token=secret, balance_points=self.store.balance(uid)*1000,
                    payment_verified=False, activation_policy='host_gated_usage')


def annual_handler(parent, accounts):
    class Handler(parent):
        def run_request(self):
            if self.path != '/skill-pay/account':
                return super().run_request()
            if self.command != 'POST':
                return self.send(405, {'error': '仅允许POST'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise accounts.problem(400, '请求大小无效')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict) or set(body) != {'install_secret', 'accepted'}:
                    raise accounts.problem(400, '账户请求字段无效')
                ip = self.headers.get('X-Real-IP', self.client_address[0]) if self.client_address[0] == '127.0.0.1' else self.client_address[0]
                if len(ip) > 64:
                    raise accounts.problem(400, '网络标识无效')
                return self.send(200, accounts.account(body['install_secret'], body['accepted'], ip))
            except accounts.problem as error:
                return self.send(error.status, {'error': error.message})
            except (ValueError, TypeError, UnicodeError):
                return self.send(400, {'error': '请求格式错误'})
            except Exception:
                return self.send(500, {'error': '账户服务暂不可用，请保留原身份稍后重试'})
        do_GET = run_request
        do_POST = run_request
    return Handler
