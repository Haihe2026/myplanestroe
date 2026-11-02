from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
OLD='/opt/skill-platform/grok-video-0.1.3/run_paid.py'
if not Path(OLD).is_file():raise RuntimeError('Actual prior shared entry missing')
sys.path[:0]=[str(ROOT),'/opt/skill-platform/grok-video-0.1.3','/opt/skill-platform/grok-video-0.1.2','/opt/skill-platform/grok-video-0.1.0','/opt/skill-platform/member-0.10.16','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/ops']
import server,entry_fix,listing_gateway,listing_receipts
listing_receipts.install()
previous=entry_fix.wrap
def wrap(parent,store,server):return listing_gateway.wrap(previous(parent,store,server),store,server)
entry_fix.wrap=wrap
runpy.run_path(OLD,run_name='__main__')
