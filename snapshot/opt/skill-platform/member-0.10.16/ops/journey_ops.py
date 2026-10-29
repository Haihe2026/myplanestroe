"""Authenticated analytics APIs and static injection using the existing ops session."""
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from journey.report import Report
from journey.store import Journey, database

ROOT = Path(__file__).resolve().parents[1]

def extend_handler(original, journey=None, shared=None, legacy=None):
    def factory(report, password, web, secure=True, settler=None):
        base = original(report, password, web, secure=secure, settler=settler)
        journey_store = journey or Journey(os.environ.get('SKILL_JOURNEY_DB', '/var/lib/skill-monitor/journey-0.10.16.db'))
        try:
            journey_store.initialize()
        except Exception:
            pass
        shared_path = shared or (settler.adapters['shared'].path if settler and 'shared' in settler.adapters else '/var/lib/skill-platform/shared.db')
        paths = legacy or (getattr(report, 'products', {}) or {})
        projection = Report(journey_store, shared_path, paths)
        class Handler(base):
            def send(self, status, result, mime='application/json; charset=utf-8', cookie=None):
                if status == 200 and mime.startswith('text/html') and isinstance(result, bytes):
                    result = result.replace(b'</head>', b'<link rel="stylesheet" href="/ops/journey/panel.css?v=0.10.16"><script defer src="/ops/journey/panel.js?v=0.10.16"></script></head>', 1)
                return super().send(status, result, mime, cookie=cookie)

            def do_GET(self):
                parsed = urlsplit(self.path)
                assets = {'/ops/journey/panel.js': ('panel.js', 'application/javascript; charset=utf-8'),
                          '/ops/journey/panel.css': ('panel.css', 'text/css; charset=utf-8')}
                if parsed.path in assets:
                    name, mime = assets[parsed.path]
                    return self.send(200, (ROOT / 'web/journey' / name).read_bytes(), mime)
                prefix = '/ops/api/journey-v2/'
                if not parsed.path.startswith(prefix):
                    return super().do_GET()
                if not self.authenticated():
                    return self.send(401, {'error': 'ops_login_required'})
                q = parse_qs(parsed.query)
                def flag(name, default):
                    v = q.get(name, [default])[0]
                    if v not in ('0', '1'):
                        raise ValueError('Invalid filter')
                    return v == '1'
                try:
                    route = parsed.path[len(prefix):]
                    if route == 'health':
                        health = journey_store.health()
                        with database(shared_path, True) as c:
                            c.execute('SELECT id,status,paid_at FROM member_orders LIMIT 0')
                            c.execute('SELECT order_id,product FROM order_sources LIMIT 0')
                        return self.send(200 if health['ok'] else 503,
                                         dict(version='0.10.16', journey=health, order_projection_readable=True))
                    if route == 'summary':
                        return self.send(200, projection.summary(int(q.get('days', ['7'])[0]),
                            flag('exclude_unknown', '0'), flag('exclude_test_accounts', '1'), flag('exclude_test_orders', '1')))
                    if route == 'users':
                        return self.send(200, projection.users(int(q.get('page', ['1'])[0]), q.get('q', [''])[0]))
                    if route == 'user':
                        return self.send(200, projection.user(q.get('uid', [''])[0]))
                    return self.send(404, {'error': 'not_found'})
                except (ValueError, LookupError):
                    return self.send(400, {'error': 'invalid_query'})
                except Exception:
                    return self.send(503, {'error': 'journey_data_unavailable', 'coverage': 'missing'})

            def do_POST(self):
                if urlsplit(self.path).path != '/ops/api/journey-v2/test-account':
                    return super().do_POST()
                if not self.authenticated():
                    return self.send(401, {'error': 'ops_login_required'})
                if self.headers.get('Origin') != ('https://myplanestore.com' if secure else 'http://127.0.0.1:18890'):
                    return self.send(403, {'error': 'same_origin_required'})
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 1024:
                        raise ValueError('Invalid size')
                    body = json.loads(self.rfile.read(size))
                    uid, marked = body.get('uid'), body.get('marked')
                    if type(marked) is not bool or body.get('confirmed') is not True:
                        raise ValueError('Explicit confirmation required')
                    with database(shared_path, True) as c:
                        if not c.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
                            raise ValueError('Unknown account')
                    journey_store.mark_test(uid, marked, 'operator_confirmed_test_account')
                    return self.send(200, {'ok': True, 'marked': marked, 'business_unchanged': True})
                except (ValueError, TypeError, AttributeError):
                    return self.send(400, {'error': 'invalid_test_account_confirmation'})
                except Exception:
                    return self.send(503, {'error': 'journey_metadata_unavailable'})
        return Handler
    return factory
