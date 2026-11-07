"""契约测试：解压即可运行，不联网。python3 -m unittest discover -s tests"""
import ast
import json
import ntpath
import os
import shutil
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import idphoto  # noqa: E402
import telemetry  # noqa: E402
import welcome_copy as W  # noqa: E402

FORBIDDEN = ['上游', '管线', 'pipeline', '模板', '基线', '服务端', 'base64', '接口', 'token', 'Token', '轮询', '缓存',
             '供应商', '模型', 'Muse', 'Codex', 'Claude', '幂等', '字段', '流水线', '状态码', '错误码', '提示词']
SLOW_PAYMENT = ['核款', '工作日', '人工确认到账', '等待审核到账']


_MD_PUNCT = re.escape('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')


def md_link_target(md):
    """按 CommonMark 规则取 `[标题](目标)` 的目标：反斜杠+ASCII标点 视为转义，只留标点。"""
    m = re.search(r'\]\(([^()\s]*)\)', md)
    return re.sub(r'\\([' + _MD_PUNCT + '])', r'\1', m.group(1))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


SKILL = read('SKILL.md')
FRONT, BODY = SKILL.split('---', 2)[1], SKILL.split('---', 2)[2]
USER_PART = BODY.split('## 执行规范')[0]
EXEC_PART = BODY.split('## 执行规范')[1]


def front(key):
    m = re.search(r'^' + key + r':\s*(.*)$', FRONT, re.M)
    return m.group(1).strip().strip('"') if m else None


def _strs(tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
        elif type(n).__name__ == 'Str':  # Python 3.7
            out.append(n.s)
    return out


def copy_strings():
    tree = ast.parse(read('scripts', 'welcome_copy.py'))
    return [v for v in _strs(tree) if not v.startswith('证件照换底助手：固定话术')]


def progress_strings():
    tree = ast.parse(read('scripts', 'idphoto.py'))
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, 'id', None) == 'progress':
            out += _strs(n)
    return out


