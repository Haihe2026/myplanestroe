"""Integer trade recharge tiers; retain the deployed complete service chain."""
from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
OLD_ENTRY='/opt/skill-platform/member-0.10.48/run_shared.py'
if not Path(OLD_ENTRY).is_file():raise RuntimeError('Actual previous shared entry missing')
sys.path.insert(0,str(ROOT))
import trade_config
runpy.run_path(OLD_ENTRY,run_name='__main__')
