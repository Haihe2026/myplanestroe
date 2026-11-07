"""Opt-in telemetry sidecar. Never opens a business database for writing."""
import base64
from contextlib import closing, contextmanager
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

CONTRACT = 'machine-funnel-v1'
CHANNELS = {'workbuddy_skill', 'workbuddy_expert', 'skillhub'}
FIELDS = {'event_id', 'installation_id', 'machine_id', 'skill_id', 'skill_name',
          'skill_version', 'channel', 'client_occurred_at', 'is_test'}
TZ = timezone(timedelta(hours=8))
DAY = 86400


class Invalid(ValueError):
    pass


class Conflict(Invalid):
    pass


class Limited(Invalid):
    pass


def identity(value):
    try:
        parsed = uuid.UUID(value)
        return str(parsed) == value and parsed.version == 4 and parsed.variant == uuid.RFC_4122
    except (ValueError, TypeError, AttributeError):
        return False


def window(start, end):
    """Inclusive Beijing dates -> half-open UTC seconds; maximum 90 days."""
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if not 0 <= (b-a).days < 90:
        raise Invalid('invalid_window')
    return (int(datetime.combine(a, datetime.min.time(), TZ).timestamp()),
            int(datetime.combine(b+timedelta(days=1), datetime.min.time(), TZ).timestamp()))


SCHEMA = '''
CREATE TABLE mf_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
INSERT INTO mf_meta VALUES('schema','1');
CREATE TABLE mf_events(
 event_id TEXT PRIMARY KEY,installation_id TEXT NOT NULL,machine_id TEXT NOT NULL,
 skill_id TEXT NOT NULL,skill_name TEXT NOT NULL,skill_version TEXT NOT NULL,
 channel TEXT NOT NULL,ip_day_hash TEXT NOT NULL,occurred_at INTEGER NOT NULL,
 is_test INTEGER NOT NULL,user_id TEXT,linked_at INTEGER,
 UNIQUE(installation_id,skill_id,channel,is_test));
CREATE TABLE mf_machines(machine_id TEXT NOT NULL,is_test INTEGER NOT NULL,
 first_at INTEGER NOT NULL,PRIMARY KEY(machine_id,is_test));
CREATE TABLE mf_installations(installation_id TEXT NOT NULL,machine_id TEXT NOT NULL,
 skill_id TEXT NOT NULL,channel TEXT NOT NULL,is_test INTEGER NOT NULL,first_at INTEGER NOT NULL,
 PRIMARY KEY(installation_id,skill_id,channel,is_test));
CREATE TABLE mf_bindings(user_id TEXT NOT NULL,skill_id TEXT NOT NULL,channel TEXT NOT NULL,
 installation_id TEXT NOT NULL,machine_id TEXT NOT NULL,is_test INTEGER NOT NULL,
 first_at INTEGER NOT NULL,PRIMARY KEY(user_id,skill_id,channel,is_test));
CREATE TABLE mf_pages(visit_id TEXT PRIMARY KEY,kind TEXT NOT NULL,skill_id TEXT NOT NULL,
 channel TEXT NOT NULL,ip_day_hash TEXT NOT NULL,user_id TEXT,is_test INTEGER NOT NULL,
 occurred_at INTEGER NOT NULL);
CREATE TABLE mf_visitors(ip_day_hash TEXT NOT NULL,is_test INTEGER NOT NULL,
 first_at INTEGER NOT NULL,PRIMARY KEY(ip_day_hash,is_test));
CREATE TABLE mf_ip_budgets(day TEXT NOT NULL,ip_day_hash TEXT NOT NULL,count INTEGER NOT NULL,
 PRIMARY KEY(day,ip_day_hash));
CREATE INDEX mf_event_time ON mf_events(is_test,skill_id,occurred_at);
CREATE INDEX mf_page_time ON mf_pages(is_test,skill_id,occurred_at);
'''


