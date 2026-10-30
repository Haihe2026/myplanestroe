"""Authenticated, query-only account listing. Never enroll, expire or grant funds."""
from pathlib import Path
import json,sqlite3,time,os
from contextlib import closing
from urllib.parse import urlsplit,parse_qs

ROOT=Path(__file__).resolve().parent
def connect(path):
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
    c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');return c
def exists(c,name):return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone() is not None

class Directory:
    def __init__(self,path,legacy=None):self.path,self.legacy=path,legacy or {}
    def listing(self,page=1,query=''):
        if type(page)is not int or not 1<=page<=100000 or not isinstance(query,str) or len(query)>64:raise ValueError('invalid query')
        from journey.report import Report
        projection=Report(None,self.path,self.legacy)
        now=int(time.time());size=25;rows=[]
        pattern='%'+query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        with closing(connect(self.path)) as c:
            c.execute('ATTACH DATABASE ? AS dialogue', (Path(os.environ.get('FIRST_DIALOGUES_DB','/var/lib/skill-monitor/first-dialogues.sqlite3')).resolve().as_uri()+'?mode=ro',))
            c.execute('BEGIN')
            sources=[]
            if exists(c,'ledger'):sources.append("SELECT user_id,min(created) stamp,'account_created' basis,1 priority FROM ledger WHERE kind='account_created' GROUP BY user_id")
            if exists(c,'trial_claims'):sources.append("SELECT user_id,min(created) stamp,'credential_registered' basis,2 priority FROM trial_claims GROUP BY user_id")
            if exists(c,'trade_tokens'):sources.append("SELECT account_id user_id,min(created) stamp,'trade_account_linked' basis,3 priority FROM trade_tokens GROUP BY account_id")
            if exists(c,'pet_accounts'):sources.append("SELECT user_id,created stamp,'pet_enrolled' basis,4 priority FROM pet_accounts")
            if not sources:sources=["SELECT id user_id,NULL stamp,'unknown' basis,9 priority FROM users WHERE 0"]
            cte='WITH observations AS ('+' UNION ALL '.join(sources)+'''), ranked AS (
              SELECT *,row_number() OVER(PARTITION BY user_id ORDER BY priority,stamp) rn FROM observations
            ) '''
            # Unified pagination happens before quota projection. Read all retained
            # first-interaction metadata; never fabricate registrations or conversation text.
            cte += """, firsts AS (
              SELECT *,row_number() OVER(PARTITION BY user_id ORDER BY received_at,event_id) pos
              FROM dialogue.first_dialogues WHERE is_test=0 AND user_id IS NOT NULL
            ), entries AS (
              SELECT u.id,r.stamp,r.basis,f.event_id,coalesce(f.received_at,r.stamp) observed_at,0 anonymous
              FROM users u LEFT JOIN ranked r ON r.user_id=u.id AND r.rn=1
              LEFT JOIN firsts f ON f.user_id=u.id AND f.pos=1
              WHERE u.id LIKE ? ESCAPE '\\'
              UNION ALL
              SELECT f.event_id,NULL,'first_interaction',f.event_id,f.received_at,1
              FROM dialogue.first_dialogues f WHERE f.is_test=0
              AND NOT EXISTS(SELECT 1 FROM users u WHERE u.id=f.user_id)
              AND (f.event_id LIKE ? ESCAPE '\\' OR f.skill_name LIKE ? ESCAPE '\\')
            ) """
            params=(pattern,pattern,pattern)
            total=c.execute(cte+'SELECT count(*) FROM entries',params).fetchone()[0]
            records=c.execute(cte+'SELECT * FROM entries ORDER BY (observed_at IS NULL),observed_at DESC,anonymous,id LIMIT ? OFFSET ?',params+(size,(page-1)*size)).fetchall()
            for r in records:
                uid=r['id'];first=None
                if r['event_id']:
                    f=c.execute('SELECT event_id,skill_id,skill_name,skill_version,channel,received_at,client_occurred_at FROM dialogue.first_dialogues WHERE event_id=?',(r['event_id'],)).fetchone()
                    first=dict(f) if f else None
                if r['anonymous']:
                    rows.append(dict(id=uid,record_type='interaction',event_id=r['event_id'],observed_at=r['observed_at'],first_dialogue=first));continue
                item=dict(id=uid,record_type='account',observed_at=r['observed_at'],first_dialogue=first,registered_at=r['stamp'],registration_basis=r['basis'] or 'unknown',image=None,pet=None,trade=None,missing=[])
                try:item['image']=projection.quota(c,uid,now)
                except (sqlite3.Error,KeyError,TypeError):item['missing'].append('image_quota_unavailable')
                if exists(c,'pet_accounts'):
                    a=c.execute('SELECT trial_photos FROM pet_accounts WHERE user_id=?',(uid,)).fetchone()
                    if a:
                        try:
                            grants=c.execute('SELECT plan,snapshot,remaining,expires FROM pet_grants WHERE user_id=? AND starts<=? AND expires>?',(uid,now,now)).fetchall()
                            plans=[json.loads(g['snapshot']) for g in grants]
                            paid=c.execute('SELECT 1 FROM pet_grants WHERE user_id=?',(uid,)).fetchone() is not None
                            cap=-1 if any(p['pet_profiles']==-1 for p in plans) else max([p['pet_profiles'] for p in plans],default=0)
                            item['pet']=dict(plan_ids=[g['plan'] for g in grants],expires_at=max([g['expires'] for g in grants],default=None),photo_remaining=sum(g['remaining'] for g in grants),trial_photo_remaining=0 if paid else a[0],profiles_used=c.execute('SELECT count(*) FROM pet_profiles WHERE user_id=?',(uid,)).fetchone()[0],profiles_limit=cap)
                        except (sqlite3.Error,KeyError,TypeError,ValueError):item['missing'].append('pet_quota_unavailable')
                if exists(c,'trade_wallets'):
                    wallet=c.execute('SELECT balance_fen,reserved_fen FROM trade_wallets WHERE account_id=?',(uid,)).fetchone()
                    if wallet:item['trade']=dict(balance_fen=wallet[0],reserved_fen=wallet[1],available_fen=wallet[0]-wallet[1])
                rows.append(item)
        return dict(users=rows,total=total,page=page,page_size=size,generated_at=now,scope='accounts_and_first_interactions_not_unique_people',ordering='first_received_or_registration_desc_unknown_last')
