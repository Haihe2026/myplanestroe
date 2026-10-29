"""Trade recharge tiers only; preserve the complete deployed pet/image chain."""
from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
OLD_ENTRY='/opt/skill-platform/member-0.10.44/run_shared.py'
if not Path(OLD_ENTRY).is_file():raise RuntimeError('Actual previous shared entry missing')
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.41']
import trade_config,trade_gateway
runpy.run_path(OLD_ENTRY,run_name='__main__')
