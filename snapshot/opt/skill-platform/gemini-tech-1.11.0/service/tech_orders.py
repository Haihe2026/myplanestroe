"""Per-task technical-service orders; no model keys, images or credit accounts."""
import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager


class Problem(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


class TechOrders:
    def __init__(self, db, payments, amount_fen):
        if type(amount_fen) is not int or not 1 <= amount_fen <= 10000:
            raise ValueError('Configure the same price as the SkillHub listing, in fen')
        self.db, self.pay, self.amount = str(db), payments, amount_fen
        with self.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS tech_orders(
                  id TEXT PRIMARY KEY, owner TEXT NOT NULL, task TEXT NOT NULL,
                  digest TEXT NOT NULL, amount INTEGER NOT NULL,
                  status TEXT NOT NULL, code_url TEXT, payment_code TEXT,
                  expires INTEGER, lease INTEGER NOT NULL DEFAULT 0,
                  transaction_id TEXT UNIQUE, created INTEGER NOT NULL,
                  UNIQUE(owner, task));
                CREATE TABLE IF NOT EXISTS tech_events(
                  id INTEGER PRIMARY KEY, order_id TEXT NOT NULL,
                  kind TEXT NOT NULL, created INTEGER NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=15)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def health(self):
        return {'version': '1.11.0', 'payment_ready': self.pay.ready,
                'amount_fen': self.amount, 'currency': 'CNY', 'model_cost_included': False}

    def invoke(self, token, body, order=None):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            raise Problem(401, 'INVALID_TASK_TOKEN')
        if (not isinstance(body, dict) or set(body) != {'task_id', 'task_hash', 'amount_fen', 'currency'}
                or not isinstance(body.get('task_id'), str)
                or not re.fullmatch(r'[a-f0-9]{32}', body['task_id'])
                or not isinstance(body.get('task_hash'), str)
                or not re.fullmatch(r'[a-f0-9]{64}', body['task_hash'])
                or type(body.get('amount_fen')) is not int or body['currency'] != 'CNY'):
            raise Problem(400, 'INVALID_REQUEST')
        if not self.pay.ready:
            raise Problem(503, 'PAYMENT_NOT_CONFIGURED')
        owner = hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM tech_orders WHERE owner=? AND task=?', (owner, body['task_id'])).fetchone()
            if row:
                if (row['digest'] != body['task_hash'] or row['amount'] != body['amount_fen']
                        or (order and order != row['id'])):
                    raise Problem(409, 'ORDER_TASK_MISMATCH')
            else:
                if order:
                    raise Problem(404, 'ORDER_NOT_FOUND')
                if body['amount_fen'] != self.amount:
                    raise Problem(409, 'PRICE_CHANGED')
                # A global pending-order ceiling bounds anonymous pre-order abuse.
                pending = c.execute("SELECT count(*) FROM tech_orders WHERE status='pending' AND created>?",
                                    (int(time.time())-3600,)).fetchone()[0]
                if pending >= 500:
                    raise Problem(429, 'ORDER_RATE_LIMIT')
                oid = 'GT' + uuid.uuid4().hex[:30]
                c.execute("INSERT INTO tech_orders(id,owner,task,digest,amount,status,created) VALUES(?,?,?,?,?,'pending',?)",
                          (oid, owner, body['task_id'], body['task_hash'], self.amount, int(time.time())))
                row = c.execute('SELECT * FROM tech_orders WHERE id=?', (oid,)).fetchone()
        row = dict(row)
        if row['status'] in ('refunding', 'refunded'):
            raise Problem(409, 'REFUNDED' if row['status'] == 'refunded' else 'REFUND_PENDING')
        if not row['payment_code'] and not row['transaction_id']:
            return self.offer(row)
        if order or row['transaction_id']:
            receipt = self.pay.query(row['id'])
            state = receipt.get('trade_state')
            if state == 'SUCCESS':
                self.confirm(row['id'], receipt)
                with self.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    current = c.execute('SELECT * FROM tech_orders WHERE id=?', (row['id'],)).fetchone()
                    if current['status'] in ('refunding', 'refunded'):
                        raise Problem(409, 'REFUND_PENDING')
                    if current['status'] != 'authorized':
                        c.execute("UPDATE tech_orders SET status='authorized' WHERE id=?", (row['id'],))
                        c.execute("INSERT INTO tech_events(order_id,kind,created) VALUES(?,'authorized',?)", (row['id'], int(time.time())))
                return 200, {'code': 'AUTHORIZED', 'out_trade_no': row['id'], 'task_id': row['task'],
                             'task_hash': row['digest'], 'amount_fen': row['amount'], 'currency': 'CNY'}, {}
            if state in ('CLOSED', 'REVOKED', 'PAYERROR', 'REFUND'):
                raise Problem(409, 'REFUNDED' if state == 'REFUND' else 'ORDER_CLOSED')
            if state not in ('NOTPAY', 'USERPAYING'):
                raise Problem(503, 'PAYMENT_QUERY_UNCERTAIN')
            if row['expires'] and row['expires'] <= time.time():
                raise Problem(409, 'PAYMENT_CODE_EXPIRED')
            return 202, {'code': 'NOT_PAID', 'out_trade_no': row['id']}, {}
        return self.offer(row)

    def offer(self, row):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = dict(c.execute('SELECT * FROM tech_orders WHERE id=?', (row['id'],)).fetchone())
            if row['lease'] > time.time():
                return 202, {'code': 'PREPARING_PAYMENT', 'out_trade_no': row['id']}, {}
            if row['payment_code']:
                if row['expires'] <= time.time():
                    raise Problem(409, 'PAYMENT_CODE_EXPIRED')
                return self.challenge(row)
            c.execute('UPDATE tech_orders SET lease=? WHERE id=?', (int(time.time())+120, row['id']))
        try:
            url = row['code_url'] or self.pay.create(row['id'], row['amount'])
            with self.connect() as c:
                c.execute('UPDATE tech_orders SET code_url=? WHERE id=?', (url, row['id']))
            code = self.pay.preorder(url)
            if not isinstance(code, str) or not re.fullmatch(r'[\x21-\x7e]{1,2048}', code):
                raise Problem(503, 'INVALID_PAYMENT_CODE')
            row.update(payment_code=code, expires=int(time.time())+900)
            with self.connect() as c:
                c.execute('UPDATE tech_orders SET payment_code=?,expires=? WHERE id=?', (code, row['expires'], row['id']))
        finally:
            with self.connect() as c:
                c.execute('UPDATE tech_orders SET lease=0 WHERE id=?', (row['id'],))
        return self.challenge(row)

    @staticmethod
    def challenge(row):
        headers = {'WeixinPay-Required': row['payment_code'], 'X-Out-Trade-No': row['id']}
        return 402, {'code': 'PAYMENT_REQUIRED', 'out_trade_no': row['id'], 'amount_fen': row['amount'],
                     'amount': f"{row['amount']/100:.2f}", 'currency': 'CNY', 'expires_at': row['expires'],
                     'WeixinPay': {'WeixinPay-Required': row['payment_code'],
                                  'prompt': '将此值作为paymentCode交给宿主weixinpay_pay。用户确认后携同一订单号原样重试。'}}, headers

    def confirm(self, oid, receipt):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM tech_orders WHERE id=?', (oid,)).fetchone()
            if not row:
                raise Problem(404, 'ORDER_NOT_FOUND')
            amount = receipt.get('amount', {})
            if (receipt.get('out_trade_no') != oid or receipt.get('mchid') != self.pay.mch
                    or receipt.get('appid') != self.pay.app or receipt.get('trade_state') != 'SUCCESS'
                    or amount.get('total') != row['amount'] or amount.get('currency') != 'CNY'
                    or not isinstance(receipt.get('transaction_id'), str) or not receipt['transaction_id']):
                raise Problem(403, 'INVALID_RECEIPT')
            if row['transaction_id'] and row['transaction_id'] != receipt['transaction_id']:
                raise Problem(409, 'TRANSACTION_CONFLICT')
            if not row['transaction_id']:
                c.execute("UPDATE tech_orders SET transaction_id=?,status='paid' WHERE id=?",
                          (receipt['transaction_id'], oid))
                c.execute("INSERT INTO tech_events(order_id,kind,created) VALUES(?,'paid',?)", (oid, int(time.time())))

    def notify(self, headers, raw):
        receipt = self.pay.notify(headers, raw)
        self.confirm(receipt.get('out_trade_no'), receipt)
        return {'code': 'SUCCESS', 'message': 'OK'}

    def refund(self, oid, confirmed=False):
        if confirmed is not True:
            raise Problem(400, 'OPERATOR_CONFIRMATION_REQUIRED')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM tech_orders WHERE id=?', (oid,)).fetchone()
            if not row or not row['transaction_id']:
                raise Problem(409, 'PAID_ORDER_REQUIRED')
            if row['status'] == 'refunded':
                return {'status': 'SUCCESS', 'already_refunded': True}
            c.execute("UPDATE tech_orders SET status='refunding' WHERE id=?", (oid,))
        result = self.pay.refund(oid, row['amount'])
        self.refund_result(result)
        return result

    def refund_result(self, value, callback=False):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM tech_orders WHERE id=?', (value.get('out_trade_no'),)).fetchone()
            if not row or row['status'] not in ('refunding', 'refunded'):
                raise Problem(409, 'REFUND_ORDER_MISMATCH')
            amount = value.get('amount', {})
            if (value.get('out_refund_no') != row['id'] or amount.get('refund') != row['amount']
                    or amount.get('total') != row['amount']):
                raise Problem(403, 'REFUND_AMOUNT_MISMATCH')
            if callback and (value.get('mchid') != self.pay.mch or value.get('transaction_id') != row['transaction_id']):
                raise Problem(403, 'REFUND_RECEIPT_MISMATCH')
            if not callback and amount.get('currency') != 'CNY':
                raise Problem(403, 'REFUND_CURRENCY_MISMATCH')
            status = value.get('refund_status' if callback else 'status')
            if status == 'SUCCESS' and row['status'] != 'refunded':
                c.execute("UPDATE tech_orders SET status='refunded' WHERE id=?", (row['id'],))
                c.execute("INSERT INTO tech_events(order_id,kind,created) VALUES(?,'refunded',?)", (row['id'], int(time.time())))

    def refund_notify(self, headers, raw):
        self.refund_result(self.pay.refund_notify(headers, raw), callback=True)
        return {'code': 'SUCCESS', 'message': 'OK'}