def migrate(path):
    """Explicit new-sidecar migration. Existing unrelated databases are refused."""
    path = Path(path)
    if path.is_symlink():
        raise Invalid('symlink_database')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(fd)
    if path.is_symlink() or (os.name != 'nt' and path.stat().st_mode & 0o077):
        raise Invalid('private_database_required')
    expected = {'mf_meta', 'mf_events', 'mf_machines', 'mf_installations',
                'mf_bindings', 'mf_pages', 'mf_visitors', 'mf_ip_budgets'}
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=rw', uri=True)) as c, c:
        c.execute('BEGIN IMMEDIATE')
        names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if names:
            if names != expected or c.execute("SELECT value FROM mf_meta WHERE key='schema'").fetchone() != ('1',):
                raise Invalid('not_a_machine_funnel_database')
            return
        if c.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone():
            raise Invalid('not_a_machine_funnel_database')
        for statement in SCHEMA.split(';'):
            if statement.strip():
                c.execute(statement)


class Funnel:
    def __init__(self, path, key, skills=('mps-id-photo-background',), clock=time.time, daily_limit=50):
        if not isinstance(key, bytes) or len(key) != 32:
            raise Invalid('invalid_server_key')
        if not skills or any(not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,63}', s) for s in skills):
            raise Invalid('invalid_skill_allowlist')
        if type(daily_limit) is not int or not 1 <= daily_limit <= 1000:
            raise Invalid('invalid_daily_limit')
        self.path, self.key, self.skills = Path(path), key, frozenset(skills)
        self.clock, self.daily_limit = clock, daily_limit

    @contextmanager
    def connect(self, writable=False):
        if self.path.is_symlink():
            raise Invalid('symlink_database')
        c = sqlite3.connect(self.path.resolve().as_uri()+('?mode=rw' if writable else '?mode=ro'),
                            uri=True, timeout=.2)
        c.row_factory = sqlite3.Row
        try:
            deadline=time.monotonic()+2
            c.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
            if not writable:
                c.execute('PRAGMA query_only=ON')
            c.execute('BEGIN IMMEDIATE' if writable else 'BEGIN')
            if tuple(c.execute("SELECT value FROM mf_meta WHERE key='schema'").fetchone() or ()) != ('1',):
                raise Invalid('migration_required')
            yield c
            c.commit()
        finally:
            c.close()

    def digest(self, text):
        return hmac.new(self.key, text.encode(), hashlib.sha256).hexdigest()

    def ip_hash(self, ip, at):
        ip = str(ipaddress.ip_address(ip))
        day = datetime.fromtimestamp(at, TZ).date().isoformat()
        salt = hmac.new(self.key, ('ip-day:'+day).encode(), hashlib.sha256).digest()
        return day, hmac.new(salt, ip.encode(), hashlib.sha256).hexdigest()

    def receipt(self, row):
        value = 'machine-receipt:'+row['event_id']+':'+row['installation_id']
        return base64.urlsafe_b64encode(hmac.new(self.key, value.encode(), hashlib.sha256).digest()).decode().rstrip('=')

    def validate(self, body):
        if not isinstance(body, dict) or set(body)-FIELDS or not {'event_id','installation_id','machine_id','skill_id','channel'} <= set(body):
            raise Invalid('metadata_fields_only')
        if not all(identity(body[k]) for k in ('event_id','installation_id','machine_id')):
            raise Invalid('canonical_uuid4_required')
        if not isinstance(body['skill_id'], str) or not isinstance(body['channel'], str) or body['skill_id'] not in self.skills or body['channel'] not in CHANNELS:
            raise Invalid('skill_or_channel_not_enabled')
        if type(body.get('is_test', False)) is not bool:
            raise Invalid('invalid_test_flag')
        name, version = body.get('skill_name', body['skill_id']), body.get('skill_version', '')
        if not isinstance(name,str) or not 1 <= len(name) <= 100 or not isinstance(version,str) or len(version)>40 or any(ord(x)<32 for x in name+version):
            raise Invalid('invalid_public_identity')
        if 'client_occurred_at' in body:
            try:
                stamp = datetime.fromisoformat(body['client_occurred_at'].replace('Z','+00:00'))
                if stamp.tzinfo is None:
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise Invalid('timezone_required') from None
        return name, version

    def record(self, body, ip):
        name, version = self.validate(body)
        at = int(self.clock()); day, iph = self.ip_hash(ip, at)
        inst = self.digest('installation:'+body['installation_id'])
        machine = self.digest('machine:'+body['machine_id'])
        skill, channel, test = body['skill_id'], body['channel'], int(body.get('is_test',False))
        with self.connect(True) as c:
            used = c.execute('SELECT count FROM mf_ip_budgets WHERE day=? AND ip_day_hash=?', (day,iph)).fetchone()
            if used and used[0] >= self.daily_limit:
                raise Limited('daily_limit')
            existing = c.execute('SELECT * FROM mf_events WHERE event_id=?', (body['event_id'],)).fetchone()
            if existing and (existing['installation_id'],existing['machine_id'],existing['skill_id'],existing['channel'],existing['is_test']) != (inst,machine,skill,channel,test):
                raise Conflict('event_identity_conflict')
            old_install = c.execute('SELECT machine_id FROM mf_installations WHERE installation_id=? AND skill_id=? AND channel=? AND is_test=?', (inst,skill,channel,test)).fetchone()
            if old_install and old_install[0] != machine:
                raise Conflict('installation_machine_conflict')
            row = c.execute('SELECT * FROM mf_events WHERE installation_id=? AND skill_id=? AND channel=? AND is_test=?', (inst,skill,channel,test)).fetchone()
            duplicate = row is not None or old_install is not None
            if not row and not old_install:
                c.execute('INSERT INTO mf_events VALUES(?,?,?,?,?,?,?,?,?,?,NULL,NULL)',
                          (body['event_id'],inst,machine,skill,name,version,channel,iph,at,test))
                row = c.execute('SELECT * FROM mf_events WHERE event_id=?',(body['event_id'],)).fetchone()
                c.execute('INSERT OR IGNORE INTO mf_machines VALUES(?,?,?)',(machine,test,at))
                c.execute('INSERT INTO mf_installations VALUES(?,?,?,?,?,?)',(inst,machine,skill,channel,test,at))
            c.execute('INSERT INTO mf_ip_budgets VALUES(?,?,1) ON CONFLICT(day,ip_day_hash) DO UPDATE SET count=count+1',(day,iph))
            # A detail expired after 180 days is never recreated as a new installation.
            return {'event_id':row['event_id'] if row else body['event_id'],
                    'receipt':self.receipt(row) if row else None, 'duplicate':duplicate,
                    'detail_expired':row is None}

    def owns(self, event_id):
        with self.connect() as c:
            return bool(c.execute('SELECT 1 FROM mf_events WHERE event_id=?',(event_id,)).fetchone())

    def link(self, event_id, receipt, uid):
        if not identity(event_id) or not isinstance(receipt,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',receipt):
            raise Invalid('invalid_receipt')
        if not isinstance(uid,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',uid):
            raise Invalid('server_account_required')
        at = int(self.clock())
        with self.connect(True) as c:
            row = c.execute('SELECT * FROM mf_events WHERE event_id=?',(event_id,)).fetchone()
            if not row or not hmac.compare_digest(self.receipt(row),receipt):
                raise Invalid('invalid_receipt')
            if row['user_id'] and row['user_id'] != uid:
                raise Conflict('already_linked')
            if not row['user_id']:
                c.execute('UPDATE mf_events SET user_id=?,linked_at=? WHERE event_id=?',(uid,at,event_id))
            c.execute('INSERT OR IGNORE INTO mf_bindings VALUES(?,?,?,?,?,?,?)',
                      (uid,row['skill_id'],row['channel'],row['installation_id'],row['machine_id'],row['is_test'],at))
        return {'event_id':event_id,'linked':True}

    def page(self, visit_id, kind, skill, channel, ip, uid=None, is_test=False):
        """Only called after the existing page handler has returned success."""
        if kind not in ('registration','recharge') or skill not in self.skills or channel not in CHANNELS:
            raise Invalid('invalid_page')
        if not isinstance(visit_id,str) or not re.fullmatch(r'[0-9a-f]{32}',visit_id) or type(is_test) is not bool:
            raise Invalid('invalid_visit_id')
        if kind=='registration' and uid is not None or kind=='recharge' and not uid:
            raise Invalid('page_identity_mismatch')
        at=int(self.clock()); _,iph=self.ip_hash(ip,at)
        key=self.digest('page:'+':'.join((skill,channel,kind,visit_id)))
        with self.connect(True) as c:
            c.execute('INSERT OR IGNORE INTO mf_pages VALUES(?,?,?,?,?,?,?,?)',
                      (key,kind,skill,channel,iph,uid,int(is_test),at))
            if kind=='registration':
                c.execute('INSERT OR IGNORE INTO mf_visitors VALUES(?,?,?)',(iph,int(is_test),at))

    def purge(self):
        cutoff=int(self.clock())-180*DAY
        with self.connect(True) as c:
            c.execute('DELETE FROM mf_events WHERE occurred_at<?',(cutoff,))
            c.execute('DELETE FROM mf_pages WHERE occurred_at<?',(cutoff,))
            c.execute('DELETE FROM mf_visitors WHERE first_at<?',(cutoff,))
            c.execute('DELETE FROM mf_ip_budgets WHERE day<?',
                      ((datetime.fromtimestamp(self.clock(),TZ).date()-timedelta(days=2)).isoformat(),))

    def report(self, start, end, shared_db, skill='', is_test=False):
        low,high=window(start,end)
        if skill and skill not in self.skills or type(is_test) is not bool:
            raise Invalid('invalid_filter')
        clauses='is_test=?'+(' AND skill_id=?' if skill else '')
        args=[int(is_test)]+([skill] if skill else [])
        with self.connect() as c:
            installations=[dict(r) for r in c.execute('SELECT * FROM mf_installations WHERE '+clauses,args)]
            machines={r['machine_id']:r['first_at'] for r in c.execute('SELECT * FROM mf_machines WHERE is_test=?',(int(is_test),))}
            events=[dict(r) for r in c.execute('SELECT event_id,machine_id,skill_id,channel,occurred_at FROM mf_events WHERE '+clauses+' AND occurred_at>=? AND occurred_at<?',args+[low,high])]
            pages=[dict(r) for r in c.execute('SELECT * FROM mf_pages WHERE '+clauses+' AND occurred_at>=? AND occurred_at<?',args+[low,high])]
            bindings=[dict(r) for r in c.execute('SELECT * FROM mf_bindings WHERE '+clauses,args)]
            visitors={r['ip_day_hash']:r['first_at'] for r in c.execute('SELECT * FROM mf_visitors WHERE is_test=?',(int(is_test),))}
        l0={}
        for event in sorted(events,key=lambda e:(e['occurred_at'],e['event_id'])):
            if low<=machines[event['machine_id']]<high:
                l0.setdefault(event['machine_id'],{k:event[k] for k in ('event_id','skill_id','channel','occurred_at')})
        l1={}
        for p in pages:
            if p['kind']=='registration' and p['user_id'] is None and low<=visitors.get(p['ip_day_hash'],-1)<high:
                l1.setdefault(p['ip_day_hash'],{k:p[k] for k in ('visit_id','skill_id','channel','occurred_at')})
        details={'L0':list(l0.values()),'L1':list(l1.values())}
        counts={'L0':len(l0),'L1':len(l1),'L2':None,'L3':None,'L4':None}
        fresh=[x for x in installations if low<=x['first_at']<high]
        metrics={'skill_enabled':{'new_device':sum(low<=machines[x['machine_id']]<high for x in fresh),'old_device':sum(machines[x['machine_id']]<low for x in fresh)},'skill_activated':None,'recharges':None,'anonymous_page_views':sum(p['kind']=='registration' and p['user_id'] is None for p in pages)}
        gaps=[]
        try:
            created,credits=self.business(shared_db)
            new={u for u,at in created.items() if low<=at<high}
            first_link={}
            for binding in bindings:
                uid=binding['user_id'];first_link[uid]=min(first_link.get(uid,binding['first_at']),binding['first_at'])
            l2={u for u,at in first_link.items() if u in new and low<=at<high}
            l3={p['user_id'] for p in pages if p['kind']=='recharge' and p['user_id'] in new}
            first_paid={}
            for credit in credits:
                uid=credit['user_id'];first_paid[uid]=min(first_paid.get(uid,credit['at']),credit['at'])
            cohort=set(first_link)
            l4={u for u,at in first_paid.items() if u in new and u in cohort and low<=at<high}
            for label,users in [('L2',l2),('L3',l3),('L4',l4)]:
                counts[label]=len(users);details[label]=[{'user_id':u} for u in sorted(users)]
            activated=[b for b in bindings if low<=b['first_at']<high]
            metrics['skill_activated']={'new_account':sum(b['user_id'] in new for b in activated),'old_account':sum(b['user_id'] in created and created[b['user_id']]<low for b in activated),'unknown_account_age':sum(b['user_id'] not in created for b in activated)}
            # Credits are associated common-wallet credits, not attributed Skill revenue.
            relevant=[r for r in credits if low<=r['at']<high and r['user_id'] in cohort]
            metrics['recharges']={}
            for credit in relevant:
                key=credit['channel'];metrics['recharges'][key]=metrics['recharges'].get(key,0)+1
            if any(b['user_id'] not in created for b in bindings):
                gaps.append('Some legacy account creation dates are unavailable; never infer them from first use.')
        except (sqlite3.Error,OSError,LookupError) as exc:
            gaps.append('business_projection_unavailable:'+type(exc).__name__)
        return {'contract':CONTRACT,'start':start,'end':end,'timezone':'Asia/Shanghai',
                'is_test':is_test,'skill_id':skill,'steps':counts,'metrics':metrics,'details':details,
                'data_gaps':gaps,'definitions':{'L1':'Daily-salted anonymous-IP visitors, not lifetime people.',
                'L4':'First common-wallet credit of new linked accounts; not Skill-attributed revenue.',
                'cross_day':'Use >=7-day windows; daily cohorts undercount later payment.',
                'retention':'Details 180 days; HMAC first-seen/deduplication indexes retain identity history.'}}

    @staticmethod
    def business(path):
        """Read source-proven users/ledger/member_orders; never use balance as revenue."""
        p=Path(path)
        if p.is_symlink():
            raise LookupError('symlink_business_database')
        c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True,timeout=.2)
        c.row_factory=sqlite3.Row
        deadline=time.monotonic()+2
        c.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
        try:
            c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
            created={r[0]:r[1] for r in c.execute("SELECT user_id,min(created) FROM ledger WHERE kind='account_created' GROUP BY user_id")}
            # Source membership.py/manual_payments.py uses order id as ledger.job_id.
            paid=[dict(r) for r in c.execute("SELECT id,user_id,paid_at,provider FROM member_orders WHERE status='paid' AND paid_at IS NOT NULL")]
            if len(paid)>100000:
                raise LookupError('projection_budget_exceeded')
            paid_ids={r['id'] for r in paid}
            order_ids={r[0] for r in c.execute('SELECT id FROM member_orders')}
            credits=[{'key':'order:'+r['id'],'user_id':r['user_id'],'at':r['paid_at'],'channel':r['provider'] or 'unknown'} for r in paid]
            for r in c.execute("SELECT id,user_id,job_id,created,kind FROM ledger WHERE amount>0 AND kind IN ('paid_topup','manual_verified_topup')"):
                if r['job_id'] in paid_ids:
                    continue
                if r['job_id'] in order_ids:
                    raise LookupError('credit_order_state_conflict')
                credits.append({'key':'ledger:'+str(r['id']),'user_id':r['user_id'],'at':r['created'],'channel':r['kind']})
                if len(credits)>100000:
                    raise LookupError('projection_budget_exceeded')
            return created,credits
        finally:
            c.close()
