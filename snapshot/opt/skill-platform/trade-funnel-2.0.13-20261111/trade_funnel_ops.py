"""Authenticated read-only aggregates and existing journey augmentation."""
import os
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from trade_funnel import Funnel,Invalid,query_window

ROOT=Path(__file__).resolve().parent
SUMMARY='/ops/api/trade-funnel'
ITEMS=SUMMARY+'/items'


def extend(factory,shared_path,make_funnel=None):
    def build(*args,**kwargs):
        parent=factory(*args,**kwargs)
        try:
            if make_funnel:funnel=make_funnel(shared_path)
            else:
                from dialogue_store import Dialogues
                old=Dialogues()
                funnel=Funnel(os.environ.get('TRADE_FUNNEL_DB','/var/lib/skill-monitor/trade-funnel.sqlite3'),old.key,dialogues=old,shared_path=shared_path)
        except Exception:funnel=None
        class Handler(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
                path=urlsplit(self.path).path
                if status==200 and mime.startswith('text/html') and isinstance(result,bytes) and path in ('/ops','/ops/'):
                    tag=b'<link rel="stylesheet" href="/ops/trade-funnel.css?v=20261111-2013"><script defer src="/ops/trade-funnel.js?v=20261111-2013"></script>'
                    if b'/ops/trade-funnel.js' not in result:result=result.replace(b'</head>',tag+b'</head>',1)
                if funnel is not None and status==200 and isinstance(result,dict):
                    try:
                        if path=='/ops/api/journey-v2/user' and result.get('id'):
                            result=dict(result,trade_funnel_activity=funnel.activity(uid=result['id']))
                        elif path=='/ops/api/user-journey/anonymous' and isinstance(result.get('item'),dict) and result['item'].get('event_id'):
                            result=dict(result,trade_funnel_activity=funnel.activity(event_id=result['item']['event_id']))
                    except Exception:result=dict(result,trade_funnel_activity=dict(unavailable=True,items=[]))
                return super().send(status,result,mime,cookie=cookie)

            def do_GET(self):
                path=urlsplit(self.path).path
                if path in ('/ops/trade-funnel.js','/ops/trade-funnel.css','/ops/user-journey.js'):
                    try:
                        filename=path.rsplit('/',1)[-1]
                        mime='application/javascript' if filename.endswith('.js') else 'text/css'
                        return self.send(200,(ROOT/filename).read_bytes(),mime+'; charset=utf-8')
                    except OSError:return self.send(404,dict(error='asset_not_found'))
                if path not in (SUMMARY,ITEMS):return super().do_GET()
                if not self.authenticated():return self.send(401,dict(error='ops_login_required'))
                if funnel is None:return self.send(503,dict(error='trade_funnel_unavailable'))
                try:
                    q=parse_qs(urlsplit(self.path).query,keep_blank_values=True)
                    if set(q)-{'since','until','days','stage','page','include_test'} or any(len(v)!=1 for v in q.values()):raise Invalid('invalid_query')
                    get=lambda key,default=None:q.get(key,[default])[0]
                    if get('include_test','0') not in ('0','1'):raise Invalid('invalid_test_filter')
                    include_test=get('include_test','0')=='1'
                    window=query_window(get('since'),get('until'),int(get('days','7')),funnel.clock())
                    result=funnel.items(window,get('stage'),int(get('page','1')),include_test) if path==ITEMS else funnel.summary(window,include_test)
                    return self.send(200,result)
                except (Invalid,ValueError,TypeError):return self.send(400,dict(error='invalid_funnel_query'))
                except Exception:return self.send(503,dict(error='trade_funnel_unavailable'))
        return Handler
    return build
