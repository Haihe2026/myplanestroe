# Deterministic clock for isolated expiry tests, not a production entrypoint.
from pathlib import Path
import sys,os,time,runpy
ROOT=Path(__file__).parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.34-candidate','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core']
sys.path.append('/usr/lib64/python3.11/site-packages')
import account_gateway
class Clock:
 sleep=staticmethod(time.sleep)
 @staticmethod
 def time():return time.time()+float(Path(os.environ['PHONE_TEST_CLOCK']).read_text())
account_gateway.time=Clock
runpy.run_path(str(ROOT/'run_shared.py'),run_name='__main__')
