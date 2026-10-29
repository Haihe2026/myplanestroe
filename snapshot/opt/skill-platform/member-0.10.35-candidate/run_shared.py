from pathlib import Path
import sys,runpy
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core','/opt/skill-platform/member-0.10.14/ops']
sys.path.append('/usr/lib64/python3.11/site-packages')
import server,shared_platform,image_retention
image_retention.install(server,shared_platform)
runpy.run_path('/opt/skill-platform/member-0.10.34-candidate/run_shared.py',run_name='__main__')
