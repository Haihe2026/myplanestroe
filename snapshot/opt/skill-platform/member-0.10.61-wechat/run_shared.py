"""Only add WeChat identity binding over the deployed new-resource chain."""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.16','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/ops']
import telemetry,wechat_binding
previous=telemetry.observed_handler
def observed(parent,store,product,event_db):
    import server  # Let the existing chain load pricing/auth modules in its original order.
    return wechat_binding.handler(previous(parent,store,product,event_db),store,server)
telemetry.observed_handler=observed
runpy.run_path('/opt/skill-platform/member-0.10.60-new-resource-only/run_shared.py',run_name='__main__')
