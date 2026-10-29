from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/ops']
sys.path[:0]=['/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.14/core']
import permanent_plans,install_pricing
install_pricing.install()
import telemetry,dialogue_gateway
previous=telemetry.observed_handler
def observed(parent,store,product,event_db):return dialogue_gateway.install(previous(parent,store,product,event_db),store)
telemetry.observed_handler=observed
runpy.run_path('/opt/skill-platform/member-0.10.57/run_shared.py',run_name='__main__')
