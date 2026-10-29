"""Account handoff and prepaid packages. No browser-trusted payment receipts."""
import hmac
import secrets
import time
import uuid
from permanent_plans import PLANS as PERMANENT_PLANS

PLANS = {
    'plus': {'name': 'Plus', 'price_fen': 2900, 'images': 32},
    'pro': {'name': 'Pro', 'price_fen': 3900, 'images': 43},
    'ultra': {'name': 'Ultra', 'price_fen': 4900, 'images': 54},
    'business': {'name': '终身会员', 'price_fen': 99900, 'images': 2000},
}
PLANS.update(PERMANENT_PLANS)

class Membership:
    def __init__(self, store, problem, hash_value, point_values):
        global Problem, digest, points
        Problem, digest, points = problem, hash_value, point_values
        self.store = store
        # Deliberately closed until a real merchant adapter has been configured and tested.
        self.payment_ready = False
        with store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS web_tickets(hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL,used INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS web_sessions(hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS paid_wallets(user_id TEXT PRIMARY KEY,remaining INTEGER NOT NULL DEFAULT 0 CHECK(remaining>=0));
            CREATE TABLE IF NOT EXISTS member_orders(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,plan TEXT NOT NULL,
              amount_fen INTEGER NOT NULL,units INTEGER NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL,
              provider TEXT,transaction_id TEXT UNIQUE,paid_at INTEGER);
            CREATE TABLE IF NOT EXISTS paid_jobs(job_id TEXT PRIMARY KEY);
            ''')
            if 'product' not in [row['name'] for row in c.execute('PRAGMA table_info(member_orders)')]:
                c.execute("ALTER TABLE member_orders ADD COLUMN product TEXT NOT NULL DEFAULT 'gemini-image-assistant'")

    def plans(self):
        return {'payment_ready': self.payment_ready, 'purchase_type': 'membership', 'auto_renew_ready': False,
                'rules_confirmed': False,
                'plans': [dict(p, id=key, points=p['images']*1000,
                               period='permanent', valid_days=None,
                               renewal_price_fen=None)
                          for key, p in PERMANENT_PLANS.items()]}

    def handoff(self, uid):
        token = secrets.token_urlsafe(32)
        with self.store.connect() as c:
            c.execute('DELETE FROM web_tickets WHERE expires<?', (time.time(),))
            c.execute('INSERT INTO web_tickets VALUES(?,?,?,0)', (digest(token), uid, int(time.time())+300))
        return {'url': 'https://myplanestore.com/membership/#ticket=' + token, 'expires_in': 300}

    def redeem(self, ticket):
        if not isinstance(ticket, str) or len(ticket) != 43:
            raise Problem(401, '会员连接无效，请从 Skill 重新打开')
        session = secrets.token_urlsafe(32)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM web_tickets WHERE hash=? AND used=0 AND expires>?', (digest(ticket), time.time())).fetchone()
            if not row:
                raise Problem(401, '连接已使用或过期，请从 Skill 重新打开')
            c.execute('UPDATE web_tickets SET used=1 WHERE hash=?', (digest(ticket),))
            c.execute('DELETE FROM web_sessions WHERE expires<?', (time.time(),))
            c.execute('INSERT INTO web_sessions VALUES(?,?,?)', (digest(session), row['user_id'], int(time.time())+1800))
        return session

    def web_user(self, token):
        if not isinstance(token, str) or len(token) != 43:
            raise Problem(401, '请从 WorkBuddy 生图助手打开会员页面')
        with self.store.connect() as c:
            r = c.execute('SELECT user_id FROM web_sessions WHERE hash=? AND expires>?', (digest(token), time.time())).fetchone()
        if not r:
            raise Problem(401, '连接已过期，请从 Skill 重新打开')
        return r['user_id']

    def account(self, uid):
        return dict(points(self.store.balance(uid)), account_label='生图账户 · '+uid[:8])

    def order(self, uid, plan, product='gemini-image-assistant'):
        if not isinstance(plan, str) or plan not in PLANS:
            raise Problem(400, '套餐不存在')
        if product != 'gemini-image-assistant':
            raise Problem(503, '此技能的会员结算正在接入，现有额度保持独立')
        if not self.payment_ready:
            raise Problem(503, '收款通道尚未接入，暂不收款；免费生图照常使用')
        return self.create_pending(uid, plan)

    def create_pending(self, uid, plan):
        # Used only by a future server-side merchant adapter, never browser-supplied prices.
        if plan != 'business':
            raise Problem(503, '月度额度到期规则尚未确定，暂不创建月度订单')
        p = PLANS[plan]
        oid = uuid.uuid4().hex
        with self.store.connect() as c:
            c.execute('INSERT INTO member_orders(id,user_id,plan,amount_fen,units,status,created) VALUES(?,?,?,?,?,?,?)',
                      (oid, uid, plan, p['price_fen'], p['images'], 'pending', int(time.time())))
        return self.get_order(uid, oid)

    def get_order(self, uid, oid):
        with self.store.connect() as c:
            r = c.execute('SELECT id,plan,amount_fen,units,status FROM member_orders WHERE id=? AND user_id=?', (oid, uid)).fetchone()
        if not r:
            raise Problem(404, '订单不存在')
        return dict(r)

    def apply_verified_receipt(self, oid, amount_fen, transaction_id, provider, currency):
        # No HTTP route invokes this. A real adapter must verify signature AND query
        # the merchant order before calling; frontend redirects are never receipts.
        if (type(amount_fen) is not int or currency != 'CNY' or provider not in ('wechat','alipay')
                or not isinstance(transaction_id, str) or not 6 <= len(transaction_id) <= 128):
            raise Problem(400, '支付凭据格式无效')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            r = c.execute('SELECT * FROM member_orders WHERE id=?', (oid,)).fetchone()
            if not r or r['amount_fen'] != amount_fen:
                raise Problem(409, '订单金额不匹配')
            if r['plan'] != 'business':
                raise Problem(503, '月度结算尚未启用，不能按永久次数包入账')
            if r['status'] == 'paid':
                if r['transaction_id'] == transaction_id and r['provider'] == provider:
                    return False
                raise Problem(409, '订单已由其他交易结算')
            if r['status'] != 'pending' or c.execute('SELECT 1 FROM member_orders WHERE transaction_id=?', (transaction_id,)).fetchone():
                raise Problem(409, '交易已使用或订单状态无效')
            now = int(time.time())
            c.execute("UPDATE member_orders SET status='paid',provider=?,transaction_id=?,paid_at=? WHERE id=?", (provider,transaction_id,now,oid))
            c.execute('UPDATE users SET balance=balance+? WHERE id=?', (r['units'], r['user_id']))
            c.execute('INSERT INTO paid_wallets VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET remaining=remaining+excluded.remaining', (r['user_id'],r['units']))
            c.execute('INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,?,?,?)', (r['user_id'],oid,r['units'],'paid_topup',now))
            c.execute("INSERT OR IGNORE INTO member_gifts VALUES(?,'scam-check-360','member-welcome',?)", (r['user_id'],now))
        return True
