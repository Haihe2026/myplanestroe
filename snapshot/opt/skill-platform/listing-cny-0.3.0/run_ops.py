from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
OLD='/opt/skill-platform/ops-2026-10-28-costs/run_ops.py'
if not Path(OLD).is_file():raise RuntimeError('Actual prior admin entry missing')
sys.path[:0]=[str(ROOT),'/opt/skill-platform/ops-2026-10-28-costs','/opt/skill-platform/ops-2026-10-28-journey','/opt/skill-platform/member-0.10.58','/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops-extension','/opt/skill-platform/member-0.10.55','/opt/skill-platform/member-0.10.50']
import permanent_plans,install_pricing
install_pricing.install()
import manual_admin,listing_ops,listing_receipts
listing_receipts.install()
previous=manual_admin.extend
def extend(factory,path):return listing_ops.extend(previous(factory,path),path)
manual_admin.extend=extend
runpy.run_path(OLD,run_name='__main__')
