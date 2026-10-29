"""0.10.39 pet layer; 0.10.40 is reserved for account recovery."""
from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops']
from product_config import OLD_ENTRY
if not Path(OLD_ENTRY).is_file():raise RuntimeError('Required chain head missing: '+OLD_ENTRY)
import server,shared_platform,telemetry,pet_gateway
previous=telemetry.observed_handler
def observed(parent,store,product,event_db):
    final=previous(parent,store,product,event_db)
    return pet_gateway.install(store,server,shared_platform,final)
telemetry.observed_handler=observed
runpy.run_path(OLD_ENTRY,run_name='__main__')
