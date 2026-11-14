#!/usr/bin/env python3
"""敦煌写真照相馆 本地客户端（Python 3.7+ 标准库）。

stdout 第一行是一行 JSON 信号，之后是固定话术；stderr 只放对客进度。
退出码：0 完成；2 可续接（等待用户动作）；3 参数或服务错误；4 登录信息已失效并已清除。
"""
import argparse
import base64
import datetime
import hashlib
import html
import json
import os
import re
import secrets
import shutil
import sys
import time
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_images  # noqa: E402
import png_local  # noqa: E402
import telemetry  # noqa: E402
import private_store
import http_bytes
import theme as T
import welcome_copy as W  # noqa: E402

SKILL_ID = 'mps-dunhuang-portrait-studio'
SKILL_VERSION = '1.0.1'
CHANNEL = 'workbuddy_skill'
ORIGIN = 'https://myplanestore.com'
API_PREFIX = '/platform-api/gemini'
FIRST_PARTY = ('https://aistore.zhaopintong.com', 'https://myplanestore.com')
LINK_PATHS = ('/membership/', '/membership/gemini/', '/membership/gemini/register/', '/auth/wechat/')

# Per-command budgets. All read attempts, including by-key and credential-recovery GETs, share caps.
REQUEST_TIMEOUT_S = 90
QUERY_TIMEOUT_S = 15
POLL_INTERVAL_S = 3
POLL_ATTEMPTS = 6
POLL_WINDOW_S = 120
DOWNLOAD_TIMEOUT_S = 30
DOWNLOAD_WINDOW_S = 120
IMAGE_MAX_GETS = 2
ACCOUNT_MAX_REQUESTS = 4
PROCESS_MARGIN_S = 90
RATE_LIMIT_WAIT_S = 0
OUTER_TIMEOUT_S = 420
_BUDGET = None


def reset_budget():
    global _BUDGET
    _BUDGET = dict(start=time.monotonic(), queries=0, images=0, accounts=0,
                   query_start=None, download_start=None)


def _budget_timeout(path, requested, binary):
    if _BUDGET is None:
        reset_budget()
    now = time.monotonic()
    remaining = OUTER_TIMEOUT_S - (now - _BUDGET['start'])
    if remaining <= 0:
        raise GatewayError(0)
    if path.startswith('/jobs/'):
        counter, maximum = ('images', IMAGE_MAX_GETS) if binary else ('queries', POLL_ATTEMPTS)
        phase, window = ('download_start', DOWNLOAD_WINDOW_S) if binary else ('query_start', POLL_WINDOW_S)
        if _BUDGET[counter] >= maximum:
            raise GatewayError(0)
        if _BUDGET[phase] is None:
            _BUDGET[phase] = now
        remaining = min(remaining, window - (now - _BUDGET[phase]))
        if remaining <= 0:
            raise GatewayError(0)
        _BUDGET[counter] += 1
        requested = DOWNLOAD_TIMEOUT_S if binary else QUERY_TIMEOUT_S
    elif path != '/skill-jobs':
        if _BUDGET['accounts'] >= ACCOUNT_MAX_REQUESTS:
            raise GatewayError(0)
        _BUDGET['accounts'] += 1
        requested = min(requested, QUERY_TIMEOUT_S)
    return max(0.001, min(requested, remaining))


SIZES = {'portrait': '1024x1536', 'landscape': '1536x1024', 'square': '1024x1024'}  # 适配器已映射的 1K 画幅
IMAGE_ENGINE = 'photo-retouch-sunburst'
BODY_FIELDS = frozenset({'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent'})
IDEM_RE = re.compile(r'[A-Za-z0-9_.:-]{16,100}')
SECRET_RE = re.compile(r'[A-Za-z0-9_-]{43}')
SKILL_KEY_RE = re.compile(r'mpskill_[0-9a-f]{32}_[A-Za-z0-9_-]{43}')

EXIT_OK, EXIT_WAIT, EXIT_ERROR, EXIT_RESET = 0, 2, 3, 4

SERIES = T.SERIES
SCENES = T.SCENES
LOOKS = T.LOOKS
DISCLOSURE = 'AI 生成敦煌写真，非实拍'

TEXT_MAX_CHARS = 40
LOCKED_STATES = ('submit_unknown', 'submitted', 'download_pending')
FINISHED_STATES = ('delivered', 'failed', 'rejected')
REPLAN_STATE = 'replanning'  # 改方案已开始、新方案尚未成功保存：旧确认与待提交键已作废，不能 run/resume/regenerate


# ---------------------------------------------------------------- 输出

def emit(signal, text='', code=EXIT_OK, **fields):
    print(json.dumps(dict(signal=signal, **fields), ensure_ascii=False))
    if text:
        print(text)
    return code


def progress(text):
    print(text, file=sys.stderr)


# ---------------------------------------------------------------- 本地状态

STATE_HOME = None  # 测试时指向隔离目录；默认用户主目录


def state_dir():
    return private_store.directory(os.path.join(STATE_HOME or os.path.expanduser('~'), SKILL_ID))


# Markdown 链接目标里会断链的字符：空白、括号、尖括号；% 一并编码，保证可逆
_MD_LINK_UNSAFE = {' ': '%20', '\t': '%09', '(': '%28', ')': '%29', '<': '%3C', '>': '%3E', '#': '%23', '?': '%3F'}


def md_safe_path(p):
    """给用户看的绝对路径：正斜杠（Markdown 不吞反斜杠），空格等断链字符做 URL 编码（%20）；`#`→%23、`?`→%3F，免得被当成链接片段或查询串截断。"""
    p = os.path.abspath(p).replace('\\', '/').replace('%', '%25')
    return ''.join(_MD_LINK_UNSAFE.get(c, c) for c in p)


def _path(name):
    parts = name.replace('\\', '/').split('/')
    if os.path.isabs(name) or any(part in ('', '.', '..') for part in parts):
        raise SystemExit(emit('stateUnsafe', '', EXIT_ERROR))
    p = state_dir()
    for part in parts:
        p = os.path.join(p, part)
        try:
            private_store._reject_link(p)
        except OSError:
            raise SystemExit(emit('stateUnsafe', '', EXIT_ERROR))
    return p


