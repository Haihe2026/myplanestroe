"""Wrap the active service chain, substituting only its WeChat module loader."""
from pathlib import Path
import importlib.util
import runpy
import sys

ROOT=Path(__file__).resolve().parent
PREVIOUS='/opt/skill-platform/trade-funnel-2.0.13-20261111/run_shared.py'
LEGACY_BINDING='/opt/skill-platform/trade-link-fix-20261111/wechat_binding.py'


def install_overlay():
    if 'wechat_binding' in sys.modules:
        raise RuntimeError('WeChat overlay must be installed before the active chain')
    original=importlib.util.spec_from_file_location
    def select(name,location,*args,**kwargs):
        if name=='wechat_binding' and str(location).replace('\\','/')==LEGACY_BINDING:
            location=ROOT/'oa_binding.py'
        return original(name,location,*args,**kwargs)
    importlib.util.spec_from_file_location=select
    sys.path.insert(0,str(ROOT/'_vendor'))
    return original


if __name__=='__main__':
    if not Path(PREVIOUS).is_file() or not Path(LEGACY_BINDING).is_file():
        raise RuntimeError('Required active service-chain entry is missing')
    install_overlay()
    runpy.run_path(PREVIOUS,run_name='__main__')
