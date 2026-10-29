"""58 with a narrow independent child-creation block; no new-resource imports.

Used only after child async tasks have drained. Never restore bare 58: old child
clients could otherwise silently invoke the expensive legacy provider again.
"""
from pathlib import Path
import runpy,sys
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
OLD='/opt/skill-platform/member-0.10.58/run_shared.py'
if not Path(OLD).is_file():raise RuntimeError('Original entry missing')
sys.path[:0]=['/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.14/ops','/opt/skill-platform/member-0.10.14/core']
import permanent_plans,install_pricing
install_pricing.install()
import telemetry,server
original_http=server.handler
def health_handler(store):
    parent=original_http(store)
    class Handler(parent):
        def send(self,status,result,mime='application/json; charset=utf-8',cookie=None,download=None):
            if (status==200 and isinstance(result,dict) and urlsplit(self.path).path=='/platform-api/gemini/health'
                    and self.headers.get('X-Skill-Source')=='jyai-baby-growth-album'):
                engines=dict(result.get('image_engines',{}))
                engines['gemini-personal-sunburst']=dict(configured=False,reference_editing=True,text_to_image=True,
                    contract='child-photo-resource-v1',paused=True)
                result=dict(result,image_engines=engines)
            return super().send(status,result,mime,cookie,download)
    return Handler
server.handler=health_handler
previous=telemetry.observed_handler
def observed(parent,store,product,event_db):
    inner=previous(parent,store,product,event_db)
    class Handler(inner):
        def run_request(self):
            if (self.command=='POST' and self.headers.get('X-Skill-Source')=='jyai-baby-growth-album'
                    and urlsplit(self.path).path in ('/platform-api/gemini/jobs','/platform-api/gemini/skill-jobs')):
                return self.send(503,dict(error='图片服务暂不可用，方案已保留，请稍后继续'))
            return super().run_request()
        do_GET=run_request
        do_POST=run_request
    return Handler
telemetry.observed_handler=observed
runpy.run_path(OLD,run_name='__main__')
