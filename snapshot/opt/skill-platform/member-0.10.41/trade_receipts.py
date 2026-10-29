"""Reserve pet receipts in the existing cross-product receipt registry.
Only new receipt rows are inserted; old order/grant behavior delegates unchanged.
This prevents a new trade recharge receipt being replayed into the pet channel.
"""
def install():
    from pet_billing import PetBilling
    if getattr(PetBilling,'_trade_receipt_guard',False):return
    previous=PetBilling.settle
    def settle(self,oid,amount,transaction,actor,verified):
        created=False
        # Validate before reserving a transaction; delegated method remains authoritative.
        import re
        if verified is True and type(amount) is int and re.fullmatch(r'[A-Za-z0-9_-]{6,128}',transaction or '') and actor:
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                c.execute('CREATE TABLE IF NOT EXISTS settlement_receipts(transaction_id TEXT PRIMARY KEY,product TEXT NOT NULL,order_id TEXT NOT NULL,amount_fen INTEGER NOT NULL,actor TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL)')
                r=c.execute('SELECT * FROM settlement_receipts WHERE transaction_id=?',(transaction,)).fetchone()
                if r and (r['product']!='pet' or r['order_id']!=oid or r['amount_fen']!=amount):self.fail(409,'交易流水已用于其他订单')
                if not r:
                    c.execute("INSERT INTO settlement_receipts VALUES(?,'pet',?,?,?,'reserved',?)",(transaction,oid,amount,actor,int(self.clock())));created=True
        try:
            result=previous(self,oid,amount,transaction,actor,verified)
            with self.store.connect() as c:c.execute("UPDATE settlement_receipts SET state='paid' WHERE transaction_id=? AND product='pet' AND order_id=?",(transaction,oid))
            return result
        except Exception:
            if created:
                with self.store.connect() as c:c.execute("DELETE FROM settlement_receipts WHERE transaction_id=? AND product='pet' AND order_id=? AND state='reserved'",(transaction,oid))
            raise
    PetBilling.settle=settle;PetBilling._trade_receipt_guard=True
