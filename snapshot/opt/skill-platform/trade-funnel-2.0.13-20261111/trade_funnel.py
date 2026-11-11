"""Trade-only measurement sidecar. Business databases are read-only projections.

This adapts the requested phone funnel to the site's existing WeChat identity.
It never registers, approves, grants, settles, or changes business balances.
"""
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import ipaddress
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

CONTRACT = 'trade-funnel-v1'
SKILL = 'mps-linkedin-buyer-radar'
CHANNELS = ('workbuddy_skill', 'workbuddy_expert', 'skillhub')
TZ = timezone(timedelta(hours=8))
DAY = 86400


class Invalid(ValueError): pass
class Limited(Invalid): pass
class Conflict(Invalid): pass


def identity(value):
    try:
        parsed = uuid.UUID(value)
        return isinstance(value, str) and str(parsed) == value and parsed.version == 4 and parsed.variant == uuid.RFC_4122
    except (ValueError, TypeError, AttributeError):
        return False


def query_window(since=None, until=None, days=7, now=None):
    now = int(time.time() if now is None else now)
    if since is not None or until is not None:
        if not isinstance(since, str) or not isinstance(until, str): raise Invalid('both_dates_required')
        try: a, b = date.fromisoformat(since), date.fromisoformat(until)
        except ValueError: raise Invalid('invalid_dates') from None
        if a.isoformat() != since or b.isoformat() != until or not 0 <= (b-a).days < 90: raise Invalid('invalid_dates')
        start = int(datetime.combine(a, datetime.min.time(), TZ).timestamp())
        end = int(datetime.combine(b+timedelta(days=1), datetime.min.time(), TZ).timestamp())
        return dict(since=since, until=until, start=start, end=end, timezone='Asia/Shanghai', mode='beijing_dates')
    if type(days) is not int or days not in (1, 7, 14, 30, 90): raise Invalid('invalid_days')
    return dict(since=None, until=None, start=now-days*DAY, end=now+1, days=days, timezone='UTC', mode='rolling')


SCHEMA = '''
CREATE TABLE tf_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
INSERT INTO tf_meta VALUES('schema','1');
CREATE TABLE skill_trigger_events(id TEXT PRIMARY KEY,skill_code TEXT NOT NULL,instance_id TEXT NOT NULL,machine_id TEXT NOT NULL,ip_day_hash TEXT NOT NULL,occurred_at INTEGER NOT NULL,is_test INTEGER NOT NULL);
CREATE INDEX tf_trigger_time ON skill_trigger_events(occurred_at);
CREATE TABLE skill_installations(instance_id TEXT PRIMARY KEY,skill_code TEXT NOT NULL,machine_id TEXT NOT NULL,installation_hash TEXT NOT NULL,channel TEXT NOT NULL,skill_version TEXT NOT NULL,first_at INTEGER NOT NULL,event_id TEXT,user_id TEXT,bridge_ok INTEGER NOT NULL DEFAULT 0,is_test INTEGER NOT NULL);
CREATE TABLE tf_machines(machine_id TEXT NOT NULL,first_at INTEGER NOT NULL,instance_id TEXT NOT NULL,is_test INTEGER NOT NULL,PRIMARY KEY(machine_id,is_test));
CREATE TABLE tf_rates(day TEXT NOT NULL,ip_day_hash TEXT NOT NULL,count INTEGER NOT NULL,PRIMARY KEY(day,ip_day_hash));
CREATE TABLE tf_links(code_hash TEXT PRIMARY KEY,device_hash TEXT NOT NULL,instance_id TEXT,created INTEGER NOT NULL,is_test INTEGER NOT NULL);
CREATE TABLE tf_oauth(entity TEXT PRIMARY KEY,code_hash TEXT NOT NULL,instance_id TEXT,user_id TEXT,first_at INTEGER NOT NULL,is_test INTEGER NOT NULL);
CREATE TABLE tf_activations(code_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,first_at INTEGER NOT NULL,is_new INTEGER NOT NULL,is_test INTEGER NOT NULL);
CREATE TABLE tf_account_origins(user_id TEXT PRIMARY KEY,created INTEGER NOT NULL,is_test INTEGER NOT NULL);
CREATE TABLE page_view_events(id TEXT PRIMARY KEY,page TEXT NOT NULL,ip_day_hash TEXT NOT NULL,occurred_at INTEGER NOT NULL,user_id TEXT,instance_id TEXT,is_test INTEGER NOT NULL);
CREATE INDEX tf_page_time ON page_view_events(occurred_at);
CREATE TABLE tf_visitors(ip_day_hash TEXT NOT NULL,first_at INTEGER NOT NULL,visit_id TEXT NOT NULL,is_test INTEGER NOT NULL,PRIMARY KEY(ip_day_hash,is_test));
'''
TABLES = {'tf_meta','skill_trigger_events','skill_installations','tf_machines','tf_rates','tf_links','tf_oauth','tf_activations','tf_account_origins','page_view_events','tf_visitors'}


