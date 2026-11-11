"""Add authenticated funnel projections around the existing admin chain."""
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
PREVIOUS='/opt/skill-platform/unified-orders-20261111/run_ops.py'

if __name__=='__main__':
    sys.path[:0]=[str(ROOT),'/opt/skill-platform/ops-2026-10-28-journey']
    import manual_admin
    import trade_funnel_ops
    previous=manual_admin.extend
    def extend(factory,path):
        return trade_funnel_ops.extend(previous(factory,path),path)
    manual_admin.extend=extend
    runpy.run_path(PREVIOUS,run_name='__main__')
