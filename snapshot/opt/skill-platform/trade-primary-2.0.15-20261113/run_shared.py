"""Wrap only the active WeChat factory after its existing loader has selected it."""
import importlib.abc
import importlib.util
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parent
PREVIOUS='/opt/skill-platform/wechat-official-20261113/run_shared.py'


class FactoryLoader(importlib.abc.Loader):
    def __init__(self,original):self.original=original
    def __getattr__(self,name):return getattr(self.original,name)
    def create_module(self,spec):
        create=getattr(self.original,'create_module',None)
        return create(spec) if create else None
    def exec_module(self,module):
        self.original.exec_module(module)
        from trade_web_handoff import install
        previous=module.handler
        def handler(parent,store,server):return install(previous(parent,store,server),store,server)
        module.handler=handler


def install_overlay():
    if 'wechat_binding' in sys.modules:raise RuntimeError('Trade handoff must precede the active WeChat chain')
    original=importlib.util.spec_from_file_location
    def select(name,location,*args,**kwargs):
        spec=original(name,location,*args,**kwargs)
        if name=='wechat_binding' and spec is not None and spec.loader is not None and not isinstance(spec.loader,FactoryLoader):
            spec.loader=FactoryLoader(spec.loader)
        return spec
    importlib.util.spec_from_file_location=select


if __name__=='__main__':
    if not Path(PREVIOUS).is_file():raise RuntimeError('Required active shared entry missing')
    sys.path.insert(0,str(ROOT))
    install_overlay()
    runpy.run_path(PREVIOUS,run_name='__main__')
