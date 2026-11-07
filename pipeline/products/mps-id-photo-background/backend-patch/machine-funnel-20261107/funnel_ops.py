"""Read-only endpoints guarded by the existing administrator session check."""
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from machine_funnel import Invalid
import sqlite3


def extend(factory,funnel,shared_db):
    def build(*args,**kwargs):
        parent=factory(*args,**kwargs)
        class Handler(parent):
            def do_GET(self):
                path=urlsplit(self.path).path
                if path not in ('/ops/api/machine-funnel','/ops/machine-funnel'):
                    return super().do_GET()
                if not self.authenticated():
                    return self.send(401,{'error':'ops_login_required'})
                if path=='/ops/machine-funnel':
                    return self.send(200,Path(__file__).with_name('machine-funnel.html').read_bytes(),'text/html; charset=utf-8')
                try:
                    q=parse_qs(urlsplit(self.path).query,keep_blank_values=True)
                    if set(q)-{'start','end','skill_id','step','page','is_test'} or any(len(v)!=1 for v in q.values()):
                        raise Invalid('invalid_query')
                    get=lambda key,default='':q.get(key,[default])[0]
                    if get('is_test','false') not in ('true','false'):
                        raise Invalid('invalid_test_filter')
                    report=funnel.report(get('start'),get('end'),shared_db,get('skill_id'),get('is_test','false')=='true')
                    step=get('step');page=int(get('page','1'))
                    if step and step not in ('L0','L1','L2','L3','L4') or not 1<=page<=100000:
                        raise Invalid('invalid_detail_query')
                    if step:
                        rows=report.pop('details').get(step,[])
                        available=report['steps'][step] is not None
                        report.update(step=step,available=available,total=len(rows) if available else None,
                                      page=page,rows=rows[(page-1)*50:page*50])
                    else:
                        report.pop('details')
                    return self.send(200,report)
                except (Invalid,ValueError,TypeError):
                    return self.send(400,{'error':'invalid_funnel_query'})
                except (OSError,sqlite3.Error):
                    return self.send(503,{'error':'funnel_projection_unavailable'})
        return Handler
    return build
