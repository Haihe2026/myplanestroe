"""Pet checkout login recovery; preserve the complete .43 pricing/photo chain."""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
OLD_ENTRY='/opt/skill-platform/member-0.10.43/run_shared.py'
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.43','/opt/skill-platform/member-0.10.39']
if not Path(OLD_ENTRY).is_file():raise RuntimeError('Missing actual prior entry: '+OLD_ENTRY)
import pet_routes,checkout_resume
previous=pet_routes.wrap
def wrap(parent,store,server,vision):
    return checkout_resume.wrap(previous(parent,store,server,vision),store,server)
pet_routes.wrap=wrap
runpy.run_path(OLD_ENTRY,run_name='__main__')
