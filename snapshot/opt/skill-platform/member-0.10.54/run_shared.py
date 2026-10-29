from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.41']
import trade_config,trade_store
runpy.run_path('/opt/skill-platform/member-0.10.49/run_shared.py',run_name='__main__')
