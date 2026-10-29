"""Anonymous entry observations, not conversation counts or registered users.
No credential hashes, invitation IDs, customer content or client IPs are returned.
"""
from pathlib import Path
from contextlib import closing
from urllib.parse import urlsplit,parse_qs
import sqlite3,time
ROOT=Path(__file__).resolve().parent
class Arrivals:
 def __init__(self,path='/var/lib/skill-monitor/journey-0.10.16.db'):self.path=Path(path)
 def listing(self,days=7):
  if days not in (1,2,7,14,30,90):raise ValueError('invalid_days')
  now=int(time.time());since=now-days*86400
  with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=3)) as c:
   c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
   excluded=c.execute("SELECT count(*) FROM journey_invitations i JOIN journey_test_accounts t ON t.user_id=i.user_id WHERE i.created>=?",(since,)).fetchone()[0]
   where='i.created>=? AND NOT EXISTS(SELECT 1 FROM journey_test_accounts t WHERE t.user_id=i.user_id)'
   rows=[dict(r) for r in c.execute("SELECT date(i.created,'unixepoch','+8 hours') day,i.product,i.source,i.channel,count(*) entries,sum(i.user_id IS NULL) unlinked,sum(i.user_id IS NOT NULL) linked,count(DISTINCT i.user_id) linked_accounts FROM journey_invitations i WHERE "+where+" GROUP BY 1,2,3,4 ORDER BY 1 DESC,2,3,4",(since,))]
   totals=dict(c.execute('SELECT count(*) entries,coalesce(sum(i.user_id IS NULL),0) unlinked,coalesce(sum(i.user_id IS NOT NULL),0) linked,count(DISTINCT i.user_id) linked_accounts FROM journey_invitations i WHERE '+where,(since,)).fetchone())
   metadata=dict(c.execute('SELECT key,value FROM journey_meta'))
  return dict(rows=rows,totals=totals,excluded_marked_test_entries=excluded,generated_at=now,since=since,days=days,collection_started=int(metadata.get('collection_started',0)),scope='server_generated_entries_not_downloads_or_conversations',anonymous_unique_users=None)
def extend(factory,path):
 def build(*args,**kwargs):
  parent=factory(*args,**kwargs);arrival=Arrivals()
  class Handler(parent):
   def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
    if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=result.replace(b'</head>',b'<script defer src="/ops/first-use.js?v=0.10.46"></script></head>',1)
    return super().send(status,result,mime,cookie=cookie)
   def do_GET(self):
    u=urlsplit(self.path)
    if u.path=='/ops/first-use.js':return self.send(200,(ROOT/'first-use.js').read_bytes(),'application/javascript; charset=utf-8')
    if u.path!='/ops/api/first-use':return super().do_GET()
    if not self.authenticated():return self.send(401,{'error':'ops_login_required'})
    try:return self.send(200,arrival.listing(int(parse_qs(u.query).get('days',['7'])[0])))
    except (ValueError,TypeError):return self.send(400,{'error':'invalid_days'})
    except (OSError,sqlite3.Error):return self.send(503,{'error':'first_use_data_unavailable'})
  return Handler
 return build
