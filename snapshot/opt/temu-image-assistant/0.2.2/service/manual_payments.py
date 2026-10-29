"""Manual QR orders and expiring grants, with operator-only settlement."""
import os
import time
import uuid
from membership import Membership, PLANS


class ManualMembership(Membership):
    def __init__(self, store, problem, hash_value, point_values):
        super().__init__(store, problem, hash_value, point_values)
        self.problem = problem
        self.payment_ready = os.environ.get("IMAGE_MANUAL_QR_ENABLED") == "yes"
        with store.connect() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS member_grants(
                  order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,
                  remaining INTEGER NOT NULL CHECK(remaining>=0),expires INTEGER);
                CREATE TABLE IF NOT EXISTS grant_jobs(job_id TEXT PRIMARY KEY,order_id TEXT NOT NULL);
            """)

    def plans(self):
        data = super().plans()
        data.update(rules_confirmed=True,payment_mode="manual_qr",
                    support_wechat="GMC2B2022",qr_url="/membership/payment-qr.png",
                    monthly_valid_days=30,auto_renew_ready=False)
        return data

    def order(self, uid, plan, product="temu-image-assistant"):
        if not self.payment_ready:
            raise self.problem(503, "扫码收款暂未开放")
        if product != "temu-image-assistant" or not isinstance(plan,str) or plan not in PLANS:
            raise self.problem(400, "此技能或套餐尚未开放购买")
        now = int(time.time())
        with self.store.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            old = c.execute("SELECT id FROM member_orders WHERE user_id=? AND plan=? AND status IN ('pending','reported') AND created>? ORDER BY created DESC LIMIT 1",
                            (uid,plan,now-86400)).fetchone()
            if old:
                oid = old["id"]
            else:
                if c.execute("SELECT count(*) FROM member_orders WHERE user_id=? AND created>?",(uid,now-86400)).fetchone()[0] >= 12:
                    raise self.problem(429,"今天的订单创建次数已达上限，请联系客服")
                oid = uuid.uuid4().hex
                p = PLANS[plan]
                c.execute("INSERT INTO member_orders(id,user_id,plan,amount_fen,units,status,created,product) VALUES(?,?,?,?,?,'pending',?,?)",
                          (oid,uid,plan,p["price_fen"],p["images"],now,product))
        return self.get_order(uid,oid)

    def get_order(self, uid, oid):
        data = super().get_order(uid,oid)
        with self.store.connect() as c:
            grant = c.execute("SELECT expires FROM member_grants WHERE order_id=?", (oid,)).fetchone()
            created = c.execute("SELECT created FROM member_orders WHERE id=?", (oid,)).fetchone()[0]
        data.update(product="temu-image-assistant",created=created,
                    expires_at=grant["expires"] if grant else None,
                    support_wechat="GMC2B2022",qr_url="/membership/payment-qr.png",
                    valid_days=None if data["plan"]=="business" else 30)
        return data

    def orders(self, uid):
        with self.store.connect() as c:
            ids = [row["id"] for row in c.execute("SELECT id FROM member_orders WHERE user_id=? ORDER BY created DESC LIMIT 20",(uid,))]
        return {"orders":[self.get_order(uid,oid) for oid in ids]}

    def report_paid(self, uid, oid):
        with self.store.connect() as c:
            c.execute("UPDATE member_orders SET status='reported' WHERE id=? AND user_id=? AND status='pending'",(oid,uid))
        return self.get_order(uid,oid)

    def confirm_manual(self, oid, amount_fen, transaction_id):
        if type(amount_fen) is not int or not isinstance(transaction_id,str) or not 6 <= len(transaction_id) <= 128:
            raise self.problem(400,"核款参数无效")
        now = int(time.time())
        with self.store.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM member_orders WHERE id=?", (oid,)).fetchone()
            if not row or row["amount_fen"] != amount_fen or row["product"] != "temu-image-assistant":
                raise self.problem(409,"订单或实收金额不匹配")
            if row["status"] == "paid":
                if row["transaction_id"] == transaction_id and row["provider"] == "manual_qr":
                    return False
                raise self.problem(409,"订单已结算")
            if row["status"] not in ("pending","reported") or c.execute("SELECT 1 FROM member_orders WHERE transaction_id=?",(transaction_id,)).fetchone():
                raise self.problem(409,"交易流水已使用或订单状态无效")
            expires = None if row["plan"]=="business" else now+30*86400
            c.execute("UPDATE member_orders SET status='paid',provider='manual_qr',transaction_id=?,paid_at=? WHERE id=?",(transaction_id,now,oid))
            c.execute("INSERT INTO member_grants VALUES(?,?,?,?)",(oid,row["user_id"],row["units"],expires))
            c.execute("UPDATE users SET balance=balance+? WHERE id=?",(row["units"],row["user_id"]))
            c.execute("INSERT INTO paid_wallets VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET remaining=remaining+excluded.remaining",(row["user_id"],row["units"]))
            c.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,?,'manual_verified_topup',?)",(row["user_id"],oid,row["units"],now))
            c.execute("INSERT OR IGNORE INTO member_gifts VALUES(?,'scam-check-360','member-welcome',?)",(row["user_id"],now))
        return True

    def expire(self, c, uid):
        now = int(time.time())
        for row in c.execute("SELECT order_id,remaining FROM member_grants WHERE user_id=? AND remaining>0 AND expires IS NOT NULL AND expires<=?",(uid,now)).fetchall():
            c.execute("UPDATE users SET balance=balance-? WHERE id=?",(row["remaining"],uid))
            c.execute("UPDATE paid_wallets SET remaining=remaining-? WHERE user_id=?",(row["remaining"],uid))
            c.execute("UPDATE member_grants SET remaining=0 WHERE order_id=?",(row["order_id"],))
            c.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,?,'monthly_expiry',?)",(uid,row["order_id"],-row["remaining"],now))

    def next_grant(self, c, uid):
        return c.execute("SELECT order_id FROM member_grants WHERE user_id=? AND remaining>0 AND (expires IS NULL OR expires>?) ORDER BY expires IS NULL,expires,order_id LIMIT 1",(uid,time.time())).fetchone()

    def reserve_grant(self, c, uid, jid):
        row = self.next_grant(c,uid)
        if row:
            c.execute("UPDATE member_grants SET remaining=remaining-1 WHERE order_id=?",(row["order_id"],))
            c.execute("INSERT INTO grant_jobs VALUES(?,?)",(jid,row["order_id"]))

    def refund_grant(self, c, jid):
        row = c.execute("SELECT g.order_id,g.expires FROM member_grants g JOIN grant_jobs j ON g.order_id=j.order_id WHERE j.job_id=?",(jid,)).fetchone()
        if not row:
            return True
        if row["expires"] is not None and row["expires"] <= time.time():
            return False
        c.execute("UPDATE member_grants SET remaining=remaining+1 WHERE order_id=?",(row["order_id"],))
        return True
