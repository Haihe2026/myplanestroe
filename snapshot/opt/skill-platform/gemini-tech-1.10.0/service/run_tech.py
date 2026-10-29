"""Bind locally behind HTTPS; customer model API keys never reach this service."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tech_orders import TechOrders, Problem

BASE = '/skillpay/gemini-tech'


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(90)

    def log_message(self, *args):
        pass

    def send(self, status, body, headers=None):
        raw = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.send(200, self.server.service.health()) if self.path == BASE+'/health' else self.send(404, {'code': 'NOT_FOUND'})

    def do_POST(self):
        service = self.server.service
        try:
            if self.headers.get('Transfer-Encoding'):
                raise Problem(400, 'INVALID_ENCODING')
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 65536:
                raise Problem(413, 'INVALID_BODY_LENGTH')
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise Problem(400, 'INCOMPLETE_REQUEST')
            if self.path == BASE+'/notify':
                return self.send(200, service.notify(dict(self.headers), raw))
            if self.path == BASE+'/refund-notify':
                return self.send(200, service.refund_notify(dict(self.headers), raw))
            if self.path != BASE+'/invoke':
                raise Problem(404, 'NOT_FOUND')
            token = self.headers.get('Authorization', '').removeprefix('Bearer ')
            self.send(*service.invoke(token, json.loads(raw), self.headers.get('X-Out-Trade-No')))
        except Problem as e:
            self.send(e.status, {'code': e.code})
        except (ValueError, TypeError, UnicodeError):
            self.send(400, {'code': 'INVALID_REQUEST'})
        except Exception:
            self.send(503, {'code': 'PAYMENT_STATUS_UNCERTAIN', 'notice': '保留原任务和订单，不重复付款。'})


def make_server(address, service):
    server = ThreadingHTTPServer(address, Handler)
    server.service = service
    return server


if __name__ == '__main__':
    from payments import Payments
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--port', type=int, default=18790)
    args = parser.parse_args()
    os.umask(0o077)
    service = TechOrders(args.db, Payments(), int(os.environ['TECH_AMOUNT_FEN']))
    make_server(('127.0.0.1', args.port), service).serve_forever()
