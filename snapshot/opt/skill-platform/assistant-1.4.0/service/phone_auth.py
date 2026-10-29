"""Browser SMS verification and account recovery using the existing ledger."""
import base64
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
import uuid
from http.cookies import SimpleCookie


class TencentSms:
    def __init__(self):
        path = os.environ.get('IMAGE_SMS_CONFIG_FILE')
        try:
            self.config = json.loads(Path(path).read_text(encoding='utf-8')) if path else {}
            if not isinstance(self.config, dict):
                self.config = {}
        except (OSError, ValueError):
            self.config = {}
        self.enabled = self.config.get('enabled') is True
        required = ('secret_id', 'secret_key', 'sdk_app_id', 'sign_name', 'template_id')
        try:
            sdk = importlib.util.find_spec('tencentcloud.sms') is not None
        except ModuleNotFoundError:
            sdk = False
        self.ready = self.enabled and sdk and all(isinstance(self.config.get(k), str) and self.config[k].strip() for k in required)

    def send(self, phone, code):
        if not self.ready:
            raise RuntimeError('SMS unavailable')
        from tencentcloud.common.credential import Credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.sms.v20210111.sms_client import SmsClient
        from tencentcloud.sms.v20210111.models import SendSmsRequest
        http = HttpProfile()
        http.endpoint = 'sms.tencentcloudapi.com'
        http.reqTimeout = 10
        profile = ClientProfile()
        profile.httpProfile = http
        request = SendSmsRequest()
        request.SmsSdkAppId = self.config['sdk_app_id']
        request.SignName = self.config['sign_name']
        request.TemplateId = self.config['template_id']
        request.PhoneNumberSet = [phone]
        # Template must use one code variable, or code + minutes when configured.
        request.TemplateParamSet = [code] + (['5'] if self.config.get('minutes_parameter') is True else [])
        response = SmsClient(Credential(self.config['secret_id'], self.config['secret_key']),
                             self.config.get('region', 'ap-guangzhou'), profile).SendSms(request)
        values = response.SendStatusSet
        if len(values) != 1 or values[0].Code != 'Ok':
            raise RuntimeError('SMS send not accepted')


