"""Isolated CNY ledger; no updates to image/pet balances or historical rows."""
import hashlib,json,re,secrets,time,uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from trade_config import config,mock_identity

def digest(x):return hashlib.sha256(x.encode()).hexdigest()

class Error(Exception):
    def __init__(self,status,code,message='',**extra):
        self.status=status;self.code=code;self.message=message;self.extra=extra
    def body(self):return dict(error=dict(code=self.code,message=self.message),**self.extra)

SCHEMA='''
CREATE TABLE IF NOT EXISTS trade_order_promotions(order_id TEXT PRIMARY KEY,campaign_id TEXT NOT NULL,bonus_fen INTEGER NOT NULL CHECK(bonus_fen>=0),search_unit_fen INTEGER NOT NULL CHECK(search_unit_fen>0),bonus_searches INTEGER NOT NULL CHECK(bonus_searches>=0));
CREATE TABLE IF NOT EXISTS settlement_receipts(transaction_id TEXT PRIMARY KEY,product TEXT NOT NULL,order_id TEXT NOT NULL,amount_fen INTEGER NOT NULL,actor TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS trade_wallets(account_id TEXT PRIMARY KEY,wallet_type TEXT NOT NULL DEFAULT 'cny',scope TEXT NOT NULL DEFAULT 'trade-leads',balance_fen INTEGER NOT NULL DEFAULT 0 CHECK(balance_fen>=0),reserved_fen INTEGER NOT NULL DEFAULT 0 CHECK(reserved_fen>=0 AND reserved_fen<=balance_fen),is_test INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS trade_ledger(id INTEGER PRIMARY KEY,account_id TEXT NOT NULL,scope TEXT NOT NULL DEFAULT 'trade-leads',action TEXT NOT NULL,amount_fen INTEGER NOT NULL,ref_id TEXT NOT NULL,idempotency_key TEXT NOT NULL,created_at INTEGER NOT NULL,is_test INTEGER NOT NULL,UNIQUE(account_id,idempotency_key));
CREATE TABLE IF NOT EXISTS trade_tokens(hash TEXT PRIMARY KEY,account_id TEXT NOT NULL,device_hash TEXT NOT NULL,created INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS trade_links(code_hash TEXT PRIMARY KEY,device_hash TEXT NOT NULL,created INTEGER NOT NULL,expires INTEGER NOT NULL,account_id TEXT,token TEXT);
CREATE TABLE IF NOT EXISTS trade_daily(day TEXT NOT NULL,kind TEXT NOT NULL,identity TEXT NOT NULL,used INTEGER NOT NULL DEFAULT 0,held INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(day,kind,identity));
CREATE TABLE IF NOT EXISTS trade_idem(actor TEXT NOT NULL,key TEXT NOT NULL,body_hash TEXT NOT NULL,status INTEGER,response TEXT,created INTEGER NOT NULL,account_id TEXT,reserved INTEGER NOT NULL DEFAULT 0,free_keys TEXT NOT NULL DEFAULT '[]',is_test INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(actor,key));
CREATE TABLE IF NOT EXISTS trade_orders(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,skill_id TEXT NOT NULL DEFAULT 'trade-leads',amount_fen INTEGER NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL,paid_at INTEGER,transaction_id TEXT UNIQUE,is_test INTEGER NOT NULL,actor TEXT);
CREATE TABLE IF NOT EXISTS trade_rates(key TEXT PRIMARY KEY,window INTEGER NOT NULL,count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS trade_cache(provider TEXT NOT NULL,key TEXT NOT NULL,payload TEXT NOT NULL,expires INTEGER NOT NULL,PRIMARY KEY(provider,key));
CREATE TABLE IF NOT EXISTS trade_upstream(id INTEGER PRIMARY KEY,provider TEXT NOT NULL,endpoint TEXT NOT NULL,cache_hit INTEGER NOT NULL,http_status INTEGER,latency_ms INTEGER,account_id TEXT,ref_id TEXT,created_at INTEGER NOT NULL,credits_remaining INTEGER,mapping_failed INTEGER NOT NULL DEFAULT 0,is_test INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS trade_quota(month TEXT PRIMARY KEY,local_used INTEGER NOT NULL DEFAULT 0,requests INTEGER NOT NULL DEFAULT 0,remote_remaining INTEGER,remote_requests INTEGER,blocked INTEGER NOT NULL DEFAULT 0,lease_until INTEGER NOT NULL DEFAULT 0,alerted INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS trade_fixtures(id TEXT PRIMARY KEY,endpoint TEXT NOT NULL,path TEXT NOT NULL,created INTEGER NOT NULL,mapping_failed INTEGER NOT NULL);
'''