def read_json(name, default=None):
    try:
        with open(_path(name), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(name, data):
    private_store.atomic_json(_path(name), data)


def load_account():
    path = _path('account.json')
    if os.path.exists(path):
        private_store.restrict(path)
        try:
            with open(path, encoding='utf-8') as stream:
                a = json.load(stream)
        except (OSError, ValueError):
            raise ValueError('saved account unavailable')
        if not isinstance(a, dict) or (a.get('install_secret') and not SECRET_RE.fullmatch(a['install_secret'])):
            raise ValueError('saved original identity unavailable')
    else:
        a = {}
    if a.get('skill_key') and not SKILL_KEY_RE.fullmatch(a['skill_key']):
        a.pop('skill_key')
    if not a.get('skill_key'):
        a.pop('skill_key_bound', None)
    return a


def save_account(a):
    write_json('account.json', a)


def ensure_install_secret(a):
    """原安装身份只创建一次。"""
    if not a.get('install_secret'):
        a['install_secret'] = secrets.token_urlsafe(32)  # 43 位 URL-safe
        save_account(a)
    return a['install_secret']


def draft_name(draft_id):
    if not re.fullmatch(r'd-[0-9a-f]{32}', draft_id or ''):
        raise SystemExit(emit('draftInvalid', '', EXIT_ERROR))
    return os.path.join('drafts', draft_id + '.json')


def load_draft(draft_id):
    d = read_json(draft_name(draft_id))
    if not isinstance(d, dict):
        raise SystemExit(emit('draftMissing', '', EXIT_ERROR))
    return d


def save_draft(d):
    write_json(draft_name(d['draft_id']), d)


# ---------------------------------------------------------------- 网络

class GatewayError(Exception):
    def __init__(self, status):
        super().__init__('gateway status %s' % status)
        self.status = status


def _default_transport(method, url, body, headers, timeout, binary):
    limit = 16 * 1024 * 1024 if binary else 2 * 1024 * 1024
    try:
        return http_bytes.request(method, url, body, headers, timeout, limit)
    except (OSError, ValueError):
        raise GatewayError(0) from None


TRANSPORT = _default_transport  # 测试时替换为模拟或抛异常函数


def device():
    # 只按操作系统区分；无法可靠判断时报 unknown，不猜测
    return 'desktop' if sys.platform in ('darwin', 'win32') else 'unknown'


def call(method, path, body=None, auth=None, idem=None, binary=False, timeout=QUERY_TIMEOUT_S):
    headers = {'X-Skill-Source': SKILL_ID, 'X-Skill-Channel': CHANNEL, 'X-Skill-Device': device()}
    if auth:
        headers['Authorization'] = 'Bearer ' + auth
    if body is not None:
        headers['Content-Type'] = 'application/json'
        if path == '/skill-jobs':
            if not isinstance(body, dict) or set(body) != BODY_FIELDS:
                raise ValueError('unregistered field')
            if (body.get('confirmed') is not True or body.get('reference_consent') is not True or
                    body.get('image_engine') != IMAGE_ENGINE or body.get('size') not in SIZES.values() or
                    not isinstance(body.get('prompt'), str) or not 1 <= len(body['prompt']) <= 6000 or
                    not isinstance(body.get('references'), list) or len(body['references']) != 1):
                raise ValueError('invalid generation body')
            reference = body['references'][0]
            if (not isinstance(reference, dict) or set(reference) != {'mime', 'content'} or
                    reference['mime'] not in ('image/png', 'image/jpeg') or not isinstance(reference['content'], str)):
                raise ValueError('invalid reference')
    if idem is not None:
        if not IDEM_RE.fullmatch(idem):
            raise ValueError('task key')
        headers['Idempotency-Key'] = idem
    timeout = _budget_timeout(path, timeout, binary)
    status, raw = TRANSPORT(method, ORIGIN + API_PREFIX + path, body, headers, timeout, binary)
    if type(status) is not int or status < 200 or status >= 300:
        raise GatewayError(status if type(status) is int else 0)
    if binary:
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
            raise GatewayError(0)
        return raw
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError):
        raise GatewayError(0) from None
    if not isinstance(result, dict):
        raise GatewayError(0)
    return result


def trusted_link(url):
    """只接受服务端签发的本站链接，映射到当前可访问站点，保留 query/fragment。"""
    if not isinstance(url, str):
        raise GatewayError(0)
    u = urlsplit(url or '')
    if u.scheme + '://' + u.netloc not in FIRST_PARTY or u.username or u.password or u.path not in LINK_PATHS:
        raise GatewayError(0)
    return urlunsplit(('https', 'myplanestore.com', u.path, u.query, u.fragment))


def link_fresh(r):
    """服务端签发的短期链接必须带明确有效期：只有正整数秒的 expires_in 才算有效；缺失、0、负数、非整数都不转述。"""
    v = r.get('expires_in')
    return type(v) is int and v > 0


EXPIRED = 'expired'  # 链接已失效（区别于网络 0 和服务端错误码）


# ---------------------------------------------------------------- 提示词

route_scene = T.route_scene
route_intent = T.route_intent
strip_negated = T.strip_negated
outfit_of = T.outfit_of
outfit_conflict = T.outfit_conflict
look_name = T.look_name
outfit_text = T.outfit_text
build_prompt = T.build_prompt


def wait_text():
    return '1 到 4 分钟'


# ---------------------------------------------------------------- 命令

def cmd_first_turn(args):
    # Telemetry and local preview persistence are best effort; no business network on the first turn.
    text = args.text or ''
    draft_id = 'd-' + uuid.uuid4().hex
    images = [os.path.abspath(p) for p in (args.image or [])]
    kept = False
    try:
        telemetry.report_once(state_dir())
        save_draft(dict(draft_id=draft_id, created=_now(), text=text, images=images,
                        scene=None, size=None, look_profile=None, owner_consent=False,
                        upload_consent=False, pay_consent=False, idem=None, job_id=None, state='draft'))
        kept = True
    except (OSError, ValueError, SystemExit):
        pass
    account_words = (('history', ('消费记录', '使用记录')), ('balance', ('查余额', '剩余次数')),
                     ('paid', ('已付款', '已充值', '付好了')), ('auth', ('已授权', '恢复账户', '我的账户')),
                     ('topup', ('充值', '付费链接', '付款链接', '订单查询')))
    for command, words in account_words:
        if any(word in text for word in words):
            return emit('accountIntent', '', EXIT_WAIT, next_command=command, draft_kept=kept)
    explicit_request = any(word in text for word in
                           ('想做', '想拍', '想用', '想要', '要做', '要拍', '帮我', '制作', '生成', '做一张', '拍一张', '来一张'))
    has_need = bool(images) or bool(text.strip()) and (args.has_need or bool(route_scene(text)) and explicit_request)
    return emit('firstTurn', W.WELCOME + '\n' + W.first_turn_close(has_need), EXIT_OK,
                draft_id=draft_id if kept else None, draft_kept=kept, has_image=bool(images),
                welcome=W.WELCOME, demo_intro=W.DEMO_INTRO, suggested_scene=route_scene(text), intent=route_intent(text))


DEMO_FILE_RE = re.compile(r'[a-z0-9][a-z0-9_-]{0,40}\.(?:png|jpg|jpeg)')


def _demo_manifest(base):
    """读并校验示例清单：必须恰好是十个场景各一项（键集合与 SCENES 一致、不重复），字段齐全，文件名为裸文件名。
    任何异常返回 None，由调用方按资源不可用退出 3，不做部分展示。"""
    try:
        with open(os.path.join(base, 'demos.json'), encoding='utf-8') as f:
            demos = json.load(f)['demos']
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not isinstance(demos, list) or len(demos) != len(SCENES):
        return None
    keys = []
    for d in demos:
        if not isinstance(d, dict):
            return None
        if not all(isinstance(d.get(k), str) and d.get(k) for k in ('key', 'title', 'note', 'file')):
            return None
        if not DEMO_FILE_RE.fullmatch(d['file']):
            return None
        keys.append(d['key'])
    if len(set(keys)) != len(keys) or set(keys) != set(SCENES):
        return None
    return demos


def cmd_demo(args):
    # 只释放包内示例图：不联网、不读凭证。首次对话上报由同轮的 first-turn 负责。
    base = os.path.join(os.path.dirname(HERE), 'assets')
    demos = _demo_manifest(base)
    if demos is None:
        return emit('demoUnavailable', W.DEMO_UNAVAILABLE, EXIT_ERROR)
    if args.key:
        demos = [d for d in demos if d['key'] == args.key]
        if not demos:
            return emit('demoNotFound', '', EXIT_ERROR, key=args.key)
    # 先校验本次要求的完整集合全部在位，缺任何一张都不输出、不复制（不做部分成功）
    missing = [d['key'] for d in demos if not os.path.isfile(os.path.join(base, d['file']))]
    if missing:
        return emit('demoUnavailable', W.DEMO_UNAVAILABLE, EXIT_ERROR, missing=missing)
    out_dir = os.path.join(state_dir(), 'demos')
    os.makedirs(out_dir, mode=0o700, exist_ok=True)
    items = []
    for d in demos:
        src = os.path.join(base, d['file'])
        dst = os.path.join(out_dir, d['file'])
        try:
            if not os.path.isfile(dst) or _photo_digest(dst) != _photo_digest(src):
                shutil.copyfile(src, dst)
        except OSError:
            return emit('demoUnavailable', W.DEMO_UNAVAILABLE, EXIT_ERROR)
        items.append(dict(key=d['key'], title=d['title'], note=d['note'], path=md_safe_path(dst)))
    if len(items) != len(demos):
        return emit('demoUnavailable', W.DEMO_UNAVAILABLE, EXIT_ERROR)
    return emit('demos', W.DEMO_INTRO, EXIT_OK, items=items)