class PhoneAuth:
    def __init__(self, store, problem, sender=None, key=None):
        self.store, self.problem = store, problem
        self.sender = sender if sender is not None else TencentSms()
        self.key = key or getattr(self.sender, 'config', {}).get('phone_hmac_key') or os.environ.get('IMAGE_PHONE_HMAC_KEY', '')
        self.lock = threading.RLock()
        with store.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS phone_accounts(phone_hash TEXT PRIMARY KEY,user_id TEXT UNIQUE NOT NULL,last4 TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS phone_auth_sessions(id TEXT PRIMARY KEY,ticket_hash TEXT UNIQUE,poll_hash TEXT NOT NULL,
                browser_hash TEXT,origin_uid TEXT,expires INTEGER NOT NULL,phone_hash TEXT,last4 TEXT,
                code_hash TEXT,code_expires INTEGER,attempts INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL,
                user_id TEXT,granted INTEGER NOT NULL DEFAULT 0,session_hash TEXT);
            CREATE TABLE IF NOT EXISTS phone_auth_limits(scope TEXT NOT NULL,day TEXT NOT NULL,count INTEGER NOT NULL,last INTEGER NOT NULL,
                PRIMARY KEY(scope,day));
            ''')

    @property
    def ready(self):
        return self.sender.ready and len(self.key) >= 32

    def keyed(self, purpose, value):
        return hmac.new(self.key.encode(), (purpose + ':' + value).encode(), hashlib.sha256).hexdigest()

    def secret(self, purpose, value):
        raw = hmac.new(self.key.encode(), (purpose + ':' + value).encode(), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(raw).decode().rstrip('=')

    @staticmethod
    def digest(value):
        return hashlib.sha256(value.encode()).hexdigest()

    def require_ready(self):
        if not self.ready:
            raise self.problem(503, '手机号验证暂未开放，已有账户可继续使用。')

    def limit(self, c, scope, cap, cooldown=0):
        now = int(time.time())
        day = time.strftime('%Y-%m-%d', time.gmtime(now))
        row = c.execute('SELECT * FROM phone_auth_limits WHERE scope=? AND day=?', (scope, day)).fetchone()
        if row and (row['count'] >= cap or now - row['last'] < cooldown):
            raise self.problem(429, '验证码请求较多，请稍后再试。')
        c.execute('INSERT INTO phone_auth_limits VALUES(?,?,1,?) ON CONFLICT(scope,day) DO UPDATE SET count=count+1,last=excluded.last', (scope, day, now))

    def create(self, body, ip):
        if not self.ready:
            return {'ready': False, 'notice': '手机号验证暂未开放，已有账户可继续使用。'}
        origin = None
        token = body.get('existing_credential')
        if token is not None:
            if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
                raise self.problem(400, '账户凭据格式错误')
            with self.store.connect() as c:
                row = c.execute('SELECT user_id FROM trial_claims WHERE hash=? UNION SELECT user_id FROM sessions WHERE hash=?', (self.digest(token), self.digest(token))).fetchone()
            if not row:
                raise self.problem(401, '请先恢复原账户再关联手机')
            origin = row['user_id']
        sid, ticket, poll = str(uuid.uuid4()), secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            self.limit(c, 'create:' + self.keyed('ip', ip), 30)
            c.execute('INSERT INTO phone_auth_sessions(id,ticket_hash,poll_hash,origin_uid,expires,status) VALUES(?,?,?,?,?,?)',
                      (sid, self.digest(ticket), self.digest(poll), origin, int(time.time()) + 900, 'waiting'))
        return {'ready': True, 'id': sid, 'poll_secret': poll, 'url': 'https://myplanestore.com/auth/#ticket=' + ticket, 'expires_in': 900}

    def redeem(self, ticket):
        self.require_ready()
        if not isinstance(ticket, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', ticket):
            raise self.problem(400, '授权链接无效')
        cookie = secrets.token_urlsafe(32)
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM phone_auth_sessions WHERE ticket_hash=? AND expires>?', (self.digest(ticket), time.time())).fetchone()
            if not row:
                raise self.problem(410, '授权链接已过期或已打开，请从助手重新打开。')
            c.execute('UPDATE phone_auth_sessions SET ticket_hash=NULL,browser_hash=? WHERE id=?', (self.digest(cookie), row['id']))
        return cookie

    def browser_session(self, c, cookie):
        if not isinstance(cookie, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', cookie):
            raise self.problem(401, '请从生图助手打开授权页面。')
        row = c.execute('SELECT * FROM phone_auth_sessions WHERE browser_hash=? AND expires>?', (self.digest(cookie), time.time())).fetchone()
        if not row:
            raise self.problem(401, '页面已过期，请从助手重新打开。')
        return row

    def send_code(self, cookie, body, ip):
        self.require_ready()
        if body.get('accepted') is not True:
            raise self.problem(400, '请同意手机号用于账户关联与登录')
        phone = body.get('phone')
        if not isinstance(phone, str):
            raise self.problem(400, '请输入中国大陆手机号')
        phone = phone.strip()
        if re.fullmatch(r'1[3-9][0-9]{9}', phone):
            phone = '+86' + phone
        if not re.fullmatch(r'\+861[3-9][0-9]{9}', phone):
            raise self.problem(400, '首版支持中国大陆手机号')
        ph = self.keyed('phone', phone)
        code = f'{secrets.randbelow(1000000):06d}'
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self.browser_session(c, cookie)
            if row['status'] in ('verified', 'done'):
                raise self.problem(409, '此页面已验证完成')
            self.limit(c, 'phone:' + ph, 5, 60)
            self.limit(c, 'send-ip:' + self.keyed('ip', ip), 10)
            self.limit(c, 'global', int(os.environ.get('IMAGE_SMS_DAILY_CAP', '100')))
            c.execute("UPDATE phone_auth_sessions SET phone_hash=?,last4=?,code_hash=NULL,code_expires=NULL,attempts=0,status='sending' WHERE id=?", (ph, phone[-4:], row['id']))
        # Failed/uncertain sends still count toward limits; never auto-resend.
        try:
            self.sender.send(phone, code)
        except Exception:
            raise self.problem(503, '验证码暂未发出，请稍后重试。') from None
        with self.store.connect() as c:
            c.execute("UPDATE phone_auth_sessions SET code_hash=?,code_expires=?,status='sent' WHERE id=? AND status='sending' AND phone_hash=?",
                      (self.keyed('otp:' + row['id'], code), int(time.time()) + 300, row['id'], ph))
        return {'sent': True, 'retry_after': 60, 'expires_in': 300}

    def verify(self, cookie, body, ip):
        self.require_ready()
        code = body.get('code')
        if not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code):
            raise self.problem(400, '请输入6位短信验证码')
        error = None
        with self.lock:
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                row = self.browser_session(c, cookie)
                self.limit(c, 'verify-ip:' + self.keyed('ip', ip), 50)
                if row['status'] != 'sent' or not row['code_hash'] or row['attempts'] >= 5 or row['code_expires'] <= time.time():
                    error = self.problem(400, '验证码已失效，请重新获取。')
                elif not hmac.compare_digest(row['code_hash'], self.keyed('otp:' + row['id'], code)):
                    c.execute('UPDATE phone_auth_sessions SET attempts=attempts+1 WHERE id=?', (row['id'],))
                    error = self.problem(400, '验证码不正确，请核对后重试。')
                else:
                    c.execute("UPDATE phone_auth_sessions SET status='verified',code_hash=NULL WHERE id=?", (row['id'],))
            if error:
                raise error
            return self.complete(row['id'], ip)

    def complete(self, sid, ip):
        with self.lock:
            with self.store.connect() as c:
                row = c.execute('SELECT * FROM phone_auth_sessions WHERE id=?', (sid,)).fetchone()
                if row['status'] == 'done':
                    return {'verified': True}
                if row['status'] != 'verified':
                    raise self.problem(409, '验证尚未完成')
                account = c.execute('SELECT * FROM phone_accounts WHERE phone_hash=?', (row['phone_hash'],)).fetchone()
                origin_phone = c.execute('SELECT phone_hash FROM phone_accounts WHERE user_id=?', (row['origin_uid'],)).fetchone()
            if (account and row['origin_uid'] and account['user_id'] != row['origin_uid']) or (origin_phone and origin_phone['phone_hash'] != row['phone_hash']):
                raise self.problem(409, '该手机与当前账户不同，请联系管理员核对原账户，余额未改变。')
            granted = False
            if account:
                uid = account['user_id']
            elif row['origin_uid']:
                uid = row['origin_uid']
            else:
                # Stable server-only identity makes concurrent/new-device registration grant once.
                seed = self.secret('phone-account', row['phone_hash'])
                result = self.store.register(seed, ip, True, 10)
                uid = self.store.user(result['token'])
                granted = result['granted']
            token = self.secret('phone-session', sid)
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                c.execute('INSERT OR IGNORE INTO phone_accounts VALUES(?,?,?)', (row['phone_hash'], uid, row['last4']))
                actual = c.execute('SELECT user_id FROM phone_accounts WHERE phone_hash=?', (row['phone_hash'],)).fetchone()
                if not actual or actual['user_id'] != uid:
                    raise self.problem(409, '账户关联需要核查')
                c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)', (self.digest(token), uid, int(time.time()) + 7 * 86400))
                c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)', (self.digest(token), uid, int(time.time())))
                c.execute("UPDATE phone_auth_sessions SET status='done',user_id=?,granted=?,session_hash=? WHERE id=?", (uid, int(granted), self.digest(token), sid))
            return {'verified': True}

    def poll(self, body, ip):
        self.require_ready()
        sid, secret = body.get('id'), body.get('poll_secret')
        if not isinstance(sid, str) or not isinstance(secret, str) or len(secret) != 43:
            raise self.problem(400, '授权状态参数无效')
        with self.store.connect() as c:
            row = c.execute('SELECT * FROM phone_auth_sessions WHERE id=? AND poll_hash=? AND expires>?', (sid, self.digest(secret), time.time())).fetchone()
        if not row:
            raise self.problem(410, '授权已过期，请重新打开。')
        if row['status'] == 'verified':
            self.complete(sid, ip)
            return self.poll(body, ip)
        if row['status'] != 'done':
            return {'status': 'waiting'}
        return {'status': 'verified', 'token': self.secret('phone-session', sid),
                'balance_points': self.store.balance(row['user_id']) * 1000, 'granted': bool(row['granted']), 'phone_last4': row['last4']}


def phone_handler(parent, auth):
    class Handler(parent):
        def run_request(self):
            if not self.path.startswith('/phone-auth/'):
                return super().run_request()
            try:
                if self.path == '/phone-auth/status' and self.command == 'GET':
                    return self.send(200, {'ready': auth.ready})
                if self.command != 'POST':
                    raise auth.problem(404, '接口不存在')
                self.connection.settimeout(15)
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096:
                    raise auth.problem(413, '请求长度无效')
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise auth.problem(400, '参数格式错误')
                ip = self.headers.get('X-Real-IP', self.client_address[0])
                if self.path == '/phone-auth/create':
                    return self.send(200, auth.create(body, ip))
                if self.path == '/phone-auth/poll':
                    return self.send(200, auth.poll(body, ip))
                if (self.headers.get('Origin') != 'https://myplanestore.com' or self.headers.get('X-Phone-Request') != '1'
                        or self.headers.get('Content-Type', '').split(';')[0] != 'application/json'):
                    raise auth.problem(403, '请从授权网页操作')
                if self.path == '/phone-auth/redeem':
                    cookie = auth.redeem(body.get('ticket'))
                    return self.send(200, {'ok': True}, cookie='image_phone_auth=' + cookie + '; Path=/phone-auth/; HttpOnly; Secure; SameSite=Strict; Max-Age=900')
                cookies = SimpleCookie(self.headers.get('Cookie', ''))
                cookie = cookies['image_phone_auth'].value if 'image_phone_auth' in cookies else ''
                if self.path == '/phone-auth/send':
                    return self.send(200, auth.send_code(cookie, body, ip))
                if self.path == '/phone-auth/verify':
                    return self.send(200, auth.verify(cookie, body, ip))
                raise auth.problem(404, '接口不存在')
            except auth.problem as error:
                return self.send(error.status, {'error': error.message})
            except (ValueError, TypeError, KeyError):
                return self.send(400, {'error': '请求格式错误'})
            except Exception:
                return self.send(503, {'error': '授权暂未完成，请稍后重试。'})
        do_GET = run_request
        do_POST = run_request
    return Handler
