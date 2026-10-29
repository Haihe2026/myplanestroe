from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
OLD='/opt/skill-platform/ops-2026-10-28-journey/run_ops.py'
if not Path(OLD).is_file():raise RuntimeError('Actual prior admin entry missing')
sys.path.append('/usr/lib64/python3.11/site-packages')
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.55','/opt/skill-platform/member-0.10.52']
import permanent_plans,install_pricing
install_pricing.install()
import asset_ops,asset_costs
asset_ops.ROOT=ROOT
asset_costs.install(asset_ops.Registry)
runpy.run_path(OLD,run_name='__main__')