class Trade:
    def __init__(self,store,clock=time.time):
        self.store=store;self.clock=clock
        with store.connect() as c:c.executescript(SCHEMA)
    def now(self):return int(self.clock())
    def day(self):return datetime.fromtimestamp(self.clock(),ZoneInfo('Asia/Shanghai')).date().isoformat()
    def rate(self,key,limit,seconds=60):
        now=self.now();key=digest(key)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT window,count FROM trade_rates WHERE key=?',(key,)).fetchone()
            if r and r['window']>now-seconds and r['count']>=limit:raise Error(429,'RATE_LIMITED','请求过于频繁')
            if not r or r['window']<=now-seconds:c.execute('INSERT OR REPLACE INTO trade_rates VALUES(?,?,1)',(key,now))
            else:c.execute('UPDATE trade_rates SET count=count+1 WHERE key=?',(key,))
    def wallet(self,c,uid,test=False):
        c.execute('INSERT OR IGNORE INTO trade_wallets(account_id,is_test) VALUES(?,?)',(uid,int(test)))
        return c.execute('SELECT * FROM trade_wallets WHERE account_id=?',(uid,)).fetchone()
    def balance(self,uid):
        with self.store.connect() as c:r=c.execute('SELECT balance_fen FROM trade_wallets WHERE account_id=?',(uid,)).fetchone()
        return r[0] if r else 0
    def token_user(self,token,device):
        with self.store.connect() as c:r=c.execute('SELECT account_id FROM trade_tokens WHERE hash=? AND device_hash=? AND revoked=0',(digest(token),digest(device))).fetchone()
        if not r:raise Error(401,'INVALID_TOKEN','关联已失效，请重新关联')
        return r[0]
    def start(self,device):
        code=''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
        with self.store.connect() as c:
            c.execute('DELETE FROM trade_links WHERE expires<?',(self.now(),))
            c.execute('INSERT INTO trade_links VALUES(?,?,?,?,NULL,NULL)',(digest(code),digest(device),self.now(),self.now()+600))
        return dict(link_code=code,login_url='https://myplanestore.com/link?code='+code+'&skill=trade-leads',poll_interval=7,expires_in=600)
    def approve(self,code,uid=None):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM trade_links WHERE code_hash=? AND expires>?',(digest(code),self.now())).fetchone()
            if not r:raise Error(401,'INVALID_TOKEN','关联入口已过期')
            if uid is None:
                if r['account_id']:raise Error(409,'INVALID_PARAMS','该入口已关联，请使用原浏览器')
                uid=str(uuid.uuid4());c.execute('INSERT INTO users VALUES(?,0)',(uid,))
            if r['account_id'] and r['account_id']!=uid:raise Error(409,'INVALID_PARAMS','此入口已关联其他账户')
            if not r['account_id']:
                token=secrets.token_urlsafe(32)
                c.execute('INSERT INTO trade_tokens VALUES(?,?,?,?,0)',(digest(token),uid,r['device_hash'],self.now()))
                # Short-lived plaintext token only in the 10-minute delivery envelope, never logs.
                c.execute('UPDATE trade_links SET account_id=?,token=? WHERE code_hash=?',(uid,token,digest(code)))
                from trade_config import ids
                test=uid in ids('SMOKE_TEST_ACCOUNT_IDS') or r['device_hash'] in {digest(d) for d in ids('SMOKE_TEST_DEVICE_IDS')}
                self.wallet(c,uid,test)
            return uid
    def poll(self,code,device):
        with self.store.connect() as c:r=c.execute('SELECT * FROM trade_links WHERE code_hash=? AND device_hash=? AND expires>?',(digest(code),digest(device),self.now())).fetchone()
        if not r:return {'status':'expired'}
        if not r['account_id']:return {'status':'pending'}
        return dict(status='approved',access_token=r['token'],account=dict(display='账户 · '+r['account_id'][:8]))
    def free_keys(self,uid,device,ip):
        return [('device',digest(device),config()['daily_free_trial']),('ip',digest(ip),3)]+([('account',digest(uid),config()['daily_free_trial'])] if uid else [])
    def free_available(self,c,keys):
        for kind,key,cap in keys:
            r=c.execute('SELECT used+held FROM trade_daily WHERE day=? AND kind=? AND identity=?',(self.day(),kind,key)).fetchone()
            if (r[0] if r else 0)>=cap:return False
        return True
    def insufficient(self,have,need):
        raise Error(402,'INSUFFICIENT_BALANCE','余额不足',balance_fen=have,required_fen=need,recharge_url='https://myplanestore.com/pay?skill=trade-leads')
    def execute(self,action,body,uid,device,ip,idem,provider):
        self.recover()
        if not isinstance(idem,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',idem):raise Error(400,'INVALID_PARAMS','请提供稳定的 Idempotency-Key')
        actor=('a:'+uid) if uid else ('d:'+digest(device));key=digest(idem)
        bh=digest(json.dumps([action,body],sort_keys=True,ensure_ascii=False));cfg=config();now=self.now()
        trialkeys=self.free_keys(uid,device,ip) if action=='search' else [];day=self.day()
        maximum=cfg['price_list']['contact']*body.get('max',3) if action=='contacts' else cfg['price_list'][action]
        test=mock_identity(uid,device)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM trade_idem WHERE actor=? AND key=?',(actor,key)).fetchone()
            if old and old['status'] is not None:
                if old['body_hash']!=bh:raise Error(409,'INVALID_PARAMS','同一任务内容发生变化')
                return old['status'],json.loads(old['response'])
            if old and old['status'] is None:raise Error(409,'IDEMPOTENCY_IN_PROGRESS','请求处理中，请勿重复提交')
            free=bool(trialkeys) and self.free_available(c,trialkeys)
            if not free:
                if not uid:raise Error(401,'AUTH_REQUIRED','请关联账户后继续',trial_used_today=True)
                wallet=self.wallet(c,uid,test);available=wallet['balance_fen']-wallet['reserved_fen']
                if available<maximum:self.insufficient(available,maximum)
                c.execute('UPDATE trade_wallets SET reserved_fen=reserved_fen+? WHERE account_id=?',(maximum,uid))
            else:
                for kind,identity,cap in trialkeys:
                    c.execute('INSERT INTO trade_daily VALUES(?,?,?,0,1) ON CONFLICT(day,kind,identity) DO UPDATE SET held=held+1',(day,kind,identity))
            c.execute('INSERT OR REPLACE INTO trade_idem VALUES(?,?,?,NULL,NULL,?,?,?,?,?)',(actor,key,bh,now,uid,0 if free else maximum,json.dumps([day,trialkeys]) if free else '[]',int(test)))
        try:
            status=200;charged=0
            if action=='search':
                companies={};total=0
                for keyword in body['keywords']:
                    batch=provider.search_jobs(keyword,body['country'],body.get('page',1));total+=len(batch)
                    for item in batch:
                        if item['company_id'] in companies:companies[item['company_id']]['jobs'].extend(item['jobs'])
                        else:companies[item['company_id']]=item
                payload=dict(search_id='srch_'+uuid.uuid4().hex,upstream_total=total,companies=list(companies.values()))
                charged=0 if free or not companies else maximum
                used_free=free and bool(companies)
            elif action=='company':
                company=provider.company_profile(body['company_id']);used_free=False
                if company is None:status=404;payload=Error(404,'COMPANY_NOT_FOUND','没有找到这家公司的档案').body()
                else:payload=dict(company=company);charged=maximum
            else:
                contacts=provider.company_employees(body['company_id'],body.get('max',3));used_free=False
                payload=dict(contacts=contacts);charged=len(contacts)*cfg['price_list']['contact']
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                if not free:
                    changed=c.execute('UPDATE trade_wallets SET balance_fen=balance_fen-?,reserved_fen=reserved_fen-? WHERE account_id=? AND balance_fen>=? AND reserved_fen>=?',(charged,maximum,uid,charged,maximum)).rowcount
                    if changed!=1:raise RuntimeError('wallet reservation mismatch')
                else:
                    for kind,identity,cap in trialkeys:c.execute('UPDATE trade_daily SET held=held-1,used=used+? WHERE day=? AND kind=? AND identity=?',(int(used_free),day,kind,identity))
                if charged:c.execute('INSERT INTO trade_ledger(account_id,action,amount_fen,ref_id,idempotency_key,created_at,is_test) VALUES(?,?,?,?,?,?,?)',(uid,'contact' if action=='contacts' else action,-charged,actor+':'+key,key,now,int(test)))
                balance=self.wallet(c,uid,test)['balance_fen'] if uid else 0
                if status==200:payload['billing']=dict(charged_fen=charged,free_trial=bool(used_free),balance_fen=balance)
                c.execute('UPDATE trade_idem SET status=?,response=?,reserved=0,free_keys=\'[]\' WHERE actor=? AND key=?',(status,json.dumps(payload,ensure_ascii=False),actor,key))
            return status,payload
        except BaseException:
            self.release(actor,key);raise
    def release(self,actor,key):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM trade_idem WHERE actor=? AND key=? AND status IS NULL',(actor,key)).fetchone()
            if not r:return
            if r['reserved']:c.execute('UPDATE trade_wallets SET reserved_fen=reserved_fen-? WHERE account_id=?',(r['reserved'],r['account_id']))
            if r['free_keys']!='[]':
                day,keys=json.loads(r['free_keys'])
                for kind,identity,cap in keys:c.execute('UPDATE trade_daily SET held=held-1 WHERE day=? AND kind=? AND identity=?',(day,kind,identity))
            c.execute('DELETE FROM trade_idem WHERE actor=? AND key=?',(actor,key))
    def recover(self):
        # A killed process cannot still bill; provider timeouts are 25s. Retain 10-minute leases.
        with self.store.connect() as c:stale=c.execute('SELECT actor,key FROM trade_idem WHERE status IS NULL AND created<?',(self.now()-600,)).fetchall()
        for r in stale:self.release(r['actor'],r['key'])
    def order(self,uid,amount,test=False):
        if type(amount) is not int or amount not in config()['tiers']:raise Error(400,'INVALID_PARAMS','充值档位无效')
        cfg=config();campaign=cfg['promotion']['id'] if cfg['promotion']['enabled'] else '';bonus=cfg['promotion']['bonus_searches'] if campaign else 0;unit=cfg['price_list']['search']
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');wallet=self.wallet(c,uid,test);test=bool(test or wallet['is_test'])
            r=c.execute("SELECT * FROM trade_orders WHERE account_id=? AND amount_fen=? AND status IN ('pending','reported') AND created>? AND EXISTS(SELECT 1 FROM trade_order_promotions p WHERE p.order_id=trade_orders.id AND p.campaign_id=? AND p.bonus_fen=? AND p.search_unit_fen=?) ORDER BY created DESC LIMIT 1",(uid,amount,self.now()-86400,campaign,bonus*unit,unit)).fetchone()
            if r:return dict(r)
            if c.execute('SELECT count(*) FROM trade_orders WHERE account_id=? AND created>?',(uid,self.now()-86400)).fetchone()[0]>=12:raise Error(429,'RATE_LIMITED','今日订单过多')
            oid=uuid.uuid4().hex;c.execute("INSERT INTO trade_orders VALUES(?,?,'trade-leads',?,'pending',?,NULL,NULL,?,NULL)",(oid,uid,amount,self.now(),int(test)))
            c.execute('INSERT INTO trade_order_promotions VALUES(?,?,?,?,?)',(oid,campaign,bonus*unit,unit,bonus))
            return dict(c.execute('SELECT * FROM trade_orders WHERE id=?',(oid,)).fetchone())
    def report(self,uid,oid):
        with self.store.connect() as c:
            c.execute("UPDATE trade_orders SET status='reported' WHERE id=? AND account_id=? AND status='pending'",(oid,uid))
            r=c.execute('SELECT * FROM trade_orders WHERE id=? AND account_id=?',(oid,uid)).fetchone()
            if not r:raise Error(404,'INVALID_PARAMS','订单不存在')
            return dict(r)
    def settle(self,oid,amount,transaction,actor,verified):
        if verified is not True or type(amount) is not int or not re.fullmatch(r'[A-Za-z0-9_-]{6,128}',transaction or ''):raise Error(400,'INVALID_PARAMS','请核对实收金额及交易流水')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');o=c.execute('SELECT * FROM trade_orders WHERE id=?',(oid,)).fetchone()
            if not o:raise Error(404,'INVALID_PARAMS','订单不存在')
            if o['amount_fen']!=amount:raise Error(409,'INVALID_PARAMS','金额不符')
            if o['status']=='paid':
                if o['transaction_id']!=transaction:raise Error(409,'INVALID_PARAMS','订单已使用其他流水')
                return dict(status='already_paid',credited=False)
            if o['status']!='reported':raise Error(409,'INVALID_PARAMS','订单尚未报付款')
            # Prevent reuse of any known existing product's confirmed transaction.
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ('trade_orders','pet_orders','member_orders','payment_orders','orders','settlement_receipts'):
                if table not in tables:continue
                cols={r[1] for r in c.execute('PRAGMA table_info('+table+')')}
                for col in ('transaction_id','transaction_no','provider_transaction_id'):
                    if col in cols and c.execute('SELECT 1 FROM '+table+' WHERE '+col+'=?',(transaction,)).fetchone():raise Error(409,'INVALID_PARAMS','交易流水已使用')
            self.wallet(c,o['account_id'],o['is_test'])
            c.execute("INSERT INTO settlement_receipts VALUES(?,'trade-leads',?,?,?,'paid',?)",(transaction,oid,amount,actor,self.now()))
            promo=c.execute('SELECT bonus_fen FROM trade_order_promotions WHERE order_id=?',(oid,)).fetchone();bonus=promo['bonus_fen'] if promo else 0
            c.execute('UPDATE trade_wallets SET balance_fen=balance_fen+? WHERE account_id=?',(amount+bonus,o['account_id']))
            c.execute('INSERT INTO trade_ledger(account_id,action,amount_fen,ref_id,idempotency_key,created_at,is_test) VALUES(?,\'recharge\',?,?,?,?,?)',(o['account_id'],amount,oid,'recharge:'+oid,self.now(),o['is_test']))
            if bonus:c.execute("INSERT INTO trade_ledger(account_id,action,amount_fen,ref_id,idempotency_key,created_at,is_test) VALUES(?,'promotion_bonus',?,?,?,?,?)",(o['account_id'],bonus,oid,'promotion:'+oid,self.now(),o['is_test']))
            c.execute("UPDATE trade_orders SET status='paid',paid_at=?,transaction_id=?,actor=? WHERE id=?",(self.now(),transaction,actor,oid))
        return dict(status='paid',credited=True,bonus_fen=bonus,credited_fen=amount+bonus)
