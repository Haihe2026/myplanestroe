"""Chain the existing journey gateway with a narrowly scoped Sunburst adapter."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
BASE = Path('/opt/skill-platform/member-0.10.14')
sys.path[:0] = [str(ROOT), str(BASE / 'service'), str(BASE / 'core'), str(BASE / 'ops')]
import server
import shared_platform
import sunburst
import gemini_trial

gemini_trial.install(server, shared_platform)
sunburst.install(server, shared_platform)
runpy.run_path('/opt/skill-platform/member-0.10.16/service/run_shared.py', run_name='__main__')
