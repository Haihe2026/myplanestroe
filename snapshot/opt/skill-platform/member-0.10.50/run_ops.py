from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import product_ops
runpy.run_path('/opt/skill-platform/member-0.10.47/run_ops.py',run_name='__main__')
