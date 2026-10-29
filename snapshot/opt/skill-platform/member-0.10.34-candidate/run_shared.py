from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.32-r2','/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops']
# Reuse OS-managed cryptography 41.0.4; do not modify the shared production venv.
sys.path.append('/usr/lib64/python3.11/site-packages')
import server,shared_platform,phone_binding
phone_binding.install(server,shared_platform)
runpy.run_path('/opt/skill-platform/member-0.10.32-r2/run_shared.py',run_name='__main__')
