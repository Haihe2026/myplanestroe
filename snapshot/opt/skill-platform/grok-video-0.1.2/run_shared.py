from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
OLD='/opt/skill-platform/grok-video-0.1.0/run_shared.py'
sys.path[:0]=[str(ROOT),'/opt/skill-platform/grok-video-0.1.0','/opt/skill-platform/member-0.10.16','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/ops']
import server,grok_gateway,entry_fix
previous=grok_gateway.wrap
def wrap(parent,store,product):return entry_fix.wrap(previous(parent,store,product),store,server)
grok_gateway.wrap=wrap
runpy.run_path(OLD,run_name='__main__')
