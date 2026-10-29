from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
OLD='/opt/skill-platform/member-0.10.58/run_ops.py'
if not Path(OLD).is_file():raise RuntimeError('Actual previous admin entry missing')
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.58','/opt/skill-platform/member-0.10.56','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops-extension','/opt/skill-platform/member-0.10.55','/opt/skill-platform/member-0.10.50']
# Preserve the original chain's pricing import order; this layer changes no plans.
import permanent_plans,install_pricing
install_pricing.install()
import channel_refresh,users_ops,product_ops,enterprise_ops,manual_admin
users_ops.ROOT=ROOT
product_ops.ROOT=ROOT
previous=enterprise_ops.extend_handler
def extended(original,db):return manual_admin.extend(previous(original,db),db)
enterprise_ops.extend_handler=extended
# The original 0.10.58 factory still attaches first-dialogue metadata and serves
# the anonymous list; replace its static list with the journey-button variant.
import dialogue_ops
old_assets=dialogue_ops.ROOT
dialogue_ops.ROOT=ROOT
runpy.run_path(OLD,run_name='__main__')
