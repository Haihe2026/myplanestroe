"""Serve the unchanged enterprise feedback asset omitted from prior deployment bundles."""
from pathlib import Path
from urllib.parse import urlsplit


def extend(original, asset):
    def factory(*args, **kwargs):
        base = original(*args, **kwargs)
        class Handler(base):
            def do_GET(self):
                if urlsplit(self.path).path == '/ops/enterprise-feedback.js':
                    try:
                        return self.send(200, Path(asset).read_bytes(),
                                         'application/javascript; charset=utf-8')
                    except OSError:
                        return self.send(503, {'error': 'enterprise_asset_unavailable'})
                return super().do_GET()
        return Handler
    return factory
