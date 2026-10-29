from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/ops-extension','/opt/skill-platform/member-0.10.55']
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.14/core']
import permanent_plans,install_pricing
install_pricing.install()
import enterprise_ops,dialogue_ops,resource_ops,users_ops
resource_ops.BUILD='0.10.58'
previous=enterprise_ops.extend_handler
def extended(original,db):return dialogue_ops.extend(previous(original,db))
enterprise_ops.extend_handler=extended
runpy.run_path('/opt/skill-platform/member-0.10.56/run_ops.py',run_name='__main__')
