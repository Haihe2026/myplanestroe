#!/usr/bin/env python3
"""孕妈写真照相馆 本地客户端（Python 3.7+ 标准库）。

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

SKILL_ID = 'mps-maternity-portrait-studio'
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

# key: (系列, 标题, 推荐画幅, 场景视觉参照, 默认服饰)。全部场景默认竖版 2:3（1024×1536），本人单人孕期纪念写真。
SERIES = '孕期写真'
SCENES = {
    'studio': (SERIES, '白纱轻盈棚拍', 'portrait',
               '柔光影棚，暖象牙色背景，柔和窗光式布光；纱裙衬里不透、胸腹完整遮盖，不加头纱、捧花或婚礼仪式造型',
               '白色孕期纱裙'),
    'lawn': (SERIES, '户外草坪阳光', 'portrait',
             '户外草坪与自然阳光，柔和逆光与清爽绿意；舒适站姿，不安排运动或挑战动作',
             '日常孕期装'),
    'flowers': (SERIES, '花海仙气', 'portrait',
                '花海与柔和花色，自然侧光，端庄浪漫；纱裙衬里不透、胸腹完整遮盖',
                '孕期纱裙'),
    'oil': (SERIES, '复古油画', 'portrait',
            '复古油画质感的影棚背景，古典侧光与深色背景；不添加王室或宗教身份',
            '深色孕期长裙'),
    'home': (SERIES, '简约家居温馨', 'portrait',
             '简约家居，窗边暖光，干净的沙发与绿植；画面里没有其他人物或婴儿，不表现为纪实照片',
             '舒适上衣和宽松长裤'),
    'beach': (SERIES, '海边度假暖阳', 'portrait',
              '泛化的海边与暖阳，柔和海风与金色光线，不表现为某个真实地点；不加婚礼造型或打卡叙事',
              '孕期长裙'),
    'qipao': (SERIES, '旗袍雅致', 'portrait',
              '素雅影棚，东方雅致的简洁陈设；旗袍布料有自然余量与衣褶，不用秀禾服或婚礼装饰，服饰只是风格选择，不代表民族',
              '雅致孕期旗袍'),
    'korean': (SERIES, '韩式清新', 'portrait',
               '韩式淡雅影棚，干净柔光与低饱和背景',
               '低饱和孕期连衣裙'),
    'forest': (SERIES, '森系清新', 'portrait',
               '森林绿意与自然散射光；不加奇幻生物、宗教或部族标识',
               '端庄孕期裙装'),
    'night': (SERIES, '夜景灯火温馨', 'portrait',
              '夜色与温暖灯火，面部有平衡的暖光，背景招牌没有可读文字，不表现为真实地标',
              '孕期长裙和开衫'),
}
DISCLOSURE = 'AI 生成孕期写真，非实拍'
# 孕期视觉档：只按用户本人自述选择并确认，是创作呈现选项，不是医学分期、孕周判断或标准肚形；没有默认档。
STAGES = {
    'early': ('早期视觉档', '本人自述 1–3 个月或孕早期',
              '衣物下腹部曲线轻微自然，不强行添加明显隆起，不指定肚围或医学标准'),
    'middle': ('中期视觉档', '本人自述 4–6 个月或孕中期',
               '衣物下适度圆润的孕期轮廓，比例自然，不指定肚围，不套早期或晚期的轮廓'),
    'late': ('晚期视觉档', '本人自述 7–9 个月或孕晚期',
             '衣物下较饱满但比例自然的孕期轮廓，不夸张放大，不对应某个精确月份'),
}
# 口语关键词路由，三层：特异主题/服饰 → 一般风格词 → 泛化氛围词（清新、温馨）；只在同一层内看词序，不同层不看词序。
# 孕早/中/晚是独立视觉档，不参与主题路由（「晚期」不路由到夜景）。
ROUTE_SPECIFIC = (
    ('qipao', ('旗袍',)), ('oil', ('油画',)), ('korean', ('韩式',)), ('forest', ('森系', '森林', '树林')),
    ('flowers', ('花海', '花丛')), ('studio', ('白纱', '纱裙', '棚拍', '影棚')), ('beach', ('海边', '海滩')),
    ('lawn', ('草坪', '草地')), ('night', ('夜景', '灯火', '夜色')), ('home', ('家居', '居家', '沙发')),
)
ROUTE_STYLES = (
    ('oil', ('复古', '古典', '艺术')), ('qipao', ('雅致', '东方')), ('korean', ('淡雅', '简约')),
    ('flowers', ('花园', '浪漫')), ('studio', ('柔光',)), ('lawn', ('户外', '阳光')), ('beach', ('暖阳', '度假')),
    ('forest', ('绿意',)), ('night', ('暖调',)), ('home', ('家里',)),
)
ROUTE_MOODS = (('korean', ('清新',)), ('home', ('温馨',)))
STAGE_WORDS = (('early', ('孕早期', '早孕', '孕早')), ('middle', ('孕中期', '孕中')), ('late', ('孕晚期', '孕晚')))
_CN_NUM = {'一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
STAGE_MONTH_RE = re.compile(r'(?:怀孕|孕)了?\s*([1-9一二两三四五六七八九])\s*(?:个多|多个|个)?\s*月')
TEXT_MAX_CHARS = 40
LOCKED_STATES = ('submit_unknown', 'submitted', 'download_pending')


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


def link_fresh(r):
    """服务端签发的短期链接必须带明确有效期：只有正整数秒的 expires_in 才算有效；缺失、0、负数、非整数都不转述。"""
    v = r.get('expires_in')
    return type(v) is int and v > 0


EXPIRED = 'expired'  # 链接已失效（区别于网络 0 和服务端错误码）


# ---------------------------------------------------------------- 提示词

def route_scene(text):
    """按口语关键词给一个主推主题：特异主题/服饰 → 一般风格词 → 泛化氛围词；同一层内取原话里最先出现的，不同层不看词序。
    没有命中返回 None，由宿主按 scenes.md 现场判断并先确认。孕期阶段词不参与主题路由。"""
    text = text or ''
    for table in (ROUTE_SPECIFIC, ROUTE_STYLES, ROUTE_MOODS):
        hits = [(text.find(w), key) for key, words in table for w in words if w in text]
        if hits:
            return min(hits)[1]
    return None


def stated_stage(text):
    """只读出用户原话里明确自述的阶段（孕早/中/晚期，或「怀孕 N 个月」N=1–9）；周数不换算，说法互相冲突或没说返回 None。
    这只是供复述确认的线索，不是默认值：plan 必须由用户确认后显式给出 --stage。"""
    text = text or ''
    found = set(key for key, words in STAGE_WORDS for w in words if w in text)
    for m in STAGE_MONTH_RE.finditer(text):
        g = m.group(1)
        n = int(g) if g.isdigit() else _CN_NUM[g]
        found.add('early' if n <= 3 else 'middle' if n <= 6 else 'late')
    return found.pop() if len(found) == 1 else None


def build_prompt(scene, stage, features='', outfit=''):
    """真实性与本人身份写在第一段；人物描述只来自用户确认的可见特征，不推断年龄、民族或其他身份属性。
    孕期视觉档只是已确认的艺术呈现，不推断真实孕周或健康。"""
    series, title, _, visual, default_outfit = SCENES[scene]
    stage_name, _, stage_look = STAGES[stage]
    who = ('真实性与人物身份：以用户本人确认的这张单人原图为唯一人物依据，画面里恰好 1 位成年人物；保留本人实际可见的脸部结构、五官比例、'
           '肤色、发型、年龄外观和体态，不设计新脸、不换脸、不新增或删除人物，不改变年龄外观。')
    if features:
        who += '用户确认的可见特征：' + features + '。'
    return '\n'.join([
        who,
        '孕期呈现（' + stage_name + '，按本人自述选择的艺术呈现，不是医学孕周或标准肚形）：' + stage_look + '。',
        '动作：只按「' + title + '」主题改变服装、背景和光影：' + visual + '；服装：' + (outfit or default_outfit) +
        '；脸部完整可见，姿态舒适自然，光影和构图自然统一。',
        '文字：图中不得出现任何文字、数字、可读招牌、标志、水印、边框或凭证。',
        '安全：只有本人一位成年人物，不出现儿童、婴儿、伴侣或其他人；服装端庄，胸腹完整遮盖，不裸露腹部、不做性感化或夸张身体；'
        '不推断民族或宗教身份，不出现他人品牌和标志；手和手指形态自然，不出现多余肢体。',
    ])


def wait_text():
    return '1 到 4 分钟'


# ---------------------------------------------------------------- 命令

def cmd_first_turn(args):
    telemetry.report_once(state_dir())
    draft_id = 'd-' + uuid.uuid4().hex
    images = [os.path.abspath(p) for p in (args.image or [])]
    save_draft(dict(draft_id=draft_id, created=_now(), text=args.text or '', images=images,
                    scene=None, stage=None, size=None, subject=None,
                    owner_consent=False, upload_consent=False, pay_consent=False, idem=None, job_id=None, state='draft'))
    has_need = bool(images) or bool((args.text or '').strip()) and args.has_need
    return emit('firstTurn', W.WELCOME + '\n' + W.first_turn_close(has_need), EXIT_OK, draft_id=draft_id, has_image=bool(images),
                welcome=W.WELCOME, demo_intro=W.DEMO_INTRO, suggested_scene=route_scene(args.text),
                stated_stage=stated_stage(args.text))


DEMO_FILE_RE = re.compile(r'[a-z0-9][a-z0-9-]{0,40}\.png')


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
            if not os.path.isfile(dst) or os.path.getsize(dst) != os.path.getsize(src):
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
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if d.get('state') in LOCKED_STATES:
        return emit('taskLocked', W.task_locked(), EXIT_WAIT, draft_id=d['draft_id'])
    if args.scene not in SCENES:
        return emit('sceneInvalid', '', EXIT_ERROR)
    series, title, default_shape, _, _ = SCENES[args.scene]
    shape = args.shape or default_shape
    if shape not in SIZES:
        return emit('shapeInvalid', '', EXIT_ERROR)
    # 资格只按用户本人自述：本人、成年、确实怀孕；不看图判断年龄或孕期、不索要证明。
    # 只有用户明确说了不符合才拒绝，并按实际原因反馈；还没问到的（unknown）先一次合并补问，不当成不符合。
    if args.subject == 'other':
        return emit('notEligible', W.not_eligible('other'), EXIT_ERROR, reason='other')
    if args.adult == 'no':
        return emit('notEligible', W.not_eligible('minor'), EXIT_ERROR, reason='minor')
    if args.pregnant == 'no':
        return emit('notEligible', W.not_eligible('not_pregnant'), EXIT_ERROR, reason='not_pregnant')
    missing = [k for k, v in (('subject', args.subject), ('adult', args.adult), ('pregnant', args.pregnant)) if v == 'unknown']
    if missing:
        return emit('needsEligibility', W.needs_eligibility(missing), EXIT_WAIT, draft_id=d['draft_id'], missing=missing)
    if args.single != 'yes':
        return emit('peopleUnsupported', W.people_unsupported(), EXIT_ERROR)
    if args.stage not in STAGES:
        # 没有默认档：缺档位时只返回可续接的询问，不联网、不替用户猜
        return emit('needsStage', W.needs_stage(), EXIT_WAIT, draft_id=d['draft_id'])
    if args.face_clear != 'yes':
        return emit('needsClearerPhoto', W.needs_clearer_photo(), EXIT_WAIT, draft_id=d['draft_id'])
    features, outfit = _clean_text(args.features), _clean_text(args.outfit)
    if features is None or outfit is None:
        return emit('textInvalid', W.text_invalid(), EXIT_ERROR)
    if args.image:
        d['images'] = [os.path.abspath(args.image)]
    if len(d.get('images') or []) != 1:
        return emit('needsPhoto', W.needs_photo(), EXIT_ERROR)
    r = audit_images.check(d['images'][0])
    if not r['ok']:
        return emit('photoInvalid', W.input_error(r['file'], audit_images.describe(r['problem'])), EXIT_ERROR, problem=r['problem'])
    d.update(scene=args.scene, stage=args.stage, size=SIZES[shape], subject='self', features=features, outfit=outfit,
             photo_sha256=_photo_digest(d['images'][0]), owner_consent=False, upload_consent=False, pay_consent=False,
             idem=None, job_id=None, body_sha256=None, state='planned')
    save_draft(d)
    summary = W.plan_summary(title, STAGES[args.stage][0], W.SHAPE_NAMES[shape], outfit or SCENES[args.scene][4])
    return emit('planReady', W.confirm_paid(summary, wait_text(), features), EXIT_OK, draft_id=d['draft_id'])


def cmd_confirm(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
    if d.get('state') != 'planned' or d.get('stage') not in STAGES or d.get('scene') not in SCENES:
        return emit('needsPlan', '', EXIT_ERROR)
    if args.owner_consent != 'yes' or args.upload_consent != 'yes' or args.pay_consent != 'yes':
        return emit('needsConfirmation', '', EXIT_ERROR)
    if not d.get('photo_sha256') or _photo_digest(d['images'][0]) != d['photo_sha256']:
        return _photo_changed(d)
    d.update(owner_consent=True, upload_consent=True, pay_consent=True, idem='mtn-' + uuid.uuid4().hex,
             state='confirmed', confirmed_at=_now())
    save_draft(d)
    return emit('confirmed', '', EXIT_OK, draft_id=d['draft_id'])


def _photo_digest(path):
    try:
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _photo_changed(d):
    """确认后照片文件有变化：作废原确认和待提交的任务键，必须重新 plan + confirm。"""
    d.update(owner_consent=False, upload_consent=False, pay_consent=False, idem=None, state='photo_changed')
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
    body = dict(prompt=build_prompt(d['scene'], d['stage'], d.get('features') or '', d.get('outfit') or ''), size=d['size'], confirmed=True,
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
    if not (d.get('owner_consent') and d.get('upload_consent') and d.get('pay_consent') and d.get('idem')):
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
        return emit('onboardingPreview', W.auth(extra), EXIT_WAIT, draft_id=d['draft_id'])
    if st == 'checkout':
        if (read_json('flags.json', {}) or {}).get('delivered_once'):
            # 老用户余额用完：先问是否打开充值页，同意后才取链接
            d['state'] = 'needs_credits'
            save_draft(d)
            return emit('needsCredits', W.topup_ask(), EXIT_WAIT, draft_id=d['draft_id'], link_included=False)
        return emit('needsCredits', W.final_step(extra), EXIT_WAIT, draft_id=d['draft_id'], link_included=True)
    if st == 'error':
        return emit('serviceUnavailable', W.failure(_fail_kind(extra), 'not_started'), EXIT_ERROR)
    k = _ensure_skill_key(a)
    if k == 'needs_credits':
        url, status = _membership_link(a)
        if not url:
            return emit('serviceUnavailable', W.failure(_fail_kind(status), 'not_started'), EXIT_ERROR)
        return emit('needsCredits', W.final_step(url), EXIT_WAIT, draft_id=d['draft_id'], link_included=True)
    if k == 'key_reset':
        # 旧凭证已失效并已清除；确认单与原安装身份都保留，尚未提交生成。下次「继续」沿原身份领新凭证再确认绑定。
        return emit('credentialsReset', W.credentials_reset(), EXIT_RESET, draft_id=d['draft_id'], task_kept=True)
    if k != 'ok':
        return emit('serviceUnavailable', W.failure('network' if k == 'network' else 'busy', 'not_started'), EXIT_ERROR)
    title = SCENES[d['scene']][1]
    progress(W.start_recap(title, STAGES[d['stage']][0], W.SHAPE_NAMES[_shape_of(d['size'])]))
    return _submit(d, a, body)


def _submit(d, a, body):
    """先原子保存「提交结果未知」和冻结的请求体摘要，再发 POST；任何模糊结果只查原任务，不重发、不换键。"""
    digest = _body_digest(body)
    if d.get('body_sha256') and d['body_sha256'] != digest:
        return _photo_changed(d)
    d.update(state='submit_unknown', body_sha256=digest)
    save_draft(d)
    try:
        r = call('POST', '/skill-jobs', body, auth=a['skill_key'], idem=d['idem'], timeout=REQUEST_TIMEOUT_S)
    except GatewayError as e:
        if e.status == 401:
            return _submit_unauthorized(d, a)
        if e.status == 402:
            d['state'] = 'needs_credits'
            save_draft(d)
            return emit('needsCredits', W.topup_ask(), EXIT_WAIT, draft_id=d['draft_id'], link_included=False)
        if e.status == 429:
            d['state'] = 'confirmed'
            save_draft(d)
            return emit('serviceBusy', W.busy_kept(), EXIT_WAIT, draft_id=d['draft_id'])
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
    reached = 0
    for attempt in range(POLL_ATTEMPTS):
        if attempt:
            time.sleep(POLL_INTERVAL_S)
        try:
            r = _query('/jobs/' + d['job_id'], a)
        except GatewayError as e:
            if e.status == 401:
                return _keep_reset(d)
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
    folder = os.path.join(os.path.dirname(d['images'][0]), '孕妈写真结果')
    os.makedirs(folder, exist_ok=True)
    return folder


def _gallery(folder):
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith('.png'))
    items = ''.join('<figure><img src="%s" style="max-width:320px"><figcaption>%s<br>%s</figcaption></figure>' % (quote(f), html.escape(f), DISCLOSURE) for f in files)
    with open(os.path.join(folder, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html><meta charset="utf-8"><title>孕妈写真结果</title><body style="font-family:sans-serif">'
                '<p>' + DISCLOSURE + '</p><div style="display:flex;flex-wrap:wrap;gap:16px">' + items + '</div></body>')


def _deliver(d, a):
    try:
        png = _query('/jobs/' + d['job_id'] + '/image', a, binary=True)
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
    return emit('delivered', W.delivery(links, remaining, first, SCENES[d['scene']][1], '\n'.join(notes), md_safe_path(gallery)),
                EXIT_OK, draft_id=d['draft_id'], paths=paths, links=links, gallery=gallery, gallery_link=md_safe_path(gallery),
                remaining_uses=remaining, ask_favorite=first)


def cmd_resume(args):
    telemetry.report_once(state_dir())
    d = load_draft(args.draft)
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
        if not isinstance(remaining, int) or remaining < 1:
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
    if d.get('state') not in ('delivered', 'failed', 'rejected'):
        return emit('taskLocked', W.task_locked(), EXIT_WAIT, draft_id=d['draft_id'])
    if args.pay_consent != 'yes' or not (d.get('owner_consent') and d.get('upload_consent')):
        return emit('needsConfirmation', '', EXIT_ERROR)
    d.update(idem='mtn-' + uuid.uuid4().hex, job_id=None, body_sha256=None, state='confirmed', pay_consent=True)
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
        return emit('registered', '', EXIT_OK, remaining_uses=rem if isinstance(rem, int) else None)
    try:
        r = call('POST', '/quick-entry/status', {'install_secret': a['install_secret']})
    except GatewayError as e:
        return emit('serviceUnavailable', W.account_failure(_fail_kind(e.status), '我的账户'), EXIT_WAIT)
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
    return emit('serviceUnavailable', W.failure(_fail_kind(extra), 'not_started'), EXIT_ERROR)


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
    pl.add_argument('--subject', required=True, choices=('self', 'other', 'unknown'))
    pl.add_argument('--adult', required=True, choices=('yes', 'no', 'unknown'))
    pl.add_argument('--pregnant', required=True, choices=('yes', 'no', 'unknown'))
    pl.add_argument('--stage', default=None)
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
