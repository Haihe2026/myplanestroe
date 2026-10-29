"""Child photo route only. Preserve .58 dialogue, .57 Temu and the entire old chain."""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
OLD_ENTRY='/opt/skill-platform/member-0.10.58/run_shared.py'
if not Path(OLD_ENTRY).is_file():raise RuntimeError('Actual prior shared entry missing')
# Match the deployed 0.10.35 retention layer's existing system crypto runtime.
# Child imports happen earlier in the chain, so this must precede child_service.
sys.path.append('/usr/lib64/python3.11/site-packages')
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.56',
 '/opt/skill-platform/member-0.10.57','/opt/skill-platform/member-0.10.24',
 '/opt/skill-platform/member-0.10.16','/opt/skill-platform/member-0.10.14/service',
 '/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops']
import permanent_plans,install_pricing
install_pricing.install()
import server,shared_platform,sunburst,telemetry,child_service
child_service.install(server,shared_platform,sunburst)
previous=telemetry.observed_handler
def observed(parent,store,product,event_db):
    return child_service.wrap_handler(previous(parent,store,product,event_db),store,server)
telemetry.observed_handler=observed
runpy.run_path(OLD_ENTRY,run_name='__main__')
