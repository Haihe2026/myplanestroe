"""Operator-only adapter to the personal gateway's existing settlement method."""
from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3
import time
from types import SimpleNamespace


class SettlementError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


class Settlement:
    def __init__(self, path, confirm_method, product='gemini', stored_product='gemini-image-assistant'):
        self.path, self.confirm_method = path, confirm_method
        self.product, self.stored_product = product, stored_product
        with self.connection() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS ops_settlements(
                order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,transaction_id TEXT NOT NULL,
                amount_fen INTEGER NOT NULL,points INTEGER NOT NULL,actor TEXT NOT NULL,
                created INTEGER NOT NULL)''')

    @contextmanager
    def connection(self):
        c = sqlite3.connect(Path(self.path).resolve().as_uri() + '?mode=rw', uri=True, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def preview(self, product, oid):
        if product != self.product or not isinstance(oid, str) or not re.fullmatch(r'[a-f0-9]{32}', oid):
            raise SettlementError(400, '订单或产品无效')
        with self.connection() as c:
            r = c.execute('''SELECT o.id,o.user_id,o.product,o.plan,o.amount_fen,o.units,o.status,o.paid_at,
                g.expires FROM member_orders o LEFT JOIN member_grants g ON g.order_id=o.id
                WHERE o.id=? AND EXISTS(SELECT 1 FROM users WHERE id=o.user_id)''', (oid,)).fetchone()
            if not r or r['product'] != self.stored_product:
                raise SettlementError(404, '订单不存在或不属于个人生图助手')
            return dict(r, points=r['units'] * 1000)

    def confirm(self, body, actor):
        if not isinstance(body, dict) or body.get('verified') is not True:
            raise SettlementError(400, '请先核对微信实际到账并勾选确认')
        tx = body.get('transaction_id')
        if not isinstance(tx, str) or not re.fullmatch(r'[A-Za-z0-9_-]{6,128}', tx):
            raise SettlementError(400, '请填写收款平台的完整交易流水号（6至128位字母、数字、下划线或短横线）')
        amount = body.get('amount_fen')
        if type(amount) is not int or amount <= 0:
            raise SettlementError(400, '实收金额无效')
        order = self.preview(body.get('product'), body.get('order_id'))
        if order['amount_fen'] != amount:
            raise SettlementError(409, '实收金额与订单金额不一致，未发放积分')
        result = {}

        @contextmanager
        def audited_connection():
            with self.connection() as c:
                yield c
                # This runs inside the same transaction as the gateway's credit grant.
                paid = c.execute('''SELECT o.user_id,o.amount_fen,o.units,o.paid_at,u.balance,g.expires
                    FROM member_orders o JOIN users u ON u.id=o.user_id
                    JOIN member_grants g ON g.order_id=o.id WHERE o.id=? AND o.status='paid'
                    AND o.transaction_id=? AND o.provider='manual_qr' ''', (order['id'], tx)).fetchone()
                if not paid:
                    raise SettlementError(409, '账户或入账记录异常，已取消本次操作')
                c.execute('''INSERT OR IGNORE INTO ops_settlements
                    VALUES(?,?,?,?,?,?,?)''', (order['id'], paid['user_id'], tx, paid['amount_fen'],
                                              paid['units'] * 1000, actor, int(time.time())))
                expired = c.execute('''SELECT coalesce(sum(remaining),0) FROM member_grants
                    WHERE user_id=? AND expires IS NOT NULL AND expires<=?''',
                    (paid['user_id'], int(time.time()))).fetchone()[0]
                result.update(order_id=order['id'], user_id=paid['user_id'], points=paid['units'] * 1000,
                              balance_points=max(0, paid['balance'] - expired) * 1000,
                              expires_at=paid['expires'], paid_at=paid['paid_at'], status='paid')

        service = SimpleNamespace(store=SimpleNamespace(connect=audited_connection), problem=SettlementError)
        changed = self.confirm_method(service, order['id'], amount, tx)
        return dict(result, credited=changed)
