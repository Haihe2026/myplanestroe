"""Extend the existing operations views with shared-wallet source attribution."""
import sqlite3
import re
import threading
import time
from monitor import Report, database
from settlement import SettlementError


class Reports(Report):
    def __init__(self, products, events, shared):
        super().__init__(products, events)
        self.shared = shared

    def summary(self, days):
        data = super().summary(days)
        since = int(time.time()) - days * 86400
        items = {item['product']: item for item in data['products']}
        with database(self.shared) as c:
            data['shared_accounts'] = c.execute('SELECT count(*) FROM users').fetchone()[0]
            for product in ('gemini', 'temu', 'xhs'):
                item = items.get(product)
                if item is None:
                    item = dict(product=product, connected=True, users=0, active=0, new_users=0, jobs={}, paid=dict(orders=0,amount_fen=0,payers=0), events=self.event_summary(product,since))
                    data['products'].append(item)
                elif not item['connected']:
                    continue
                count = c.execute('SELECT count(*) FROM product_accounts WHERE product=?', (product,)).fetchone()[0]
                linked = c.execute('SELECT count(*) FROM product_accounts p JOIN legacy_links l ON l.product=p.product AND l.user_id=p.user_id WHERE p.product=?', (product,)).fetchone()[0]
                item['users'] += count - linked
                item['new_users'] += c.execute('SELECT count(*) FROM product_accounts WHERE product=? AND created>=? AND user_id NOT IN (SELECT user_id FROM legacy_links WHERE product=?)', (product,since,product)).fetchone()[0]
                item['active'] += c.execute('SELECT count(DISTINCT j.user_id) FROM jobs j JOIN job_products p ON p.job_id=j.id WHERE p.product=? AND j.created>=?', (product,since)).fetchone()[0]
                for row in c.execute('SELECT j.status,count(*) n FROM jobs j JOIN job_products p ON p.job_id=j.id WHERE p.product=? AND j.created>=? GROUP BY j.status',(product,since)):
                    item['jobs'][row['status']] = item['jobs'].get(row['status'],0) + row['n']
                paid = c.execute("SELECT count(*) orders,coalesce(sum(o.amount_fen),0) amount_fen,count(DISTINCT o.user_id) payers FROM member_orders o JOIN order_sources s ON s.order_id=o.id WHERE s.product=? AND o.status='paid' AND o.paid_at>=?", (product,since)).fetchone()
                for k in ('orders','amount_fen','payers'):
                    item['paid'][k] += paid[k]
                item['shared_product_accounts'] = count
        data['unconnected'] = []
        data['xhs_usage_note'] = '仅共用账户和入口；本地选题任务不上传，不统计为生图'
        return data

    def users(self, product, query, page):
        if product != 'shared':
            return super().users(product,query,page)
        return Report({'shared':self.shared},self.events).users(product,query,page)

    def journey(self, product, uid):
        if product != 'shared':
            return super().journey(product,uid)
        data = Report({'shared':self.shared},self.events).journey(product,uid)
        with database(self.shared) as c:
            data['sources'] = [r[0] for r in c.execute('SELECT product FROM product_accounts WHERE user_id=?',(uid,))]
            links=[dict(r) for r in c.execute('SELECT product,legacy_uid FROM legacy_links WHERE user_id=?',(uid,))]
            for job in data['jobs']:
                row = c.execute('SELECT product FROM job_products WHERE job_id=?',(job['id'],)).fetchone()
                job['product'] = row[0] if row else 'unknown'
            for order in data['orders']:
                row = c.execute('SELECT product FROM order_sources WHERE order_id=?',(order['id'],)).fetchone()
                order['source_product'] = row[0] if row else 'unknown'
        data['legacy_accounts']=[]
        for link in links:
            with database(self.products[link['product']]) as c:
                row=c.execute('SELECT balance FROM users WHERE id=?',(link['legacy_uid'],)).fetchone()
                expired=c.execute('SELECT coalesce(sum(remaining),0) FROM member_grants WHERE user_id=? AND expires IS NOT NULL AND expires<=?',(link['legacy_uid'],int(time.time()))).fetchone()[0]
                link['remaining_uses']=max(0,row[0]-expired) if row else 0
            data['legacy_accounts'].append(link)
        with database(self.events) as c:
            data['events'] = [dict(r) for r in c.execute('SELECT created,event,status,channel,device,duration_ms FROM events WHERE user_id=? ORDER BY created DESC,id DESC LIMIT 100',(uid,))]
        return data

    def orders(self, product, status, query, page):
        if product != 'shared':
            return super().orders(product,status,query,page)
        data = Report({'shared':self.shared},self.events).orders(product,status,query,page)
        with database(self.shared) as c:
            for order in data['orders']:
                row = c.execute('SELECT product FROM order_sources WHERE order_id=?',(order['id'],)).fetchone()
                order['source_product'] = row[0] if row else 'unknown'
        return data


class Settlements:
    def __init__(self, adapters):
        self.adapters = adapters
        self.lock = threading.Lock()
        with self.adapters['shared'].connection() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS settlement_receipts(
                transaction_id TEXT PRIMARY KEY,product TEXT NOT NULL,order_id TEXT NOT NULL,
                amount_fen INTEGER NOT NULL,actor TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL)''')

    def preview(self, product, oid):
        if product not in self.adapters:
            raise SettlementError(400,'核款产品无效')
        return self.adapters[product].preview(product,oid)

    def confirm(self, body, actor):
        if not isinstance(body,dict) or body.get('product') not in self.adapters:
            raise SettlementError(400,'核款产品无效')
        chosen = body['product']
        tx=body.get('transaction_id')
        if body.get('verified') is not True or type(body.get('amount_fen')) is not int or not isinstance(tx,str) or not re.fullmatch(r'[A-Za-z0-9_-]{6,128}',tx):
            raise SettlementError(400,'请核对实际到账并填写完整收款流水号')
        order=self.preview(chosen,body.get('order_id'))
        if order['amount_fen']!=body['amount_fen']:
            raise SettlementError(409,'实收金额与订单金额不一致，未发放次数')
        # One operations process is deployed. Serializing all three order namespaces
        # prevents reusing one bank transaction to credit two different wallets.
        with self.lock:
            for product, adapter in self.adapters.items():
                with adapter.connection() as c:
                    old = c.execute("SELECT id FROM member_orders WHERE status='paid' AND transaction_id=?",(body.get('transaction_id'),)).fetchone()
                if old and (product != chosen or old[0] != body.get('order_id')):
                    raise SettlementError(409,'该交易流水已发放过额度，不能用于另一订单')
            # This durable reservation survives process restarts and coordinates every
            # canonical operator writer. A failed confirmation may only retry the same order.
            with self.adapters['shared'].connection() as c:
                c.execute('BEGIN IMMEDIATE')
                row=c.execute('SELECT product,order_id,amount_fen FROM settlement_receipts WHERE transaction_id=?',(tx,)).fetchone()
                if row and (row['product'],row['order_id'],row['amount_fen'])!=(chosen,body['order_id'],body['amount_fen']):
                    raise SettlementError(409,'该流水已用于另一订单或待核查，不能再次发放')
                if not row:
                    c.execute("INSERT INTO settlement_receipts VALUES(?,?,?,?,?,'reserved',?)",(tx,chosen,body['order_id'],body['amount_fen'],actor,int(time.time())))
            result=self.adapters[chosen].confirm(body,actor)
            with self.adapters['shared'].connection() as c:
                c.execute("UPDATE settlement_receipts SET state='paid' WHERE transaction_id=?",(tx,))
            return result
