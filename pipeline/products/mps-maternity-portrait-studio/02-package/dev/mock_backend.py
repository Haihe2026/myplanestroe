"""按接口约定实现的进程内模拟后端（合成账户、Mock 出图）。不打进上架包，不联网。

行为依据（规格固定提交 2d32cc07；quick-entry 的 registration/checkout 与 membership-link 均带 expires_in=300）：
- registration_entries.py prepare/status：ready / checkout / registration、registration_pending / registered
- server.py generate：同键同体重放不重复扣费，同键异体 409，余额不足 402，扣费在校验之后
- shared_platform.py：/skill-jobs 用 Skill Bearer；/jobs/by-key、/jobs/{id}、/jobs/{id}/image
- image_inputs.py：references 仅 {mime, content}，需 reference_consent=true，PNG/JPEG，5MB
- dialogue_store.py / dialogue_gateway.py：首次对话 8 字段白名单、200 返回 event_id/receipt/duplicate；link 只收 event_id/receipt/product
- backend-patch/gemini-support-20261107/gemini_support.py（已部署，见 01-deployment-verification-20261107.json）：
  GET /consumption-history（page 1..100000、page_size 1..50，只收这两个参数）、POST /support-tickets（Idempotency-Key 16..100，
  正文只 category/text/job_id?，同键同体重放、异体 409，job 非本人 404）、GET /support-tickets/{mpsg-32hex}（他人 404）；
  三者只认账户 Bearer（43 位），Skill 凭证 401；不扣次数
"""
import base64
import hashlib
import json
import re
import secrets
import struct
import uuid
import zlib

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mps-maternity-portrait-studio', 'scripts'))
import studio  # noqa: E402

ALLOWED_JOB = {'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent', 'role', 'platform', 'slot', 'image_retention', 'reference_purpose'}
TELEMETRY_FIELDS = {'event_id', 'installation_id', 'skill_id', 'skill_name', 'skill_version', 'channel', 'client_occurred_at', 'is_test'}


