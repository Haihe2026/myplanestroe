"""Administrator-entered amount verification without a mandatory bank reference.

manual_ references are internal audit identifiers, never bank transaction IDs.
They retain per-order retry/credit protection. Without a bank reference there is
no automatic way to detect one bank payment being assigned to different orders;
the operator explicitly verifies the payer, amount and order in that case.
All original authentication, Origin, amount and grant transactions still run.
"""
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ASSET = '/ops/manual-confirmation-20261113.js'
ROUTES = {
    '/ops/api/settle': 'images',
    '/ops/api/pet-settle': 'pet',
    '/ops/api/trade-leads/settle': 'trade-leads',
    '/ops/api/listing/settle': 'listing',
    '/ops/api/metered/settle': 'metered',
}


def prepare_body(route, body):
    """Stable per-order internal reference; never changes supplied real IDs."""
    if route not in ROUTES or not isinstance(body, dict):
        return body
    if body.get('transaction_id') not in (None, ''):
        return body
    oid = body.get('order_id')
    if (body.get('verified') is not True or type(body.get('amount_fen')) is not int
            or body['amount_fen'] <= 0 or not isinstance(oid, str)
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', oid)):
        return body
    namespace = body.get('product', '') if route.endswith('/api/settle') else ROUTES[route]
    service = body.get('service_id', '') if route == '/ops/api/metered/settle' else ''
    if not isinstance(namespace, str) or not isinstance(service, str):
        return body
    identity = json.dumps([namespace, service, oid], ensure_ascii=True, separators=(',', ':'))
    return dict(body, transaction_id='manual_' + hashlib.sha256(identity.encode()).hexdigest())


def transform_html(result):
    result = re.sub(rb'<label for="settlement-transaction">.*?</label><input id="settlement-transaction"[^>]*>\s*', b'', result, count=1)
    return re.sub(rb'/ops/(?:app|all-orders-20261111)\.js\?v=[^"\s]+',
                  (ASSET + '?v=1').encode(), result)


def extend(factory):
    def build(*args, **kwargs):
        parent = factory(*args, **kwargs)

        class Handler(parent):
            def send(self, status, result, mime='application/json; charset=utf-8', cookie=None):
                if status == 200 and mime.startswith('text/html') and isinstance(result, bytes):
                    result = transform_html(result)
                if (status == 503 and urlsplit(self.path).path in ROUTES
                        and isinstance(result, dict) and 'error' in result):
                    result = dict(result, error='暂未确认入账结果，请刷新本订单后重试，勿另建订单。')
                return super().send(status, result, mime, cookie=cookie)

            def do_GET(self):
                if urlsplit(self.path).path == ASSET:
                    return self.send(200, (ROOT / 'app.js').read_bytes(), 'application/javascript; charset=utf-8')
                return super().do_GET()

            def do_POST(self):
                route = urlsplit(self.path).path
                # The original route still authenticates, checks Origin and runs
                # its own bounds/type/idempotency/audit checks after this replay.
                if route not in ROUTES or not self.authenticated():
                    return super().do_POST()
                self.connection.settimeout(10)
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                except (TypeError, ValueError):
                    return super().do_POST()
                if not 0 < size <= 2048:
                    return super().do_POST()
                raw = self.rfile.read(size)
                try:
                    body = json.loads(raw)
                    prepared = prepare_body(route, body)
                    if prepared is not body:
                        raw = json.dumps(prepared, ensure_ascii=False).encode()
                except (ValueError, TypeError):
                    pass  # Replay malformed data for the original error handling.
                original_reader = self.rfile
                original_size = self.headers.get('Content-Length')
                self.rfile = io.BytesIO(raw)
                self.headers.replace_header('Content-Length', str(len(raw)))
                try:
                    return super().do_POST()
                finally:
                    self.rfile = original_reader
                    self.headers.replace_header('Content-Length', original_size)

        return Handler
    return build
