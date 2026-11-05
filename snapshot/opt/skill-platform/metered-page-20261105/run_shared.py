from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/listing-cny-0.4.0','/opt/skill-platform/grok-video-0.1.3','/opt/skill-platform/grok-video-0.1.0','/opt/skill-platform/member-0.10.16','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/service']
import listing_gateway,metered
previous=listing_gateway.wrap
def wrap(parent,store,server):return metered.install(previous(parent,store,server),store,server)
listing_gateway.wrap=wrap
import listing_trial_gate
runpy.run_path('/opt/skill-platform/provider-costs-20261105/run_shared.py',run_name='__main__')
