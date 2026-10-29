"""Independent stdlib-only creation guard around the previous four launchers.

Used for deployment fallback, never a bare old-provider restart. Local historical
GET results, original auth/billing handlers and newer-resource recovery survive.
"""
from pathlib import Path
import os,runpy,sys,http.client
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
mode=os.environ.get('NEW_ONLY_LEGACY_SERVICE','shared')
sys.path.append('/usr/lib64/python3.11/site-packages')
try:del os.environ['IMAGE_PROVIDER_KEY']
except KeyError:pass
previous_request=http.client.HTTPConnection.putrequest
def request(self,method,url,*a,**kw):
    p=urlsplit(url);host=p.hostname or str(self.host).lower().split(':')[0]
    if host=='file.hfsyapi.cn' or p.path.startswith('/v1/images') and host!='www.aisplice.store':
        raise RuntimeError('Historical image transport disabled')
    return previous_request(self,method,url,*a,**kw)
http.client.HTTPConnection.putrequest=request
def blocked(path):return path.endswith(('/jobs','/skill-jobs','/render-jobs','/v1/images/generations'))
def guard(parent):
    class Handler(parent):
        def run_request(self):
            if self.command=='POST' and blocked(urlsplit(self.path).path):return self.send(503,dict(error='图片服务暂不可用，请保留原任务'))
            return super().run_request()
        do_GET=run_request
        do_POST=run_request
    return Handler
def disable(module):
    if not hasattr(module,'Provider'):return
    cls=module.Provider
    def init(self,*a,**kw):self.ready=False;self.edit_ready=False;self.last_usage=None
    cls.__init__=init
    cls.ready=property(lambda self:False,lambda self,v:None)
    cls.edit_ready=property(lambda self:False,lambda self,v:None)
    def stopped(*a,**kw):raise RuntimeError('Image creation paused')
    cls.__call__=cls.generate=cls.edit=stopped
def health(core):
    old=core.handler
    def handler(store):
        parent=old(store)
        class Handler(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None,download=None):
                paths=('/platform-api/gemini/health','/platform-api/temu/health') if mode=='shared' else ('/health','/temu/health','/quota-pack/gemini/health')
                if status==200 and urlsplit(self.path).path in paths and isinstance(result,dict):
                    result=dict(result,provider_configured=False,reference_editing=False,image_resource_contract='all-new-resource-v1',creation_paused=True)
                    if 'image_engines' in result:result['image_engines']={k:dict({field:value for field,value in v.items() if field!='model'},configured=False) for k,v in result['image_engines'].items()}
                return super().send(status,result,mime,cookie,download)
        return Handler
    core.handler=handler
if mode=='shared':
    sys.path[:0]=['/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.24','/opt/skill-platform/member-0.10.57','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/ops']
    import permanent_plans,install_pricing
    install_pricing.install()
    import server,sunburst,telemetry,temu_delivery
    disable(server);disable(sunburst);health(server)
    temu_delivery.Delivery.process_one=lambda self:False
    old_public=temu_delivery.Delivery.public
    def queue_public(self,row):
        result=old_public(self,row)
        return dict(result,status='pending',phase='needs_review',notice='原任务需要核对，请勿重新提交') if row['state'] in ('queued','running') and not row['job_id'] else result
    temu_delivery.Delivery.public=queue_public
    previous=telemetry.observed_handler
    def observed(parent,store,product,event_db):return guard(previous(parent,store,product,event_db))
    telemetry.observed_handler=observed
    old='/opt/skill-platform/member-0.10.59-child-photo/run_shared.py'
else:
    if mode not in ('legacy-gemini','legacy-temu','pack'):raise RuntimeError('Unknown service mode')
    if mode=='legacy-gemini':
        sys.path.insert(0,'/opt/skill-platform/legacy-permanent-0.10.9-r2');import api_access
    sys.path.insert(0,'/opt/skill-platform/member-0.5.0/service' if mode!='pack' else '/opt/skill-platform/1.7.0/service')
    source=sys.argv[sys.argv.index('--source')+1];sys.path.insert(0,source)
    import server
    core=server.pilot if mode=='legacy-temu' else server
    disable(core);health(core)
    previous=server.handler
    server.handler=lambda store:guard(previous(store))
    old={'legacy-gemini':'/opt/skill-platform/legacy-permanent-0.10.9-r2/run_legacy.py','legacy-temu':'/opt/skill-platform/member-0.5.0/service/run_legacy.py','pack':'/opt/skill-platform/1.7.0/service/run_pack.py'}[mode]
if not Path(old).is_file():raise RuntimeError('Prior guarded entry missing')
runpy.run_path(old,run_name='__main__')
