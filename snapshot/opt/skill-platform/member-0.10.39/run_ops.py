"""Optional companion to expose pet orders under unchanged persistent admin auth."""
import sys,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.17/ops-extension','/opt/skill-platform/member-0.10.14/ops-extension']
import enterprise_ops,pet_ops
old=enterprise_ops.extend_handler
def extended(original,db):return pet_ops.extend(old(original,db),db)
enterprise_ops.extend_handler=extended
runpy.run_path('/opt/skill-platform/member-0.10.17/ops-extension/run_ops.py',run_name='__main__')
