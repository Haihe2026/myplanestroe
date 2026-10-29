"""One server-owned allocation, valid for 365 days or until credits are spent."""
import time
import uuid

UNITS=150
VALID_SECONDS=365*86400


class AnnualQuota:
    def __init__(self,store):
        self.store=store
        with store.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS annual_activations(
                user_id TEXT PRIMARY KEY,grant_id TEXT NOT NULL UNIQUE,
                activated INTEGER NOT NULL,expires INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS annual_activation_requests(user_id TEXT PRIMARY KEY,created INTEGER NOT NULL);''')

    def activate_authorized_account(self,uid):
        # Caller owns activation policy; this module does not verify payment.
        now=int(time.time())
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():raise ValueError('Unknown service account')
            self.store.membership.expire(c,uid)
            old=c.execute('SELECT * FROM annual_activations WHERE user_id=?',(uid,)).fetchone()
            if old:
                grant=c.execute('SELECT remaining FROM member_grants WHERE order_id=?',(old['grant_id'],)).fetchone()
                return {'awarded_points':0,'annual_balance_points':grant['remaining']*1000,
                        'expires_at':old['expires'],'expired':old['expires']<=now}
            grant='annual:'+uuid.uuid4().hex;end=now+VALID_SECONDS
            c.execute('INSERT INTO annual_activations VALUES(?,?,?,?)',(uid,grant,now,end))
            c.execute('INSERT INTO member_grants VALUES(?,?,?,?)',(grant,uid,UNITS,end))
            c.execute('UPDATE users SET balance=balance+? WHERE id=?',(UNITS,uid))
            c.execute('INSERT INTO paid_wallets VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET remaining=remaining+excluded.remaining',(uid,UNITS))
            c.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,140,'annual_activation_grant',?)",(uid,grant,now))
            c.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,10,'annual_first_bonus',?)",(uid,grant,now))
        return {'awarded_points':150000,'annual_balance_points':150000,'expires_at':end,'expired':False}

    def status(self,uid):
        now=int(time.time())
        with self.store.connect() as c:
            self.store.membership.expire(c,uid)
            row=c.execute('SELECT a.expires,g.remaining FROM annual_activations a JOIN member_grants g ON a.grant_id=g.order_id WHERE a.user_id=?',(uid,)).fetchone()
        if not row:return {'activated':False}
        return {'activated':True,'balance_points':row['remaining']*1000,'expires_at':row['expires'],
                'active':row['expires']>now and row['remaining']>0}
