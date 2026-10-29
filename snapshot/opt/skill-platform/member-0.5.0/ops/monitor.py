"""Authenticated operations console with explicit manual settlement."""
import argparse
from contextlib import contextmanager
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import sys
from settlement import Settlement, SettlementError
from urllib.parse import urlsplit, parse_qs


@contextmanager
def database(path):
    c = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=3)
    c.row_factory = sqlite3.Row
    try:
        c.execute('PRAGMA query_only=ON')
        yield c
    finally:
        c.close()


class Report:
    def __init__(self, products, events):
        self.products, self.events = products, events

    def event_summary(self, product, since):
        with database(self.events) as c:
            rows = [dict(r) for r in c.execute('SELECT event,status,device,channel,count(*) count FROM events WHERE product=? AND created>=? GROUP BY event,status,device,channel', (product, since))]
        return rows

    def summary(self, days):
        since = int(time.time()) - days * 86400
        result = []
        for product, path in self.products.items():
            try:
                with database(path) as c:
                    users = c.execute('SELECT count(*) FROM users').fetchone()[0]
                    active = c.execute('SELECT count(DISTINCT user_id) FROM jobs WHERE created>=?', (since,)).fetchone()[0]
                    counts = {r['status']: r['n'] for r in c.execute('SELECT status,count(*) n FROM jobs WHERE created>=? GROUP BY status', (since,))}
                    new_users = c.execute("SELECT count(DISTINCT user_id) FROM ledger WHERE kind IN ('trial_grant','account_created') AND created>=?", (since,)).fetchone()[0]
                    orders = dict(c.execute("SELECT count(*) orders,coalesce(sum(amount_fen),0) amount_fen,count(DISTINCT user_id) payers FROM member_orders WHERE status='paid' AND paid_at>=?", (since,)).fetchone())
                result.append({'product': product, 'connected': True, 'users': users, 'active': active, 'new_users': new_users,
                               'jobs': counts, 'paid': orders, 'events': self.event_summary(product, since)})
            except (sqlite3.Error, OSError):
                result.append({'product': product, 'connected': False})
        with database(self.events) as c:
            started = c.execute("SELECT value FROM metadata WHERE key='collection_started'").fetchone()
        return {'products': result, 'collection_started': int(started[0]) if started else None, 'days': days,
                'native_payment_ready': False, 'unconnected': ['xhs'], 'generated_at': int(time.time())}

    def users(self, product, query, page):
        if product not in self.products:
            raise ValueError('Unknown product')
        # Escape LIKE wildcards; expose anonymous IDs only, never keys or hashes.
        query = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        with database(self.products[product]) as c:
            params = ('%' + query + '%',)
            total = c.execute("SELECT count(*) FROM users WHERE id LIKE ? ESCAPE '\\'", params).fetchone()[0]
            rows = c.execute("""SELECT u.id,u.balance,
                (SELECT min(created) FROM ledger WHERE user_id=u.id AND kind IN ('trial_grant','account_created')) activated,
                (SELECT max(created) FROM jobs WHERE user_id=u.id) last_job,
                (SELECT count(*) FROM jobs WHERE user_id=u.id AND status='succeeded') images,
                (SELECT count(*) FROM jobs WHERE user_id=u.id AND status='pending') pending,
                (SELECT coalesce(sum(remaining),0) FROM member_grants WHERE user_id=u.id AND expires IS NOT NULL AND expires<=?) expired_unsettled
                FROM users u WHERE u.id LIKE ? ESCAPE '\\' ORDER BY coalesce(last_job,activated,0) DESC,u.id LIMIT 50 OFFSET ?""",
                (int(time.time()), params[0], (page - 1) * 50)).fetchall()
        return {'total': total, 'page': page, 'users': [dict(r, balance_points=max(0, r['balance'] - r['expired_unsettled']) * 1000) for r in rows]}

    def orders(self, product, status, query, page):
        if product not in self.products or status not in ('all', 'reported', 'pending', 'paid'):
            raise ValueError('Unknown product or status')
        if not 1 <= page <= 100000 or len(query) > 64:
            raise ValueError('Invalid search')
        query = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        where = "(id LIKE ? ESCAPE '\\' OR user_id LIKE ? ESCAPE '\\')"
        params = ['%' + query + '%'] * 2
        if status != 'all':
            where += ' AND status=?'
            params.append(status)
        with database(self.products[product]) as c:
            counts = {r['status']: dict(r) for r in c.execute(
                'SELECT status,count(*) count,coalesce(sum(amount_fen),0) amount_fen FROM member_orders GROUP BY status')}
            total = c.execute('SELECT count(*) FROM member_orders WHERE ' + where, params).fetchone()[0]
            rows = [dict(r, points=r['units'] * 1000) for r in c.execute(
                'SELECT id,user_id,plan,amount_fen,units,status,created,paid_at,provider FROM member_orders WHERE ' + where +
                ' ORDER BY created DESC,id DESC LIMIT 50 OFFSET ?', params + [(page - 1) * 50])]
        return {'orders': rows, 'total': total, 'page': page, 'counts': counts}

    def journey(self, product, uid):
        if product not in self.products:
            raise ValueError('Unknown product')
        with database(self.products[product]) as c:
            row = c.execute('SELECT id,balance FROM users WHERE id=?', (uid,)).fetchone()
            if not row:
                raise LookupError('Unknown user')
            expired = c.execute('SELECT coalesce(sum(remaining),0) FROM member_grants WHERE user_id=? AND expires IS NOT NULL AND expires<=?', (uid, int(time.time()))).fetchone()[0]
            ledger = [dict(r) for r in c.execute('SELECT id,created,kind,amount FROM ledger WHERE user_id=? ORDER BY created DESC,id DESC LIMIT 100', (uid,))]
            jobs = [dict(r) for r in c.execute('SELECT id,created,status FROM jobs WHERE user_id=? ORDER BY created DESC LIMIT 100', (uid,))]
            orders = [dict(r) for r in c.execute('SELECT id,created,paid_at,plan,amount_fen,units,status,provider FROM member_orders WHERE user_id=? ORDER BY created DESC LIMIT 100', (uid,))]
        with database(self.events) as c:
            events = [dict(r) for r in c.execute('SELECT created,event,status,channel,device,duration_ms FROM events WHERE product=? AND user_id=? ORDER BY created DESC,id DESC LIMIT 100', (product, uid))]
        return {'id': uid, 'product': product, 'balance_points': max(0, row['balance'] - expired) * 1000,
                'ledger': ledger, 'jobs': jobs, 'orders': orders, 'events': events, 'limited_to': 100}


