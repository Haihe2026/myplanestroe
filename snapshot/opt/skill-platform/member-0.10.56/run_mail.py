from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/ops-extension','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/order-mail-0.6.2']
import permanent_plans,email_settlement,mail_worker,install_mail_pricing
install_mail_pricing.install(email_settlement,mail_worker)
runpy.run_path('/opt/skill-platform/member-0.10.14/ops-extension/run_mail.py',run_name='__main__')
