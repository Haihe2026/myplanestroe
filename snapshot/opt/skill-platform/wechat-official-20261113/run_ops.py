"""Add official-account binding timestamps to the existing read-only journey."""
import importlib.abc
import importlib.util
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
PREVIOUS = '/opt/skill-platform/trade-funnel-2.0.13-20261111/run_ops.py'


class ManualAdminOverlay(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'manual_admin':
            return importlib.util.spec_from_file_location(fullname, ROOT / 'oa_manual_admin.py')
        return None


def install_overlay():
    if 'manual_admin' in sys.modules:
        raise RuntimeError('Read-only journey overlay must precede the existing chain')
    finder = ManualAdminOverlay()
    sys.meta_path.insert(0, finder)
    return finder


if __name__ == '__main__':
    if not Path(PREVIOUS).is_file():
        raise RuntimeError('Required active administrator entry is missing')
    install_overlay()
    runpy.run_path(PREVIOUS, run_name='__main__')
