"""Read-only journey metadata. Original administrator authentication is retained."""
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from contextlib import closing
import os,sqlite3,uuid
from overview_data import overview
from unified_users import Directory
ROOT=Path(__file__).resolve().parent
def read_connection(path):
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=4)
    c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');return c
def activity(path,uid):
    out=[];missing=[];truncated=False
    queries=[
      ('pet_orders','pet','SELECT id,created,paid_at,status,amount_fen FROM pet_orders WHERE user_id=? ORDER BY created DESC LIMIT 201','orders'),
      ('pet_audit','pet','SELECT id,kind,reference,created FROM pet_audit WHERE user_id=? ORDER BY created DESC LIMIT 201','audit'),
      ('trade_orders','trade-leads','SELECT id,created,paid_at,status,amount_fen FROM trade_orders WHERE account_id=? ORDER BY created DESC LIMIT 201','orders'),
      ('wechat_identities','account','SELECT created FROM wechat_identities WHERE user_id=?','wechat_bound'),
    ]
    with closing(read_connection(path)) as c:
        c.execute('BEGIN')
        for table,product,sql,kind in queries:
            if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():continue
            try:
                rows=c.execute(sql,(uid,)).fetchall();truncated=truncated or len(rows)>200
                out.extend(dict(product=product,record_type=kind,**dict(r)) for r in rows[:200])
            except sqlite3.Error:missing.append(product+':'+kind)
    return dict(items=out,missing=missing,truncated=truncated)

def anonymous(path,event_id):
    if str(uuid.UUID(event_id))!=event_id:raise ValueError('Invalid event')
    with closing(read_connection(path)) as c:
        r=c.execute('SELECT event_id,skill_id,skill_name,skill_version,channel,received_at,client_occurred_at,user_id,linked_at FROM first_dialogues WHERE event_id=? AND is_test=0',(event_id,)).fetchone()
    return dict(r) if r else None

def extend(factory,shared_path):
    def build(*args,**kwargs):
        parent=factory(*args,**kwargs)
        report=args[0] if args else kwargs.get('report')
        directory=Directory(shared_path,getattr(report,'products',{}) or {})
        class Handler(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
                if status==200 and mime.startswith('text/html') and isinstance(result,bytes):
                    result=result.replace(b'</head>',b'<link rel="stylesheet" href="/ops/user-journey.css?v=20261028"><script defer src="/ops/user-journey.js?v=20261028"></script></head>',1)
                    result=result.replace(b'</head>',b'<link rel="stylesheet" href="/membership/admin-overview/overview.css?v=20261029"><script defer src="/membership/admin-overview/overview.js?v=20261029"></script></head>',1)
                if status==200 and urlsplit(self.path).path=='/ops/api/journey-v2/user' and isinstance(result,dict) and result.get('id'):
                    try:result=dict(result,additional_activity=activity(shared_path,result['id']))
                    except (sqlite3.Error,OSError):result=dict(result,additional_activity=dict(items=[],unavailable=True))
                return super().send(status,result,mime,cookie=cookie)
            def do_GET(self):
                u=urlsplit(self.path)
                if u.path in ('/ops/user-journey.js','/ops/user-journey.css'):
                    p=ROOT/u.path.rsplit('/',1)[-1];mime='application/javascript' if p.suffix=='.js' else 'text/css'
                    return self.send(200,p.read_bytes(),mime+'; charset=utf-8')
                if u.path=='/ops/api/users-activity':
                    if not self.authenticated():return self.send(401,dict(error='ops_login_required'))
                    try:
                        q=parse_qs(u.query)
                        return self.send(200,directory.listing(int(q.get('page',['1'])[0]),q.get('q',[''])[0]))
                    except (ValueError,TypeError):return self.send(400,dict(error='invalid_query'))
                    except (sqlite3.Error,OSError):return self.send(503,dict(error='users_activity_unavailable'))
                if u.path=='/ops/api/workspace-overview':
                    if not self.authenticated():return self.send(401,dict(error='ops_login_required'))
                    try:return self.send(200,overview(shared_path,int(parse_qs(u.query).get('days',['14'])[0])))
                    except (ValueError,TypeError):return self.send(400,dict(error='invalid_days'))
                    except (sqlite3.Error,OSError):return self.send(503,dict(error='overview_unavailable'))
                if u.path!='/ops/api/user-journey/anonymous':return super().do_GET()
                if not self.authenticated():return self.send(401,dict(error='ops_login_required'))
                try:
                    event_id=parse_qs(u.query).get('event_id',[''])[0]
                    item=anonymous(os.environ.get('FIRST_DIALOGUES_DB','/var/lib/skill-monitor/first-dialogues.sqlite3'),event_id)
                    return self.send(200,dict(item=item)) if item else self.send(404,dict(error='event_not_found'))
                except (ValueError,TypeError):return self.send(400,dict(error='invalid_event_id'))
                except (sqlite3.Error,OSError):return self.send(503,dict(error='journey_data_unavailable'))
        return Handler
    return build
