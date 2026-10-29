"""Atomic quota grant for an owner-confirmed order, with a distinct email provider."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
import time

PLANS = {'plus': (2900, 32), 'pro': (3900, 43), 'ultra': (4900, 54), 'business': (99900, 2000)}


@contextmanager
def connection(path, readonly=False):
    db = sqlite3.connect(Path(path).resolve().as_uri() + ('?mode=ro' if readonly else '?mode=rw'), uri=True, timeout=20)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


class EmailSettlement:
    def __init__(self, products):
        self.products = products

    def initialize(self):
        for product in self.products.values():
            with connection(product['path']) as db:
                db.executescript('''
                    CREATE TABLE IF NOT EXISTS email_approvals(
                      order_id TEXT PRIMARY KEY,reference TEXT UNIQUE NOT NULL,
                      notification_id TEXT UNIQUE NOT NULL,reply_id TEXT UNIQUE NOT NULL,
                      reply_sha256 TEXT NOT NULL,approver TEXT NOT NULL,authentication TEXT NOT NULL,
                      amount_fen INTEGER NOT NULL,units INTEGER NOT NULL,created INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS ops_settlements(
                      order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,transaction_id TEXT NOT NULL,
                      amount_fen INTEGER NOT NULL,points INTEGER NOT NULL,actor TEXT NOT NULL,created INTEGER NOT NULL);
                ''')

    def read_order(self, namespace, oid, db=None):
        if namespace not in self.products:
            raise ValueError('unknown_namespace')
        if db is None:
            with connection(self.products[namespace]['path'], readonly=True) as opened:
                return self.read_order(namespace, oid, opened)
        row = db.execute('SELECT id,user_id,product,plan,amount_fen,units,status,created,provider,paid_at FROM member_orders WHERE id=?', (oid,)).fetchone()
        if not row or row['product'] != self.products[namespace]['stored_product']:
            raise ValueError('invalid_order')
        if PLANS.get(row['plan']) != (row['amount_fen'], row['units']):
            raise ValueError('invalid_plan')
        result = dict(row, namespace=namespace)
        source = db.execute('SELECT product FROM order_sources WHERE order_id=?', (oid,)).fetchone() if namespace == 'shared' else None
        result['source_product'] = source[0] if source else ('gemini' if namespace == 'shared' else namespace)
        return result

    def reported(self):
        for namespace, product in self.products.items():
            with connection(product['path'], readonly=True) as db:
                for row in db.execute("SELECT id FROM member_orders WHERE status='reported' ORDER BY created"):
                    yield self.read_order(namespace, row[0], db)

    def approve(self, snapshot, notification_id, proof, raw_sha256):
        namespace, oid = snapshot['namespace'], snapshot['id']
        if proof['parent'] != notification_id:
            raise ValueError('notification_mismatch')
        reference = 'email_' + hashlib.sha256((namespace + ':' + oid + ':' + notification_id).encode()).hexdigest()[:48]
        now = int(time.time())
        with connection(self.products[namespace]['path']) as db:
            db.execute('BEGIN IMMEDIATE')
            order = self.read_order(namespace, oid, db)
            for key in ('user_id', 'product', 'plan', 'amount_fen', 'units', 'created', 'source_product'):
                if order[key] != snapshot[key]:
                    raise ValueError('order_changed_after_notification')
            if order['status'] == 'paid':
                audit = db.execute('SELECT reference,notification_id FROM email_approvals WHERE order_id=?', (oid,)).fetchone()
                return dict(order_id=oid, credited=False, status='already_approved' if audit and audit['reference'] == reference and audit['notification_id'] == notification_id else 'already_paid')
            if order['status'] != 'reported':
                raise ValueError('order_not_reported')
            if not db.execute('SELECT 1 FROM users WHERE id=?', (order['user_id'],)).fetchone():
                raise ValueError('missing_account')
            expires = None if order['plan'] == 'business' else now + 30 * 86400
            db.execute("UPDATE member_orders SET status='paid',provider='manual_email',transaction_id=?,paid_at=? WHERE id=?", (reference, now, oid))
            db.execute('INSERT INTO member_grants VALUES(?,?,?,?)', (oid, order['user_id'], order['units'], expires))
            db.execute('UPDATE users SET balance=balance+? WHERE id=?', (order['units'], order['user_id']))
            db.execute('INSERT INTO paid_wallets VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET remaining=remaining+excluded.remaining', (order['user_id'], order['units']))
            db.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,?,'email_verified_topup',?)", (order['user_id'], oid, order['units'], now))
            db.execute("INSERT OR IGNORE INTO member_gifts VALUES(?,'scam-check-360','member-welcome',?)", (order['user_id'], now))
            db.execute('INSERT INTO ops_settlements VALUES(?,?,?,?,?,?,?)', (oid, order['user_id'], reference, order['amount_fen'], order['units'] * 1000, 'email:' + proof['approver'], now))
            db.execute('INSERT INTO email_approvals VALUES(?,?,?,?,?,?,?,?,?,?)', (oid, reference, notification_id, proof['reply_id'], raw_sha256, proof['approver'], proof['authentication'], order['amount_fen'], order['units'], now))
        return dict(order_id=oid, credited=True, status='paid', units=order['units'], expires_at=expires, reference=reference)
