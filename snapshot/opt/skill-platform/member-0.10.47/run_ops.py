"""Keep the existing admin chain; preload the updated product projection module."""
from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import product_ops
runpy.run_path('/opt/skill-platform/member-0.10.46/run_ops.py',run_name='__main__')