def _clean_text(text):
    text = ' '.join((text or '').split())
    if len(text) > TEXT_MAX_CHARS or any(c in text for c in '[]()<>`'):
        return None
    return text


def cmd_plan(args):
    d = load_draft(args.draft)
    if d.get('state') in LOCKED_STATES or (d.get('job_id') and d.get('state') not in FINISHED_STATES):
        telemetry.report_once(state_dir())
        return emit('taskLocked', W.task_locked(), EXIT_WAIT, draft_id=d['draft_id'])
    _void_unsubmitted(d, args)
    telemetry.report_once(state_dir())
    if args.scene not in SCENES:
        return emit('sceneInvalid', '', EXIT_ERROR)
    shape = args.shape or SCENES[args.scene][2]
    if shape not in SIZES:
        return emit('shapeInvalid', '', EXIT_ERROR)
    look = args.look or args.scene
    if not T.look_valid(args.scene, look):
        return emit('lookInvalid', W.look_invalid(), EXIT_ERROR)
    if args.adult == 'no':
        return emit('notEligible', W.not_eligible('minor'), EXIT_ERROR, reason='minor')
    if args.self_photo == 'no':
        return emit('notEligible', W.not_eligible('not_self'), EXIT_ERROR, reason='not_self')
    missing = [k for k, v in (('self', args.self_photo), ('adult', args.adult)) if v == 'unknown']
    if missing:
        return emit('needsEligibility', W.needs_eligibility(missing), EXIT_WAIT, draft_id=d['draft_id'], missing=missing)
    if args.single != 'yes':
        return emit('peopleUnsupported', W.people_unsupported(), EXIT_ERROR)
    if args.face_clear != 'yes':
        return emit('needsClearerPhoto', W.needs_clearer_photo(), EXIT_WAIT, draft_id=d['draft_id'])
    features, outfit = _clean_text(args.features), _clean_text(args.outfit)
    if features is None or outfit is None:
        return emit('textInvalid', W.text_invalid(), EXIT_ERROR)
    clash = outfit_conflict(args.scene, look, outfit)
    if clash:
        return emit('outfitLookConflict', W.outfit_look_conflict(look_name(args.scene, look), clash),
                    EXIT_WAIT, draft_id=d['draft_id'], conflict=clash)
    if args.image:
        d['images'] = [os.path.abspath(args.image)]
    if len(d.get('images') or []) != 1:
        return emit('needsPhoto', W.needs_photo(), EXIT_ERROR)
    checked = audit_images.check(d['images'][0])
    if not checked['ok']:
        return emit('photoInvalid', W.input_error(checked['file'], audit_images.describe(checked['problem'])), EXIT_ERROR, problem=checked['problem'])
    prompt = build_prompt(args.scene, features, outfit, look)
    if not isinstance(prompt, str) or not 1 <= len(prompt) <= 6000:
        return emit('textInvalid', W.text_invalid(), EXIT_ERROR)
    snapshot = dict(key=look, outfit=outfit_text(args.scene, look, outfit),
                    visual=SCENES[args.scene][3], makeup=SCENES[args.scene][4])
    d.update(scene=args.scene, size=SIZES[shape], look_profile=look, look_snapshot=snapshot,
             prompt_snapshot=prompt, subject_self='yes', subject_adult='yes', features=features, outfit=outfit,
             photo_sha256=_photo_digest(d['images'][0]), owner_consent=False, upload_consent=False,
             pay_consent=False, idem=None, job_id=None, body_sha256=None, state='planned')
    save_draft(d)
    summary = W.plan_summary(SCENES[args.scene][1], W.SHAPE_NAMES[shape], SIZES[shape], snapshot['outfit'])
    return emit('planReady', W.confirm_paid(summary, wait_text(), features, 'art'), EXIT_OK, draft_id=d['draft_id'])


def _void_unsubmitted(d, args):
    # Must precede every local validation/early return. Submitted locks are handled before entry.
    d.update(owner_consent=False, upload_consent=False, pay_consent=False, idem=None, job_id=None,
             body_sha256=None, body_recipe=None, photo_sha256=None, prompt_snapshot=None, look_snapshot=None,
             look_profile=None, charged_uses=None, reserved_uses=None, remaining_after_submit=None,
             state=REPLAN_STATE, replan_scene=args.scene, replan_look=args.look)
    if args.image:
        d['images'] = [os.path.abspath(args.image)]
    save_draft(d)


def _replan_pending(d):
    return emit('needsReplan', W.replan_pending(), EXIT_WAIT, draft_id=d['draft_id'])


