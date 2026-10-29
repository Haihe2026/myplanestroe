"""Run the existing trial/payment service with one additional analytics source."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), '/opt/skill-platform/member-0.10.16']
import source_registration

source_registration.install()
runpy.run_path('/opt/skill-platform/member-0.10.24/run_shared.py', run_name='__main__')
