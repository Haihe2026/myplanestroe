from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.41']
import trade_config,trade_store,trade_ops
runpy.run_path('/opt/skill-platform/member-0.10.53/run_ops.py',run_name='__main__')
