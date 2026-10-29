"""Create zero-quota accounts; renew existing identities without modifying balances."""
import hashlib
import hmac
import os
import secrets
import time
import uuid


def register(self, secret, ip, accepted, grant=0):
    from server import Problem, digest, points
    if accepted is not True:
        raise Problem(400, '请先同意账户与图片处理说明')
    if (not isinstance(secret, str) or len(secret) != 43
            or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in secret)):
        raise Problem(400, '账户凭证格式错误')
    if not self.public_trial_enabled():
        raise Problem(503, '账户开通暂不可用，请稍后重试')
    identity, now = digest(secret), int(time.time())
    day = time.strftime('%Y-%m-%d', time.gmtime(now))
    ip_hash = hmac.new(os.environ['IMAGE_TRIAL_HMAC_KEY'].encode(), ip.encode(), hashlib.sha256).hexdigest()
    with self.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        old = c.execute('SELECT user_id FROM trial_claims WHERE hash=?', (identity,)).fetchone()
        if not old:
            old = c.execute('SELECT user_id FROM sessions WHERE hash=?', (identity,)).fetchone()
        if old:
            uid, created = old['user_id'], False
            self.membership.expire(c, uid)
        else:
            n = c.execute('SELECT count FROM claim_limits WHERE ip_hash=? AND day=?', (ip_hash, day)).fetchone()
            if n and n[0] >= int(os.environ.get('IMAGE_ASSISTANT_ACCOUNT_IP_DAILY_LIMIT', '10')):
                raise Problem(429, '账户开通频率过高，请稍后重试；已有账户仍可恢复')
            uid, created = str(uuid.uuid4()), True
            c.execute('INSERT INTO users VALUES(?,0)', (uid,))
            c.execute('INSERT INTO claim_limits VALUES(?,?,1) ON CONFLICT(ip_hash,day) DO UPDATE SET count=count+1', (ip_hash, day))
            c.execute("INSERT INTO ledger(user_id,amount,kind,created) VALUES(?,0,'account_created',?)", (uid, now))
        c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)', (identity, uid, now))
        c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)', (identity, uid, now + 7 * 86400))
        balance = c.execute('SELECT balance FROM users WHERE id=?', (uid,)).fetchone()[0]
    return dict(points(balance), token=secret, granted=False, created=created, purchase_required=balance < 1)


def install(store):
    from types import MethodType
    store.register = MethodType(register, store)
    return store
