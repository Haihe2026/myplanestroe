from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
OLD='/opt/skill-platform/member-0.10.61-wechat/run_shared.py'
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.59-child-photo','/opt/skill-platform/member-0.10.57','/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.24','/opt/skill-platform/member-0.10.16','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops']
sys.path.append('/usr/lib64/python3.11/site-packages')
import permanent_plans,install_pricing
install_pricing.install()
import telemetry
import grok_gateway
previous=telemetry.observed_handler
def observed(parent,store,product,event_db):
 return grok_gateway.wrap(previous(parent,store,product,event_db),store,product)
telemetry.observed_handler=observed
runpy.run_path(OLD,run_name='__main__')
