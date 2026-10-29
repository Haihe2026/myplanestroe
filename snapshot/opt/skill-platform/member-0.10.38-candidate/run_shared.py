from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops']
import server,telemetry,photo_consents
original=telemetry.observed_handler
def observed(parent,store,product,event_db):
 return original(photo_consents.wrap(parent,store,server),store,product,event_db)
telemetry.observed_handler=observed
runpy.run_path('/opt/skill-platform/member-0.10.36-candidate/run_shared.py',run_name='__main__')
