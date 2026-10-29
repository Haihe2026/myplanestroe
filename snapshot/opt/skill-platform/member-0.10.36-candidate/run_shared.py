from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.34-candidate','/opt/skill-platform/member-0.10.32-r2','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops']
sys.path.append('/usr/lib64/python3.11/site-packages')
import server,shared_platform,account_gateway
# The legacy launcher imports handler before Store construction. Wrap its final class
# through the existing telemetry factory, preserving every earlier middleware.
import telemetry
original_observer=telemetry.observed_handler
def observed(parent,store,product,event_db):
 outer=account_gateway.install(server,shared_platform,parent)(store)
 return original_observer(outer,store,product,event_db)
telemetry.observed_handler=observed
runpy.run_path('/opt/skill-platform/member-0.10.35-r2/run_shared.py',run_name='__main__')
