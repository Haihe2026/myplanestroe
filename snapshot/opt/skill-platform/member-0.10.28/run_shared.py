"""Add first-party Temu delivery; preserve the existing trial and source wrappers."""
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
BASE=Path('/opt/skill-platform/member-0.10.14')
sys.path[:0]=[str(ROOT),str(BASE/'service'),str(BASE/'core'),str(BASE/'ops')]
import server
import shared_platform
import temu_delivery

temu_delivery.install(server,shared_platform)
runpy.run_path('/opt/skill-platform/member-0.10.26/run_shared.py',run_name='__main__')
