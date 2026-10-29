from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/core']
import permanent_plans,install_pricing
install_pricing.install()
runpy.run_path('/opt/skill-platform/member-0.10.54/run_shared.py',run_name='__main__')
