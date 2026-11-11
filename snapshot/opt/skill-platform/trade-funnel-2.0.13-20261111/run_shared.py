"""Add optional measurement around the existing shared chain; preserve argv."""
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
PREVIOUS='/opt/skill-platform/trade-link-fix-20261111/run_shared.py'

if __name__=='__main__':
    if 'trade_gateway' in sys.modules or 'wechat_binding' in sys.modules:
        raise RuntimeError('Funnel hook must be installed before the existing chain')
    sys.path[:0]=[str(ROOT),'/opt/skill-platform/member-0.10.14/ops']
    import telemetry
    from trade_funnel_gateway import install_telemetry
    install_telemetry(telemetry)
    runpy.run_path(PREVIOUS,run_name='__main__')
