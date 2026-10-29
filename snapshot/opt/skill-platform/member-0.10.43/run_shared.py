"""0.10.43 pet pricing/photo contract on the actual 0.10.41 chain."""
from pathlib import Path
import os,runpy,sys
ROOT=Path(__file__).resolve().parent
OLD_ENTRY='/opt/skill-platform/member-0.10.41/run_shared.py'
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.39','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core']
if not Path(OLD_ENTRY).is_file():raise RuntimeError('Missing actual prior entry: '+OLD_ENTRY)
os.environ['MPS_PET_CONFIG']=str(ROOT/'pet-config.json')
import pet_gateway,server
from pet_resources import PetResources
from pet_routes import wrap
from pet_vision import Vision
previous=pet_gateway.install
pet_gateway.PetBilling=PetResources
def install(store,server,shared,parent):
    final=previous(store,server,shared,parent)
    store.pet_billing.recover_incomplete()
    return wrap(final,store,server,Vision())
pet_gateway.install=install
runpy.run_path(OLD_ENTRY,run_name='__main__')
