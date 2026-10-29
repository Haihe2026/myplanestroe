"""Change new Temu trial eligibility only; retain all existing payment and image routes."""
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
BASE=Path('/opt/skill-platform/member-0.10.14')
sys.path[:0]=[str(ROOT),str(BASE/'service'),str(BASE/'core'),str(BASE/'ops')]
import shared_platform
import temu_trial_policy
temu_trial_policy.install(shared_platform)
runpy.run_path('/opt/skill-platform/member-0.10.28/run_shared.py',run_name='__main__')
