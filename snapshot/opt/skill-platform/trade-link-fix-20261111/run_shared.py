"""Preserve the deployed trade chain and overlay only WeChat linking."""
import importlib.abc
import importlib.util
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
PREVIOUS='/opt/skill-platform/trade-leads-2.0.11/run_shared.py'


class WeChatOverlay(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname=='wechat_binding':
            return importlib.util.spec_from_file_location(fullname,ROOT/'wechat_binding.py')
        return None


if __name__=='__main__':
    if 'wechat_binding' in sys.modules:raise RuntimeError('WeChat overlay loaded too late')
    sys.meta_path.insert(0,WeChatOverlay())
    runpy.run_path(PREVIOUS,run_name='__main__')
