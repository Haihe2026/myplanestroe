"""Retain the complete 0.10.14 -> testmarks -> channel -> ops patch chain."""
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
OLD = Path(os.environ.get('JOURNEY_BASE_ROOT', '/opt/skill-platform/member-0.10.14'))
sys.path[:0] = [str(ROOT), str(ROOT / 'ops'), '/opt/skill-platform/member-0.5.0/ops']
import monitor
from journey_ops import extend_handler
monitor.handler = extend_handler(monitor.handler)
runpy.run_path(str(OLD / 'ops-extension/run_ops.py'), run_name='__main__')
