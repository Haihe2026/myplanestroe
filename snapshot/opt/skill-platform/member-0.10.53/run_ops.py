from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.5.0/ops']
import monitor,resource_ops
# Install at the base response writer so all later HTML extensions are included.
monitor.handler=resource_ops.extend(monitor.handler)
runpy.run_path('/opt/skill-platform/member-0.10.52/run_ops.py',run_name='__main__')
