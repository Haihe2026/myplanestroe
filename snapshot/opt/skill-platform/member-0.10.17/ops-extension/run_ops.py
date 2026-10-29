"""Retain journey 0.10.16 and all original auth/settlement extensions."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, '/opt/skill-platform/member-0.10.14/ops-extension')
import enterprise_ops
from enterprise_asset import extend

original = enterprise_ops.extend_handler


def compatible(*args, **kwargs):
    return extend(original(*args, **kwargs), ROOT / 'enterprise-feedback.js')


enterprise_ops.extend_handler = compatible
runpy.run_path('/opt/skill-platform/member-0.10.16/ops-extension/run_ops.py', run_name='__main__')
