import runpy
import sys
from pathlib import Path
sys.path.insert(0,'/opt/skill-platform/order-mail-0.6.2')
sys.path.insert(0,str(Path(__file__).parent))
import email_settlement
import mail_worker
from enterprise_mail import install
install(email_settlement,mail_worker)
runpy.run_path('/opt/skill-platform/order-mail-0.6.2/event_runner.py',run_name='__main__')