def handler(report, password, web, secure=True, settler=None, session_path="/var/lib/skill-monitor/ops-sessions.sqlite3"):
    from persistent_sessions import SessionStore, SESSION_SECONDS
    sessions, attempts, lock = SessionStore(session_path, password), {}, threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, data, mime='application/json; charset=utf-8', cookie=None):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if cookie:
                self.send_header('Set-Cookie', cookie)
            try:
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection=True

        def authenticated(self):
            try:
                cookie = SimpleCookie(self.headers.get('Cookie', '')).get('skill_ops')
                key = hashlib.sha256(cookie.value.encode()).hexdigest() if cookie else ''
            except Exception:
                return False
            with lock:
                return sessions.get(key, 0) > time.time()

        def do_POST(self):
            self.connection.settimeout(10)
            if self.headers.get('Origin') != ('https://myplanestore.com' if secure else 'http://127.0.0.1:18890'):
                return self.send(403, {'error': '请从本站操作'})
            route = urlsplit(self.path).path
            if route == '/ops/api/settle':
                if not self.authenticated():
                    return self.send(401, {'error': '请登录管理后台'})
                if not settler:
                    return self.send(503, {'error': '后台核款尚未启用'})
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 2048:
                        raise ValueError()
                    body = json.loads(self.rfile.read(size))
                    token = SimpleCookie(self.headers.get('Cookie', ''))['skill_ops'].value
                    actor = 'admin-session:' + hashlib.sha256(token.encode()).hexdigest()[:16]
                    return self.send(200, settler.confirm(body, actor))
                except SettlementError as e:
                    return self.send(e.status, {'error': e.message})
                except (ValueError, TypeError):
                    return self.send(400, {'error': '核款参数无效'})
                except Exception:
                    return self.send(503, {'error': '暂未确认入账结果，请用同一交易单号重试；不要更换单号'})
            if route == '/ops/api/logout':
                cookie = SimpleCookie(self.headers.get('Cookie', '')).get('skill_ops')
                with lock:
                    if cookie:
                        sessions.pop(hashlib.sha256(cookie.value.encode()).hexdigest(), None)
                return self.send(200, {'ok': True}, cookie='skill_ops=; Max-Age=0; Path=/ops/; HttpOnly; SameSite=Strict' + ('; Secure' if secure else ''))
            if route != '/ops/api/login':
                return self.send(404, {'error': '不存在'})
            key = self.headers.get('X-Real-IP', self.client_address[0]) if self.client_address[0] == '127.0.0.1' else self.client_address[0]
            now = time.time()
            with lock:
                for k in list(attempts):
                    if attempts[k][1] < now - 900:
                        attempts.pop(k)
                for k in list(sessions):
                    if sessions[k] <= now:
                        sessions.pop(k)
                count, began = attempts.get(key, (0, now))
                if count >= 8:
                    return self.send(429, {'error': '尝试过多，请15分钟后重试'})
                attempts[key] = (count + 1, began)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2048:
                    raise ValueError()
                body = json.loads(self.rfile.read(size))
                supplied = body.get('password')
                if not isinstance(supplied, str) or not hmac.compare_digest(supplied.encode(), password.encode()):
                    return self.send(401, {'error': '管理口令不正确'})
            except (ValueError, TypeError, AttributeError):
                return self.send(400, {'error': '请求格式错误'})
            token = secrets.token_urlsafe(32)
            with lock:
                sessions[hashlib.sha256(token.encode()).hexdigest()] = now + SESSION_SECONDS
                attempts.pop(key, None)
            return self.send(200, {'ok': True}, cookie='skill_ops=' + token + '; Path=/ops/; HttpOnly; SameSite=Strict; Max-Age=' + str(SESSION_SECONDS) + ('; Secure' if secure else ''))

        def do_GET(self):
            self.connection.settimeout(10)
            parsed = urlsplit(self.path)
            static = {'/ops/': ('index.html', 'text/html; charset=utf-8'), '/ops/app.js': ('app.js', 'application/javascript; charset=utf-8'), '/ops/style.css': ('style.css', 'text/css; charset=utf-8'), '/ops/logo.svg': ('logo.svg', 'image/svg+xml')}
            if parsed.path in static:
                name, mime = static[parsed.path]
                return self.send(200, (web / name).read_bytes(), mime)
            if parsed.path == '/ops/settlement.css':
                return self.send(200, (web / 'settlement.css').read_bytes(), 'text/css; charset=utf-8')
            if not parsed.path.startswith('/ops/api/'):
                return self.send(404, {'error': '不存在'})
            if not self.authenticated():
                return self.send(401, {'error': '请登录管理后台'})
            q = parse_qs(parsed.query)
            try:
                if parsed.path == '/ops/api/summary':
                    days = int(q.get('days', ['7'])[0])
                    if days not in (1, 2, 7, 30, 90):
                        raise ValueError()
                    return self.send(200, report.summary(days))
                if parsed.path == '/ops/api/users':
                    page = int(q.get('page', ['1'])[0])
                    query = q.get('q', [''])[0]
                    if not 1 <= page <= 100000 or len(query) > 64:
                        raise ValueError()
                    return self.send(200, report.users(q.get('product', ['gemini'])[0], query, page))
                if parsed.path == '/ops/api/orders':
                    data = report.orders(q.get('product', ['gemini'])[0],
                        q.get('status', ['reported'])[0], q.get('q', [''])[0], int(q.get('page', ['1'])[0]))
                    return self.send(200, dict(data, settlement_enabled=bool(settler), generated_at=int(time.time())))
                if parsed.path == '/ops/api/order':
                    if not settler:
                        return self.send(503, {'error': '后台核款尚未启用'})
                    return self.send(200, settler.preview(q.get('product', ['gemini'])[0], q.get('id', [''])[0]))
                if parsed.path == '/ops/api/journey':
                    return self.send(200, report.journey(q.get('product', ['gemini'])[0], q.get('uid', [''])[0]))
                return self.send(404, {'error': '不存在'})
            except SettlementError as e:
                return self.send(e.status, {'error': e.message})
            except (ValueError, LookupError):
                return self.send(400, {'error': '参数或账户无效'})
            except Exception:
                return self.send(503, {'error': '数据源暂不可用，请稍后重试'})
    return Handler


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--port', type=int, default=8790)
    p.add_argument('--payment-source')
    a = p.parse_args()
    os.umask(0o077)
    config = json.loads(Path(a.config).read_text())
    if len(config['password']) < 32:
        raise ValueError('Strong admin credential required')
    settler = None
    if a.payment_source:
        sys.path.insert(0, str(Path(a.payment_source).resolve()))
        from manual_payments import ManualMembership
        settler = Settlement(config['products']['gemini'], ManualMembership.confirm_manual)
    ThreadingHTTPServer(('127.0.0.1', a.port), handler(Report(config['products'], config['events']), config['password'], Path(__file__).parent.parent / 'web', settler=settler)).serve_forever()
