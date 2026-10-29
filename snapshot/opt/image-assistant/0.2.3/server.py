"""Private pilot gateway. Public deployment requires TLS and reviewed identity integration."""
import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 32768
MAX_IMAGE = 16 * 1024 * 1024
PRESETS = json.loads(Path(__file__).with_name('presets.json').read_text(encoding='utf-8'))
CATALOG = json.loads(Path(__file__).with_name('roles.json').read_text(encoding='utf-8'))
PRESETS['roles'].update({key: value['guidance'] for key, value in CATALOG['roles'].items()})
PRESETS['role_catalog'] = CATALOG


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Problem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Provider:
    def __init__(self):
        self.ready = os.environ.get('IMAGE_PROVIDER_CONFIRMED') == 'yes' and bool(os.environ.get('IMAGE_PROVIDER_KEY'))

    def __call__(self, prompt, size):
        # Only the operator-configured supplier host is reachable, never a client-provided URL.
        payload = json.dumps({'model': 'gpt-image-2', 'prompt': prompt, 'n': 1, 'size': size}).encode()
        request = urllib.request.Request('https://token.q14.cn/v1/images/generations', data=payload,
                                        headers={'Authorization': 'Bearer ' + os.environ['IMAGE_PROVIDER_KEY'],
                                                 'Content-Type': 'application/json'}, method='POST')
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(request, timeout=100) as response:
            raw = response.read(24 * 1024 * 1024 + 1)
        if len(raw) > 24 * 1024 * 1024:
            raise ValueError('oversized response')
        data = json.loads(raw)['data']
        if len(data) != 1:
            raise ValueError('unexpected image count')
        image = base64.b64decode(data[0]['b64_json'], validate=True)
        if not image.startswith(b'\x89PNG\r\n\x1a\n') or len(image) > MAX_IMAGE:
            raise ValueError('unsupported image')
        return image


