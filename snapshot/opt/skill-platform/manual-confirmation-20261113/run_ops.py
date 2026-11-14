"""Wrap the current administrator chain; shared/image services stay unchanged."""
from pathlib import Path
import http.server
import runpy
import sys

ROOT = Path(__file__).resolve().parent
PREVIOUS = '/opt/skill-platform/wechat-official-20261113/run_ops.py'


def install_overlay():
    sys.path.insert(0, str(ROOT))
    import manual_confirmation
    previous_server = http.server.ThreadingHTTPServer

    class ManualConfirmationServer(previous_server):
        def __init__(self, address, handler, *args, **kwargs):
            # Wrap the FINAL handler after every old product factory has run.
            # Wrapping an intermediate factory would miss later pet/trade/
            # listing/metered handlers that consume their POST first.
            wrapped = manual_confirmation.extend(lambda: handler)()
            super().__init__(address, wrapped, *args, **kwargs)

    http.server.ThreadingHTTPServer = ManualConfirmationServer
    return previous_server

if __name__ == '__main__':
    if not Path(PREVIOUS).is_file():
        raise RuntimeError('Current administrator dependency is missing')
    install_overlay()
    runpy.run_path(PREVIOUS, run_name='__main__')
