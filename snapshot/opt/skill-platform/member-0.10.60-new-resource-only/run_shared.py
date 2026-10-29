from pathlib import Path
import runpy,sys,inspect,textwrap
ROOT=Path(__file__).resolve().parent
OLD='/opt/skill-platform/member-0.10.59-child-photo/run_shared.py'
if not Path(OLD).is_file():raise RuntimeError('Actual 59 child entry missing')
sys.path.append('/usr/lib64/python3.11/site-packages')
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.59-child-photo','/opt/skill-platform/member-0.10.57','/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.24','/opt/skill-platform/member-0.10.16','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/ops']
import permanent_plans,install_pricing
install_pricing.install()
import server,sunburst,telemetry,new_only,temu_delivery,expert_service
new_only.deny_old_transport()
new_only.disable_old_constructor(server,'shared')
new_only.disable_old_constructor(sunburst,'shared')
new_only.health_writer(server,'shared')
# New queue rows carry this route for every real source/channel. Old queued rows
# retain their identity and wait for review instead of changing provider route.
expert_service.select_route=lambda source,channel:new_only.ROUTE
temu_delivery.Delivery.ready=lambda self:new_only.Provider('shared').ready
source=textwrap.dedent(inspect.getsource(temu_delivery.Delivery.process_one))
anchor="WHERE state='queued' ORDER BY created,id LIMIT 1"
if source.count(anchor)!=1:raise RuntimeError('Queue baseline changed')
source=source.replace(anchor,"WHERE state='queued' AND provider_route='all-new-resource-v1' ORDER BY created,id LIMIT 1")
space={};exec(compile(source,__file__+':queue','exec'),temu_delivery.__dict__,space)
new_process=space['process_one']
def process_one(self):return new_process(self) if new_only.enabled() else False
temu_delivery.Delivery.process_one=process_one
old_public=temu_delivery.Delivery.public
def queue_public(self,row):
    result=old_public(self,row)
    if row['provider_route']!=new_only.ROUTE and row['state'] in ('queued','running') and not row['job_id']:
        result=dict(result,status='pending',phase='needs_review',notice='原任务需要核对，请勿重新提交；不会更换资源重复制作')
    return result
temu_delivery.Delivery.public=queue_public
previous=telemetry.observed_handler
def observed(parent,store,product,event_db):
    inner=previous(parent,store,product,event_db)
    return new_only.shared_handler(inner,store,server)
telemetry.observed_handler=observed
runpy.run_path(OLD,run_name='__main__')
