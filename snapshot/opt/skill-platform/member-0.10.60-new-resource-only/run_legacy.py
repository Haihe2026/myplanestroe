"""Preserve each exact legacy launcher/ledger, replace provider at handler boundary."""
from pathlib import Path
import os,runpy,sys
ROOT=Path(__file__).resolve().parent
sys.path.append('/usr/lib64/python3.11/site-packages')
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.59-child-photo','/opt/skill-platform/member-0.10.57']
import new_only
new_only.deny_old_transport()
mode=os.environ.get('NEW_ONLY_LEGACY_SERVICE')
if mode not in ('legacy-gemini','legacy-temu','pack'):raise RuntimeError('Legacy namespace required')
source=sys.argv[sys.argv.index('--source')+1]
if mode=='legacy-gemini':
    # Original 0.10.9 preloads its permanent-grant API eligibility module before
    # the source server. Preserve that import order and all original auth rules.
    sys.path.insert(0,'/opt/skill-platform/legacy-permanent-0.10.9-r2')
    import api_access
sys.path.insert(0,'/opt/skill-platform/member-0.5.0/service' if mode!='pack' else '/opt/skill-platform/1.7.0/service')
sys.path.insert(0,source)
import server
core=server.pilot if mode=='legacy-temu' else server
new_only.disable_old_constructor(core,mode)
new_only.health_writer(core,mode)
previous=server.handler
def handler(store):
    new_only.wrap_store(store,core,mode)
    return new_only.guard_handler(previous(store),False)
server.handler=handler
old={'legacy-gemini':'/opt/skill-platform/legacy-permanent-0.10.9-r2/run_legacy.py',
 'legacy-temu':'/opt/skill-platform/member-0.5.0/service/run_legacy.py',
 'pack':'/opt/skill-platform/1.7.0/service/run_pack.py'}[mode]
if not Path(old).is_file():raise RuntimeError('Actual legacy entry missing')
runpy.run_path(old,run_name='__main__')
