"""Listing-only CNY prototype. All mutations require a real account and stable key.

Never trust client success flags. A server-owned delivery verifier must return a
durable, recoverable artifact before settlement. Default adapter is unconfigured.
"""
import hashlib
import json
import re
import time
import uuid
from pathlib import Path


class Error(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


SCHEMA = '''
CREATE TABLE IF NOT EXISTS listing_accounts(account_id TEXT PRIMARY KEY,
 balance_fen INTEGER NOT NULL DEFAULT 0 CHECK(balance_fen>=0),
 reserved_fen INTEGER NOT NULL DEFAULT 0 CHECK(reserved_fen>=0 AND reserved_fen<=balance_fen),
 trial_state TEXT NOT NULL DEFAULT 'available' CHECK(trial_state IN ('available','held','used')),
 created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS listing_orders(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,
 tier_id TEXT NOT NULL,price_version TEXT NOT NULL,pay_fen INTEGER NOT NULL,
 credit_fen INTEGER NOT NULL,status TEXT NOT NULL,source TEXT NOT NULL,channel TEXT NOT NULL,
 created INTEGER NOT NULL,paid_at INTEGER,transaction_id TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS listing_quotes(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,
 scope TEXT NOT NULL,price_version TEXT NOT NULL,unit_price_fen INTEGER NOT NULL,
 funding TEXT NOT NULL,expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS listing_tasks(id TEXT PRIMARY KEY,account_id TEXT NOT NULL,
 quote_id TEXT UNIQUE NOT NULL,state TEXT NOT NULL,funding TEXT NOT NULL,
 amount_fen INTEGER NOT NULL,result TEXT,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS listing_ledger(id INTEGER PRIMARY KEY,account_id TEXT NOT NULL,
 action TEXT NOT NULL,amount_fen INTEGER NOT NULL,reference TEXT NOT NULL,created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS listing_artifacts(task_id TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL,created INTEGER NOT NULL,PRIMARY KEY(task_id,revision));
CREATE TABLE IF NOT EXISTS listing_idem(account_id TEXT NOT NULL,key TEXT NOT NULL,
 body_hash TEXT NOT NULL,response TEXT NOT NULL,PRIMARY KEY(account_id,key));
'''


class UnconfiguredDelivery:
    ready = False

    def recover_verified(self, task_id, evidence, scope):
        raise Error(503, 'DELIVERY_NOT_CONFIGURED')


class Listing:
    def __init__(self, store, config=None, verifier=None, clock=time.time):
        self.store, self.clock = store, clock
        self.config = config or json.loads(Path(__file__).with_name('listing-config.json').read_text(encoding='utf8'))
        self.verifier = verifier or UnconfiguredDelivery()
        with store.connect() as c:
            c.executescript(SCHEMA)

    def ready(self):
        cfg = self.config
        return bool(cfg['charging_enabled'] and cfg['terms']['confirmed']
                    and all(cfg['terms'].get(k) is not None for k in
                            ('unit_scope','trial_scope','included_revisions','balance_validity','refund_policy'))
                    and cfg['delivery_adapter_confirmed'] and self.verifier.ready)

    def require_ready(self):
        if not self.ready():
            raise Error(503, 'LISTING_NOT_OPEN')

    def now(self):
        return int(self.clock())

    def account(self, c, uid):
        row = c.execute('SELECT * FROM listing_accounts WHERE account_id=?', (uid,)).fetchone()
        if not row:
            raise Error(403, 'LISTING_ACCOUNT_REQUIRED')
        return row

    def mutate(self, uid, key, action, body, fn):
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{16,100}', key):
            raise Error(400, 'IDEMPOTENCY_KEY_REQUIRED')
        fingerprint = sha(canonical([action, body]))
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
                raise Error(401, 'ACCOUNT_REQUIRED')
            old = c.execute('SELECT * FROM listing_idem WHERE account_id=? AND key=?', (uid,key)).fetchone()
            if old:
                if old['body_hash'] != fingerprint:
                    raise Error(409, 'IDEMPOTENCY_CONFLICT')
                return json.loads(old['response'])
            value = fn(c)
            c.execute('INSERT INTO listing_idem VALUES(?,?,?,?)', (uid,key,fingerprint,canonical(value)))
            return value

    def ledger(self, c, uid, action, amount, ref):
        c.execute('INSERT INTO listing_ledger(account_id,action,amount_fen,reference,created) VALUES(?,?,?,?,?)',
                  (uid,action,amount,ref,self.now()))

    def enroll(self, uid, key, accepted):
        if accepted is not True:
            raise Error(400, 'ACCEPTANCE_REQUIRED')
        def go(c):
            c.execute('INSERT OR IGNORE INTO listing_accounts(account_id,created) VALUES(?,?)',(uid,self.now()))
            return {'enrolled':True}
        return self.mutate(uid,key,'enroll',{'accepted':accepted},go)

    def me(self, uid):
        with self.store.connect() as c:
            a = self.account(c,uid)
            return dict(balance_fen=a['balance_fen'],reserved_fen=a['reserved_fen'],
                        available_fen=a['balance_fen']-a['reserved_fen'],trial_state=a['trial_state'])

    def order(self, uid, key, tier_id, source, channel):
        self.require_ready()
        tier = next((t for t in self.config['tiers'] if t['id']==tier_id),None)
        if tier is None or channel not in ('workbuddy_skill','workbuddy_expert','skillhub','website') or not isinstance(source,str) or not re.fullmatch('[a-z0-9][a-z0-9_-]{1,99}',source):
            raise Error(400,'INVALID_ORDER')
        def go(c):
            self.account(c,uid)
            prior=c.execute("SELECT id,status,pay_fen FROM listing_orders WHERE account_id=? AND tier_id=? AND price_version=? AND pay_fen=? AND credit_fen=? AND status IN ('pending','reported') AND created>? ORDER BY created DESC LIMIT 1",(uid,tier_id,self.config['price_version'],tier['pay_fen'],tier['credit_fen'],self.now()-86400)).fetchone()
            if prior:return dict(prior)
            if c.execute('SELECT count(*) FROM listing_orders WHERE account_id=? AND created>?',(uid,self.now()-86400)).fetchone()[0]>=12:raise Error(429,'ORDER_RATE_LIMITED')
            oid=uuid.uuid4().hex
            c.execute('INSERT INTO listing_orders VALUES(?,?,?,?,?,?,\'pending\',?,?,?,NULL,NULL)',
                      (oid,uid,tier_id,self.config['price_version'],tier['pay_fen'],tier['credit_fen'],source,channel,self.now()))
            return dict(id=oid,status='pending',pay_fen=tier['pay_fen'])
        return self.mutate(uid,key,'order',[tier_id,source,channel],go)

    def owned(self,c,table,uid,rid):
        # Only internal constant table names reach this method.
        row=c.execute('SELECT * FROM '+table+' WHERE id=? AND account_id=?',(rid,uid)).fetchone()
        if not row:raise Error(404,'NOT_FOUND')
        return row

    def report(self,uid,key,oid):
        def go(c):
            self.owned(c,'listing_orders',uid,oid)
            c.execute("UPDATE listing_orders SET status='reported' WHERE id=? AND status='pending'",(oid,))
            return dict(self.owned(c,'listing_orders',uid,oid))
        return self.mutate(uid,key,'report',oid,go)

    def confirm_receipt(self, uid, key, oid, amount, transaction, actor, verified):
        """Internal adapter only. No client route may call this authority function."""
        if verified is not True or type(amount) is not int or not actor or not re.fullmatch(r'[A-Za-z0-9_-]{6,128}',transaction or ''):
            raise Error(400,'INVALID_RECEIPT')
        def go(c):
            o=self.owned(c,'listing_orders',uid,oid)
            if amount!=o['pay_fen']:raise Error(409,'AMOUNT_MISMATCH')
            if o['status']=='paid':
                if o['transaction_id']!=transaction:raise Error(409,'RECEIPT_CONFLICT')
                return dict(status='paid',credited=False)
            if o['status']!='reported':raise Error(409,'PAYMENT_NOT_REPORTED')
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ('listing_orders','trade_orders','pet_orders','member_orders','payment_orders','orders','settlement_receipts'):
                if table not in tables:continue
                cols={r[1] for r in c.execute('PRAGMA table_info('+table+')')}
                for col in ('transaction_id','transaction_no','provider_transaction_id'):
                    if col in cols and c.execute('SELECT 1 FROM '+table+' WHERE '+col+'=?',(transaction,)).fetchone():
                        raise Error(409,'RECEIPT_ALREADY_USED')
            # Shared receipt registry makes the exclusion visible to existing product settlement.
            c.execute('CREATE TABLE IF NOT EXISTS settlement_receipts(transaction_id TEXT PRIMARY KEY,product TEXT NOT NULL,order_id TEXT NOT NULL,amount_fen INTEGER NOT NULL,actor TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL)')
            c.execute("INSERT INTO settlement_receipts VALUES(?,'listing-optimizer',?,?,?,'paid',?)",(transaction,oid,amount,actor,self.now()))
            c.execute('UPDATE listing_accounts SET balance_fen=balance_fen+? WHERE account_id=?',(o['credit_fen'],uid))
            c.execute("UPDATE listing_orders SET status='paid',paid_at=?,transaction_id=? WHERE id=?",(self.now(),transaction,oid))
            self.ledger(c,uid,'recharge',o['credit_fen'],oid)
            return dict(status='paid',credited=True)
        return self.mutate(uid,key,'confirm',[oid,amount,transaction,actor],go)

    def quote(self,uid,key,scope):
        self.require_ready()
        from listing_scope import normalize
        scope=normalize(scope,self.config)
        def go(c):
            a=self.account(c,uid)
            if a['trial_state']=='held':raise Error(409,'TRIAL_IN_PROGRESS')
            trial=a['trial_state']=='available';qid=uuid.uuid4().hex
            c.execute('INSERT INTO listing_quotes VALUES(?,?,?,?,?,?,?)',(qid,uid,canonical(scope),self.config['price_version'],self.config['unit_price_fen'],'trial' if trial else 'paid',self.now()+600))
            return dict(id=qid,units=1,trial_units=int(trial),paid_units=int(not trial),reserve_fen=0 if trial else self.config['unit_price_fen'],expires=self.now()+600,scope=scope,scope_hash=sha(canonical(scope)),price_version=self.config['price_version'])
        return self.mutate(uid,key,'quote',scope,go)

    def reserve(self,uid,key,qid,confirmed):
        self.require_ready()
        if confirmed is not True:raise Error(400,'CONFIRMATION_REQUIRED')
        def go(c):
            q=self.owned(c,'listing_quotes',uid,qid)
            existing=c.execute('SELECT * FROM listing_tasks WHERE quote_id=?',(qid,)).fetchone()
            if existing:return dict(id=existing['id'],state=existing['state'])
            if q['expires']<=self.now():raise Error(409,'QUOTE_EXPIRED')
            a=self.account(c,uid);amount=q['unit_price_fen'] if q['funding']=='paid' else 0
            if q['funding']=='trial':
                if a['trial_state']!='available':raise Error(409,'REQUOTE_REQUIRED')
                c.execute("UPDATE listing_accounts SET trial_state='held' WHERE account_id=?",(uid,))
            else:
                if a['trial_state']!='used':raise Error(409,'REQUOTE_REQUIRED')
                if a['balance_fen']-a['reserved_fen']<amount:raise Error(402,'INSUFFICIENT_BALANCE')
                c.execute('UPDATE listing_accounts SET reserved_fen=reserved_fen+? WHERE account_id=?',(amount,uid))
            tid=uuid.uuid4().hex
            c.execute("INSERT INTO listing_tasks VALUES(?,?,?,'reserved',?,?,NULL,?)",(tid,uid,qid,q['funding'],amount,self.now()))
            self.ledger(c,uid,'reserve',amount,tid)
            return dict(id=tid,state='reserved')
        return self.mutate(uid,key,'reserve',[qid,confirmed],go)

    def complete(self,uid,key,tid,evidence):
        # Server verifier owns readiness, durable result storage and retrieval.
        # No public success=true/charge_fen field can authorize settlement.
        with self.store.connect() as c:
            t=self.owned(c,'listing_tasks',uid,tid)
            if t['state'] not in ('reserved','settled'):raise Error(409,'TASK_NOT_SETTLEABLE')
            saved=json.loads(t['result']) if t['state']=='settled' else None
        with self.store.connect() as c:
            scope=json.loads(self.owned(c,'listing_quotes',uid,t['quote_id'])['scope'])
        artifact=saved or self.verifier.recover_verified(tid,evidence,scope)
        self.validate_artifact(artifact,scope)
        def go(c):
            t=self.owned(c,'listing_tasks',uid,tid)
            if t['state']=='settled':return json.loads(t['result'])
            if t['state']!='reserved':raise Error(409,'TASK_NOT_SETTLEABLE')
            if t['funding']=='trial':
                c.execute("UPDATE listing_accounts SET trial_state='used' WHERE account_id=? AND trial_state='held'",(uid,))
            else:
                c.execute('UPDATE listing_accounts SET balance_fen=balance_fen-?,reserved_fen=reserved_fen-? WHERE account_id=?',(t['amount_fen'],t['amount_fen'],uid))
            c.execute("UPDATE listing_tasks SET state='settled',result=? WHERE id=?",(canonical(artifact),tid))
            c.execute('INSERT INTO listing_artifacts VALUES(?,0,?,?)',(tid,canonical(artifact),self.now()))
            self.ledger(c,uid,'settle',-t['amount_fen'],tid)
            return artifact
        return self.mutate(uid,key,'complete',[tid,evidence],go)

    def validate_artifact(self,artifact,scope):
        # A trusted adapter verifies factual accuracy, platform-specific fields,
        # durable storage and recoverability. Core additionally rejects partial
        # bundles or artifacts attested for another immutable scope.
        if not isinstance(artifact,dict) or not artifact.get('artifact_id') or artifact.get('scope_hash')!=sha(canonical(scope)):
            raise Error(409,'NO_VERIFIED_DELIVERY')
        deliveries=artifact.get('deliveries')
        if not isinstance(deliveries,list) or len(deliveries)!=len(scope['targets']):raise Error(409,'INCOMPLETE_BUNDLE')
        wanted=sorted(canonical(t) for t in scope['targets'])
        actual=[]
        for item in deliveries:
            if not isinstance(item,dict) or not isinstance(item.get('content'),dict) or not item['content']:
                raise Error(409,'INCOMPLETE_BUNDLE')
            actual.append(canonical(item.get('target')))
        if sorted(actual)!=wanted:raise Error(409,'INCOMPLETE_BUNDLE')

    def revise(self,uid,key,tid,evidence):
        """Same immutable SKU/targets; unlimited verified revisions, no new charge.

        All prior artifacts remain recoverable. Changing SKU/targets requires a
        separately confirmed task; the public client cannot override scope here.
        """
        with self.store.connect() as c:
            t=self.owned(c,'listing_tasks',uid,tid)
            if t['state']!='settled':raise Error(409,'TASK_NOT_DELIVERED')
            scope=json.loads(self.owned(c,'listing_quotes',uid,t['quote_id'])['scope'])
        artifact=self.verifier.recover_verified(tid,evidence,scope)
        self.validate_artifact(artifact,scope)
        def go(c):
            t=self.owned(c,'listing_tasks',uid,tid)
            if t['state']!='settled':raise Error(409,'TASK_NOT_DELIVERED')
            revision=c.execute('SELECT coalesce(max(revision),-1)+1 FROM listing_artifacts WHERE task_id=?',(tid,)).fetchone()[0]
            c.execute('INSERT INTO listing_artifacts VALUES(?,?,?,?)',(tid,revision,canonical(artifact),self.now()))
            c.execute('UPDATE listing_tasks SET result=? WHERE id=?',(canonical(artifact),tid))
            return dict(task_id=tid,revision=revision,result=artifact,charged_fen=0)
        return self.mutate(uid,key,'revise',[tid,evidence],go)

    def release_confirmed_failure(self,uid,key,tid,verdict):
        """Trusted worker only: unknown stays reserved and recoverable, never auto-refunded."""
        if verdict not in ('confirmed_failure','unknown'):raise Error(400,'INVALID_VERDICT')
        def go(c):
            t=self.owned(c,'listing_tasks',uid,tid)
            if t['state']=='settled':raise Error(409,'ALREADY_SETTLED')
            if t['state']=='released' or verdict=='unknown':return dict(id=tid,state=t['state'])
            if t['funding']=='trial':c.execute("UPDATE listing_accounts SET trial_state='available' WHERE account_id=? AND trial_state='held'",(uid,))
            else:c.execute('UPDATE listing_accounts SET reserved_fen=reserved_fen-? WHERE account_id=?',(t['amount_fen'],uid))
            c.execute("UPDATE listing_tasks SET state='released' WHERE id=?",(tid,))
            self.ledger(c,uid,'release',t['amount_fen'],tid)
            return dict(id=tid,state='released')
        return self.mutate(uid,key,'release',[tid,verdict],go)

    def task(self,uid,tid):
        with self.store.connect() as c:
            row=dict(self.owned(c,'listing_tasks',uid,tid))
            row['result']=json.loads(row['result']) if row['result'] else None
            row['requires_review']=row['state']=='reserved' and self.now()-row['created']>1800
            return row
