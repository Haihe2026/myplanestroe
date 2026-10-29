import runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.39','/opt/skill-platform/member-0.10.17/ops-extension','/opt/skill-platform/member-0.10.14/ops-extension']
import enterprise_ops,trade_ops
import trade_receipts
trade_receipts.install()
previous=enterprise_ops.extend_handler
def extended(original,db):return trade_ops.extend(previous(original,db),db)
enterprise_ops.extend_handler=extended
runpy.run_path('/opt/skill-platform/member-0.10.39/run_ops.py',run_name='__main__')
