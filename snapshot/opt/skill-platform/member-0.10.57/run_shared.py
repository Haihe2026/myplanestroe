"""Expert-only image resource layer; all existing service/payment wrappers remain."""
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.24',
              '/opt/skill-platform/member-0.10.14/service','/opt/skill-platform/member-0.10.14/core']
import server,shared_platform,sunburst,expert_service,temu_delivery
expert_service.install(server,shared_platform,sunburst)
previous=(ROOT/'previous-entry.txt').read_text().strip()
if not previous.startswith('/opt/skill-platform/member-') or not previous.endswith('/run_shared.py') or not Path(previous).is_file():
    raise RuntimeError('Previous gateway entry missing')
runpy.run_path(previous,run_name='__main__')
