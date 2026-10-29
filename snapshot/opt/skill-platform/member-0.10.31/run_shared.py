"""Add remembered-browser account linking (scheme A); run the unchanged 0.10.29 chain underneath."""
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
BASE=Path('/opt/skill-platform/member-0.10.14')
sys.path[:0]=[str(ROOT),str(BASE/'service'),str(BASE/'core'),str(BASE/'ops')]
import server
import shared_platform
import account_link

account_link.install(server,shared_platform)
runpy.run_path('/opt/skill-platform/member-0.10.29/run_shared.py',run_name='__main__')
