"""Pet-only transactional resources. No writes to shared balances/grants/orders.
Inquiries are host-side best effort: a model can answer without calling us. Paid
inquiries are unlimited by config; there is deliberately no inquiry counter here.
"""
import hashlib,json,re,secrets,time,uuid
from product_config import settings

class PetBilling:
    def __init__(self, store, problem, clock=time.time):
        self.store,self.Problem,self.clock=store,problem,clock
        with store.connect() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS pet_accounts(user_id TEXT PRIMARY KEY,created INTEGER NOT NULL,trial_photos INTEGER NOT NULL CHECK(trial_photos>=0));
CREATE TABLE IF NOT EXISTS pet_orders(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,plan TEXT NOT NULL,snapshot TEXT NOT NULL,amount_fen INTEGER NOT NULL,status TEXT NOT NULL CHECK(status IN ('pending','reported','paid')),created INTEGER NOT NULL,paid_at INTEGER,transaction_id TEXT UNIQUE,actor TEXT);
CREATE TABLE IF NOT EXISTS pet_grants(order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,plan TEXT NOT NULL,snapshot TEXT NOT NULL,starts INTEGER NOT NULL,expires INTEGER NOT NULL,remaining INTEGER NOT NULL CHECK(remaining>=0));
CREATE TABLE IF NOT EXISTS pet_profiles(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,body TEXT NOT NULL,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS pet_photo_jobs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,idem TEXT NOT NULL,payload_hash TEXT NOT NULL,grant_id TEXT,state TEXT NOT NULL CHECK(state IN ('reserved','succeeded','failed','unknown')),created INTEGER NOT NULL,UNIQUE(user_id,idem));
CREATE TABLE IF NOT EXISTS pet_photo_execution(job_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS pet_audit(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,user_id TEXT NOT NULL,reference TEXT,created INTEGER NOT NULL);
''')
    def fail(self,status,msg): raise self.Problem(status,msg)
    def audit(self,c,kind,uid,ref=None): c.execute('INSERT INTO pet_audit(kind,user_id,reference,created) VALUES(?,?,?,?)',(kind,uid,ref,int(self.clock())))
    def require(self,c,uid):
        if not c.execute('SELECT 1 FROM pet_accounts WHERE user_id=?',(uid,)).fetchone(): self.fail(403,'请先开通宠物账户')
    def enroll(self,c,uid,new_identity):
        # Only called inside the new registration transaction, never by a read or claim API.
        trial=settings()['trial']['photo_analyses']
        # Eligibility is first pet enrollment, not first global MyPlaneStore identity.
        changed=c.execute('INSERT OR IGNORE INTO pet_accounts VALUES(?,?,?)',(uid,int(self.clock()),trial)).rowcount
        if changed:self.audit(c,'pet_registered',uid)
    def active(self,c,uid):
        return c.execute('SELECT * FROM pet_grants WHERE user_id=? AND starts<=? AND expires>? ORDER BY expires,order_id',(uid,int(self.clock()),int(self.clock()))).fetchall()
    def account(self,uid):
        with self.store.connect() as c:
            self.require(c,uid);g=self.active(c,uid);plans=[json.loads(x['snapshot']) for x in g]
            profile_limit=-1 if any(p['pet_profiles']==-1 for p in plans) else max([p['pet_profiles'] for p in plans],default=0)
            a=c.execute('SELECT trial_photos FROM pet_accounts WHERE user_id=?',(uid,)).fetchone()
            return {'product':'pet','quota_policy':'独立额度，不与通用次数通兑','plan_ids':[x['plan'] for x in g], 'expires_at':max([x['expires'] for x in g],default=None),'photo_remaining':sum(x['remaining'] for x in g),'trial_photo_remaining':(0 if c.execute('SELECT 1 FROM pet_grants WHERE user_id=?',(uid,)).fetchone() else a[0]), 'profiles_used':c.execute('SELECT count(*) FROM pet_profiles WHERE user_id=?',(uid,)).fetchone()[0],'profiles_limit':profile_limit,'reminders':any(p['reminders'] for p in plans),'medical_report_pdf':any(p['medical_report_pdf'] for p in plans),'inquiries':(-1 if any(p['inquiries']==-1 for p in plans) else max([p['inquiries'] for p in plans],default=settings()['trial']['inquiries_best_effort'])),'inquiry_enforcement':'best_effort_only'}
    def check_mixed(self,c,uid,plan):
        if settings().get('renewal_proposal',{}).get('mixed_tier')!='independent_terms_confirmed' and c.execute('SELECT 1 FROM pet_grants WHERE user_id=? AND plan<>? AND expires>?',(uid,plan,int(self.clock()))).fetchone():self.fail(409,'混合档位续费策略待负责人确认，暂不受理跨档续费')
    def order(self,uid,plan):
        cfg=settings()['plans']
        if plan not in cfg:self.fail(400,'无效宠物套餐')
        p=cfg[plan];oid=uuid.uuid4().hex
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');self.require(c,uid)
            self.check_mixed(c,uid,plan)
            old=c.execute("SELECT id FROM pet_orders WHERE user_id=? AND plan=? AND status IN ('pending','reported') AND created>? ORDER BY created DESC LIMIT 1",(uid,plan,int(self.clock())-86400)).fetchone()
            if old:return self.get_order(uid,old[0])
            if c.execute('SELECT count(*) FROM pet_orders WHERE user_id=? AND created>?',(uid,int(self.clock())-86400)).fetchone()[0]>=12:self.fail(429,'今天的订单创建次数已达上限')
            c.execute('INSERT INTO pet_orders VALUES(?,?,?,?,?,\'pending\',?,NULL,NULL,NULL)',(oid,uid,plan,json.dumps(p,ensure_ascii=False),p['price_fen'],int(self.clock())))
            self.audit(c,'order_created',uid,oid)
        return self.get_order(uid,oid)
    def get_order(self,uid,oid):
        with self.store.connect() as c:r=c.execute('SELECT id,plan,amount_fen,status,created,paid_at FROM pet_orders WHERE id=? AND user_id=?',(oid,uid)).fetchone()
        if not r:self.fail(404,'订单不存在')
        return dict(r)
    def report_payment(self,uid,oid):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            r=c.execute('SELECT status FROM pet_orders WHERE id=? AND user_id=?',(oid,uid)).fetchone()
            if not r:self.fail(404,'订单不存在')
            if r[0]=='pending':
                c.execute("UPDATE pet_orders SET status='reported' WHERE id=?",(oid,));self.audit(c,'payment_reported_not_received',uid,oid)
        return self.get_order(uid,oid)
    def settle(self,oid,amount,transaction,actor,verified):
        # Trusted operator integration only. Never mounted on a customer route.
        if verified is not True or type(amount) is not int or not re.fullmatch(r'[A-Za-z0-9_-]{6,128}',transaction or '') or not actor:self.fail(400,'须核对实收金额和交易流水')
        now=int(self.clock())
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');o=c.execute('SELECT * FROM pet_orders WHERE id=?',(oid,)).fetchone()
            if not o:self.fail(404,'订单不存在')
            if amount!=o['amount_fen']:self.fail(409,'金额不一致')
            if o['status']=='paid':
                if o['transaction_id']!=transaction:self.fail(409,'该订单已使用其他流水核款')
                return {'status':'already_paid','credited':False}
            if o['status']!='reported':self.fail(409,'订单尚未报付款')
            if c.execute('SELECT 1 FROM pet_orders WHERE transaction_id=?',(transaction,)).fetchone():self.fail(409,'流水已使用')
            self.check_mixed(c,o['user_id'],o['plan'])
            p=json.loads(o['snapshot'])
            # Same tier extends its own subscription, adds photos immediately. Other tiers
            # overlap independently: a cheap renewal NEVER extends higher-tier features.
            previous=c.execute('SELECT max(expires) FROM pet_grants WHERE user_id=? AND plan=?',(o['user_id'],o['plan'])).fetchone()[0] or now
            expiry=max(now,previous)+p['duration_days']*86400
            c.execute('INSERT INTO pet_grants VALUES(?,?,?,?,?,?,?)',(oid,o['user_id'],o['plan'],o['snapshot'],now,expiry,p['photo_analyses']))
            if previous>now:c.execute('UPDATE pet_grants SET expires=? WHERE user_id=? AND plan=? AND expires>?',(expiry,o['user_id'],o['plan'],now))
            c.execute("UPDATE pet_orders SET status='paid',paid_at=?,transaction_id=?,actor=? WHERE id=?",(now,transaction,actor,oid))
            self.audit(c,'verified_payment_granted',o['user_id'],oid)
        return {'status':'paid','credited':True,'expires_at':expiry}
    def profile(self,uid,body,profile_id=None):
        if not isinstance(body,dict) or len(json.dumps(body))>8192:self.fail(400,'档案格式或长度无效')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');self.require(c,uid);plans=[json.loads(g['snapshot']) for g in self.active(c,uid)]
            cap=-1 if any(p['pet_profiles']==-1 for p in plans) else max([p['pet_profiles'] for p in plans],default=0)
            if cap==0:self.fail(402,'档案保存需要有效订阅')
            if profile_id:
                if not c.execute('SELECT 1 FROM pet_profiles WHERE id=? AND user_id=?',(profile_id,uid)).fetchone():self.fail(404,'档案不存在')
                c.execute('UPDATE pet_profiles SET body=? WHERE id=?',(json.dumps(body,ensure_ascii=False),profile_id))
            else:
                used=c.execute('SELECT count(*) FROM pet_profiles WHERE user_id=?',(uid,)).fetchone()[0]
                if cap!=-1 and used>=cap:self.fail(402,'宠物档案数量已达套餐上限')
                profile_id=uuid.uuid4().hex;c.execute('INSERT INTO pet_profiles VALUES(?,?,?,?)',(profile_id,uid,json.dumps(body,ensure_ascii=False),int(self.clock())))
            self.audit(c,'profile_written',uid,profile_id)
        return {'id':profile_id}
    def reserve_photo(self,uid,idem,payload_hash):
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',idem or '') or not re.fullmatch(r'[a-f0-9]{64}',payload_hash or ''):self.fail(400,'分析请求需稳定任务编号与内容摘要')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');self.require(c,uid)
            old=c.execute('SELECT * FROM pet_photo_jobs WHERE user_id=? AND idem=?',(uid,idem)).fetchone()
            if old:
                if old['payload_hash']!=payload_hash:self.fail(409,'同一任务内容已改变')
                if old['state']!='failed':return dict(old)
                c.execute('DELETE FROM pet_photo_execution WHERE job_id=?',(old['id'],))
            active=self.active(c,uid);g=next((x for x in active if x['remaining']>0),None)
            grant_id=None
            if g:
                grant_id=g['order_id'];c.execute('UPDATE pet_grants SET remaining=remaining-1 WHERE order_id=?',(grant_id,))
            else:
                # Trial is its own entitlement; exhausted/expired paid photos never fall back
                # to image funds. A previous paid subscriber cannot resurrect a stale trial.
                paid=c.execute('SELECT 1 FROM pet_grants WHERE user_id=?',(uid,)).fetchone()
                changed=0 if paid else c.execute('UPDATE pet_accounts SET trial_photos=trial_photos-1 WHERE user_id=? AND trial_photos>0',(uid,)).rowcount
                if not changed:self.fail(402,'宠物照片分析额度不足或订阅已到期，请充值')
            jid=old['id'] if old else uuid.uuid4().hex
            if old:c.execute("UPDATE pet_photo_jobs SET grant_id=?,state='reserved' WHERE id=?",(grant_id,jid))
            else:c.execute("INSERT INTO pet_photo_jobs VALUES(?,?,?,?,?,'reserved',?)",(jid,uid,idem,payload_hash,grant_id,int(self.clock())))
            self.audit(c,'photo_reserved',uid,jid)
            return dict(c.execute('SELECT * FROM pet_photo_jobs WHERE id=?',(jid,)).fetchone())
    def finish_photo(self,uid,jid,state):
        if state not in ('succeeded','failed','unknown'):self.fail(400,'无效任务状态')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');j=c.execute('SELECT * FROM pet_photo_jobs WHERE id=? AND user_id=?',(jid,uid)).fetchone()
            if not j:self.fail(404,'任务不存在')
            if j['state']!='reserved':return {'state':j['state']}
            if state in ('failed','unknown'):
                if j['grant_id']:c.execute('UPDATE pet_grants SET remaining=remaining+1 WHERE order_id=?',(j['grant_id'],))
                else:c.execute('UPDATE pet_accounts SET trial_photos=trial_photos+1 WHERE user_id=?',(uid,))
            c.execute('UPDATE pet_photo_jobs SET state=? WHERE id=?',(state,jid));self.audit(c,'photo_'+state,uid,jid)
        return {'state':state}
    def reminders(self,uid,body=None):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');self.require(c,uid)
            if not any(json.loads(g['snapshot'])['reminders'] for g in self.active(c,uid)):self.fail(402,'提醒需要有效季度或年度订阅')
            c.execute('CREATE TABLE IF NOT EXISTS pet_reminders(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,title TEXT NOT NULL,due INTEGER NOT NULL)')
            if body is not None:
                title=body.get('title');due=body.get('due')
                if not isinstance(title,str) or not 1<=len(title)<=120 or type(due) is not int or due<=self.clock():self.fail(400,'请填写有效提醒名称和未来时间')
                if c.execute('SELECT count(*) FROM pet_reminders WHERE user_id=?',(uid,)).fetchone()[0]>=100:self.fail(429,'提醒记录已达上限')
                rid=uuid.uuid4().hex;c.execute('INSERT INTO pet_reminders VALUES(?,?,?,?)',(rid,uid,title,due));self.audit(c,'reminder_created',uid,rid)
            return {'items':[dict(x) for x in c.execute('SELECT id,title,due FROM pet_reminders WHERE user_id=? ORDER BY due',(uid,))],'delivery':'skill_query_only_no_push'}
    def report_pdf(self,uid,profile_id):
        with self.store.connect() as c:
            self.require(c,uid)
            if not any(json.loads(g['snapshot'])['medical_report_pdf'] for g in self.active(c,uid)):self.fail(402,'就医报告PDF需要有效年度订阅')
            row=c.execute('SELECT body FROM pet_profiles WHERE id=? AND user_id=?',(profile_id,uid)).fetchone()
            if not row:self.fail(404,'档案不存在')
        # Standard PDF CJK font, no external library/network or remote conversion.
        import textwrap
        def fields(value, prefix=''):
            result=[]
            if isinstance(value,dict):
                for key,item in value.items():result.extend(fields(item, prefix+' / '+str(key) if prefix else str(key)))
            elif isinstance(value,list):
                for n,item in enumerate(value,1):result.extend(fields(item,prefix+'（'+str(n)+'）'))
                if not value:result.append(prefix+'：未填写')
            else:
                label='未填写' if value is None or value=='' else ('是' if value is True else '否' if value is False else str(value))
                result.append(prefix+'：'+label)
            return result
        text='宠物就医信息整理（用户提供，非诊断）\n'+'\n'.join(fields(json.loads(row[0])))+'\n照片无法替代检查；不能排除急症。出现急症征象请立即就医。'
        lines=[]
        for line in text.splitlines():lines.extend(textwrap.wrap(line,34) or [''])
        pages=[lines[i:i+34] for i in range(0,len(lines),34)];objects=[]
        objects.append(b'<< /Type /Catalog /Pages 2 0 R >>')
        kids=' '.join(str(5+i*2)+' 0 R' for i in range(len(pages)))
        objects.append(('<< /Type /Pages /Kids ['+kids+'] /Count '+str(len(pages))+' >>').encode())
        objects.append(b'<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts [4 0 R] >>')
        objects.append(b'<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 4 >> >>')
        for i,page in enumerate(pages):
            objects.append(('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents '+str(6+i*2)+' 0 R >>').encode())
            stream=('BT /F1 12 Tf 40 790 Td 20 TL '+ ' '.join('<'+line.encode('utf-16-be').hex()+'> Tj T*' for line in page)+' ET').encode()
            objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
        out=bytearray(b'%PDF-1.4\n');offsets=[0]
        for n,obj in enumerate(objects,1):offsets.append(len(out));out.extend(str(n).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
        start=len(out);out.extend(('xref\n0 '+str(len(objects)+1)+'\n0000000000 65535 f \n').encode())
        for offset in offsets[1:]:out.extend(('%010d 00000 n \n'%offset).encode())
        out.extend(('trailer << /Size '+str(len(objects)+1)+' /Root 1 0 R >>\nstartxref\n'+str(start)+'\n%%EOF').encode())
        return bytes(out)
