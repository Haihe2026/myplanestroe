"""Atomic receipt reservation around legacy shared confirmations, following pet guard."""
def install():
 from manual_payments import ManualMembership
 if getattr(ManualMembership,'_listing_guard',False):return
 old=ManualMembership.confirm_manual
 def confirm(self,oid,amount,transaction):
  import time
  created=False
  if type(amount)is int and isinstance(transaction,str) and 6<=len(transaction)<=128:
   with self.store.connect() as c:
    c.execute('BEGIN IMMEDIATE')
    c.execute('CREATE TABLE IF NOT EXISTS settlement_receipts(transaction_id TEXT PRIMARY KEY,product TEXT NOT NULL,order_id TEXT NOT NULL,amount_fen INTEGER NOT NULL,actor TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL)')
    o=c.execute('SELECT amount_fen,status FROM member_orders WHERE id=?',(oid,)).fetchone()
    r=c.execute('SELECT * FROM settlement_receipts WHERE transaction_id=?',(transaction,)).fetchone()
    if r and (r['product']!='shared' or r['order_id']!=oid or r['amount_fen']!=amount):raise self.problem(409,'交易流水已用于其他订单')
    if o and o['amount_fen']==amount and o['status'] in ('pending','reported') and not r:
     c.execute("INSERT INTO settlement_receipts VALUES(?,'shared',?,?,'legacy_shared','reserved',?)",(transaction,oid,amount,int(time.time())));created=True
  try:
   value=old(self,oid,amount,transaction)
   with self.store.connect() as c:c.execute("UPDATE settlement_receipts SET state='paid' WHERE transaction_id=? AND product='shared' AND order_id=?",(transaction,oid))
   return value
  except Exception:
   if created:
    with self.store.connect() as c:c.execute("DELETE FROM settlement_receipts WHERE transaction_id=? AND product='shared' AND order_id=? AND state='reserved'",(transaction,oid))
   raise
 ManualMembership.confirm_manual=confirm;ManualMembership._listing_guard=True
