"""Pet-only additions. Legacy orders/grants continue using their immutable snapshots."""
import hashlib,json,re,time,uuid
from datetime import datetime,timezone,timedelta
from pet_billing import PetBilling as LegacyBilling
from product_config import settings

class PetResources(LegacyBilling):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        with self.store.connect() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS pet_photo_results(job_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,image_hash TEXT NOT NULL,result TEXT);
CREATE INDEX IF NOT EXISTS pet_photo_image_lookup ON pet_photo_results(user_id,image_hash);
CREATE TABLE IF NOT EXISTS pet_photo_keys(user_id TEXT NOT NULL,idem TEXT NOT NULL,payload_hash TEXT NOT NULL,job_id TEXT NOT NULL,PRIMARY KEY(user_id,idem));
CREATE TABLE IF NOT EXISTS pet_photo_daily(day TEXT PRIMARY KEY,unavailable_503 INTEGER NOT NULL DEFAULT 0);
''')

    def photo_balances(self,c,uid):
        self.require(c,uid)
        active=self.active(c,uid)
        ever_paid=c.execute('SELECT 1 FROM pet_grants WHERE user_id=?',(uid,)).fetchone()
        trial=c.execute('SELECT trial_photos FROM pet_accounts WHERE user_id=?',(uid,)).fetchone()[0]
        # An expired paid member cannot reactivate a stale trial by re-registering.
        return dict(photo_remaining=sum(g['remaining'] for g in active),trial_photo_remaining=trial if active or not ever_paid else 0)

    def account(self,uid):
        value=super().account(uid)
        with self.store.connect() as c:value.update(self.photo_balances(c,uid))
        return value

    def order(self,uid,plan):
        plans=settings()['plans']
        if plan not in plans:self.fail(400,'无效宠物套餐')
        p=plans[plan];now=int(self.clock());snapshot=json.dumps(p,ensure_ascii=False)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');self.require(c,uid);self.check_mixed(c,uid,plan)
            # Old unpaid quotes are preserved too; only reuse a matching current quote.
            old=c.execute("SELECT id FROM pet_orders WHERE user_id=? AND plan=? AND snapshot=? AND status IN ('pending','reported') AND created>? ORDER BY created DESC LIMIT 1",(uid,plan,snapshot,now-86400)).fetchone()
            if old:oid=old['id']
            else:
                if c.execute('SELECT count(*) FROM pet_orders WHERE user_id=? AND created>?',(uid,now-86400)).fetchone()[0]>=12:self.fail(429,'今天的订单创建次数已达上限')
                oid=uuid.uuid4().hex
                c.execute("INSERT INTO pet_orders VALUES(?,?,?,?,?,'pending',?,NULL,NULL,NULL)",(oid,uid,plan,snapshot,p['price_fen'],now))
                self.audit(c,'order_created',uid,oid)
        return self.get_order(uid,oid)

    def unavailable(self):
        day=datetime.fromtimestamp(self.clock(),timezone(timedelta(hours=8))).date().isoformat()
        with self.store.connect() as c:
            c.execute('INSERT INTO pet_photo_daily VALUES(?,1) ON CONFLICT(day) DO UPDATE SET unavailable_503=unavailable_503+1',(day,))
        # Aggregate request count only: no credentials, IPs, images or customer text.

    def recover_incomplete(self):
        # Called once on service startup after the previous process has stopped.
        # An interrupted supplier request is unknown, never a customer charge.
        with self.store.connect() as c:
            jobs=c.execute("SELECT j.id,j.user_id FROM pet_photo_jobs j JOIN pet_photo_results r ON r.job_id=j.id WHERE j.state='reserved'").fetchall()
        for j in jobs:self.complete_analysis(j['user_id'],j['id'],'unknown')

    def reminders(self,uid,body=None):
        try:return super().reminders(uid,body)
        except self.Problem as e:
            if e.status==402:self.fail(402,'提醒需要包含此权益的有效养护套餐')
            raise

    def analysis(self,uid,jid):
        with self.store.connect() as c:
            self.require(c,uid)
            j=c.execute('SELECT j.*,r.result FROM pet_photo_jobs j LEFT JOIN pet_photo_results r ON r.job_id=j.id WHERE j.id=? AND j.user_id=?',(jid,uid)).fetchone()
            if not j:self.fail(404,'照片任务不存在')
            return dict(id=j['id'],status={'reserved':'pending','unknown':'failed'}.get(j['state'],j['state']),result=json.loads(j['result']) if j['result'] else None,**self.photo_balances(c,uid))

    def reserve_analysis(self,uid,idem,payload_hash,image_hash,profile_id=None):
        if not isinstance(idem,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,100}',idem):self.fail(400,'请提供16至100位任务编号')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');self.require(c,uid)
            alias=c.execute('SELECT * FROM pet_photo_keys WHERE user_id=? AND idem=?',(uid,idem)).fetchone()
            if alias:
                if alias['payload_hash']!=payload_hash:self.fail(409,'同一任务编号的内容不能更改')
                return dict(c.execute('SELECT * FROM pet_photo_jobs WHERE id=?',(alias['job_id'],)).fetchone()),False
            old=c.execute('SELECT * FROM pet_photo_jobs WHERE user_id=? AND idem=?',(uid,idem)).fetchone()
            if old:
                if old['payload_hash']!=payload_hash:self.fail(409,'同一任务编号的内容不能更改')
                return dict(old),False
            # A different retry key for exactly the same photo also reuses its task.
            old=c.execute("SELECT j.* FROM pet_photo_results r JOIN pet_photo_jobs j ON j.id=r.job_id WHERE r.user_id=? AND r.image_hash=? AND j.state IN ('reserved','succeeded') ORDER BY j.created DESC LIMIT 1",(uid,image_hash)).fetchone()
            if old:
                c.execute('INSERT INTO pet_photo_keys VALUES(?,?,?,?)',(uid,idem,payload_hash,old['id']))
                return dict(old),False
            if profile_id and not c.execute('SELECT 1 FROM pet_profiles WHERE user_id=? AND id=?',(uid,profile_id)).fetchone():self.fail(404,'宠物档案不存在')
            balances=self.photo_balances(c,uid);grant_id=None
            if balances['trial_photo_remaining']>0:
                c.execute('UPDATE pet_accounts SET trial_photos=trial_photos-1 WHERE user_id=?',(uid,))
            else:
                g=next((g for g in self.active(c,uid) if g['remaining']>0),None)
                if not g:self.fail(402,'照片额度不足或订阅已到期，请选择养护套餐')
                grant_id=g['order_id'];c.execute('UPDATE pet_grants SET remaining=remaining-1 WHERE order_id=?',(grant_id,))
            jid=uuid.uuid4().hex
            c.execute("INSERT INTO pet_photo_jobs VALUES(?,?,?,?,?,'reserved',?)",(jid,uid,idem,payload_hash,grant_id,int(self.clock())))
            c.execute('INSERT INTO pet_photo_results VALUES(?,?,?,NULL)',(jid,uid,image_hash))
            c.execute('INSERT INTO pet_photo_keys VALUES(?,?,?,?)',(uid,idem,payload_hash,jid))
            self.audit(c,'photo_reserved',uid,jid)
            return dict(c.execute('SELECT * FROM pet_photo_jobs WHERE id=?',(jid,)).fetchone()),True

    def complete_analysis(self,uid,jid,state,result=None):
        if state not in ('succeeded','failed','unknown'):self.fail(400,'照片任务状态无效')
        # Persist result and consume/refund the reservation atomically, once only.
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            j=c.execute('SELECT * FROM pet_photo_jobs WHERE user_id=? AND id=?',(uid,jid)).fetchone()
            if not j:self.fail(404,'照片任务不存在')
            if j['state']!='reserved':return
            if state!='succeeded':
                if j['grant_id']:c.execute('UPDATE pet_grants SET remaining=remaining+1 WHERE order_id=?',(j['grant_id'],))
                else:c.execute('UPDATE pet_accounts SET trial_photos=trial_photos+1 WHERE user_id=?',(uid,))
            c.execute('UPDATE pet_photo_jobs SET state=? WHERE id=?',(state,jid))
            c.execute('UPDATE pet_photo_results SET result=? WHERE job_id=?',(json.dumps(result,ensure_ascii=False) if state=='succeeded' else None,jid))
            self.audit(c,'photo_'+state,uid,jid)