class Store:
    def __init__(self, database, provider=None):
        self.database = str(database)
        self.provider = provider if provider is not None else Provider()
        with self.connect() as c:
            c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, balance INTEGER NOT NULL CHECK(balance >= 0));
            CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS invites(hash TEXT PRIMARY KEY, expires INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY, user_id TEXT, job_id TEXT, amount INTEGER, kind TEXT, created INTEGER);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, idem TEXT NOT NULL,
                request_hash TEXT NOT NULL, status TEXT NOT NULL, image BLOB, created INTEGER,
                UNIQUE(user_id, idem));
            ''')

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.database, timeout=15)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def invite(self):
        code = secrets.token_urlsafe(32)
        with self.connect() as c:
            c.execute('INSERT INTO invites(hash,expires) VALUES(?,?)', (digest(code), int(time.time()) + 86400))
        return code

    def activate(self, code):
        if not isinstance(code, str) or not 20 <= len(code) <= 128:
            raise Problem(400, '试用凭证格式错误')
        token, uid = secrets.token_urlsafe(32), str(uuid.uuid4())
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM invites WHERE hash=?', (digest(code),)).fetchone()
            if not row or row['used'] or row['expires'] < time.time():
                raise Problem(403, '试用凭证无效、已领取或已过期')
            c.execute('UPDATE invites SET used=1 WHERE hash=?', (digest(code),))
            c.execute('INSERT INTO users VALUES(?,5)', (uid,))
            c.execute('INSERT INTO sessions VALUES(?,?,?)', (digest(token), uid, int(time.time()) + 7 * 86400))
            c.execute('INSERT INTO ledger(user_id,amount,kind,created) VALUES(?,5,?,?)', (uid, 'trial_grant', int(time.time())))
        return {'token': token, 'balance': 5, 'notice': '本服务试用积分，非WorkBuddy积分；测试凭证有效期7天'}

    def user(self, token):
        if not token or len(token) > 128:
            raise Problem(401, '请先激活试用凭证')
        with self.connect() as c:
            row = c.execute('SELECT user_id FROM sessions WHERE hash=? AND expires>?', (digest(token), time.time())).fetchone()
        if not row:
            raise Problem(401, '试用会话无效或过期，请联系测试管理员')
        return row['user_id']

    def balance(self, uid):
        with self.connect() as c:
            return c.execute('SELECT balance FROM users WHERE id=?', (uid,)).fetchone()['balance']

    def get_job(self, uid, jid):
        with self.connect() as c:
            row = c.execute('SELECT id,status,image FROM jobs WHERE id=? AND user_id=?', (jid, uid)).fetchone()
        if not row:
            raise Problem(404, '任务不存在')
        return dict(row)

    def generate(self, uid, body, idem):
        if not isinstance(idem, str) or not 16 <= len(idem) <= 100:
            raise Problem(400, '缺少有效任务幂等标识')
        if not isinstance(body, dict):
            raise Problem(400, '任务须为JSON对象')
        prompt = body.get('prompt', '')
        role, platform = body.get('role', 'general'), body.get('platform', 'general')
        slot, size = body.get('slot', 'illustration'), body.get('size', '1024x1024')
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 6000:
            raise Problem(400, '需求不能为空或超过6000字符')
        if role not in PRESETS['roles'] or platform not in PRESETS['platforms'] or slot not in PRESETS['slots'] or size not in PRESETS['sizes']:
            raise Problem(400, '岗位、平台、用途或尺寸无效')
        if slot == 'main':
            raise Problem(422, '实物商品主图须使用真实参考素材与可控加工，本版暂不支持，未扣积分')
        if body.get('confirmed') is not True:
            raise Problem(400, '请先确认图片方案及一次1积分消耗')
        normalized = {'prompt': prompt, 'role': role, 'platform': platform, 'slot': slot, 'size': size}
        rhash = digest(json.dumps(normalized, sort_keys=True, ensure_ascii=False))
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT id,status,request_hash FROM jobs WHERE user_id=? AND idem=?', (uid, idem)).fetchone()
            if old:
                if not hmac.compare_digest(old['request_hash'], rhash):
                    raise Problem(409, '同一任务标识不能更换需求')
                return {'id': old['id'], 'status': old['status'], 'replayed': True}
            if not self.provider.ready:
                raise Problem(503, '真实生图接口尚未配置，未扣积分')
            # Pilot hard cap counts reserved/successful tasks, independent of client counters.
            total = c.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','succeeded')").fetchone()[0]
            if total >= int(os.environ.get('IMAGE_PILOT_MAX_IMAGES', '20')):
                raise Problem(429, '全站测试额度已用完，未扣积分')
            if c.execute('SELECT balance FROM users WHERE id=?', (uid,)).fetchone()['balance'] < 1:
                raise Problem(402, '试用积分已用完')
            jid = str(uuid.uuid4())
            c.execute('UPDATE users SET balance=balance-1 WHERE id=?', (uid,))
            c.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?)', (jid, uid, idem, rhash, 'pending', None, int(time.time())))
            c.execute('INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,-1,?,?)', (uid, jid, 'reserve', int(time.time())))
        compiled = '\n'.join([PRESETS['roles'][role], PRESETS['platforms'][platform]['guidance'],
                              '图片用途：' + slot, '不编造产品功能、数据或证据。', prompt])
        try:
            image = self.provider(compiled, size)
            if not isinstance(image, bytes) or not image.startswith(b'\x89PNG\r\n\x1a\n') or len(image) > MAX_IMAGE:
                raise ValueError('invalid image')
        except Exception:
            # A timeout/error does not establish the upstream failed. Never retry automatically.
            return {'id': jid, 'status': 'pending', 'notice': '上游结果待核查，积分已预占；请勿重建任务重复生成'}
        with self.connect() as c:
            c.execute("UPDATE jobs SET status='succeeded',image=? WHERE id=? AND status='pending'", (image, jid))
        return {'id': jid, 'status': 'succeeded', 'balance': self.balance(uid), 'rules_status': PRESETS['platforms'][platform]['status']}

    def refund_confirmed_failure(self, jid):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute("SELECT user_id FROM jobs WHERE id=? AND status='pending'", (jid,)).fetchone()
            if not row:
                raise Problem(409, '只能退回确认失败的待核查任务')
            c.execute("UPDATE jobs SET status='failed' WHERE id=?", (jid,))
            c.execute('UPDATE users SET balance=balance+1 WHERE id=?', (row['user_id'],))
            c.execute('INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,1,?,?)', (row['user_id'], jid, 'confirmed_failure_refund', int(time.time())))


def handler(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Request bodies and credentials must not enter access logs.

        def send(self, status, result, mime='application/json; charset=utf-8'):
            data = result if isinstance(result, bytes) else json.dumps(result, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def run_request(self):
            self.connection.settimeout(15)
            try:
                path = self.path
                body = {}
                if self.command == 'POST':
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= MAX_BODY:
                        raise Problem(413, '请求体过大或缺少长度')
                    body = json.loads(self.rfile.read(size))
                    if not isinstance(body, dict):
                        raise Problem(400, '请求须为JSON对象')
                if path == '/health' and self.command == 'GET':
                    return self.send(200, {'status': 'ok', 'version': '0.2.3', 'provider_configured': store.provider.ready, 'public_registration': False})
                if path == '/activate' and self.command == 'POST':
                    return self.send(200, store.activate(body.get('code')))
                uid = store.user(self.headers.get('Authorization', '').removeprefix('Bearer '))
                if path == '/balance' and self.command == 'GET':
                    return self.send(200, {'balance': store.balance(uid)})
                if path == '/presets' and self.command == 'GET':
                    return self.send(200, PRESETS)
                if path == '/jobs' and self.command == 'POST':
                    return self.send(200, store.generate(uid, body, self.headers.get('Idempotency-Key')))
                parts = path.split('/')
                if len(parts) in (3, 4) and parts[1] == 'jobs' and self.command == 'GET':
                    job = store.get_job(uid, parts[2])
                    image = job.pop('image')
                    if len(parts) == 4 and parts[3] == 'image':
                        if not image:
                            raise Problem(409, '图片尚未可用')
                        return self.send(200, image, 'image/png')
                    if len(parts) == 3:
                        return self.send(200, job)
                raise Problem(404, '接口不存在')
            except Problem as e:
                self.send(e.status, {'error': e.message})
            except (ValueError, TypeError, UnicodeError):
                self.send(400, {'error': '请求格式错误'})
            except Exception:
                self.send(500, {'error': '服务暂不可用，请保留任务标识联系管理员'})

        do_GET = run_request
        do_POST = run_request
    return Handler


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', required=True)
    p.add_argument('--port', type=int, default=8787)
    p.add_argument('--issue-invite-file')
    p.add_argument('--refund-confirmed-failure')
    args = p.parse_args()
    os.umask(0o077)
    store = Store(args.db)
    if args.issue_invite_file:
        with open(args.issue_invite_file, 'x', encoding='utf-8') as f:
            f.write(store.invite())
        print('试用凭证已写入指定文件，未显示内容')
    elif args.refund_confirmed_failure:
        store.refund_confirmed_failure(args.refund_confirmed_failure)
        print('已退回一次积分')
    else:
        ThreadingHTTPServer(('127.0.0.1', args.port), handler(store)).serve_forever()


if __name__ == '__main__':
    main()
