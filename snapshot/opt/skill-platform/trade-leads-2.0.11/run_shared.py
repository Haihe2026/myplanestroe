# Sanitized reading mirror: adapter names/configuration differ from production; target URL omitted.
"""Overlay only the trade gateway and data adapter; retain the existing chain."""
import importlib.abc
import importlib.util
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
PREVIOUS = '/opt/skill-platform/gemini-support-20261107/run_shared.py'


class TradeOverlay(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in ('trade_gateway', 'trade_data'):
            return importlib.util.spec_from_file_location(fullname, ROOT/(fullname+'.py'))
        return None


if __name__ == '__main__':
    if any(name in sys.modules for name in ('trade_gateway', 'trade_data')):
        raise RuntimeError('Trade overlay must be installed before the previous chain')
    sys.meta_path.insert(0, TradeOverlay())
    runpy.run_path(PREVIOUS, run_name='__main__')
