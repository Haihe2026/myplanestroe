"""Baby phone+KEY extension; run unchanged existing service chain."""
from pathlib import Path
import runpy
import sys
ROOT=Path(__file__).resolve().parent
BASE=Path('/opt/skill-platform/member-0.10.14')
sys.path[:0]=[str(ROOT),str(BASE/'service'),str(BASE/'core'),str(BASE/'ops')]
import server
import shared_platform
import album_accounts
album_accounts.install(server,shared_platform)
runpy.run_path('/opt/skill-platform/member-0.10.31/run_shared.py',run_name='__main__')