def migrate(path):
    """Explicit migration for a new private sidecar; refuse unrelated databases."""
    path = Path(path)
    if path.is_symlink(): raise Invalid('symlink_database')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try: fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError: pass
    else: os.close(fd)
    if path.is_symlink() or (os.name != 'nt' and path.stat().st_mode & 0o077): raise Invalid('private_database_required')
    c = sqlite3.connect(path.resolve().as_uri()+'?mode=rw', uri=True)
    try:
        with c:
            c.execute('BEGIN IMMEDIATE')
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables:
                if tables != TABLES or c.execute("SELECT value FROM tf_meta WHERE key='schema'").fetchone() != ('1',): raise Invalid('not_a_trade_funnel_database')
                return
            if c.execute('SELECT 1 FROM sqlite_master LIMIT 1').fetchone(): raise Invalid('not_an_empty_database')
            for statement in SCHEMA.split(';'):
                if statement.strip(): c.execute(statement)
    finally: c.close()


@contextmanager
def read_database(path):
    c = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True, timeout=.2)
    c.row_factory = sqlite3.Row
    deadline = time.monotonic()+2
    c.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
    c.execute('PRAGMA query_only=ON')
    try:
        c.execute('BEGIN')
        yield c
    finally: c.close()


class Funnel:
    def __init__(self, path, key, dialogues=None, shared_path=None, clock=time.time):
        if not isinstance(key, bytes) or len(key) != 32: raise Invalid('invalid_server_key')
        self.path, self.key, self.dialogues, self.clock = Path(path), key, dialogues, clock
        self.shared_path = Path(shared_path) if shared_path else None

    @contextmanager
    def connect(self, write=False):
        if self.path.is_symlink(): raise Invalid('symlink_database')
        mode = 'rw' if write else 'ro'
        c = sqlite3.connect(self.path.resolve().as_uri()+'?mode='+mode, uri=True, timeout=.2)
        c.row_factory = sqlite3.Row
        deadline = time.monotonic()+1
        c.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
        try:
            if not write: c.execute('PRAGMA query_only=ON')
            c.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            if tuple(c.execute("SELECT value FROM tf_meta WHERE key='schema'").fetchone() or ()) != ('1',): raise Invalid('migration_required')
            yield c
            c.commit()
        finally: c.close()

    def digest(self, value): return hmac.new(self.key,value.encode(),hashlib.sha256).hexdigest()

    def ip_hash(self, ip, at=None):
        ip = str(ipaddress.ip_address(ip)); at = int(self.clock() if at is None else at)
        day = datetime.fromtimestamp(at,TZ).date().isoformat()
        return day, self.digest('ip-day:'+day+':'+ip)

    def trigger(self, body, ip, channel='workbuddy_expert', version='', is_test=False):
        if not isinstance(body,dict) or set(body) != {'skill_code','instance_id','machine_id'}: raise Invalid('exact_three_fields_required')
        code = body['skill_code']
        if not isinstance(code,str) or len(code)>64 or not re.fullmatch('[a-z][a-z0-9]*(?:-[a-z0-9]+)*',code) or code != SKILL: raise Invalid('skill_not_enabled')
        if not identity(body['instance_id']) or not identity(body['machine_id']): raise Invalid('canonical_uuid4_required')
        channel = channel if channel in CHANNELS else 'workbuddy_expert'
        if not isinstance(version,str) or len(version)>40 or any(ord(x)<32 for x in version): version=''
        at=int(self.clock()); day,iph=self.ip_hash(ip,at); inst=body['instance_id']; machine=body['machine_id']
        install_hash = self.dialogues.digest('installation:'+inst) if self.dialogues else self.digest('installation:'+inst)
        with self.connect(True) as c:
            rate=c.execute('SELECT count FROM tf_rates WHERE day=? AND ip_day_hash=?',(day,iph)).fetchone()
            if rate and rate[0]>=50: raise Limited('daily_limit')
            c.execute('INSERT INTO tf_rates VALUES(?,?,1) ON CONFLICT(day,ip_day_hash) DO UPDATE SET count=count+1',(day,iph))
            row=c.execute('SELECT skill_code,machine_id,is_test FROM skill_installations WHERE instance_id=?',(inst,)).fetchone()
            if row and (row['skill_code']!=code or row['machine_id']!=machine or row['is_test']!=int(bool(is_test))):
                # A syntactically valid replay still consumes its daily request.
                conflict=True
            else:
                conflict=False
                c.execute('INSERT OR IGNORE INTO skill_installations(instance_id,skill_code,machine_id,installation_hash,channel,skill_version,first_at,is_test) VALUES(?,?,?,?,?,?,?,?)',(inst,code,machine,install_hash,channel,version,at,int(bool(is_test))))
                c.execute('INSERT OR IGNORE INTO tf_machines VALUES(?,?,?,?)',(machine,at,inst,int(bool(is_test))))
                c.execute('INSERT INTO skill_trigger_events VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),code,inst,machine,iph,at,int(bool(is_test))))
                c.execute('UPDATE tf_links SET is_test=? WHERE instance_id=?',(int(bool(is_test)),inst))
                c.execute('UPDATE tf_oauth SET is_test=? WHERE instance_id=?',(int(bool(is_test)),inst))
                if is_test:
                    # A loopback test beacon can race its own page request.
                    # Move only that instance's details/derived visitor firsts;
                    # never reclassify an unrelated page or a business record.
                    affected=[r[0] for r in c.execute("SELECT DISTINCT ip_day_hash FROM page_view_events WHERE instance_id=? AND page='skill-activate' AND user_id IS NULL",(inst,))]
                    c.execute('UPDATE page_view_events SET is_test=1 WHERE instance_id=?',(inst,))
                    for page_ip in affected:
                        c.execute('DELETE FROM tf_visitors WHERE ip_day_hash=? AND visit_id IN (SELECT id FROM page_view_events WHERE instance_id=?)',(page_ip,inst))
                        for test_mode in (0,1):
                            first=c.execute("SELECT id,occurred_at FROM page_view_events WHERE ip_day_hash=? AND page='skill-activate' AND user_id IS NULL AND is_test=? ORDER BY occurred_at,id LIMIT 1",(page_ip,test_mode)).fetchone()
                            if first:c.execute('INSERT OR IGNORE INTO tf_visitors VALUES(?,?,?,?)',(page_ip,first['occurred_at'],first['id'],test_mode))
        if conflict: raise Conflict('instance_identity_conflict')
        # Existing protocol owns account linking and its receipt; no account is
        # inferred from IP, machine, device, or an untrusted measurement header.
        self.bridge(inst)

    def prune(self):
        """Only expiring sidecar details; historical firsts never reset."""
        at=int(self.clock())
        with self.connect(True) as c:
            c.execute('DELETE FROM skill_trigger_events WHERE occurred_at<?',(at-180*DAY,))
            c.execute('DELETE FROM page_view_events WHERE occurred_at<?',(at-180*DAY,))
            c.execute('DELETE FROM tf_rates WHERE day<?',((datetime.fromtimestamp(at,TZ).date()-timedelta(days=2)).isoformat(),))
        self.last_pruned_at=at

    def bridge(self, instance):
        if not self.dialogues: return
        with self.connect() as c: row=c.execute('SELECT * FROM skill_installations WHERE instance_id=?',(instance,)).fetchone()
        if not row: return
        result=self.dialogues.record(dict(event_id=str(uuid.uuid4()),installation_id=instance,skill_id=SKILL,
            skill_name='外贸获客Linkedin',skill_version=row['skill_version'],channel=row['channel'],is_test=bool(row['is_test'])))
        self.link_from_dialogue(result['event_id'])

    def link_from_dialogue(self, event_id):
        if not self.dialogues: return
        with self.dialogues.connect(True) as d:
            row=d.execute('SELECT event_id,installation_hash,skill_id,channel,user_id,is_test FROM first_dialogues WHERE event_id=?',(event_id,)).fetchone()
        if not row or row['skill_id']!=SKILL: return
        with self.connect(True) as c:
            current=c.execute('SELECT user_id,is_test FROM skill_installations WHERE installation_hash=? AND channel=?',(row['installation_hash'],row['channel'])).fetchone()
            if current and current['is_test']!=row['is_test']: raise Conflict('test_identity_conflict')
            if current and current['user_id'] and row['user_id'] and current['user_id']!=row['user_id']: raise Conflict('trusted_link_conflict')
            c.execute('UPDATE skill_installations SET event_id=?,user_id=COALESCE(user_id,?),bridge_ok=1 WHERE installation_hash=? AND channel=?',
                      (row['event_id'],row['user_id'],row['installation_hash'],row['channel']))

    def remember_link(self, code, device, instance):
        try: device_valid=isinstance(device,str) and str(uuid.UUID(device))==device.lower()
        except (ValueError,TypeError,AttributeError): device_valid=False
        if not isinstance(code,str) or not re.fullmatch('[A-Z2-9]{8}',code) or not device_valid: return
        instance=instance if identity(instance) else None
        with self.connect(True) as c:
            known=c.execute('SELECT is_test FROM skill_installations WHERE instance_id=? AND skill_code=?',(instance,SKILL)).fetchone()
            # First-open workers are asynchronous. Retain this untrusted
            # measurement hint even if the beacon arrives after auth/start.
            # It grants no account linkage; only the old signed receipt does.
            c.execute('INSERT OR IGNORE INTO tf_links VALUES(?,?,?,?,?)',(hashlib.sha256(code.encode()).hexdigest(),hashlib.sha256(device.encode()).hexdigest(),instance,int(self.clock()),known['is_test'] if known else 0))

    def oauth_started(self, code_hash, source_uid=None):
        if not isinstance(code_hash,str) or not re.fullmatch('[a-f0-9]{64}',code_hash): return
        with self.connect(True) as c:
            link=c.execute('SELECT instance_id,is_test FROM tf_links WHERE code_hash=?',(code_hash,)).fetchone()
            instance=link[0] if link else None
            entity='instance:'+instance if instance else 'code:'+code_hash
            c.execute('INSERT OR IGNORE INTO tf_oauth VALUES(?,?,?,?,?,?)',(entity,code_hash,instance,source_uid,int(self.clock()),link['is_test'] if link else 0))

    def approved(self, code_hash, uid, new_account, is_test=False, device_hash=None):
        if not isinstance(uid,str) or not uid: return
        at=int(self.clock())
        with self.connect(True) as c:
            if isinstance(device_hash,str) and re.fullmatch('[a-f0-9]{64}',device_hash):
                c.execute('INSERT OR IGNORE INTO tf_links VALUES(?,?,NULL,?,?)',(code_hash,device_hash,at,int(bool(is_test))))
            link=c.execute('SELECT is_test FROM tf_links WHERE code_hash=?',(code_hash,)).fetchone()
            is_test=bool(is_test or (link and link['is_test']))
            c.execute('INSERT OR IGNORE INTO tf_activations VALUES(?,?,?,?,?)',(code_hash,uid,at,int(bool(new_account)),int(is_test)))
            if new_account: c.execute('INSERT OR IGNORE INTO tf_account_origins VALUES(?,?,?)',(uid,at,int(is_test)))
            c.execute('UPDATE tf_oauth SET user_id=COALESCE(user_id,?) WHERE code_hash=? OR instance_id=(SELECT instance_id FROM tf_links WHERE code_hash=?)',(uid,code_hash,code_hash))

    def identity_confirmed(self, code_hash, uid):
        """Only a verified OAuth database identity may replace its prior hint."""
        with self.connect(True) as c:
            c.execute('UPDATE tf_oauth SET user_id=? WHERE code_hash=?',(uid,code_hash))

    def page(self, page, ip, uid=None, code=None, is_test=False):
        if page not in ('skill-activate','recharge'): raise Invalid('invalid_page')
        if code is not None and (not isinstance(code,str) or not re.fullmatch('[A-Z2-9]{8}',code)): raise Invalid('invalid_code')
        at=int(self.clock());day,iph=self.ip_hash(ip,at); visit=str(uuid.uuid4()); instance=None
        with self.connect(True) as c:
            page_budget=self.digest('page-budget:'+iph)
            rate=c.execute('SELECT count FROM tf_rates WHERE day=? AND ip_day_hash=?',(day,page_budget)).fetchone()
            if rate and rate[0]>=200:raise Limited('page_daily_limit')
            c.execute('INSERT INTO tf_rates VALUES(?,?,1) ON CONFLICT(day,ip_day_hash) DO UPDATE SET count=count+1',(day,page_budget))
            if code:
                row=c.execute('SELECT instance_id,is_test FROM tf_links WHERE code_hash=?',(hashlib.sha256(code.encode()).hexdigest(),)).fetchone()
                instance=row[0] if row else None
                is_test=bool(is_test or (row and row['is_test']))
            c.execute('INSERT INTO page_view_events VALUES(?,?,?,?,?,?,?)',(visit,page,iph,at,uid,instance,int(bool(is_test))))
            if page=='skill-activate' and not uid: c.execute('INSERT OR IGNORE INTO tf_visitors VALUES(?,?,?,?)',(iph,at,visit,int(bool(is_test))))

    def _payments(self):
        if not self.shared_path: return [],False
        with read_database(self.shared_path) as c:
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'trade_orders','trade_ledger'}<=tables: return [],False
            rows=[dict(r) for r in c.execute("SELECT 'order:'||id AS id,account_id AS user_id,paid_at AS occurred_at,amount_fen,'orders' AS kind FROM trade_orders WHERE status='paid' AND paid_at IS NOT NULL AND is_test=0 AND amount_fen>0 UNION ALL SELECT 'ledger:'||l.id,l.account_id,l.created_at,l.amount_fen,'ledger_only' FROM trade_ledger l WHERE l.action='recharge' AND l.scope='trade-leads' AND l.is_test=0 AND l.amount_fen>0 AND NOT EXISTS(SELECT 1 FROM trade_orders o WHERE o.id=l.ref_id AND o.account_id=l.account_id)")]
        return rows,True

    def rows(self, window, include_test=False):
        start,end=window['start'],window['end']; inside=lambda at:start<=at<end
        with self.connect() as c:
            where='' if include_test else ' WHERE is_test=0'
            machines=[dict(r) for r in c.execute('SELECT * FROM tf_machines'+where)]
            installs=[dict(r) for r in c.execute('SELECT * FROM skill_installations'+where)]
            visitors=[dict(r) for r in c.execute('SELECT * FROM tf_visitors'+where)]
            oauth=[dict(r) for r in c.execute('SELECT * FROM tf_oauth'+where)]
            activations=[dict(r) for r in c.execute('SELECT * FROM tf_activations'+where)]
            links={r['code_hash']:dict(r) for r in c.execute('SELECT * FROM tf_links')}
            origins={r['user_id']:r['created'] for r in c.execute('SELECT * FROM tf_account_origins'+where)}
            pages=[dict(r) for r in c.execute('SELECT * FROM page_view_events WHERE occurred_at>=? AND occurred_at<?'+('' if include_test else ' AND is_test=0'),(start,end))]
        install_by_id={r['instance_id']:r for r in installs}
        def item(kind,key,at,uid=None,instance=None,**extra):
            row=dict(id=kind+':'+self.digest(str(key))[:32],occurred_at=at,skill_code=SKILL,**extra)
            if uid: row['user_id']=uid
            linked=install_by_id.get(instance)
            if linked:
                row['channel']=linked['channel']
                if linked['event_id']: row['event_id']=linked['event_id']
                if linked['user_id']: row.setdefault('user_id',linked['user_id'])
            return row
        page_by_id={r['id']:r for r in pages}
        first_authorization={}
        pending_authorization=[]
        for row in oauth:
            uid=row['user_id']
            if not uid:
                if inside(row['first_at']):pending_authorization.append(row)
            elif uid in origins and inside(origins[uid]):
                if uid not in first_authorization or row['first_at']<first_authorization[uid]['first_at']:
                    first_authorization[uid]=row
        authorization=pending_authorization+[r for r in first_authorization.values() if inside(r['first_at'])]
        stages={'L0':[item('machine',r['machine_id'],r['first_at'],instance=r['instance_id']) for r in machines if inside(r['first_at'])],
                'L1':[item('visitor',r['visit_id'],r['first_at'],instance=page_by_id.get(r['visit_id'],{}).get('instance_id')) for r in visitors if inside(r['first_at'])],
                'L2':[item('authorization',r['entity'],r['first_at'],r['user_id'],r['instance_id']) for r in authorization],
                'L3':[item('account',uid,at,uid) for uid,at in origins.items() if inside(at)],'L4':[],'L5':[]}
        first_recharge_page={}
        for row in pages:
            uid=row['user_id']
            if row['page']=='recharge' and uid in origins and inside(origins[uid]):
                if uid not in first_recharge_page or row['occurred_at']<first_recharge_page[uid]['occurred_at']:first_recharge_page[uid]=row
        stages['L4']=[item('recharge-page',r['id'],r['occurred_at'],uid) for uid,r in first_recharge_page.items()]
        payments,payments_available=self._payments();first_paid={}
        for row in payments:
            uid=row['user_id']
            if uid not in first_paid or (row['occurred_at'],row['id'])<(first_paid[uid]['occurred_at'],first_paid[uid]['id']):first_paid[uid]=row
        stages['L5']=[item('first-payment',r['id'],r['occurred_at'],uid,amount_fen=r['amount_fen']) for uid,r in first_paid.items() if uid in origins and inside(origins[uid]) and inside(r['occurred_at'])]
        all_installs=[r for r in installs if inside(r['first_at'])];machine_at={(r['machine_id'],r['is_test']):r['first_at'] for r in machines}
        new_machine=sum(inside(machine_at[(r['machine_id'],r['is_test'])]) for r in all_installs)
        activation_first={}
        for row in activations:
            link=links.get(row['code_hash'],{})
            if link.get('instance_id'):entity=('instance',link['instance_id'],row['user_id'])
            elif link.get('device_hash'):entity=('device',link['device_hash'],row['user_id'])
            else:entity=('unattributed',row['user_id'])
            # Timestamps have one-second precision. A proven account-creation
            # activation must win ties against same-second reauthorization.
            order=(row['first_at'],not row['is_new'],row['code_hash'])
            old=activation_first.get(entity)
            if old is None or order<(old['first_at'],not old['is_new'],old['code_hash']):
                activation_first[entity]=dict(row,unattributed=entity[0]!='instance')
        active=[r for r in activation_first.values() if inside(r['first_at'])];paid=[r for r in payments if inside(r['occurred_at'])]
        extras=dict(skill_first_opens=dict(total=len(all_installs),new_machine=new_machine,existing_machine=len(all_installs)-new_machine),
            skill_activations=dict(total=len(active),new_account=sum(r['is_new'] for r in active),existing_account=sum(not r['is_new'] for r in active),unattributed=sum(r['unattributed'] for r in active)),
            recharge_entries=dict(total=len(paid),orders=sum(r['kind']=='orders' for r in paid),ledger_only=sum(r['kind']=='ledger_only' for r in paid),amount_fen=sum(r['amount_fen'] for r in paid)),
            bridge_pending=sum(not r['bridge_ok'] for r in installs),payments_available=payments_available)
        return stages,extras

    def summary(self, window, include_test=False):
        rows,extras=self.rows(window,include_test)
        labels={'L0':'首次开口（新设备）','L1':'打开关联页（新访客）','L2':'发起微信授权（首次）','L3':'首次关联（新账户）','L4':'打开充值页（新账户）','L5':'充值成功（新账户首充）'}
        bases={'L0':'随机machine_id历史首现；180天明细清理不重置历史首现','L1':'页面真实上报；仅匿名ip_day_hash历史首现，不以生成链接代替访问','L2':'原微信start接受同意且成功创建外贸授权状态；已知旧账户排除，未完成授权身份可能未知','L3':'原Trade.approve在uid为空时实际创建账户并成功关联；不推测历史账户创建时间','L4':'已验证浏览器账户在充值页真实上报，且账户属于本窗口新建cohort','L5':'原trade paid订单或未挂订单recharge账本；全历史首笔且账户创建在本窗口'}
        return dict(contract=CONTRACT,skill_code=SKILL,generated_at=int(self.clock()),window=window,identity_method='wechat',
            stages=[dict(id=stage,label=labels[stage],count=len(rows[stage]),available=stage!='L5' or extras['payments_available'],basis=bases[stage]) for stage in labels],
            skill_first_opens=extras['skill_first_opens'],skill_activations=extras['skill_activations'],recharge_entries=extras['recharge_entries'],
            source_summary=[dict(skill_code=SKILL,activations=extras['skill_activations']['total'],recharge_entries=extras['recharge_entries']['total'],amount_fen=extras['recharge_entries']['amount_fen'])],
            bridge_pending=extras['bridge_pending'],test_excluded=not include_test,limitations=['采用微信流程映射L2/L3，不是手机号身份SOP的原表迁移。','只观察接入后的事件；历史users无created列，不补造新账户cohort。','同日新账户cohort会低估跨日首充；老账户激活及全部入账另列。','页面及首触由客户端主动上报；无上报不等于未使用，不采集聊天正文。','ip_day_hash仅为当日匿名访问去重，不用于账户身份合并。'])

    def items(self, window, stage, page=1, include_test=False):
        if stage not in ('L0','L1','L2','L3','L4','L5') or type(page)is not int or not 1<=page<=100000:raise Invalid('invalid_items_query')
        rows,_=self.rows(window,include_test);items=sorted(rows[stage],key=lambda r:(r['occurred_at'],r['id']),reverse=True)
        return dict(stage=stage,page=page,page_size=50,total=len(items),items=items[(page-1)*50:page*50])

    def activity(self, uid=None, event_id=None):
        # Personal history keeps return visits; cohort restrictions belong only
        # to summary/items. Identity joins require the original signed receipt.
        cutoff=int(self.clock())-90*DAY
        with self.connect() as c:
            installs=[dict(r) for r in c.execute('SELECT * FROM skill_installations WHERE is_test=0')
                      if (uid and r['user_id']==uid) or (event_id and r['event_id']==event_id)]
            inst={r['instance_id']:r for r in installs}
            pages=[dict(r) for r in c.execute('SELECT * FROM page_view_events WHERE is_test=0 AND occurred_at>=?',(cutoff,))
                   if (uid and r['user_id']==uid) or r['instance_id'] in inst]
            oauth=[dict(r) for r in c.execute('SELECT * FROM tf_oauth WHERE is_test=0 AND first_at>=?',(cutoff,))
                   if (uid and r['user_id']==uid) or r['instance_id'] in inst]
            activations=[dict(r) for r in c.execute('SELECT * FROM tf_activations WHERE is_test=0 AND first_at>=?',(cutoff,)) if uid and r['user_id']==uid]
        def item(stage,key,at,instance=None,user=None,**extra):
            row=dict(stage=stage,id=stage+':'+self.digest(str(key))[:32],occurred_at=at,skill_code=SKILL,**extra)
            if user:row['user_id']=user
            if instance in inst:
                row['event_id']=inst[instance]['event_id'];row['channel']=inst[instance]['channel']
            return row
        items=[item('L0',r['instance_id'],r['first_at'],r['instance_id'],r['user_id']) for r in installs if r['first_at']>=cutoff]
        items.extend(item('L1' if r['page']=='skill-activate' else 'L4',r['id'],r['occurred_at'],r['instance_id'],r['user_id']) for r in pages)
        items.extend(item('L2',r['entity'],r['first_at'],r['instance_id'],r['user_id']) for r in oauth)
        items.extend(item('L3',r['code_hash'],r['first_at'],user=r['user_id']) for r in activations)
        if uid:
            payments,_=self._payments()
            items.extend(item('L5',r['id'],r['occurred_at'],user=uid,amount_fen=r['amount_fen']) for r in payments if r['user_id']==uid and r['occurred_at']>=cutoff)
        items.sort(key=lambda row:(row['occurred_at'],row['id']))
        return dict(items=items[:100],truncated=len(items)>100,days=90,identity_method='wechat',scope='all_personal_events')