def make_png(w, h, rgb=(200, 200, 200)):
    raw = b''.join(b'\x00' + bytes(rgb) * w for _ in range(h))

    def chunk(k, b):
        return struct.pack('>I', len(b)) + k + b + struct.pack('>I', zlib.crc32(k + b) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')


class Mock:
    def __init__(self):
        self.users = {}          # install_secret -> dict(balance, key)
        self.keys = {}           # skill key -> secret
        self.jobs = {}           # job id -> dict
        self.idem = {}           # (secret, idem) -> job id
        self.calls = []
        self.charges = 0
        self.scenario = {}
        self.output_size = None  # None：按请求画幅出图；设成元组模拟实际尺寸偏差
        self.telemetry = {}      # installation_id -> record
        self.telemetry_calls = []
        self.telemetry_status = None
        self.link_calls = []
        self.membership_links = 0
        self.tickets = {}        # id -> dict(owner, ...)
        self.ticket_keys = {}    # (owner, key) -> (id, digest)
        self.ledger_unknown = set()   # 无账本的任务 id

    # 测试辅助 ------------------------------------------------------
    def authorize(self, secret, balance=0):
        self.users.setdefault(secret, dict(balance=0, key=None))['balance'] = balance

    def rotate_key(self, secret):
        """A3-TRV-01-R1：模拟用户在网页轮换/撤销技能凭证——旧凭证立即失效（任何认证均 401），下次 /skill-key 发新凭证。"""
        u = self.users[secret]
        old = u['key']
        self.keys.pop(old, None)
        u['key'], u['bound'] = None, False
        return old

    def secret_of(self, auth):
        tok = (auth or '').replace('Bearer ', '')
        if tok in self.users:
            return tok
        if tok in self.keys:
            return self.keys[tok]
        return None

    # 业务网关 ------------------------------------------------------
    def transport(self, method, url, body, headers, timeout, binary):
        path = url.split('/platform-api/gemini', 1)[1]
        self.calls.append((method, path, body, dict(headers)))
        assert headers.get('X-Skill-Source') == 'mps-maternity-portrait-studio'
        assert headers.get('X-Skill-Channel') == 'workbuddy_skill'
        assert 'Origin' not in headers and 'Cookie' not in headers

        def ok(d):
            return 200, json.dumps(d).encode()

        def err(code):
            raise studio.GatewayError(code)
        auth = headers.get('Authorization')
        if path == '/quick-entry' and method == 'POST':
            s = body.get('install_secret')
            if not isinstance(s, str) or len(s) != 43:
                err(400)
            if s in self.users:
                u = self.users[s]
                if u['balance'] > 0:
                    return ok(dict(status='ready', remaining_uses=u['balance']))
                return ok(dict(status='checkout', url='https://myplanestore.com/membership/gemini/#ticket=' + secrets.token_urlsafe(8), expires_in=300, remaining_uses=0))
            return ok(dict(status='registration', url='https://myplanestore.com/membership/gemini/register/#entry=' + secrets.token_urlsafe(8), expires_in=300))
        if path == '/quick-entry/status' and method == 'POST':
            s = body.get('install_secret')
            if s in self.users:
                return ok(dict(status='registered', remaining_uses=self.users[s]['balance']))
            return ok(dict(status='registration_pending'))
        if path == '/balance' and method == 'GET':
            s = auth and auth[7:] in self.users and auth[7:]
            if not s:
                err(401)
            return ok(dict(remaining_uses=self.users[s]['balance'], balance=self.users[s]['balance'], shared_uses=self.users[s]['balance'], legacy_uses=0))
        if path == '/membership-link' and method == 'POST':
            s = auth and auth[7:] in self.users and auth[7:]
            if not s:
                err(401)
            self.membership_links += 1
            return ok(dict(url='https://myplanestore.com/membership/#ticket=' + secrets.token_urlsafe(8), expires_in=300))
        if path == '/skill-key' and method == 'POST':
            s = auth and auth[7:] in self.users and auth[7:]
            if not s:
                err(401)
            u = self.users[s]
            if u['balance'] < 1 and not u['key']:
                return ok(dict(state='pending_payment', required=False))
            if not u['key']:
                u['key'] = 'mpskill_' + secrets.token_hex(16) + '_' + secrets.token_urlsafe(32)
                self.keys[u['key']] = s
            return ok(dict(state='ready', key=u['key']))
        if path == '/skill-key/bound' and method == 'POST':
            # A3-TRV-01：scenario['bound'] 可设 false / missing / timeout / 500 / 401 / garbage，模拟绑定未确认
            s = auth and auth[7:] in self.users and auth[7:]
            if not s:
                err(401)
            mode = self.scenario.get('bound')
            if mode == 'timeout':
                err(0)
            if mode in (500, 401):
                err(mode)
            if mode == 'false':
                return ok(dict(bound=False))
            if mode == 'missing':
                return ok(dict())
            if mode == 'garbage':
                return 200, b'not json'
            if mode == 'truthy':
                return ok(dict(bound='true'))
            if self.keys.get(body.get('key')) != s:
                err(401)  # 已轮换/撤销或不属于本账户的凭证：服务端认证即拒绝（对应 skill_access.acknowledge → authenticate）
            if body.get('key') != self.users[s]['key']:
                return ok(dict(bound=False))
            self.users[s]['bound'] = True
            return ok(dict(bound=True))
        if path == '/skill-jobs' and method == 'POST':
            tok = (auth or '')[7:]
            if tok not in self.keys:
                err(401)
            s = self.keys[tok]
            if self.scenario.get('rate_limit'):
                err(429)
            if set(body) - ALLOWED_JOB or body.get('confirmed') is not True or body.get('image_engine') != 'photo-retouch-sunburst':
                err(400)
            if body.get('size') not in ('1024x1024', '1536x1024', '1024x1536'):  # 适配器已映射的三种画幅
                err(400)
            refs = body.get('references')
            if body.get('reference_consent') is not True or not isinstance(refs, list) or len(refs) != 1 or set(refs[0]) != {'mime', 'content'}:
                err(422)
            raw = base64.b64decode(refs[0]['content'], validate=True)
            if len(raw) > 5 * 1024 * 1024 or not (raw.startswith(b'\x89PNG') or raw.startswith(b'\xff\xd8')):
                err(400)
            if self.scenario.get('policy'):
                err(422)
            idem = headers.get('Idempotency-Key')
            rhash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            if (s, idem) in self.idem:
                j = self.jobs[self.idem[(s, idem)]]
                if j['hash'] != rhash:
                    err(409)
                return ok(dict(id=j['id'], status=j['status'], replayed=True))
            if self.users[s]['balance'] < 1:
                err(402)
            jid = str(uuid.uuid4())
            self.users[s]['balance'] -= 1
            self.charges += 1
            pend = self.scenario.get('pending_rounds', 0)
            status = 'pending' if pend else ('failed' if self.scenario.get('fail') else 'succeeded')
            self.jobs[jid] = dict(id=jid, hash=rhash, status=status, rounds=pend, owner=s,
                                  size=tuple(int(x) for x in body['size'].split('x')))
            self.idem[(s, idem)] = jid
            if self.scenario.get('submit_lost'):
                err(0)  # 已扣费建单，但客户端没收到应答
            if self.scenario.get('submit_5xx'):
                err(502)
            return ok(dict(id=jid, status=status, remaining_uses=self.users[s]['balance']))
        if path.startswith('/consumption-history') or path.startswith('/support-tickets'):
            return self.support(method, path, body, headers)
        m = re.fullmatch(r'/jobs/by-key/(.+)', path)
        if m and method == 'GET':
            s = self.secret_of(auth)
            if not s:
                err(401)
            from urllib.parse import unquote
            jid = self.idem.get((s, unquote(m.group(1))))
            if not jid:
                err(404)
            return ok(dict(id=jid, status=self.jobs[jid]['status']))
        m = re.fullmatch(r'/jobs/([0-9a-f-]{36})(/image)?', path)
        if m and method == 'GET':
            s = self.secret_of(auth)
            if not s:
                err(401)
            if self.scenario.get('auth_expired_on_poll') and not m.group(2):
                err(401)
            j = self.jobs.get(m.group(1))
            if not j or j['owner'] != s:
                err(404)
            if m.group(2):
                if self.scenario.get('image_fail', 0) > 0:
                    self.scenario['image_fail'] -= 1
                    err(0)
                if j['status'] != 'succeeded':
                    err(409)
                return 200, make_png(*(self.output_size or j['size']), rgb=(255, 255, 255))
            if self.scenario.get('poll_down'):
                err(0)
            if self.scenario.get('poll_glitch', 0) > 0:
                self.scenario['poll_glitch'] -= 1
                err(0)
            if j['status'] == 'pending' and j['rounds'] > 0:
                j['rounds'] -= 1
                if j['rounds'] == 0:
                    j['status'] = 'failed' if self.scenario.get('fail') else 'succeeded'
            return ok(dict(id=j['id'], status=j['status']))
        err(404)

    # 消费记录与工单 ------------------------------------------------
    def support(self, method, path, body, headers):
        from urllib.parse import urlsplit, parse_qs

        def ok(d):
            return 200, json.dumps(d).encode()

        def err(code):
            raise studio.GatewayError(code)
        if self.scenario.get('support_down'):
            err(0)
        if self.scenario.get('support_busy'):
            err(503)
        auth = headers.get('Authorization', '')
        if not re.fullmatch(r'Bearer [A-Za-z0-9_-]{43}', auth) or auth[7:] not in self.users:
            err(401)  # Skill 凭证、失效凭证都不接受
        uid = auth[7:]
        u = urlsplit(path)
        q = parse_qs(u.query, keep_blank_values=True)
        if u.path == '/consumption-history':
            if method != 'GET' or set(q) - {'page', 'page_size'} or any(len(v) != 1 for v in q.values()):
                err(400)
            page, size = int(q.get('page', ['1'])[0]), int(q.get('page_size', ['20'])[0])
            if not (1 <= page <= 100000 and 1 <= size <= 50):
                err(400)
            mine = [j for j in self.jobs.values() if j['owner'] == uid]
            mine.reverse()
            items = []
            for j in mine[(page - 1) * size: page * size]:
                known = j['id'] not in self.ledger_unknown
                st = j['status']
                charged = (1 if st == 'succeeded' else (0 if st == 'failed' and j.get('refunded') else None)) if known else None
                items.append(dict(job_id=j['id'], occurred_at=1762480000, content='通用生图任务', status=st,
                                  charged_uses=charged, reserved_uses=1 if known and st in ('pending', 'needs_review') else None,
                                  refunded_uses=(1 if j.get('refunded') else 0) if known else None,
                                  unit='image_use', ledger_available=known))
            return ok(dict(items=items, total=len(mine), page=page, page_size=size, product='gemini',
                           scope='current_shared_database_gemini_jobs', content_scope='x'))
        if u.path == '/support-tickets':
            if method != 'POST' or q:
                err(405 if method != 'POST' else 400)
            key = headers.get('Idempotency-Key') or ''
            if not re.fullmatch(r'[A-Za-z0-9_.:-]{16,100}', key):
                err(400)
            if not isinstance(body, dict) or set(body) - {'category', 'text', 'job_id'}:
                err(400)
            if body.get('category') not in ('billing', 'image_quality', 'workflow', 'suggestion', 'other') or \
                    not isinstance(body.get('text'), str) or not 1 <= len(body['text']) <= 2000 or not body['text'].strip():
                err(400)
            jid = body.get('job_id')
            if jid is not None and (jid not in self.jobs or self.jobs[jid]['owner'] != uid):
                err(404)
            digest = hashlib.sha256(json.dumps([body.get('category'), body.get('text'), jid], ensure_ascii=False).encode()).hexdigest()
            if (uid, key) in self.ticket_keys:
                tid, d0 = self.ticket_keys[(uid, key)]
                if d0 != digest:
                    err(409)
                return ok(dict(ticket=self.public(tid), replayed=True))
            tid = 'mpsg-' + uuid.uuid4().hex
            self.tickets[tid] = dict(owner=uid, id=tid, category=body['category'], text=body['text'], job_id=jid,
                                     status='open', reply=None, created=1762480000, updated=1762480000,
                                     response_due_at=self.scenario.get('due'))
            self.ticket_keys[(uid, key)] = (tid, digest)
            if self.scenario.get('ticket_lost_once'):
                self.scenario['ticket_lost_once'] = False
                err(0)  # 已建单但应答丢失
            return ok(dict(ticket=self.public(tid), replayed=False))
        m = re.fullmatch(r'/support-tickets/(.*)', u.path)
        if m and method == 'GET':
            if q:
                err(400)
            t = self.tickets.get(m.group(1))
            if not t or t['owner'] != uid:
                err(404)
            return ok(dict(ticket=self.public(t['id'])))
        err(404)

    def public(self, tid):
        t = self.tickets[tid]
        return {k: t[k] for k in ('id', 'category', 'text', 'job_id', 'status', 'reply', 'created', 'updated', 'response_due_at')}

    def operator_reply(self, tid, status, reply):
        self.tickets[tid].update(status=status, reply=reply)

    # 首次对话上报 --------------------------------------------------
    def telemetry_transport(self, url, body, headers, timeout):
        assert timeout <= 2
        if url.endswith('/link'):
            self.link_calls.append((body, dict(headers)))
            if set(body) - {'event_id', 'receipt', 'product'} or body.get('product') != 'gemini':
                return 400, b'{}'
            if not re.fullmatch(r'Bearer [A-Za-z0-9_-]{43}', headers.get('Authorization', '')):
                return 401, b'{}'
            return 200, json.dumps(dict(linked=True, event_id=body['event_id'])).encode()
        self.telemetry_calls.append((body, dict(headers)))
        assert 'Authorization' not in headers
        if self.telemetry_status:
            return self.telemetry_status, b''
        if set(body) - TELEMETRY_FIELDS or len(json.dumps(body).encode()) > 4096:
            return 400, b'{}'
        inst = body['installation_id']
        dup = inst in self.telemetry
        if not dup:
            self.telemetry[inst] = dict(body)
        rec = self.telemetry[inst]
        receipt = base64.urlsafe_b64encode(hashlib.sha256(rec['event_id'].encode()).digest()).decode().rstrip('=')
        return 200, json.dumps(dict(event_id=rec['event_id'], received_at=1, receipt=receipt, duplicate=dup)).encode()