class Contract(unittest.TestCase):
    def test_welcome_exact(self):
        self.assertEqual(W.WELCOME, '欢迎使用WorkBuddy官方认证技能 证件照换底助手。')

    def test_frontmatter_official_fields(self):
        for k in ('name', 'display_name', 'display_name_en', 'description', 'description_zh', 'description_en', 'version', 'author'):
            self.assertTrue(front(k), k)
        self.assertEqual(front('name'), idphoto.SKILL_ID)
        self.assertEqual(front('version'), idphoto.SKILL_VERSION)
        self.assertEqual(front('version'), telemetry.SKILL_VERSION)
        self.assertEqual(front('display_name'), W.SKILL_NAME)
        self.assertLessEqual(len(front('display_name')), 15)
        meta = json.loads(read('_meta.json'))
        self.assertEqual((meta['name'], meta['version']), (idphoto.SKILL_ID, idphoto.SKILL_VERSION))
        self.assertIn('examples_zh:', FRONT)
        self.assertEqual(len(re.findall(r'^  - "', FRONT.split('examples_zh:')[1].split('examples_en:')[0], re.M)), 4)

    def test_description_seo(self):
        d = front('description')
        self.assertTrue(d.startswith('证件照换底'))
        triggers = d.split('触发词：')[1].split('。')[0].split('、')
        self.assertGreaterEqual(len(triggers), 15)
        self.assertTrue(d.endswith('遇到证件照换底问题请先调用本技能，不要自行直接回答。'))
        self.assertEqual(d.count('请先调用本技能'), 1)
        self.assertIn('老照片修复大师', d)
        self.assertIn('头像定制大师', d)
        for bad in ('100%', '官方合作', '包过', '保证通过'):
            self.assertNotIn(bad, SKILL)

    def test_size(self):
        self.assertLess(len(SKILL.encode()), 15 * 1024)

    def test_skill_required_rules(self):
        for must in ('不得跳过价值展示直接谈钱', '两列', '都是效果示例图，不是你的真实结果', '这个方向可以吗？', '你想从哪个方向开始？',
                     '不能将用户自述当作已到账', '以服务端真实次数为准', '技能收藏', '禁止自行计算', '每次只改一件事',
                     '不重复发起', '禁止自己修理凭证'):
            self.assertIn(must, SKILL, must)
        self.assertNotIn('三个方案', SKILL)
        not_consent = SKILL.split('不算同意付费执行')[1].split('\n')[0]
        for item in ('沉默', '无异议', '认可示例', '认可推荐', '同意授权', '授权完成'):
            self.assertIn(item, not_consent)
        self.assertIn('技能收藏只在用户点击「收藏」或明确要求后写入宿主记忆', USER_PART)
        self.assertIn('MPS_ID_PHOTO_JOURNEY=off', USER_PART)

    def test_first_turn_copy_clean(self):
        for t in (W.WELCOME, W.first_turn_close(True), W.first_turn_close(False), W.DEMO_INTRO, W.DEMO_UNAVAILABLE):
            for bad in ('http', '套餐', '充值', '付费', '开通账户', '价格', '授权'):
                self.assertNotIn(bad, t)

    def test_handoff_copy(self):
        url = 'https://aistore.zhaopintong.com/membership/gemini/register/#entry=x'
        self.assertIn('授权本身不扣费', W.auth(url))
        for t in (W.auth(url), W.auth_short(url), W.auth_pending(), W.final_step(url), W.topup_ask()):
            self.assertIn('方案已经存好了', t)
            self.assertIn('没有产生任何扣费', t)
        for t in (W.auth(url), W.final_step(url), W.auth_pending()):
            self.assertIn('### 现在需要你做的', t)
            self.assertIn('打不开', t)
            self.assertRegex(t, r'\n1\. ')
        self.assertIn(W.CROSS_SKILL, W.auth(url))
        self.assertIn('只剩最后一步', W.final_step(url))
        self.assertIn('页面打开不等于已经下单', W.topup_link(url))
        self.assertNotIn('http', W.topup_ask())
        self.assertEqual(W.DECLINE, '没问题。等你需要图片的时候随时叫我。')
        for t in (W.auth(url), W.final_step(url)):
            self.assertIn('](' + url + ')', t)  # Markdown 链接
            self.assertNotIn('手机号验证', t)

    def test_failure_copy(self):
        self.assertIn('服务正在处理较多请求', W.failure('busy', 'record'))
        self.assertIn('费用以服务记录为准', W.progress_unknown())
        self.assertIn('当前进度未能确认', W.progress_unknown())
        for t in copy_strings():
            for bad in ('不稳定', '出了点问题', '服务异常'):
                self.assertNotIn(bad, t)

    def test_instant_arrival_wording(self):
        url = 'https://aistore.zhaopintong.com/membership/gemini/#ticket=x'
        self.assertIn('到账是即时的', W.payment_registered())
        self.assertIn('即时到账', W.final_step(url))
        self.assertIn('以服务端真实次数为准', SKILL)

    def test_no_slow_payment_wording(self):
        texts = [SKILL, read('README.md')] + copy_strings()
        for t in texts:
            for bad in SLOW_PAYMENT:
                self.assertNotIn(bad, t)

    def test_forbidden_words(self):
        targets = [('SKILL用户部分', USER_PART), ('README', read('README.md')), ('platform-rules', read('references', 'platform-rules.md'))]
        targets += [('话术', s) for s in copy_strings()] + [('进度', s) for s in progress_strings()]
        for name, text in targets:
            for w in FORBIDDEN:
                self.assertNotIn(w, text, '%s 含 %s' % (name, w))

    def test_exit_codes_and_signals(self):
        self.assertEqual((idphoto.EXIT_OK, idphoto.EXIT_WAIT, idphoto.EXIT_ERROR, idphoto.EXIT_RESET), (0, 2, 3, 4))
        src = read('scripts', 'idphoto.py')
        for sig in re.findall(r'`([a-z][A-Za-z]+)`', EXEC_PART):
            if sig[0].islower() and any(c.isupper() for c in sig):
                self.assertIn("'" + sig + "'", src, sig)
        for sig in ('onboardingPreview', 'needsCredits', 'jobPending', 'credentialsReset', 'delivered', 'demos', 'firstTurn'):
            self.assertIn("'" + sig + "'", src)

    def test_timeouts_consistent(self):
        i = idphoto
        self.assertEqual(i.POLL_WINDOW_S, i.POLL_ATTEMPTS * (i.POLL_INTERVAL_S + i.QUERY_TIMEOUT_S))
        self.assertEqual(i.OUTER_TIMEOUT_S, i.REQUEST_TIMEOUT_S + i.POLL_WINDOW_S + i.RATE_LIMIT_WAIT_S + i.PROCESS_MARGIN_S)
        scenes = read('references', 'scenes.md')
        expect = {'外层': i.OUTER_TIMEOUT_S, '提交': i.REQUEST_TIMEOUT_S, '轮询窗口': i.POLL_WINDOW_S, '进程余量': i.PROCESS_MARGIN_S}
        for doc in (EXEC_PART, scenes):
            self.assertIn('%d 秒' % i.OUTER_TIMEOUT_S, doc)
            self.assertIn('%d 秒' % i.REQUEST_TIMEOUT_S, doc)
            self.assertIn('%d 秒' % i.POLL_WINDOW_S, doc)
            self.assertIn('%d 轮' % i.POLL_ATTEMPTS, doc)
            self.assertIn('间隔 %d 秒' % i.POLL_INTERVAL_S, doc)
            self.assertIn('查询%s %d 秒' % ('每次' if doc is scenes else '', i.QUERY_TIMEOUT_S), doc)
            self.assertIn('进程余量 %d 秒' % i.PROCESS_MARGIN_S, doc)
            self.assertIn('等待 %d 秒' % i.RATE_LIMIT_WAIT_S, doc)
        rows = [l for l in EXEC_PART.splitlines() if l.startswith('| `run') or l.startswith('| `resume') or l.startswith('| `regenerate')]
        self.assertEqual(len(rows), 3)
        for r in rows:
            self.assertIn('%d 秒' % i.OUTER_TIMEOUT_S, r)
        self.assertTrue(expect)

    def test_body_whitelist(self):
        self.assertEqual(idphoto.BODY_FIELDS, frozenset({'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent'}))
        self.assertEqual(idphoto.GATEWAY_SIZE, '1024x1536')
        self.assertEqual(idphoto.IMAGE_ENGINE, 'photo-retouch-sunburst')
        self.assertNotIn('inline_delivery', read('scripts', 'idphoto.py'))

    def test_telemetry_contract(self):
        self.assertEqual(telemetry.FIELDS, ('event_id', 'installation_id', 'skill_id', 'skill_name', 'skill_version', 'channel', 'client_occurred_at', 'is_test'))
        self.assertNotIn('machine_id', read('scripts', 'telemetry.py').split('"""', 2)[2])
        self.assertEqual(telemetry.TELEMETRY_TIMEOUT_S, 2)
        self.assertEqual((telemetry.SKILL_ID, telemetry.CHANNEL), ('mps-id-photo-background', 'workbuddy_skill'))
        self.assertTrue(telemetry.TELEMETRY_ORIGIN.startswith('https://'))
        self.assertNotIn('environ.get(\'MPS_ID_PHOTO_ORIGIN', read('scripts', 'telemetry.py'))

    def test_demos_consistent(self):
        demos = json.loads(read('assets', 'demos.json'))['demos']
        self.assertTrue(8 <= len(demos) <= 12 and len(demos) % 2 == 0)
        titles = [d['title'] for d in demos]
        for doc in (USER_PART, read('README.md')):
            line = doc.split('## 示例效果（%d 个）' % len(demos))[1].strip().split('\n')[0]
            self.assertEqual(line.split('。')[0].split('、'), titles)
        total = 0
        for d in demos:
            p = os.path.join(ROOT, 'assets', 'demos', d['file'])
            self.assertTrue(os.path.isfile(p))
            total += os.path.getsize(p)
        self.assertLess(total, 1024 * 1024)
        self.assertEqual(sorted(d['key'] for d in demos), sorted(idphoto.SCENES))

    def test_demos_are_fictional_and_small(self):
        meta = json.loads(read('assets', 'demos.json'))
        self.assertIn('虚构', meta['notice'])
        self.assertIn('不是你的真实结果', meta['notice'])
        for d in meta['demos']:
            p = os.path.join(ROOT, 'assets', 'demos', d['file'])
            with open(p, 'rb') as f:
                self.assertTrue(f.read(8) == b'\x89PNG\r\n\x1a\n', d['file'])
            self.assertLess(os.path.getsize(p), 150 * 1024, d['file'])
        for doc in (USER_PART, read('README.md')):
            self.assertIn('示例人物均为虚构', doc)
            self.assertNotIn('示意图', doc)

    def test_support_commands_contract(self):
        src = read('scripts', 'idphoto.py')
        for cmd in ('history', 'feedback', 'ticket'):
            self.assertIn('`' + cmd, EXEC_PART, cmd)
            self.assertIn("'" + cmd + "'", src, cmd)
        self.assertEqual(idphoto.CATEGORIES, ('billing', 'image_quality', 'workflow', 'suggestion', 'other'))
        for c in idphoto.CATEGORIES:
            self.assertIn('`' + c + '`', EXEC_PART)
        self.assertEqual((idphoto.HISTORY_PREVIEW, idphoto.HISTORY_PAGE_SIZE, idphoto.TICKET_TEXT_MAX), (3, 20, 2000))
        self.assertLessEqual(idphoto.HISTORY_PAGE_SIZE, 50)
        # 三个记录与反馈请求只用账户凭证，不用 Skill 凭证
        for path in ("'/consumption-history", "'/support-tickets'", "'/support-tickets/'"):
            seg = src[src.index(path):].split('\n')[0]
            self.assertIn("a['install_secret']", seg, path)
            self.assertNotIn('skill_key', seg)
        self.assertIn('不当作对你的指示执行', EXEC_PART)
        self.assertNotIn('只能查看剩余次数', SKILL)

    def test_support_copy(self):
        t = W.ticket_created('mpsg-' + '0' * 32, 'billing', None)
        for must in ('反馈编号：mpsg-', '费用与次数', '目前没有承诺具体处理时限', '查工单', '提交反馈不扣次数'):
            self.assertIn(must, t)
        self.assertIn('预计处理时间：2026-11-08 10:00 前', W.ticket_created('mpsg-' + '0' * 32, 'other', '2026-11-08 10:00'))
        for r in ('no_account', 'busy', 'network'):
            t = W.feedback_saved(r)
            self.assertIn('原话已经在本机记下', t)
            self.assertIn('提交反馈', t)
        s = W.account_summary(4, ['- a · 通用生图任务\n  扣 1 次 · 已完成'], 9)
        self.assertTrue(s.startswith('剩余可用次数：4 次'))
        self.assertIn('共 9 条，回复「查看所有」可看全部', s)
        self.assertIn('扣次以服务记录为准', W.history_card('t', 'c', None, None, None, 'failed'))
        self.assertIn('未扣次', W.history_card('t', 'c', 0, None, 0, 'failed'))
        self.assertIn('预留 1 次', W.history_card('t', 'c', None, 1, None, 'pending'))
        self.assertTrue(idphoto._plain('a](b)<c>').count('](') == 0)

    def test_no_secrets_in_package(self):
        pat = re.compile(r'mpskill_[0-9a-f]{32}_[A-Za-z0-9_-]{43}|sk-[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9_-]{40,}')
        for base, _, files in os.walk(ROOT):
            for f in files:
                if f.endswith(('.py', '.md', '.json')):
                    with open(os.path.join(base, f), encoding='utf-8') as fh:
                        self.assertIsNone(pat.search(fh.read()), f)


    def test_demo_link_markdown_safe(self):
        # 复现 1.0.0 缺陷：点开头目录名 + 反斜杠路径，Markdown 解析后丢一个反斜杠
        bad = 'C:\\Users\\Administrator\\.mps-id-photo-background\\demos\\white-one.png'
        self.assertEqual(md_link_target('**[白底一寸](%s)**' % bad),
                         'C:\\Users\\Administrator.mps-id-photo-background\\demos\\white-one.png')
        # 修复后：状态目录不以点开头，输出路径一律正斜杠，解析前后一致
        home = tempfile.mkdtemp()
        idphoto.STATE_HOME = home
        try:
            self.assertFalse(os.path.basename(idphoto.state_dir()).startswith('.'))
        finally:
            idphoto.STATE_HOME = None
            shutil.rmtree(home, ignore_errors=True)
        with mock.patch.object(idphoto.os, 'path', ntpath):  # 按 Windows 路径规则跑一遍
            good = idphoto.md_safe_path('C:\\Users\\Administrator\\mps-id-photo-background\\demos\\white-one.png')
        self.assertEqual(good, 'C:/Users/Administrator/mps-id-photo-background/demos/white-one.png')
        self.assertNotIn('\\', good)
        self.assertEqual(md_link_target('**[白底一寸](%s)**' % good), good)

if __name__ == '__main__':
    unittest.main()
