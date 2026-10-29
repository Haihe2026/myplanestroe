"""Read-only account directory; preserve the full 0.10.41 admin/auth chain."""
from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/ops-extension']
import enterprise_ops,users_ops
previous=enterprise_ops.extend_handler
def extended(original,db):return users_ops.extend(previous(original,db),db)
enterprise_ops.extend_handler=extended
runpy.run_path('/opt/skill-platform/member-0.10.41/run_ops.py',run_name='__main__')
