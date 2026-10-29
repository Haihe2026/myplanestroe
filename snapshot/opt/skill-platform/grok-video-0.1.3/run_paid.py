from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/grok-video-0.1.2','/opt/skill-platform/grok-video-0.1.0','/opt/skill-platform/member-0.10.16','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/ops']
import server,entry_fix,paid_gateway
previous=entry_fix.wrap
def wrap(parent,store,core):return paid_gateway.wrap(previous(parent,store,core),store,core)
entry_fix.wrap=wrap
runpy.run_path('/opt/skill-platform/grok-video-0.1.2/run_shared.py',run_name='__main__')
