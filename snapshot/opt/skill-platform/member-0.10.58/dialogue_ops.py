from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json
from dialogue_store import Dialogues,Invalid
ROOT=Path(__file__).resolve().parent
def extend(factory):
 def build(*a,**kw):
  parent=factory(*a,**kw);events=Dialogues()
  class Handler(parent):
   def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
    if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=result.replace(b'</head>',b'<script defer src="/ops/first-dialogues.js?v=0.10.58"></script></head>',1)
    if status==200 and urlsplit(self.path).path=='/ops/api/journey-v2/user' and isinstance(result,dict) and result.get('id'):
     try:result=dict(result,first_dialogues=events.for_user(result['id']))
     except Exception:result=dict(result,first_dialogues=[],first_dialogues_unavailable=True)
    if status==200 and urlsplit(self.path).path=='/ops/api/users-directory' and isinstance(result,dict):
     try:
      first=events.first_for_users([u['id'] for u in result.get('users',[])])
      result=dict(result,users=[dict(u,first_dialogue=first.get(u['id'])) for u in result.get('users',[])])
     except Exception:result=dict(result,users=[dict(u,first_dialogue=None,first_dialogue_unavailable=True) for u in result.get('users',[])])
    return super().send(status,result,mime,cookie=cookie)
   def do_GET(self):
    path=urlsplit(self.path).path
    assets={'/ops/first-dialogues.js':'first-dialogues.js','/ops/journey/panel.js':'panel.js'}
    if path in assets:return self.send(200,(ROOT/assets[path]).read_bytes(),'application/javascript; charset=utf-8')
    if path!='/ops/api/first-dialogues':return super().do_GET()
    if not self.authenticated():return self.send(401,dict(error='ops_login_required'))
    try:
     q=parse_qs(urlsplit(self.path).query);get=lambda k,default='':q.get(k,[default])[0]
     return self.send(200,events.listing(int(get('days','30')),int(get('page','1')),get('skill_id'),get('channel'),get('state')))
    except (Invalid,ValueError):return self.send(400,dict(error='invalid_query'))
    except Exception:return self.send(503,dict(error='first_dialogues_unavailable'))
  return Handler
 return build
