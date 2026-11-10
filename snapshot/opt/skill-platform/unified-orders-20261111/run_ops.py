"""Add all-product order reporting to the active admin chain."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
OLD = '/opt/skill-platform/admin-redesign-20261103/run_ops.py'
if not Path(OLD).is_file():
    raise RuntimeError('Actual existing admin entry missing')
sys.path[:0] = [str(ROOT), '/opt/skill-platform/ops-2026-10-28-journey']
import manual_admin
import unified_orders

previous = manual_admin.extend


def extend(factory, path):
    return unified_orders.extend(previous(factory, path), path)


manual_admin.extend = extend
runpy.run_path(OLD, run_name='__main__')
