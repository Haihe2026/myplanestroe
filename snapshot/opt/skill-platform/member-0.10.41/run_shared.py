"""0.10.41 wraps deployed 0.10.39; 0.10.40 remains reserved."""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.39','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops']
import trade_receipts
trade_receipts.install()
import telemetry,trade_gateway
previous=telemetry.observed_handler
def observed(parent,store,product,event_db):return trade_gateway.install(store,previous(parent,store,product,event_db))
telemetry.observed_handler=observed
runpy.run_path('/opt/skill-platform/member-0.10.39/run_shared.py',run_name='__main__')
