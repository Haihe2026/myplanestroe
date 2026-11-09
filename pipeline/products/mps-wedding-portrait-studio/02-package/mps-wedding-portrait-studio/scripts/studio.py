#!/usr/bin/env python3
"""婚纱写真照相馆 本地客户端（Python 3.7+ 标准库）。

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
import urllib.error
import urllib.request
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_images  # noqa: E402
import png_local  # noqa: E402
import telemetry  # noqa: E402
import welcome_copy as W  # noqa: E402

SKILL_ID = 'mps-wedding-portrait-studio'
SKILL_VERSION = '1.0.1'
CHANNEL = 'workbuddy_skill'
ORIGIN = 'https://aistore.zhaopintong.com'
API_PREFIX = '/platform-api/gemini'
FIRST_PARTY = ('https://aistore.zhaopintong.com', 'https://myplanestore.com')
LINK_PATHS = ('/membership/', '/membership/gemini/', '/membership/gemini/register/', '/auth/wechat/')

# 等待预算（脚本常量；文档中的数值由测试逐处比对）
REQUEST_TIMEOUT_S = 90
QUERY_TIMEOUT_S = 15
POLL_INTERVAL_S = 5
POLL_ATTEMPTS = 6
POLL_WINDOW_S = POLL_ATTEMPTS * (POLL_INTERVAL_S + QUERY_TIMEOUT_S)
RATE_LIMIT_WAIT_S = 0
PROCESS_MARGIN_S = 30
OUTER_TIMEOUT_S = REQUEST_TIMEOUT_S + POLL_WINDOW_S + RATE_LIMIT_WAIT_S + PROCESS_MARGIN_S

SIZES = {'portrait': '1024x1536', 'landscape': '1536x1024', 'square': '1024x1024'}  # 适配器已映射的 1K 画幅
IMAGE_ENGINE = 'photo-retouch-sunburst'
BODY_FIELDS = frozenset({'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent'})
IDEM_RE = re.compile(r'[A-Za-z0-9_.:-]{16,100}')
SECRET_RE = re.compile(r'[A-Za-z0-9_-]{43}')
SKILL_KEY_RE = re.compile(r'mpskill_[0-9a-f]{32}_[A-Za-z0-9_-]{43}')

EXIT_OK, EXIT_WAIT, EXIT_ERROR, EXIT_RESET = 0, 2, 3, 4

# key: (系列, 标题, 推荐画幅, 场景视觉参照)。婚纱系列可单人或两人同框，写真系列仅单人。
SCENES = {
    'white-studio': ('婚纱', '经典白纱影棚', 'portrait',
                     '换上白色婚纱礼服（两人时另一位换深色西装礼服），灰白色无缝影棚背景，大面积柔光，胸像或半身的自然姿势'),
    'xiuhe': ('婚纱', '中式秀禾服', 'portrait',
              '换上红金配色的中式秀禾服（两人时另一位换中式礼服长衫），简洁木质中式布景，对称构图，保留原本肤色'),
    'garden': ('婚纱', '户外草坪婚礼', 'landscape',
               '换上浅色婚纱礼服，户外草坪花园背景，暖阳斜光，人物完整并在画面两侧留出空间'),
    'seaside': ('婚纱', '海边度假婚纱', 'landscape',
                '换上轻盈的度假风婚纱礼服，海平线与沙滩背景，海风自然吹动衣摆，服装和光影方向一致，浪花克制不遮挡人物'),
    'oil-wedding': ('婚纱', '复古油画婚纱', 'portrait',
                    '换上复古婚纱礼服，暖棕色复古背景，低调古典侧光，油画笔触只用于背景和服装质感，人脸细节保持清晰真实'),
    'korean': ('婚纱', '韩式清新婚纱', 'portrait',
               '换上轻盈白纱，淡彩影棚背景并留白，高调漫射光，自然轻妆感'),
    'hanfu': ('写真', '汉服古风写真', 'portrait',
              '换上典雅的汉服，清简庭院背景，柔光，衣襟交领方向正确，自然持袖姿势'),
    'oil-portrait': ('写真', '油画艺术写真', 'portrait',
                     '古典单人肖像构图，深暖色背景和明暗层次，油画质感只用于背景和服装，人脸保留真实特征'),
    'cyber': ('写真', '赛博朋克写真', 'portrait',
              '青紫色霓虹城市虚化背景和轮廓光，脸部有自然的补光，画面里没有任何品牌广告或招牌文字'),
    'japanese': ('写真', '日系清新写真', 'portrait',
                 '窗边自然光，淡色日常服装，轻柔的胶片色感，头肩上方留出空间'),
}
MAX_PEOPLE = {'婚纱': 2, '写真': 1}


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
    d = os.path.join(STATE_HOME or os.path.expanduser('~'), SKILL_ID)  # 不以点开头：避免 Markdown 链接里 \. 被当转义
    if os.path.islink(d):
        raise SystemExit(emit('stateUnsafe', '', EXIT_ERROR))
    os.makedirs(d, mode=0o700, exist_ok=True)
    return d


# Markdown 链接目标里会断链的字符：空白、括号、尖括号；% 一并编码，保证可逆
_MD_LINK_UNSAFE = {' ': '%20', '\t': '%09', '(': '%28', ')': '%29', '<': '%3C', '>': '%3E', '#': '%23', '?': '%3F'}


def md_safe_path(p):
    """给用户看的绝对路径：正斜杠（Markdown 不吞反斜杠），空格等断链字符做 URL 编码（%20）；`#`→%23、`?`→%3F，免得被当成链接片段或查询串截断。"""
    p = os.path.abspath(p).replace('\\', '/').replace('%', '%25')
    return ''.join(_MD_LINK_UNSAFE.get(c, c) for c in p)


def _path(name):
    p = os.path.join(state_dir(), name)
    if os.path.islink(p):
        raise SystemExit(emit('stateUnsafe', '', EXIT_ERROR))
    return p


def read_json(name, default=None):
    try:
        with open(_path(name), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(name, data):
    p = _path(name)
    os.makedirs(os.path.dirname(p), mode=0o700, exist_ok=True)
    tmp = p + '.tmp'
    if os.path.islink(tmp):
        raise SystemExit(emit('stateUnsafe', '', EXIT_ERROR))
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, p)


def load_account():
    a = read_json('account.json', {}) or {}
    if not isinstance(a, dict):
        a = {}
    if a.get('install_secret') and not SECRET_RE.fullmatch(a['install_secret']):
        a.pop('install_secret')
    if a.get('skill_key') and not SKILL_KEY_RE.fullmatch(a['skill_key']):
        a.pop('skill_key')
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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _default_transport(method, url, body, headers, timeout, binary):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    limit = 16 * 1024 * 1024 if binary else 2 * 1024 * 1024
    try:
        with urllib.request.build_opener(_NoRedirect()).open(req, timeout=timeout) as r:
            raw = r.read(limit + 1)
            status = r.status
    except urllib.error.HTTPError as e:
        raise GatewayError(e.code) from None
    except (urllib.error.URLError, OSError, ValueError):
        raise GatewayError(0) from None
    if len(raw) > limit:
        raise GatewayError(0)
    return status, raw


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
            if set(body) - BODY_FIELDS:
                raise ValueError('unregistered field')
    if idem is not None:
        if not IDEM_RE.fullmatch(idem):
            raise ValueError('task key')
        headers['Idempotency-Key'] = idem
    status, raw = TRANSPORT(method, ORIGIN + API_PREFIX + path, body, headers, timeout, binary)
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
    u = urlsplit(url or '')
    if u.scheme + '://' + u.netloc not in FIRST_PARTY or u.username or u.password or u.path not in LINK_PATHS:
        raise GatewayError(0)
    return urlunsplit(('https', 'aistore.zhaopintong.com', u.path, u.query, u.fragment))


# ---------------------------------------------------------------- 提示词

def build_prompt(scene, people):
    series, title, _, visual = SCENES[scene]
    if people == 2:
        who = ('真实性与人物身份：参考照片里有两位成年人，左侧的人和右侧的人分别锁定：各自保留脸部身份、五官比例、发际线、肤色和年龄感，'
               '两人不混脸、不互换特征；保持两人的人数和左右相对位置不变。')
    else:
        who = '真实性与人物身份：参考照片里只有一位成年人，保留这位人物的脸部身份、五官比例、发际线、肤色和年龄感，不美颜变脸。'
    return '\n'.join([
        who,
        '动作：把这张照片做成「' + title + '」主题的' + series + '照：' + visual + '；光影和构图自然统一。',
        '文字：图中不得出现任何文字、数字、水印、标志或边框。',
        '安全：不添加额外人物，不出现他人品牌和标志；手和手指形态自然，不出现多余肢体。',
    ])


def wait_text():
    return '1 到 4 分钟'


# ---------------------------------------------------------------- 命令

def cmd_first_turn(args):
    telemetry.report_once(state_dir())
    draft_id = 'd-' + uuid.uuid4().hex
    images = [os.path.abspath(p) for p in (args.image or [])]
    save_draft(dict(draft_id=draft_id, created=_now(), text=args.text or '', images=images,
                    scene=None, size=None, people=None, purpose=None,
                    photo_consent=False, pay_consent=False, idem=None, job_id=None, state='draft'))
    has_need = bool(images) or bool((args.text or '').strip()) and args.has_need
    return emit('firstTurn', W.WELCOME + '\n' + W.first_turn_close(has_need), EXIT_OK, draft_id=draft_id, has_image=bool(images),
                welcome=W.WELCOME, demo_intro=W.DEMO_INTRO)


def cmd_demo(args):
    # 只释放包内示例图：不联网、不读凭证。首次对话上报由同轮的 first-turn 负责。
    base = os.path.join(os.path.dirname(HERE), 'assets')
    try:
        with open(os.path.join(base, 'demos.json'), encoding='utf-8') as f:
            demos = json.load(f)['demos']
    except (OSError, ValueError, KeyError):
        return emit('demoUnavailable', W.DEMO_UNAVAILABLE, EXIT_ERROR)
    if args.key:
        demos = [d for d in demos if d['key'] == args.key]
        if not demos:
            return emit('demoNotFound', '', EXIT_ERROR, key=args.key)
    out_dir = os.path.join(state_dir(), 'demos')
    os.makedirs(out_dir, mode=0o700, exist_ok=True)
    items = []
    for d in demos:
        src = os.path.join(base, d['file'])
        if not os.path.isfile(src):
            continue
        dst = os.path.join(out_dir, d['file'])
        if not os.path.isfile(dst):
            shutil.copyfile(src, dst)
        items.append(dict(key=d['key'], title=d['title'], note=d['note'], path=md_safe_path(dst)))
    if not items:
        return emit('demoUnavailable', W.DEMO_UNAVAILABLE, EXIT_ERROR)
    return emit('demos', W.DEMO_INTRO, EXIT_OK, items=items)


def cmd_plan(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if args.scene not in SCENES:
        return emit('sceneInvalid', '', EXIT_ERROR)
    series, title, default_shape, _ = SCENES[args.scene]
    shape = args.shape or default_shape
    if shape not in SIZES:
        return emit('shapeInvalid', '', EXIT_ERROR)
    people = args.people
    if people not in (1, 2):
        return emit('peopleInvalid', '', EXIT_ERROR)
    if people > MAX_PEOPLE[series]:
        return emit('peopleUnsupported', W.people_unsupported(title), EXIT_ERROR, max_people=MAX_PEOPLE[series])
    if args.image:
        d['images'] = [os.path.abspath(args.image)]
    if len(d.get('images') or []) != 1:
        return emit('needsPhoto', '', EXIT_ERROR)
    r = audit_images.check(d['images'][0])
    if not r['ok']:
        return emit('photoInvalid', W.input_error(r['file'], audit_images.describe(r['problem'])), EXIT_ERROR, problem=r['problem'])
    if d.get('state') in ('submitted', 'delivered'):
        return emit('taskLocked', '', EXIT_ERROR)
    d.update(scene=args.scene, size=SIZES[shape], people=people, purpose=args.purpose or '',
             photo_sha256=_photo_digest(d['images'][0]), photo_consent=False, pay_consent=False, idem=None, state='planned')
    save_draft(d)
    summary = W.plan_summary(series, title, W.SHAPE_NAMES[shape], people)
    return emit('planReady', W.confirm_paid(summary, wait_text(), people), EXIT_OK, draft_id=d['draft_id'])


def cmd_confirm(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if d.get('state') != 'planned':
        return emit('needsPlan', '', EXIT_ERROR)
    if args.photo_consent != 'yes' or args.pay_consent != 'yes':
        return emit('needsConfirmation', '', EXIT_ERROR)
    if not d.get('photo_sha256') or _photo_digest(d['images'][0]) != d['photo_sha256']:
        return _photo_changed(d)
    d.update(photo_consent=True, pay_consent=True, idem='wps-' + uuid.uuid4().hex, state='confirmed', confirmed_at=_now())
    save_draft(d)
    return emit('confirmed', '', EXIT_OK, draft_id=d['draft_id'])


def _photo_digest(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _photo_changed(d):
    """确认后照片文件有变化：作废原确认和原任务键，必须重新 plan + confirm。"""
    d.update(photo_consent=False, pay_consent=False, idem=None, state='photo_changed')
    save_draft(d)
    return emit('photoChanged', W.photo_changed(), EXIT_WAIT, draft_id=d['draft_id'])


def _job_body(d):
    path = d['images'][0]
    r = audit_images.check(path)
    if not r['ok']:
        return None, emit('photoInvalid', W.input_error(r['file'], audit_images.describe(r['problem'])), EXIT_ERROR, problem=r['problem'])
    with open(path, 'rb') as f:
        raw = f.read()
    if not d.get('photo_sha256') or hashlib.sha256(raw).hexdigest() != d['photo_sha256']:
        return None, _photo_changed(d)
    content = base64.b64encode(raw).decode()
    body = dict(prompt=build_prompt(d['scene'], d['people']), size=d['size'], confirmed=True, image_engine=IMAGE_ENGINE,
                references=[dict(mime=r['mime'], content=content)], reference_consent=True)
    return body, None


def _account_ready(a):
    """返回 (状态, 附带)：('ready', quota) / ('registration', url) / ('checkout', url) / ('error', status)"""
    secret = ensure_install_secret(a)
    try:
        r = call('POST', '/quick-entry', {'install_secret': secret})
    except GatewayError as e:
        return 'error', e.status
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
    if a.get('skill_key'):
        return 'ok'
    try:
        r = call('POST', '/skill-key', {}, auth=a['install_secret'])
    except GatewayError as e:
        return 'needs_auth' if e.status == 401 else 'error'
    if r.get('state') == 'pending_payment':
        return 'needs_credits'
    if r.get('state') != 'ready' or not SKILL_KEY_RE.fullmatch(r.get('key') or ''):
        return 'error'
    a['skill_key'] = r['key']
    save_account(a)  # 先安全保存再确认
    try:
        call('POST', '/skill-key/bound', {'key': a['skill_key']}, auth=a['install_secret'])
    except GatewayError:
        pass  # 下次使用时服务端仍可识别；不影响已保存凭证
    return 'ok'


def _membership_link(a):
    try:
        r = call('POST', '/membership-link', {}, auth=a['install_secret'])
        return trusted_link(r.get('url'))
    except GatewayError:
        return None


def cmd_run(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if not (d.get('photo_consent') and d.get('pay_consent') and d.get('idem')):
        return emit('needsConfirmation', '', EXIT_ERROR)
    if d.get('job_id') or d.get('state') == 'submit_unknown':
        return _continue_job(d)
    a = load_account()
    st, extra = _account_ready(a)
    if st == 'registration':
        return emit('onboardingPreview', W.auth(extra), EXIT_WAIT, draft_id=d['draft_id'])
    if st == 'checkout':
        if (read_json('flags.json', {}) or {}).get('delivered_once'):
            # 老用户余额用完：先问是否打开充值页，同意后才取链接
            d['state'] = 'needs_credits'
            save_draft(d)
            return emit('needsCredits', W.topup_ask(), EXIT_WAIT, draft_id=d['draft_id'], link_included=False)
        return emit('needsCredits', W.final_step(extra), EXIT_WAIT, draft_id=d['draft_id'], link_included=True)
    if st == 'error':
        kind = 'network' if extra == 0 else 'busy'
        return emit('serviceUnavailable', W.failure(kind, 'not_started'), EXIT_ERROR)
    k = _ensure_skill_key(a)
    if k == 'needs_credits':
        url = _membership_link(a)
        if not url:
            return emit('serviceUnavailable', W.failure('busy', 'not_started'), EXIT_ERROR)
        return emit('needsCredits', W.final_step(url), EXIT_WAIT, draft_id=d['draft_id'], link_included=True)
    if k != 'ok':
        return emit('serviceUnavailable', W.failure('busy', 'not_started'), EXIT_ERROR)
    body, err = _job_body(d)
    if err is not None:
        return err
    series, title, _, _ = SCENES[d['scene']]
    progress(W.start_recap(title, series, W.SHAPE_NAMES[_shape_of(d['size'])], d['people']))
    return _submit(d, a, body)


def _submit(d, a, body):
    try:
        r = call('POST', '/skill-jobs', body, auth=a['skill_key'], idem=d['idem'], timeout=REQUEST_TIMEOUT_S)
    except GatewayError as e:
        if e.status == 401:
            a.pop('skill_key', None)
            save_account(a)
            return emit('credentialsReset', W.credentials_reset(), EXIT_RESET, draft_id=d['draft_id'])
        if e.status == 402:
            d['state'] = 'needs_credits'
            save_draft(d)
            return emit('needsCredits', W.topup_ask(), EXIT_WAIT, draft_id=d['draft_id'], link_included=False)
        if e.status == 429:
            return emit('serviceBusy', W.busy_kept(), EXIT_WAIT, draft_id=d['draft_id'])
        if e.status in (400, 403, 409, 413, 422):
            d['state'] = 'rejected'
            save_draft(d)
            return emit('jobRejected', W.failure('rejected', 'not_started'), EXIT_ERROR, draft_id=d['draft_id'])
        # 超时、网络或5xx：不重发，只查原任务
        d['state'] = 'submit_unknown'
        save_draft(d)
        return _continue_job(d)
    jid = r.get('id')
    try:
        uuid.UUID(jid)
    except (ValueError, TypeError, AttributeError):
        d['state'] = 'submit_unknown'
        save_draft(d)
        return _continue_job(d)
    d.update(job_id=jid, state='submitted', remaining_after_submit=r.get('remaining_uses'))
    save_draft(d)
    if r.get('status') == 'succeeded':
        return _deliver(d, a)
    return _poll(d, a)


def _shape_of(size):
    return next(k for k, v in SIZES.items() if v == size)


def _query_auth(a):
    return a.get('skill_key') or a.get('install_secret')


def _continue_job(d):
    a = load_account()
    if not d.get('job_id'):
        try:
            r = call('GET', '/jobs/by-key/' + quote(d['idem'], safe=''), auth=_query_auth(a))
            uuid.UUID(r.get('id'))
            d.update(job_id=r['id'], state='submitted')
            save_draft(d)
        except (GatewayError, ValueError, TypeError, AttributeError):
            return emit('jobPending', W.progress_unknown(), EXIT_WAIT, draft_id=d['draft_id'], progress='unconfirmed')
    if d.get('state') == 'download_pending':
        return _deliver(d, a)
    return _poll(d, a)


def _poll(d, a):
    reached = 0
    for attempt in range(POLL_ATTEMPTS):
        if attempt:
            time.sleep(POLL_INTERVAL_S)
        try:
            r = call('GET', '/jobs/' + d['job_id'], auth=_query_auth(a))
        except GatewayError as e:
            if e.status == 401:
                a.pop('skill_key', None)
                save_account(a)
                return emit('credentialsReset', W.credentials_reset(), EXIT_RESET, draft_id=d['draft_id'])
            continue
        reached += 1
        st = r.get('status')
        if st == 'succeeded':
            return _deliver(d, a)
        if st == 'failed':
            d['state'] = 'failed'
            save_draft(d)
            return emit('jobFailed', W.failure('busy', 'record'), EXIT_ERROR, draft_id=d['draft_id'])
        progress('还在处理中，请稍候。')
    if reached:
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
    folder = os.path.join(os.path.dirname(d['images'][0]), '婚纱写真结果')
    os.makedirs(folder, exist_ok=True)
    return folder


def _gallery(folder):
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.png'))
    items = ''.join('<figure><img src="%s" style="max-width:320px"><figcaption>%s</figcaption></figure>' % (quote(f), html.escape(f)) for f in files)
    with open(os.path.join(folder, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html><meta charset="utf-8"><title>婚纱写真结果</title><body style="font-family:sans-serif;display:flex;flex-wrap:wrap;gap:16px">' + items + '</body>')


def _deliver(d, a):
    try:
        png = call('GET', '/jobs/' + d['job_id'] + '/image', auth=_query_auth(a), binary=True)
    except GatewayError:
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
    if not isinstance(remaining, int):
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
    return emit('delivered', W.delivery(links, remaining, first, SCENES[d['scene']][1], d['people'], '\n'.join(notes), md_safe_path(gallery)),
                EXIT_OK, draft_id=d['draft_id'], paths=paths, links=links, gallery=gallery, gallery_link=md_safe_path(gallery),
                remaining_uses=remaining, ask_favorite=first)


def cmd_resume(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if d.get('state') == 'needs_credits':
        a = load_account()
        try:
            remaining = call('GET', '/balance', auth=a.get('install_secret')).get('remaining_uses')
        except GatewayError:
            return emit('serviceUnavailable', W.progress_unknown(), EXIT_WAIT)
        if not isinstance(remaining, int) or remaining < 1:
            return emit('creditsPending', W.credits_not_yet(), EXIT_WAIT, draft_id=d['draft_id'])
        d['state'] = 'confirmed'
        save_draft(d)
        return cmd_run(args)
    if d.get('job_id') or d.get('state') in ('submit_unknown', 'download_pending'):
        return _continue_job(d)
    return cmd_run(args)


def cmd_regenerate(args):
    """仅在用户明确说「重新生成」且再次同意计费时使用：新任务键。"""
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if args.pay_consent != 'yes' or not d.get('photo_consent'):
        return emit('needsConfirmation', '', EXIT_ERROR)
    d.update(idem='wps-' + uuid.uuid4().hex, job_id=None, state='confirmed', pay_consent=True)
    save_draft(d)
    return cmd_run(args)


def cmd_status(args):
    telemetry.report_once(state_dir())
    a = load_account()
    if not a.get('install_secret'):
        return emit('noAccount', W.account_missing(), EXIT_WAIT)
    try:
        r = call('POST', '/quick-entry/status', {'install_secret': a['install_secret']})
    except GatewayError:
        return emit('serviceUnavailable', W.progress_unknown(), EXIT_WAIT)
    if r.get('status') != 'registered':
        return emit('authPending', W.auth_pending(), EXIT_WAIT)
    telemetry.link_account(state_dir(), a['install_secret'])
    rem = r.get('remaining_uses')
    return emit('registered', '', EXIT_OK, remaining_uses=rem if isinstance(rem, int) else None)


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
    return emit('serviceUnavailable', W.failure('network' if extra == 0 else 'busy', 'not_started'), EXIT_ERROR)


def cmd_topup(args):
    telemetry.report_once(state_dir())
    a = load_account()
    if not a.get('install_secret'):
        return emit('noAccount', W.account_missing(), EXIT_WAIT)
    url = _membership_link(a)
    if not url:
        return emit('serviceUnavailable', W.failure('busy', 'not_started'), EXIT_ERROR)
    return emit('topupLink', W.topup_link(url), EXIT_WAIT)


def cmd_paid(args):
    telemetry.report_once(state_dir())
    return emit('paymentRegistered', W.payment_registered(), EXIT_WAIT)


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
        return emit('noAccount', W.account_missing(), EXIT_OK)
    try:
        r = call('GET', '/balance', auth=a['install_secret'])
    except GatewayError as e:
        if e.status == 401:
            return emit('noAccount', W.account_missing(), EXIT_OK)
        return emit('serviceUnavailable', W.progress_unknown(), EXIT_WAIT)
    rem = r.get('remaining_uses')
    if not isinstance(rem, int):
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
    if not a.get('install_secret'):
        return emit('noAccount', W.account_missing(), EXIT_OK)
    if not 1 <= args.page <= 100000:
        return emit('usage', '', EXIT_ERROR)
    try:
        cards, total, more = _history(a, args.page, HISTORY_PAGE_SIZE)
    except GatewayError as e:
        if e.status == 401:
            return emit('noAccount', W.account_missing(), EXIT_OK)
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


def _submit_pending(a, st):
    """逐条提交待交反馈。返回 (已建工单列表, 未交原因或 None)。同一条反馈始终用同一个请求编号。"""
    done, reason = [], None
    for item in list(st['pending']):
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
        if digest not in [x.get('digest') for x in st['pending']]:
            st['pending'].append(dict(digest=digest, key='fb-' + uuid.uuid4().hex, body=body))
            _save_support(st)
    elif not st['pending']:
        return emit('feedbackNone', W.feedback_nothing_pending(), EXIT_OK)
    a = load_account()
    if not a.get('install_secret'):
        return emit('feedbackSaved', W.feedback_saved('no_account'), EXIT_WAIT, pending=len(st['pending']))
    done, reason = _submit_pending(a, st)
    if reason and not done:
        return emit('feedbackSaved', W.feedback_saved(reason), EXIT_WAIT, pending=len(st['pending']))
    text = '\n\n'.join(W.ticket_created(t['id'], t.get('category'), _due_text(t)) for t in done)
    if reason:
        text += '\n\n' + W.feedback_saved(reason)
    return emit('ticketCreated', text, EXIT_OK, ticket_ids=[t['id'] for t in done], pending=len(st['pending']))


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
    pl.add_argument('--people', type=int, default=1)
    pl.add_argument('--purpose')
    pl.add_argument('--image')
    c = s.add_parser('confirm')
    c.add_argument('--draft', required=True)
    c.add_argument('--photo-consent', required=True)
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
    except ValueError:
        return emit('requestInvalid', '', EXIT_ERROR)


if __name__ == '__main__':
    sys.exit(main())
