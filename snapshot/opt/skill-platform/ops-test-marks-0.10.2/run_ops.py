import runpy
import sys
from pathlib import Path
sys.path.insert(0,'/opt/skill-platform/member-0.5.0/ops')
sys.path.insert(0,str(Path(__file__).parent))
import monitor
from test_mark import extend_handler,test_orders
monitor.handler=extend_handler(monitor.handler)
monitor.Report.orders=test_orders(monitor.Report.orders)
runpy.run_path('/opt/skill-platform/channel-stats-0.9.1/run_ops.py',run_name='__main__')