def cmd_confirm(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if (d.get('state') != 'planned' or d.get('scene') not in SCENES or
            d.get('subject_self') != 'yes' or d.get('subject_adult') != 'yes' or not d.get('look_snapshot')):
        return emit('needsPlan', '', EXIT_ERROR)
    if args.owner_consent != 'yes' or args.upload_consent != 'yes' or args.pay_consent != 'yes':
        return emit('needsConfirmation', '', EXIT_ERROR)
    if not d.get('photo_sha256') or _photo_digest(d['images'][0]) != d['photo_sha256']:
        return _photo_changed(d)
    d.update(owner_consent=True, upload_consent=True, pay_consent=True, idem='dhp-' + uuid.uuid4().hex,
             state='confirmed', confirmed_at=_now())
    save_draft(d)
    return emit('confirmed', '', EXIT_OK, draft_id=d['draft_id'])


def _photo_digest(path):
    try:
        with open(path, 'rb') as f:
            digest, count = hashlib.sha256(), 0
            while True:
                block = f.read(65536)
                if not block:
                    return digest.hexdigest()
                count += len(block)
                if count > 5 * 1024 * 1024:
                    return None
                digest.update(block)
    except OSError:
        return None


def _photo_changed(d):
    """确认后照片文件有变化：作废原确认和待提交的任务键，必须重新 plan + confirm。"""
    d.update(owner_consent=False, upload_consent=False, pay_consent=False, idem=None, state='photo_changed')
    save_draft(d)
    return emit('photoChanged', W.photo_changed(), EXIT_WAIT, draft_id=d['draft_id'])


def _job_body(d):
    if not isinstance(d.get('prompt_snapshot'), str) or not 1 <= len(d['prompt_snapshot']) <= 6000 or not d.get('look_snapshot'):
        return None, emit('needsPlan', '', EXIT_ERROR)
    path = d['images'][0]
    r = audit_images.check(path)
    if not r['ok']:
        return None, emit('photoInvalid', W.input_error(r['file'], audit_images.describe(r['problem'])), EXIT_ERROR, problem=r['problem'])
    with open(path, 'rb') as f:
        raw = f.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        return None, emit('photoInvalid', W.input_error(path, audit_images.describe('too_large')), EXIT_ERROR, problem='too_large')
    if not d.get('photo_sha256') or hashlib.sha256(raw).hexdigest() != d['photo_sha256']:
        return None, _photo_changed(d)
    content = base64.b64encode(raw).decode()
    body = dict(prompt=d['prompt_snapshot'], size=d['size'], confirmed=True,
                image_engine=IMAGE_ENGINE, references=[dict(mime=r['mime'], content=content)], reference_consent=True)
    return body, None


def _body_digest(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def _account_ready(a):
    """返回 (状态, 附带)：('ready', quota) / ('registration', url) / ('checkout', url) / ('error', status)
    链接已失效时沿原安装身份重取一次；仍失效返回 ('error', EXPIRED)，不转述失效链接。"""
    secret = ensure_install_secret(a)
    for _ in range(2):
        try:
            r = call('POST', '/quick-entry', {'install_secret': secret})
        except GatewayError as e:
            return 'error', e.status
        if r.get('status') not in ('registration', 'checkout') or link_fresh(r):
            break
    else:
        return 'error', EXPIRED
    st = r.get('status')
    if st == 'ready':
        telemetry.link_account(state_dir(), secret)
        return 'ready', r
    if st in ('registration', 'checkout'):
        try:
            url = trusted_link(r.get('url'))
        except GatewayError:
            return 'error', 0
        if st == 'checkout':
            telemetry.link_account(state_dir(), secret)
        return st, url
    return 'error', 0


def _ensure_skill_key(a):
    """返回 'ok' 只表示：本机有合法技能凭证，且服务端已明确确认绑定（bound=true）。
    凭证保存与绑定成功是两个独立状态：合法凭证先私存（skill_key_bound=False），再单独确认绑定；
    确认失败（bound 不是 true、缺字段、超时、断网、5xx）时凭证保留但不得用于新生成，下次命令再确认一次；
    确认返回 401（凭证已被轮换/撤销，A3-TRV-01-R1）时返回 'key_reset'：本机作废该凭证及绑定标记，
    保留原安装身份与所有任务；下次沿原安装身份重新领取新凭证并再次确认 bound=true。
    已缓存但未确认的凭证（含进程重启后、旧版本迁移来的无标记凭证）同样先确认。只影响新生成，不改动已提交任务的原键和原请求体。"""
    if not a.get('skill_key'):
        try:
            r = call('POST', '/skill-key', {}, auth=a['install_secret'])
        except GatewayError as e:
            if e.status == 401:
                return 'needs_auth'
            return 'network' if e.status == 0 else 'error'
        if r.get('state') == 'pending_payment':
            return 'needs_credits'
        if r.get('state') != 'ready' or not SKILL_KEY_RE.fullmatch(r.get('key') or ''):
            return 'error'
        a['skill_key'] = r['key']
        a['skill_key_bound'] = False
        save_account(a)  # 先安全保存（未确认），再单独确认绑定
    if a.get('skill_key_bound') is True:
        return 'ok'
    return _confirm_bound(a)


def _confirm_bound(a):
    """POST /skill-key/bound，只有 HTTP 200 且 bound 恰为 true 才记为已绑定；其余一律未确认。
    401 是「这把凭证已失效」的确定信号，不是繁忙：立即作废本机凭证与绑定标记（不动 install_secret、不动任务），
    否则下次运行会见缓存凭证跳过领取、反复绑定同一把旧凭证而永久循环。"""
    try:
        r = call('POST', '/skill-key/bound', {'key': a['skill_key']}, auth=a['install_secret'])
    except GatewayError as e:
        if e.status == 401:
            a.pop('skill_key', None)
            a.pop('skill_key_bound', None)
            save_account(a)
            return 'key_reset'
        return 'network' if e.status == 0 else 'error'
    if not isinstance(r, dict) or r.get('bound') is not True:
        return 'error'
    a['skill_key_bound'] = True
    save_account(a)
    return 'ok'


def _membership_link(a):
    """返回 (链接, None) 或 (None, 状态)：状态 0 = 连接失败、超时、坏响应或链接不可信；非 0 = 服务端返回的错误码。"""
    for _ in range(2):
        try:
            r = call('POST', '/membership-link', {}, auth=a['install_secret'])
            if not link_fresh(r):
                continue  # 已失效：沿原安装身份重取一次
            return trusted_link(r.get('url')), None
        except GatewayError as e:
            return None, e.status
    return None, EXPIRED


def _fail_kind(status):
    """状态 0 是网络没连上；链接已失效是这一步还没完成；其他是服务正在处理较多请求。不得把网络故障说成服务繁忙。"""
    if status == EXPIRED:
        return 'stale'
    return 'network' if status == 0 else 'busy'


def _account_entry(a, retry_word):
    """本机没有账户（或服务端还不认识本机）时的出路：确保安装标识 → 一次性关联入口。
    registration 给关联链接；error 如实说网络/繁忙；checkout/ready 已接上本机凭证，返回 None 由调用方继续。"""
    st, extra = _account_ready(a)
    if st == 'registration':
        return emit('linkAccount', W.account_link(extra, retry_word), EXIT_WAIT, link_included=True)
    if st == 'error':
        return emit('serviceUnavailable', W.account_failure(_fail_kind(extra), retry_word), EXIT_ERROR)
    return None


def cmd_run(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if d.get('state') == REPLAN_STATE:
        return _replan_pending(d)
    if not (all(d.get(k) is True for k in ('owner_consent', 'upload_consent', 'pay_consent')) and d.get('idem')):
        return emit('needsConfirmation', '', EXIT_ERROR)
    if d.get('job_id') or d.get('state') == 'submit_unknown':
        return _continue_job(d)
    # 未提交分支：先在本地完整校验源图并核对确认时的源 SHA，再碰账户、凭证等任何业务请求。
    # 坏图本地退出 3 并点名；换了图作废未提交确认与键。已提交或结果未知的任务在上面已只续查原任务。
    body, err = _job_body(d)
    if err is not None:
        return err
    a = load_account()
    st, extra = _account_ready(a)
    if st == 'registration':
        return emit('onboardingPreview', W.auth(extra, unsubmitted=True), EXIT_WAIT, draft_id=d['draft_id'])
    if st == 'checkout':
        if (read_json('flags.json', {}) or {}).get('delivered_once'):
            # 老用户余额用完：先问是否打开充值页，同意后才取链接
            d['state'] = 'needs_credits'
            save_draft(d)
            return emit('needsCredits', W.topup_ask(unsubmitted=True), EXIT_WAIT, draft_id=d['draft_id'], link_included=False)
        return emit('needsCredits', W.final_step(extra, unsubmitted=True), EXIT_WAIT, draft_id=d['draft_id'], link_included=True)
    if st == 'error':
        return emit('serviceUnavailable', W.failure(_fail_kind(extra), 'not_started'), EXIT_ERROR)
    k = _ensure_skill_key(a)
    if k == 'needs_credits':
        url, status = _membership_link(a)
        if not url:
            return emit('serviceUnavailable', W.failure(_fail_kind(status), 'not_started'), EXIT_ERROR)
        return emit('needsCredits', W.final_step(url, unsubmitted=True), EXIT_WAIT, draft_id=d['draft_id'], link_included=True)
    if k == 'key_reset':
        # 旧凭证已失效并已清除；确认单与原安装身份都保留，尚未提交生成。下次「继续」沿原身份领新凭证再确认绑定。
        return emit('credentialsReset', W.credentials_reset(), EXIT_RESET, draft_id=d['draft_id'], task_kept=True)
    if k != 'ok':
        return emit('serviceUnavailable', W.failure('network' if k == 'network' else 'busy', 'not_started'), EXIT_ERROR)
    title = SCENES[d['scene']][1]
    progress(W.start_recap(title, d['look_snapshot']['outfit'], W.SHAPE_NAMES[_shape_of(d['size'])], d['size']))
    return _submit(d, a, body)


def _submit(d, a, body):
    """先原子保存「提交结果未知」和冻结的请求体摘要，再发 POST；任何模糊结果只查原任务，不重发、不换键。"""
    digest = _body_digest(body)
    if d.get('body_sha256') and d['body_sha256'] != digest:
        return _photo_changed(d)
    d.update(state='submit_unknown', body_sha256=digest, body_recipe=dict(prompt=body['prompt'], size=body['size'], image_engine=IMAGE_ENGINE, reference_sha256=d['photo_sha256'], reference_mime=body['references'][0]['mime']))
    save_draft(d)
    try:
        r = call('POST', '/skill-jobs', body, auth=a['skill_key'], idem=d['idem'], timeout=REQUEST_TIMEOUT_S)
    except GatewayError as e:
        if e.status == 401:
            return _submit_unauthorized(d, a)
        if e.status == 402:
            d['state'] = 'needs_credits'
            save_draft(d)
            return emit('needsCredits', W.topup_ask(unsubmitted=True), EXIT_WAIT, draft_id=d['draft_id'], link_included=False)
        if e.status in (400, 403, 413, 422):
            d['state'] = 'rejected'
            save_draft(d)
            return emit('jobRejected', W.failure('rejected', 'not_started'), EXIT_ERROR, draft_id=d['draft_id'])
        # 超时、网络、409 或 5xx：保持 submit_unknown，只查原任务
        return _continue_job(d)
    jid = r.get('id')
    try:
        uuid.UUID(jid)
    except (ValueError, TypeError, AttributeError):
        return _continue_job(d)
    d.update(job_id=jid, state='submitted', remaining_after_submit=r.get('remaining_uses'))
    for field in ('charged_uses', 'reserved_uses'):
        if type(r.get(field)) is int and r[field] >= 0:
            d[field] = r[field]
    save_draft(d)
    if r.get('status') == 'succeeded':
        return _deliver(d, a)
    return _poll(d, a)


def _recover_skill_key(a):
    """技能凭证失效：清除后用原安装身份恢复一次（持久化新凭证并确认绑定）。返回是否恢复成功。"""
    a.pop('skill_key', None)
    a.pop('skill_key_bound', None)
    save_account(a)
    if not a.get('install_secret'):
        return False
    return _ensure_skill_key(a) == 'ok'  # 恢复同样必须确认绑定


def _submit_unauthorized(d, a):
    """提交时凭证被拒：生成请求已经发出，不能证明服务端未受理。任务状态保持 submit_unknown，原键、原请求体摘要不动；
    凭证状态单独处理（只改本机账户文件，不回写任务状态）。恢复凭证一次后只按原任务键只读查询：
    查到就沿原任务续接；查不到（含 404）、查询失败、断网或响应异常，一律保留原任务、提示进度未能确认，稍后继续只查原任务；
    恢复失败或查询仍被拒，退出 4 且 task_kept=true。任何分支都不再发生成请求、不换键、不让 plan/confirm/regenerate 覆盖。"""
    if not _recover_skill_key(a):
        return _keep_reset(d)
    try:
        r = call('GET', '/jobs/by-key/' + quote(d['idem'], safe=''), auth=a['skill_key'])
        uuid.UUID(r.get('id'))
    except GatewayError as e:
        if e.status == 401:
            a.pop('skill_key', None)  # 只清本机失效凭证；任务仍是 submit_unknown
            a.pop('skill_key_bound', None)
            save_account(a)
            return _keep_reset(d)
        return emit('jobPending', W.progress_unknown(), EXIT_WAIT, draft_id=d['draft_id'], progress='unconfirmed')
    except (ValueError, TypeError, AttributeError):
        return emit('jobPending', W.progress_unknown(), EXIT_WAIT, draft_id=d['draft_id'], progress='unconfirmed')
    d.update(job_id=r['id'], state='submitted')
    save_draft(d)
    return _poll(d, a)


def _shape_of(size):
    return next(k for k, v in SIZES.items() if v == size)


def _query_auth(a):
    return a.get('skill_key') or a.get('install_secret')


def _query(path, a, binary=False):
    """只读查询：技能凭证 401 时恢复一次，再回退原账户身份；最多两次查询。持续 401 抛 GatewayError(401)。"""
    try:
        return call('GET', path, auth=_query_auth(a), binary=binary)
    except GatewayError as e:
        if e.status != 401:
            raise
    if a.get('skill_key') and _recover_skill_key(a):
        return call('GET', path, auth=a['skill_key'], binary=binary)
    if a.get('install_secret'):
        return call('GET', path, auth=a['install_secret'], binary=binary)
    raise GatewayError(401)


def _keep_reset(d):
    return emit('credentialsReset', W.credentials_reset(), EXIT_RESET, draft_id=d['draft_id'], task_kept=True)


def _continue_job(d):
    a = load_account()
    if not d.get('job_id'):
        try:
            r = _query('/jobs/by-key/' + quote(d['idem'], safe=''), a)
            uuid.UUID(r.get('id'))
            d.update(job_id=r['id'], state='submitted')
            save_draft(d)
        except GatewayError as e:
            if e.status == 401:
                return _keep_reset(d)
            return emit('jobPending', W.progress_unknown(), EXIT_WAIT, draft_id=d['draft_id'], progress='unconfirmed')
        except (ValueError, TypeError, AttributeError):
            return emit('jobPending', W.progress_unknown(), EXIT_WAIT, draft_id=d['draft_id'], progress='unconfirmed')
    if d.get('state') == 'download_pending':
        return _deliver(d, a)
    return _poll(d, a)


def _poll(d, a):
    confirmed_pending = False
    for attempt in range(POLL_ATTEMPTS):
        if _BUDGET is not None and _BUDGET['queries'] >= POLL_ATTEMPTS:
            break
        if attempt:
            remaining = POLL_WINDOW_S - (time.monotonic() - (_BUDGET['query_start'] if _BUDGET and _BUDGET['query_start'] is not None else time.monotonic()))
            if remaining <= POLL_INTERVAL_S:
                break
            time.sleep(POLL_INTERVAL_S)
        try:
            r = _query('/jobs/' + d['job_id'], a)
        except GatewayError as e:
            if e.status == 401:
                return _keep_reset(d)
            confirmed_pending = False
            continue
        if not isinstance(r, dict):
            confirmed_pending = False
            continue
        for field in ('charged_uses', 'reserved_uses'):
            if type(r.get(field)) is int and r[field] >= 0:
                d[field] = r[field]
        st = r.get('status')
        if st == 'succeeded':
            return _deliver(d, a)
        if st == 'failed':
            d['state'] = 'failed'
            save_draft(d)
            return emit('jobFailed', W.failure('busy', 'record'), EXIT_ERROR, draft_id=d['draft_id'])
        # Only explicit pending states prove processing; an HTTP response alone does not.
        notice = r.get('notice')
        uncertain = isinstance(notice, str) and any(word in notice for word in ('核查', '未知', '未确认'))
        confirmed_pending = st in ('pending', 'processing') and not uncertain
        if confirmed_pending:
            progress('还在处理中，请稍候。')
    if confirmed_pending:
        return emit('jobPending', W.still_processing(), EXIT_WAIT, draft_id=d['draft_id'], progress='processing')
    return emit('jobPending', W.progress_unknown(), EXIT_WAIT, draft_id=d['draft_id'], progress='unconfirmed')


def _unique(path):
    base, ext = os.path.splitext(path)
    n, p = 1, path
    while os.path.exists(p):
        n += 1
        p = '%s-%d%s' % (base, n, ext)
    return p


def _out_dir(d):
    folder = os.path.join(os.path.dirname(d['images'][0]), '敦煌写真结果')
    os.makedirs(folder, exist_ok=True)
    return folder


def _gallery(folder):
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.png'))
    items = ''.join('<figure><img src="%s" style="max-width:320px"><figcaption>%s<br>%s</figcaption></figure>' % (quote(f), html.escape(f), DISCLOSURE) for f in files)
    with open(os.path.join(folder, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html><meta charset="utf-8"><title>敦煌写真结果</title><body style="font-family:sans-serif">'
                '<p>' + DISCLOSURE + '</p><div style="display:flex;flex-wrap:wrap;gap:16px">' + items + '</div></body>')


def _deliver(d, a):
    try:
        png = _query('/jobs/' + d['job_id'] + '/image', a, binary=True)
        width, height = png_local.size_of(png)
        if max(width, height) > 8000 or width * height > 20000000:
            raise ValueError('output dimensions exceed local limits')
        png_local.verify(png)  # 完整校验（分块 CRC、zlib、扫描行长度）通过才算交付
    except GatewayError as e:
        d['state'] = 'download_pending'
        save_draft(d)
        if e.status == 401:
            return _keep_reset(d)
        return emit('downloadPending', W.download_incomplete(), EXIT_WAIT, draft_id=d['draft_id'])
    except ValueError:
        d['state'] = 'download_pending'
        save_draft(d)
        return emit('downloadPending', W.download_incomplete(), EXIT_WAIT, draft_id=d['draft_id'])
    folder = _out_dir(d)
    stem = os.path.splitext(os.path.basename(d['images'][0]))[0]
    main_path = _unique(os.path.join(folder, '%s-%s.png' % (stem, d['scene'])))
    with open(main_path, 'xb') as f:
        f.write(png)
    paths = [main_path]
    notes = []
    try:
        aw, ah = png_local.size_of(png)
    except ValueError:
        aw = ah = None
    req_w, req_h = (int(x) for x in d['size'].split('x'))
    if aw and (aw, ah) != (req_w, req_h):
        notes.append(W.size_mismatch('%d×%d' % (aw, ah), '%d×%d' % (req_w, req_h)))
    _gallery(folder)
    remaining = None
    try:
        remaining = call('GET', '/balance', auth=a['install_secret']).get('remaining_uses')
    except (GatewayError, KeyError):
        pass
    if type(remaining) is not int or remaining < 0:
        remaining = None
    flags = read_json('flags.json', {}) or {}
    first = not flags.get('adjust_guide_shown')
    flags['adjust_guide_shown'] = True
    flags['delivered_once'] = True
    write_json('flags.json', flags)
    d.update(state='delivered', delivered=paths, delivered_at=_now())
    save_draft(d)
    links = [md_safe_path(p) for p in paths]  # 面向用户的链接目标；paths 仍是原始文件路径
    gallery = os.path.join(folder, 'index.html')
    return emit('delivered', W.delivery(links, remaining, first, SCENES[d['scene']][1], '\n'.join(notes), md_safe_path(gallery), charged=d.get('charged_uses')),
                EXIT_OK, draft_id=d['draft_id'], paths=paths, links=links, gallery=gallery, gallery_link=md_safe_path(gallery),
                remaining_uses=remaining, ask_favorite=first)


def cmd_resume(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if d.get('state') == REPLAN_STATE:
        return _replan_pending(d)
    if d.get('state') == 'needs_credits' and not d.get('job_id'):
        # 尚未生成的任务续接前同样先本地验图，坏图或换图不发任何业务请求
        _, err = _job_body(d)
        if err is not None:
            return err
    if d.get('state') == 'needs_credits':
        a = load_account()
        try:
            remaining = call('GET', '/balance', auth=a.get('install_secret')).get('remaining_uses')
        except GatewayError:
            return emit('serviceUnavailable', W.progress_unknown(), EXIT_WAIT)
        if type(remaining) is not int or remaining < 1:
            return emit('creditsPending', W.credits_not_yet(), EXIT_WAIT, draft_id=d['draft_id'])
        d['state'] = 'confirmed'
        save_draft(d)
        return cmd_run(args)
    if d.get('job_id') or d.get('state') in ('submit_unknown', 'download_pending'):
        return _continue_job(d)
    return cmd_run(args)


def cmd_regenerate(args):
    """仅在用户明确说「重新生成」且再次同意计费时使用：新任务键。进行中或结果未知的任务不得换键。"""
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if d.get('state') == REPLAN_STATE:
        return _replan_pending(d)
    if d.get('state') not in FINISHED_STATES:
        return emit('taskLocked', W.task_locked(), EXIT_WAIT, draft_id=d['draft_id'])
    if args.pay_consent != 'yes' or not (d.get('owner_consent') is True and d.get('upload_consent') is True):
        return emit('needsConfirmation', '', EXIT_ERROR)
    d.update(idem='dhp-' + uuid.uuid4().hex, job_id=None, body_sha256=None, body_recipe=None,
             charged_uses=None, reserved_uses=None, remaining_after_submit=None,
             state='confirmed', pay_consent=True)
    save_draft(d)
    return cmd_run(args)


def cmd_status(args):
    telemetry.report_once(state_dir())
    a = load_account()
    if not a.get('install_secret'):
        # 新用户：不回死胡同，走一次性关联入口
        st, extra = _account_ready(a)
        if st == 'registration':
            return emit('linkAccount', W.account_link(extra, '我的账户'), EXIT_WAIT, link_included=True)
        if st == 'checkout':
            return emit('needsCredits', W.final_step(extra), EXIT_WAIT, link_included=True)
        if st == 'error':
            return emit('serviceUnavailable', W.account_failure(_fail_kind(extra), '我的账户'), EXIT_ERROR)
        rem = extra.get('remaining_uses')
        return emit('registered', '', EXIT_OK, remaining_uses=rem if type(rem) is int and rem >= 0 else None)
    try:
        r = call('POST', '/quick-entry/status', {'install_secret': a['install_secret']})
    except GatewayError as e:
        return emit('serviceUnavailable', W.account_failure(_fail_kind(e.status), '我的账户'), EXIT_WAIT)
    if r.get('status') != 'registered':
        return emit('authPending', W.auth_pending(), EXIT_WAIT)
    telemetry.link_account(state_dir(), a['install_secret'])
    rem = r.get('remaining_uses')
    return emit('registered', '', EXIT_OK, remaining_uses=rem if type(rem) is int and rem >= 0 else None)


def cmd_auth(args):
    telemetry.report_once(state_dir())
    a = load_account()
    st, extra = _account_ready(a)
    if st == 'registration':
        return emit('onboardingPreview', W.auth_short(extra), EXIT_WAIT)
    if st == 'checkout':
        return emit('needsCredits', W.final_step(extra), EXIT_WAIT, link_included=True)
    if st == 'ready':
        return emit('ready', '', EXIT_OK)
    return emit('serviceUnavailable', W.account_failure(_fail_kind(extra), '授权'), EXIT_ERROR)


def cmd_topup(args):
    telemetry.report_once(state_dir())
    a = load_account()
    if a.get('install_secret'):
        url, status = _membership_link(a)
        if url:
            return emit('topupLink', W.topup_link(url), EXIT_WAIT)
        if status != 401:
            return emit('serviceUnavailable', W.account_failure(_fail_kind(status), '充值'), EXIT_ERROR)
        # 401：服务端还不认识本机安装标识（关联未完成），改走一次性关联入口
    st, extra = _account_ready(a)  # 没有安装标识就先生成并持久化
    if st == 'registration':
        return emit('linkAccount', W.account_link(extra, '充值'), EXIT_WAIT, link_included=True)
    if st == 'checkout':
        return emit('topupLink', W.topup_link(extra), EXIT_WAIT)
    if st == 'error':
        return emit('serviceUnavailable', W.account_failure(_fail_kind(extra), '充值'), EXIT_ERROR)
    url, status = _membership_link(a)  # ready：本机凭证已接上，取充值链接
    if not url:
        return emit('serviceUnavailable', W.account_failure(_fail_kind(status), '充值'), EXIT_ERROR)
    return emit('topupLink', W.topup_link(url), EXIT_WAIT)


def cmd_paid(args):
    """用户说已付款：只按服务端查到的次数说话，不把用户自述当作到账。
    本机没有账户（或服务端还不认识本机）时，与其他账户命令一样走一次性关联入口给链接。"""
    telemetry.report_once(state_dir())
    a = load_account()
    if not a.get('install_secret'):
        st, extra = _account_ready(a)  # 没有安装标识就先生成并持久化
        if st == 'registration':
            return emit('linkAccount', W.account_link(extra, '付好了'), EXIT_WAIT, link_included=True)
        if st == 'checkout':
            return emit('creditsPending', W.paid_not_yet(extra), EXIT_WAIT, link_included=True)
        if st == 'error':
            return emit('serviceUnavailable', W.account_failure(_fail_kind(extra), '付好了'), EXIT_ERROR)
    try:
        r = call('GET', '/balance', auth=a['install_secret'])
    except GatewayError as e:
        if e.status != 401:
            return emit('serviceUnavailable', W.account_failure(_fail_kind(e.status), '付好了'), EXIT_WAIT)
        # 401：服务端还不认识本机安装标识，改走一次性关联入口
        st, extra = _account_ready(a)
        if st == 'registration':
            return emit('linkAccount', W.account_link(extra, '付好了'), EXIT_WAIT, link_included=True)
        if st == 'checkout':
            return emit('creditsPending', W.paid_not_yet(extra), EXIT_WAIT, link_included=True)
        if st == 'error':
            return emit('serviceUnavailable', W.account_failure(_fail_kind(extra), '付好了'), EXIT_ERROR)
        try:
            r = call('GET', '/balance', auth=a['install_secret'])
        except GatewayError as e2:
            return emit('serviceUnavailable', W.account_failure(_fail_kind(e2.status), '付好了'), EXIT_WAIT)
    rem = r.get('remaining_uses')
    if not isinstance(rem, int) or isinstance(rem, bool):
        return emit('serviceUnavailable', W.progress_unknown(), EXIT_WAIT)
    if rem < 1:
        return emit('creditsPending', W.paid_not_yet(), EXIT_WAIT, remaining_uses=rem)
    telemetry.link_account(state_dir(), a['install_secret'])
    return emit('creditsConfirmed', W.paid_confirmed(rem), EXIT_OK, remaining_uses=rem)


HISTORY_PREVIEW = 3
HISTORY_PAGE_SIZE = 20
TICKET_RE = re.compile(r'mpsg-[a-f0-9]{32}')
CATEGORIES = ('billing', 'image_quality', 'workflow', 'suggestion', 'other')
TICKET_TEXT_MAX = 2000
TICKETS_SHOWN = 3


def _local_time(ts):
    if type(ts) is not int or ts <= 0:
        return '时间未知'
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')


def _plain(text, limit=4000):
    """服务记录里的文字只当纯文本展示：去掉控制字符和 Markdown 链接/图片语法的入口。"""
    if not isinstance(text, str):
        return ''
    text = ''.join(ch if ch in '\n\t' or ord(ch) >= 32 else ' ' for ch in text)[:limit]
    return text.replace('](', '] (').replace('<', '＜').replace('>', '＞').strip()


def _history(a, page, page_size):
    """返回 (cards, total, has_more)；失败抛 GatewayError。"""
    r = call('GET', '/consumption-history?page=%d&page_size=%d' % (page, page_size), auth=a['install_secret'])
    items, total = r.get('items'), r.get('total')
    if not isinstance(items, list) or type(total) is not int:
        raise GatewayError(0)
    cards = []
    for it in items:
        if not isinstance(it, dict):
            continue
        cards.append(W.history_card(_local_time(it.get('occurred_at')), _plain(it.get('content'), 40) or '生图任务',
                                    it.get('charged_uses'), it.get('reserved_uses'), it.get('refunded_uses'),
                                    it.get('status')))
    return cards, total, page * page_size < total


def cmd_balance(args):
    telemetry.report_once(state_dir())
    a = load_account()
    if not a.get('install_secret'):
        r = _account_entry(a, '查余额')
        if r is not None:
            return r
    try:
        r = call('GET', '/balance', auth=a['install_secret'])
    except GatewayError as e:
        if e.status == 401:
            r = _account_entry(a, '查余额')
            return r if r is not None else emit('serviceUnavailable', W.account_failure('busy', '查余额'), EXIT_WAIT)
        return emit('serviceUnavailable', W.account_failure(_fail_kind(e.status), '查余额'), EXIT_WAIT)
    rem = r.get('remaining_uses')
    if type(rem) is not int or rem < 0:
        return emit('serviceUnavailable', W.progress_unknown(), EXIT_WAIT)
    try:
        cards, total, _ = _history(a, 1, HISTORY_PREVIEW)
    except GatewayError:
        cards, total = None, None
    return emit('balance', W.account_summary(rem, cards, total), EXIT_OK, remaining_uses=rem,
                history_total=total, history_loaded=cards is not None)


def cmd_history(args):
    telemetry.report_once(state_dir())
    a = load_account()
    if not 1 <= args.page <= 100000:
        return emit('usage', '', EXIT_ERROR)
    if not a.get('install_secret'):
        r = _account_entry(a, '查余额')
        if r is not None:
            return r
    try:
        cards, total, more = _history(a, args.page, HISTORY_PAGE_SIZE)
    except GatewayError as e:
        if e.status == 401:
            r = _account_entry(a, '查余额')
            return r if r is not None else emit('serviceUnavailable', W.history_unavailable(), EXIT_WAIT)
        if e.status == 429:
            return emit('tooFrequent', W.too_frequent(), EXIT_WAIT)
        return emit('serviceUnavailable', W.history_unavailable(), EXIT_WAIT)
    return emit('history', W.history_page(cards, total, args.page, more), EXIT_OK, page=args.page, total=total,
                has_more=more, next_page=args.page + 1 if more else None)


def _due_text(t):
    due = t.get('response_due_at')
    return _local_time(due) if type(due) is int and due > 0 else None


def _support_state():
    st = read_json(os.path.join('support', 'state.json'), {}) or {}
    if not isinstance(st, dict):
        st = {}
    st.setdefault('pending', [])
    st.setdefault('tickets', [])
    return st


def _save_support(st):
    write_json(os.path.join('support', 'state.json'), st)


def _submit_pending(a, st, only_key=None):
    """Submit only the newly confirmed item, or explicitly retried saved feedback."""
    done, reason = [], None
    for item in list(st['pending']):
        if only_key is not None and item['key'] != only_key:
            continue
        try:
            r = call('POST', '/support-tickets', item['body'], auth=a['install_secret'], idem=item['key'])
        except GatewayError as e:
            if e.status == 404 and item['body'].get('job_id'):
                # 关联的任务不属于当前账户：去掉关联、换新请求编号，留待下次提交
                item['body'].pop('job_id')
                item['key'] = 'fb-' + uuid.uuid4().hex
                reason = 'busy'
            elif e.status == 401:
                reason = 'no_account'
            elif e.status in (400, 409):
                st['pending'].remove(item)  # 内容不被接受，不反复提交
                reason = reason or 'busy'
            else:
                reason = 'network' if e.status == 0 else 'busy'
            _save_support(st)
            break
        t = r.get('ticket')
        if not isinstance(t, dict) or not TICKET_RE.fullmatch(t.get('id') or ''):
            reason = 'busy'
            break
        st['pending'].remove(item)
        if t['id'] not in [x['id'] for x in st['tickets']]:
            st['tickets'].append(dict(id=t['id'], created=_now()))
        _save_support(st)
        done.append(t)
    return done, reason


def cmd_feedback(args):
    telemetry.report_once(state_dir())
    st = _support_state()
    only_key = None
    if not args.retry:
        text = (args.text or '').strip()
        if args.category not in CATEGORIES or not text or len(text) > TICKET_TEXT_MAX or \
                any(ord(ch) < 32 and ch not in '\n\t\r' for ch in text):
            return emit('usage', '', EXIT_ERROR)
        body = dict(category=args.category, text=text)
        if args.draft:
            d = load_draft(args.draft)
            jid = d.get('job_id')
            if isinstance(jid, str) and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', jid):
                body['job_id'] = jid
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if digest in [x.get('digest') for x in st['pending']]:
            # Repeating an unknown item's text must not silently stand in for --retry.
            return emit('feedbackSaved', W.feedback_saved('pending'), EXIT_WAIT,
                        pending=len(st['pending']), auto_retry=False)
        only_key = 'fb-' + uuid.uuid4().hex
        st['pending'].append(dict(digest=digest, key=only_key, body=body))
        _save_support(st)
    elif not st['pending']:
        return emit('feedbackNone', W.feedback_nothing_pending(), EXIT_OK)
    a = load_account()
    if not a.get('install_secret'):
        return emit('feedbackSaved', W.feedback_saved('no_account'), EXIT_WAIT, pending=len(st['pending']), auto_retry=False)
    done, reason = _submit_pending(a, st, only_key=only_key)
    if reason and not done:
        # HNF-A3-03：没拿到反馈编号时原请求编号和原内容已保留；只有用户明确说「提交反馈」才 --retry，宿主不自动重跑
        return emit('feedbackSaved', W.feedback_saved(reason), EXIT_WAIT, pending=len(st['pending']), auto_retry=False)
    text = '\n\n'.join(W.ticket_created(t['id'], t.get('category'), _due_text(t)) for t in done)
    if reason:
        text += '\n\n' + W.feedback_saved(reason)
    return emit('ticketCreated', text, EXIT_OK, ticket_ids=[t['id'] for t in done], pending=len(st['pending']),
                auto_retry=False)


def cmd_ticket(args):
    telemetry.report_once(state_dir())
    if args.id is not None and not TICKET_RE.fullmatch(args.id):
        return emit('ticketNotFound', W.ticket_not_found(), EXIT_OK)
    a = load_account()
    if not a.get('install_secret'):
        return emit('noAccount', W.account_missing(), EXIT_OK)
    ids = [args.id] if args.id else [x['id'] for x in _support_state()['tickets']][-TICKETS_SHOWN:][::-1]
    if not ids:
        return emit('ticketNone', W.tickets_none(), EXIT_OK)
    views = []
    for tid in ids:
        try:
            t = call('GET', '/support-tickets/' + tid, auth=a['install_secret']).get('ticket')
        except GatewayError as e:
            if e.status == 404:
                if args.id:
                    return emit('ticketNotFound', W.ticket_not_found(), EXIT_OK)
                continue
            if e.status == 401:
                return emit('noAccount', W.account_missing(), EXIT_OK)
            if e.status == 429:
                return emit('tooFrequent', W.too_frequent(), EXIT_WAIT)
            return emit('serviceUnavailable', W.ticket_lookup_failed('network' if e.status == 0 else 'busy'), EXIT_WAIT)
        if not isinstance(t, dict) or t.get('id') != tid:
            return emit('serviceUnavailable', W.ticket_lookup_failed('busy'), EXIT_WAIT)
        views.append(W.ticket_view(tid, t.get('category'), t.get('status'), _plain(t.get('reply')), _due_text(t)))
    if not views:
        return emit('ticketNotFound', W.ticket_not_found(), EXIT_OK)
    return emit('ticketStatus', '\n\n'.join(views), EXIT_OK, count=len(views))


def cmd_decline(args):
    return emit('declined', W.DECLINE, EXIT_OK)


def cmd_refuse(args):
    return emit('refused', W.refuse_misuse(), EXIT_OK)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='seconds')


def parser():
    p = argparse.ArgumentParser(prog='studio.py')
    s = p.add_subparsers(dest='cmd')
    f = s.add_parser('first-turn')
    f.add_argument('--text', default='')
    f.add_argument('--image', action='append')
    f.add_argument('--has-need', action='store_true')
    f.add_argument('--defer-entry', action='store_true')
    dm = s.add_parser('demo')
    dm.add_argument('key', nargs='?')
    pl = s.add_parser('plan')
    pl.add_argument('--draft', required=True)
    pl.add_argument('--scene', required=True)
    pl.add_argument('--shape', choices=sorted(SIZES))
    pl.add_argument('--self', dest='self_photo', required=True, choices=('yes', 'no', 'unknown'))
    pl.add_argument('--adult', required=True, choices=('yes', 'no', 'unknown'))
    pl.add_argument('--look', default=None, choices=sorted(SCENES))
    pl.add_argument('--single', required=True, choices=('yes', 'no'))
    pl.add_argument('--face-clear', required=True, choices=('yes', 'no'))
    pl.add_argument('--features', default='')
    pl.add_argument('--outfit', default='')
    pl.add_argument('--image')
    c = s.add_parser('confirm')
    c.add_argument('--draft', required=True)
    c.add_argument('--owner-consent', required=True)
    c.add_argument('--upload-consent', required=True)
    c.add_argument('--pay-consent', required=True)
    for name in ('run', 'resume'):
        s.add_parser(name).add_argument('--draft', required=True)
    rg = s.add_parser('regenerate')
    rg.add_argument('--draft', required=True)
    rg.add_argument('--pay-consent', required=True)
    for name in ('status', 'auth', 'topup', 'paid', 'balance', 'decline', 'refuse'):
        s.add_parser(name)
    hi = s.add_parser('history')
    hi.add_argument('--page', type=int, default=1)
    fb = s.add_parser('feedback')
    fb.add_argument('--category', choices=CATEGORIES)
    fb.add_argument('--text')
    fb.add_argument('--draft')
    fb.add_argument('--retry', action='store_true')
    tk = s.add_parser('ticket')
    tk.add_argument('--id')
    return p


COMMANDS = {
    'first-turn': cmd_first_turn, 'demo': cmd_demo, 'plan': cmd_plan, 'confirm': cmd_confirm, 'run': cmd_run,
    'resume': cmd_resume, 'regenerate': cmd_regenerate, 'status': cmd_status, 'auth': cmd_auth, 'topup': cmd_topup,
    'paid': cmd_paid, 'balance': cmd_balance, 'decline': cmd_decline, 'feedback': cmd_feedback, 'refuse': cmd_refuse,
    'history': cmd_history, 'ticket': cmd_ticket,
}


def main(argv=None):
    reset_budget()
    p = parser()
    try:
        args = p.parse_args(argv)
    except SystemExit:
        return emit('usage', '', EXIT_ERROR)
    if not args.cmd:
        return emit('usage', '', EXIT_ERROR)
    try:
        return COMMANDS[args.cmd](args)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else EXIT_ERROR
    except (ValueError, TypeError, KeyError, AttributeError):
        return emit('requestInvalid', '', EXIT_ERROR)
    except OSError:
        return emit('localStateUnavailable', '', EXIT_ERROR)
    except GatewayError as exc:
        return emit('serviceUnavailable', W.failure('network' if exc.status == 0 else 'busy', 'record'), EXIT_WAIT)


if __name__ == '__main__':
    sys.exit(main())
