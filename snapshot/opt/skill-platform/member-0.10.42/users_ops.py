"""Authenticated, query-only account listing. Never enroll, expire or grant funds."""
from pathlib import Path
import json,sqlite3,time
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
            total=c.execute("SELECT count(*) FROM users WHERE id LIKE ? ESCAPE '\\'",(pattern,)).fetchone()[0]
            records=c.execute(cte+"SELECT u.id,r.stamp,r.basis FROM users u LEFT JOIN ranked r ON r.user_id=u.id AND r.rn=1 WHERE u.id LIKE ? ESCAPE '\\' ORDER BY (r.stamp IS NULL),r.stamp DESC,u.id LIMIT ? OFFSET ?",(pattern,size,(page-1)*size)).fetchall()
            for r in records:
                uid=r['id'];item=dict(id=uid,registered_at=r['stamp'],registration_basis=r['basis'] or 'unknown',image=None,pet=None,trade=None,missing=[])
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
        return dict(users=rows,total=total,page=page,page_size=size,generated_at=now,scope='all_shared_accounts_including_pet_and_trade',ordering='known_registration_or_first_record_desc_unknown_last')

def extend(factory,path):
    def build(*args,**kwargs):
        parent=factory(*args,**kwargs)
        report=args[0] if args else kwargs.get('report')
        directory=Directory(path,getattr(report,'products',{}) or {})
        class Handler(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
                if status==200 and mime.startswith('text/html') and isinstance(result,bytes):
                    result=result.replace(b'</head>',b'<link rel="stylesheet" href="/ops/users-directory.css?v=0.10.42"><script defer src="/ops/users-directory.js?v=0.10.42"></script></head>',1)
                return super().send(status,result,mime,cookie=cookie)
            def do_GET(self):
                u=urlsplit(self.path)
                if u.path in ('/ops/users-directory.js','/ops/users-directory.css'):
                    name=u.path.rsplit('/',1)[-1];mime='application/javascript' if name.endswith('.js') else 'text/css'
                    return self.send(200,(ROOT/name).read_bytes(),mime+'; charset=utf-8')
                if u.path!='/ops/api/users-directory':return super().do_GET()
                if not self.authenticated():return self.send(401,{'error':'ops_login_required'})
                try:
                    q=parse_qs(u.query);return self.send(200,directory.listing(int(q.get('page',['1'])[0]),q.get('q',[''])[0]))
                except ValueError:return self.send(400,{'error':'invalid_query'})
                except Exception:return self.send(503,{'error':'users_directory_unavailable'})
        return Handler
    return build
