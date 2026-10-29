import runpy
import sys
from pathlib import Path
sys.path.insert(0,'/opt/skill-platform/member-0.5.0/ops')
sys.path.insert(0,str(Path(__file__).parent))
import monitor
from enterprise_ops import extend_handler
monitor.handler=extend_handler(monitor.handler,'/var/lib/skill-platform/shared.db')
runpy.run_path('/opt/skill-platform/ops-test-marks-0.10.2/run_ops.py',run_name='__main__')
