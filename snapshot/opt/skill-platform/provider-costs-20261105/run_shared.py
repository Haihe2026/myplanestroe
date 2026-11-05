from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from cost_store import Costs
Costs().initialize()
from usage_capture import install
install()
runpy.run_path('/opt/skill-platform/listing-cny-0.4.0/run_shared.py',run_name='__main__')
