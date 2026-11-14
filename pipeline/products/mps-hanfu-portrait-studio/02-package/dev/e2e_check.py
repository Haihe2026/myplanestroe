"""端到端检查：真实客户端代码 + 进程内模拟后端。合成账户，真实上游调用 0。

运行：python3 dev/e2e_check.py   （可加 --package <解压后的技能目录> 对干净解压的 ZIP 重跑）
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, '..', 'mps-hanfu-portrait-studio')
if '--package' in sys.argv:
    i = sys.argv.index('--package')
    PKG = os.path.abspath(sys.argv[i + 1])
    del sys.argv[i:i + 2]
ZIPS = []
_SPEC_PATH = os.path.join(HERE, '..', '..', '01-dev-spec.json')
SPEC = json.load(open(_SPEC_PATH, encoding='utf-8')) if os.path.isfile(_SPEC_PATH) else None
while '--zip' in sys.argv:
    i = sys.argv.index('--zip')
    ZIPS.append(os.path.abspath(sys.argv[i + 1]))
    del sys.argv[i:i + 2]
sys.path.insert(0, os.path.join(PKG, 'scripts'))
for m in ('studio', 'telemetry', 'welcome_copy', 'png_local', 'audit_images'):
    sys.modules.pop(m, None)
import studio  # noqa: E402
import telemetry  # noqa: E402
import png_local  # noqa: E402
import welcome_copy as W  # noqa: E402
sys.path.insert(0, HERE)
import mock_backend  # noqa: E402
mock_backend.studio = studio  # 与被测包同一模块实例


def jpeg_bytes(w=600, h=800, note=b''):
    """标准库合成的合法基线灰度 JPEG（每块 DC=0、AC 直接 EOB，各 1 比特 0），任意尺寸、可完整解码。
    1.0.1 起参考图要完整解码校验（A3-TRV-02），旧版只有 SOF 头加零字节的假 JPEG 已不再放行。"""
    import struct

    def seg(m, body):
        return b'\xff' + bytes([m]) + struct.pack('>H', len(body) + 2) + body
    blocks = -(-w // 8) * -(-h // 8)
    nbits = blocks * 2
    scan = b'\x00' * (nbits // 8) + (bytes([(1 << (8 - nbits % 8)) - 1]) if nbits % 8 else b'')
    one = bytes([1] + [0] * 15)
    return (b'\xff\xd8' + seg(0xE0, b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00') + (seg(0xFE, note) if note else b'')
            + seg(0xDB, b'\x00' + b'\x01' * 64) + seg(0xC0, b'\x08' + struct.pack('>HH', h, w) + b'\x01\x01\x11\x00')
            + seg(0xC4, b'\x00' + one + b'\x00' + b'\x10' + one + b'\x00')
            + seg(0xDA, b'\x01\x01\x00\x00\x3f\x00') + scan + b'\xff\xd9')


def _bomb_png(virtual_mb):
    import struct
    import zlib

    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    c = zlib.compressobj(9)
    zero = bytes(1 << 20)
    idat = b''.join(c.compress(zero) for _ in range(virtual_mb)) + c.flush()
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 128, 128, 8, 0, 0, 0, 0))
            + chunk(b'IDAT', idat) + chunk(b'IEND', b''))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=os.environ.get('MPS_E2E_TMP'))  # 可指定可写目录
        self.home = os.path.join(self.tmp, 'home')
        os.makedirs(self.home)
        self.env = dict(os.environ)
        os.environ['HOME'] = self.home
        studio.STATE_HOME = self.home  # 不依赖 HOME/USERPROFILE，Windows 同样隔离
        os.environ['MPS_HANFU_PORTRAIT_TEST'] = '1'
        os.environ.pop('MPS_HANFU_PORTRAIT_JOURNEY', None)
        self.mock = mock_backend.Mock()
        studio.TRANSPORT = self.mock.transport
        telemetry.TRANSPORT = self.mock.telemetry_transport
        self._sleep = studio.time.sleep
        studio.time.sleep = lambda s: None
        self.photos = os.path.join(self.tmp, 'photos')
        os.makedirs(self.photos)
        self.photo = os.path.join(self.photos, 'me.jpg')
        with open(self.photo, 'wb') as f:
            f.write(jpeg_bytes())
        with open(self.photo, 'rb') as f:
            self.photo_bytes = f.read()

    def tearDown(self):
        studio.time.sleep = self._sleep
        studio.STATE_HOME = None
        os.environ.clear()
        os.environ.update(self.env)
        # Keep a locked Windows test fixture as evidence; never mask a test-body failure.
        import gc
        gc.collect()
        base = os.path.realpath(os.environ.get('MPS_E2E_TMP', tempfile.gettempdir()))
        target = os.path.realpath(self.tmp)
        if os.path.commonpath([os.path.normcase(base), os.path.normcase(target)]) != os.path.normcase(base):
            raise AssertionError('fixture cleanup target outside declared test root')
        try:
            shutil.rmtree(target)
        except PermissionError as exc:
            if os.name != 'nt' or getattr(exc, 'winerror', None) != 32:
                raise
            log = os.environ.get('MPS_E2E_RETAIN_LOG')
            if log:
                with open(log, 'a', encoding='utf-8') as fh:
                    fh.write(json.dumps(dict(test=self.id(), retained=target, reason='Windows open test handle; cleanup only')) + '\n')

    def run_cmd(self, *argv):
        argv = list(argv)
        if argv and argv[0] == 'plan':
            # 汉服写真 plan 必填项：未显式给出时按合规的本人、成年、单人照补齐（专项用例会显式覆盖）
            if '--self' not in argv:
                argv += ['--self', 'yes']
            if '--adult' not in argv:
                argv += ['--adult', 'yes']
            if '--single' not in argv:
                argv += ['--single', 'yes']
            if '--face-clear' not in argv:
                argv += ['--face-clear', 'yes']
        if argv and argv[0] == 'confirm':
            if '--owner-consent' not in argv:
                argv += ['--owner-consent', 'yes']
            if '--upload-consent' not in argv:
                argv += ['--upload-consent', 'yes']
        out, errs = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(errs):
            code = studio.main(list(argv))
        lines = out.getvalue().split('\n', 1)
        sig = json.loads(lines[0])
        return code, sig, (lines[1] if len(lines) > 1 else ''), errs.getvalue()

    def confirmed_draft(self, scene='daily', shape=None, features=None):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '想拍汉服写真', '--image', self.photo, '--has-need')
        did = s['draft_id']
        args = ['plan', '--draft', did, '--scene', scene]
        if shape:
            args += ['--shape', shape]
        if features:
            args += ['--features', features]
        code, s, _, _ = self.run_cmd(*args)
        self.assertEqual(code, 0, s)
        code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--pay-consent', 'yes')
        self.assertEqual(code, 0)
        return did

    def secret(self):
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')) as f:
            return json.load(f)['install_secret']

    def paid_account(self, did, balance=5):
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (2, 'onboardingPreview'))
        self.mock.authorize(self.secret(), balance)


class FirstTurn(Base):
    def test_first_turn_zero_business_http(self):
        def boom(*a, **k):
            raise AssertionError('business request in first turn')
        studio.TRANSPORT = boom
        for text, img in (('你好', None), ('', self.photo), ('你能做什么', None), ('去不了哈尔滨，想用我的单人照做一张冰雪主题写真', self.photo)):
            argv = ['first-turn', '--defer-entry', '--text', text] + (['--image', img] if img else [])
            code, s, text_out, _ = self.run_cmd(*argv)
            self.assertEqual(code, 0)
            self.assertTrue(text_out.startswith(W.WELCOME))
            for bad in ('http', '套餐', '充值', '付费', '开通账户', '价格', '授权'):
                self.assertNotIn(bad, text_out + json.dumps(s, ensure_ascii=False))
        code, s, _, _ = self.run_cmd('demo')
        self.assertEqual((code, len(s['items'])), (0, 10))
        self.assertEqual(len(self.mock.telemetry_calls), 1)  # 首次对话上报仅一次，且是唯一网络动作

    def test_close_question(self):
        _, _, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertIn('你想从哪个方向开始？', t)
        _, _, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '想做京都和服写真', '--image', self.photo, '--has-need')
        self.assertIn('这个方向可以吗？', t)

    def test_demo_paths_and_single(self):
        code, s, t, _ = self.run_cmd('demo', 'garden')
        self.assertEqual(len(s['items']), 1)
        from urllib.parse import unquote
        p = unquote(s['items'][0]['path'])  # API returns Markdown-safe encoded path; file lookup uses decoded native path.
        self.assertTrue(os.path.isabs(p) and os.path.isfile(p))
        w, h = png_local.size_of(open(p, 'rb').read())
        self.assertLess(w, h)  # 汉服示例均为竖版 2:3
        self.assertIn('AI 生成汉服写真，非实拍', s['items'][0]['note'])
        self.assertIn(W.DEMO_INTRO, t)
        code, s, _, _ = self.run_cmd('demo', 'nope')
        self.assertEqual(code, 3)

    def test_demo_links_survive_markdown(self):
        """回归：demo 链接按 Markdown 解析后路径仍存在（含点开头上级目录、含空格的家目录）。"""
        import re
        punct = re.escape('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
        try:
            from markdown_it import MarkdownIt
            md = MarkdownIt()
        except ImportError:
            md = None
        home = os.path.join(self.tmp, '.dot-parent', 'Travel Demo Assets', 'Travel#Demo', 'Travel%Demo')  # 含空格（A3-E02）、#（A3-E03）与 %（规格 14 节）
        os.makedirs(home)
        studio.STATE_HOME = home
        code, s, _, _ = self.run_cmd('demo')
        self.assertEqual((code, len(s['items'])), (0, 10))
        for it in s['items']:
            p = it['path']
            self.assertNotIn('\\', p)
            self.assertNotIn('/.mps-', p)
            cell = '**[%s](%s)**<br>%s' % (it['title'], p, it['note'])
            target = re.sub(r'\\([' + punct + '])', r'\1', re.search(r'\]\(([^()\s]*)\)', cell).group(1))
            self.assertEqual(target, p)
            self.assertNotIn(' ', p)
            self.assertNotIn('#', p)
            from urllib.parse import unquote
            if md is not None:
                href = re.search(r'href="([^"]*)"', md.render(cell)).group(1)
                self.assertEqual(unquote(href), unquote(p))
            # 按 URI 规则先拆片段与查询串再解码（A3-E03 的检查方法），路径须指向存在的文件
            path, _, frag = target.partition('#')
            path, _, query = path.partition('?')
            self.assertEqual((frag, query), ('', ''))
            self.assertTrue(os.path.isfile(unquote(path)))

    def test_demo_missing_assets_exit3(self):
        real = studio.HERE
        studio.HERE = os.path.join(self.tmp, 'empty', 'scripts')
        try:
            code, s, t, _ = self.run_cmd('demo')
        finally:
            studio.HERE = real
        self.assertEqual((code, s['signal']), (3, 'demoUnavailable'))
        self.assertIn('这次暂时没能展示示例图', t)

    # ---- A3-FAM-03（1.0.1）：示例集合必须完整，缺一张不得部分成功 ----

    def _pkg_copy(self):
        dst = os.path.join(self.tmp, 'pkg copy')
        shutil.copytree(os.path.join(PKG, 'assets'), os.path.join(dst, 'assets'))
        return dst

    def _demo_in(self, pkg, *argv):
        def boom(*a, **k):
            raise AssertionError('network in demo')
        real_here, real_t, real_tt = studio.HERE, studio.TRANSPORT, telemetry.TRANSPORT
        studio.HERE, studio.TRANSPORT, telemetry.TRANSPORT = os.path.join(pkg, 'scripts'), boom, boom
        acc = os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')
        try:
            return self.run_cmd('demo', *argv)
        finally:
            studio.HERE, studio.TRANSPORT, telemetry.TRANSPORT = real_here, real_t, real_tt
            self.assertFalse(os.path.exists(acc))  # 零凭证访问

    def _out(self):
        d = os.path.join(self.home, 'mps-hanfu-portrait-studio', 'demos')
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def test_fam03_default_missing_one_exit3(self):
        pkg = self._pkg_copy()
        os.remove(os.path.join(pkg, 'assets', 'tang_ruqun.png'))
        self.assertEqual(len(json.load(open(os.path.join(pkg, 'assets', 'demos.json'), encoding='utf-8'))['demos']), 10)
        code, s, t, _ = self._demo_in(pkg)
        self.assertEqual((code, s['signal']), (3, 'demoUnavailable'))
        self.assertNotIn('items', s)
        self.assertEqual(s.get('missing'), ['tang_ruqun'])
        self.assertIn('这次暂时没能展示示例图', t)
        self.assertEqual(self._out(), [])  # 输出前校验：一张都不复制
        code, s, _, _ = self._demo_in(pkg, 'tang_ruqun')  # 单项指定缺失图
        self.assertEqual((code, s['signal']), (3, 'demoUnavailable'))
        code, s, _, _ = self._demo_in(pkg, 'garden')  # 单项指定存在图
        self.assertEqual((code, len(s['items'])), (0, 1))
        shutil.copyfile(os.path.join(PKG, 'assets', 'tang_ruqun.png'), os.path.join(pkg, 'assets', 'tang_ruqun.png'))  # 补齐
        code, s, _, _ = self._demo_in(pkg)
        self.assertEqual((code, s['signal'], len(s['items'])), (0, 'demos', 10))
        self.assertEqual([i['key'] for i in s['items']], list(studio.SCENES))
        self.assertEqual(len(self._out()), 10)

    def test_fam03_manifest_anomalies_exit3(self):
        good = json.load(open(os.path.join(PKG, 'assets', 'demos.json'), encoding='utf-8'))
        import copy
        cases = []
        c = copy.deepcopy(good); c['demos'].pop(); cases.append(('nine', c))
        c = copy.deepcopy(good); c['demos'][1]['key'] = c['demos'][0]['key']; cases.append(('dup', c))
        c = copy.deepcopy(good); c['demos'][2]['key'] = 'unknown'; cases.append(('unknown', c))
        c = copy.deepcopy(good); c['demos'][3]['file'] = '../studio.png'; cases.append(('path', c))
        c = copy.deepcopy(good); c['demos'][3]['file'] = 'demos/studio.png'; cases.append(('subdir', c))
        c = copy.deepcopy(good); del c['demos'][4]['title']; cases.append(('field', c))
        c = copy.deepcopy(good); c['demos'].append(dict(c['demos'][0])); cases.append(('eleven', c))
        cases.append(('notlist', {'demos': {}}))
        for name, data in cases:
            pkg = self._pkg_copy()
            with open(os.path.join(pkg, 'assets', 'demos.json'), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            code, s, _, _ = self._demo_in(pkg)
            self.assertEqual((code, s['signal']), (3, 'demoUnavailable'), name)
            code, s, _, _ = self._demo_in(pkg, 'garden')
            self.assertEqual((code, s['signal']), (3, 'demoUnavailable'), name)
            shutil.rmtree(pkg)
        pkg = self._pkg_copy()
        with open(os.path.join(pkg, 'assets', 'demos.json'), 'w', encoding='utf-8') as f:
            f.write('{broken')
        self.assertEqual(self._demo_in(pkg)[0], 3)

    def test_fam03_complete_set_ok(self):
        code, s, _, _ = self._demo_in(self._pkg_copy())
        self.assertEqual((code, len(s['items'])), (0, 10))
        self.assertEqual(sorted(i['key'] for i in s['items']), sorted(studio.SCENES))


class Confirmation(Base):
    def test_no_consent_no_task(self):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        did = s['draft_id']
        self.run_cmd('plan', '--draft', did, '--scene', 'daily')
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (3, 'needsConfirmation'))
        for photo, pay in (('no', 'yes'), ('yes', 'no'), ('', '')):
            code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--owner-consent', photo, '--pay-consent', pay)
            self.assertEqual(s['signal'], 'needsConfirmation')
        self.assertEqual(self.mock.calls, [])

    def test_plan_copy(self):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        code, s, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'flowing',
                                     '--features', '短发戴眼镜', '--outfit', '浅蓝色')
        self.assertIn('确认开始', t)
        self.assertIn('按张计费', t)
        self.assertIn('同意把这张照片发送给图片服务及算力供应商处理，只用于本次制作', t)
        self.assertNotIn('监护人', t)
        self.assertIn('你本人的单人照', t)
        self.assertIn('AI 生成汉服写真，非实拍', t)
        self.assertIn('艺术风格写真，不是考古精确复原', t)
        self.assertIn('我会按确认过的样子保留人物：短发戴眼镜', t)
        self.assertIn('「汉服广袖流仙」汉服写真，你本人这张单人照，服饰与妆造：' + studio.SCENES['flowing'][5] +
                      '；颜色与细节：浅蓝色（整套同一形制），竖版 2:3（1024×1536），1 张', t)  # HNF-A3-01：主题结构 + 颜色细节
        for bad in ('¥', '元', '提示词', '模板'):
            self.assertNotIn(bad, t)

    def test_bad_photo_named_no_network(self):
        bad = os.path.join(self.photos, 'broken.png')
        open(bad, 'wb').write(b'not an image')
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', bad)
        code, s, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'daily')
        self.assertEqual((code, s['signal']), (3, 'photoInvalid'))
        self.assertIn('broken.png', t)
        self.assertEqual(self.mock.calls, [])

    def test_shape_defaults_and_people_range(self):
        did = self.confirmed_draft()
        d = json.load(open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'drafts', did + '.json')))
        self.assertEqual((d['size'], d['subject_self'], d['subject_adult']), ('1024x1536', 'yes', 'yes'))
        self.assertNotIn('orderer', d)
        did = self.confirmed_draft(scene='garden', shape='landscape')
        d = json.load(open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'drafts', did + '.json')))
        self.assertEqual(d['size'], '1536x1024')
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        code, s2, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'tang_ruqun', '--single', 'no')
        self.assertEqual((code, s2['signal']), (3, 'peopleUnsupported'))
        for must in ('只做你本人一个人的单人照', '双人或多人合影', '各自用本人的单人照', '没有产生任何扣费'):
            self.assertIn(must, t)
        code, s2, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'tang_ruqun', '--face-clear', 'no')
        self.assertEqual((code, s2['signal']), (2, 'needsClearerPhoto'))
        self.assertIn('没有产生任何扣费', t)
        self.assertEqual(self.mock.calls, [])

    def test_refuse_copy(self):
        code, s, t, _ = self.run_cmd('refuse')
        self.assertEqual((code, s['signal']), (0, 'refused'))
        for must in ('成年用户本人知情同意的单人照', '不换脸', '名人', '合成到一起', '孩子', '婚服', '旗袍', '和服', '军装', '考古鉴定'):
            self.assertIn(must, t)
        self.assertEqual(self.mock.calls, [])


class AccountBilling(Base):
    def test_full_flow_auth_topup_deliver(self):
        did = self.confirmed_draft(scene='flowing', features='短发戴眼镜')
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (2, 'onboardingPreview'))
        for must in ('授权本身不扣费', '### 现在需要你做的', '打不开', W.REASSURE_SAVED, W.REASSURE_FREE, W.CROSS_SKILL, '不用手机号'):
            self.assertIn(must, t)
        self.assertIn('https://aistore.zhaopintong.com/membership/gemini/register/#entry=', t)
        secret = self.secret()
        # 未完成授权就说好了 → 续接查询
        code, s, t, _ = self.run_cmd('status')
        self.assertEqual(s['signal'], 'authPending')
        self.mock.authorize(secret, 0)
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal'], s['link_included']), (2, 'needsCredits', True))
        for must in ('只剩最后一步', '### 现在需要你做的', '打不开', W.REASSURE_SAVED, W.REASSURE_FREE):
            self.assertIn(must, t)
        self.assertNotIn('¥', t)
        code, s, t, _ = self.run_cmd('paid')  # 1.0.3：用户自述不算到账，只按服务端次数说
        self.assertEqual((code, s['signal'], s['remaining_uses']), (2, 'creditsPending', 0))
        self.assertNotIn('已收到你的付款登记', t)
        self.mock.users[secret]['balance'] = 3
        code, s, t, _ = self.run_cmd('paid')
        self.assertEqual((code, s['signal'], s['remaining_uses']), (0, 'creditsConfirmed', 3))
        self.assertIn('剩余可用次数 3 次', t)
        code, s, t, err = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (0, 'delivered'), t)
        self.assertEqual(len(s['paths']), 1)
        self.assertTrue(all(os.path.isfile(p) for p in s['paths']))
        self.assertEqual(png_local.size_of(open(s['paths'][0], 'rb').read()), (1024, 1536))
        self.assertTrue(s['paths'][0].endswith('me-flowing.png'), s['paths'][0])
        self.assertIn('「汉服广袖流仙」', t)
        self.assertIn('发型按套系换成相应髻式', t)
        self.assertIn('AI 生成汉服写真，非实拍', t)
        self.assertNotIn('实际出图尺寸', t)
        gallery = open(s['gallery'], encoding='utf-8').read()
        self.assertIn('AI 生成汉服写真，非实拍', gallery)
        job = [c for c in self.mock.calls if c[1].endswith('/skill-jobs')][-1][2]
        self.assertEqual(job['size'], '1024x1536')
        for must in ('真实性基线', '恰好 1 位成年人物', '短发戴眼镜', '汉服广袖流仙', '不改脸', '不改变性别特征',
                     '文字基线', '安全基线', '不出现儿童或其他人', '不混套系'):
            self.assertIn(must, job['prompt'])
        self.assertTrue(job['prompt'].startswith('真实性基线'))
        for bad in ('25 岁', '东亚', '女性', '军衔', 'aisplice', 'gpt-image'):
            self.assertNotIn(bad, job['prompt'])
        self.assertEqual(set(job), {'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent'})
        self.assertEqual(s['remaining_uses'], 2)
        self.assertIn('剩余 2 次', t)
        self.assertIn(W.ORIGINAL_KEPT, t)
        self.assertIn('想调整直接说', t)
        self.assertIn('可能再次按张计费', t)
        self.assertTrue(os.path.isfile(s['gallery']))
        self.assertEqual(open(self.photo, 'rb').read(), self.photo_bytes)
        self.assertEqual(self.mock.charges, 1)
        self.assertIn('开始制作', err)
        # 首次对话已关联到账户，只传三字段
        self.assertTrue(self.mock.link_calls)
        self.assertEqual(set(self.mock.link_calls[0][0]), {'event_id', 'receipt', 'product'})
        # 第二次交付不再附完整调整引导
        did2 = self.confirmed_draft()
        code, s, t, _ = self.run_cmd('run', '--draft', did2)
        self.assertEqual(s['signal'], 'delivered')
        self.assertNotIn('想调整直接说', t)
        self.assertFalse(s['ask_favorite'])
        # 输出不覆盖
        self.assertEqual(len(set(s['paths'])), 1)

    def test_existing_account_skips_auth_and_topup(self):
        did = self.confirmed_draft()
        self.paid_account(did, 5)
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        paths = [c[1] for c in self.mock.calls]
        self.assertNotIn('/membership-link', paths)

    def test_mid_task_insufficient_asks_first(self):
        did = self.confirmed_draft()
        self.paid_account(did, 1)
        self.assertEqual(self.run_cmd('run', '--draft', did)[1]['signal'], 'delivered')
        did2 = self.confirmed_draft()
        code, s, t, _ = self.run_cmd('run', '--draft', did2)
        self.assertEqual((code, s['signal'], s['link_included']), (2, 'needsCredits', False))
        self.assertNotIn('http', t)
        self.assertIn('要我打开充值页吗', t)
        self.assertEqual(self.mock.membership_links, 0)
        code, s, t, _ = self.run_cmd('topup')
        self.assertIn('页面打开不等于已经下单', t)
        self.assertEqual(self.mock.membership_links, 1)
        code, s, t, _ = self.run_cmd('resume', '--draft', did2)
        self.assertEqual(s['signal'], 'creditsPending')  # 自述不当到账
        self.mock.users[self.secret()]['balance'] = 2
        code, s, t, _ = self.run_cmd('resume', '--draft', did2)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(self.mock.charges, 2)

    def test_policy_reject_not_charged(self):
        did = self.confirmed_draft()
        self.paid_account(did, 2)
        self.mock.scenario['policy'] = True
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (3, 'jobRejected'))
        self.assertIn('没有扣次数', t)
        self.assertEqual(self.mock.charges, 0)

    def test_rate_limited_keeps_task_same_key(self):
        did = self.confirmed_draft()
        self.paid_account(did, 2)
        self.mock.scenario['rate_limit'] = True
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'serviceBusy')
        self.assertIn('服务正在处理较多请求', t)
        keys1 = [c[3].get('Idempotency-Key') for c in self.mock.calls if c[1] == '/skill-jobs']
        self.mock.scenario.clear()
        self.run_cmd('resume', '--draft', did)
        keys = [c[3].get('Idempotency-Key') for c in self.mock.calls if c[1] == '/skill-jobs']
        self.assertEqual(len(set(keys)), 1)
        self.assertEqual(len(keys1), 1)

    def test_submit_lost_queries_original_not_resubmit(self):
        did = self.confirmed_draft()
        self.paid_account(did, 2)
        self.mock.scenario['submit_lost'] = True
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(len([c for c in self.mock.calls if c[1] == '/skill-jobs']), 1)
        self.assertTrue(any(c[1].startswith('/jobs/by-key/') for c in self.mock.calls))
        self.assertEqual(self.mock.charges, 1)

    def test_5xx_not_retried(self):
        did = self.confirmed_draft()
        self.paid_account(did, 2)
        self.mock.scenario['submit_5xx'] = True
        self.run_cmd('run', '--draft', did)
        self.assertEqual(len([c for c in self.mock.calls if c[1] == '/skill-jobs']), 1)

    def test_replay_same_key_charged_once(self):
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        self.run_cmd('run', '--draft', did)
        d = json.load(open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'drafts', did + '.json')))
        a = json.load(open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')))
        body, _ = studio._job_body(d)
        r = studio.call('POST', '/skill-jobs', body, auth=a['skill_key'], idem=d['idem'])
        self.assertTrue(r['replayed'])
        self.assertEqual(self.mock.charges, 1)

    def test_skill_key_expired_reset_exit4(self):
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        self.run_cmd('run', '--draft', did)  # 取得 Skill 凭证
        acc = os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE(os.stat(acc).st_mode), 0o600)  # Windows ACL cannot be inferred from POSIX bits
        self.mock.keys.clear()
        did2 = self.confirmed_draft()
        code, s, t, _ = self.run_cmd('run', '--draft', did2)
        self.assertEqual((code, s['signal'], s.get('task_kept')), (4, 'credentialsReset', True))
        self.assertNotIn('skill_key', json.load(open(acc)))
        self.assertEqual(json.load(open(acc))['install_secret'], self.secret())  # 原安装身份保留
        charges = self.mock.charges
        for u in self.mock.users.values():
            u['key'] = None
        # 1.0.1（A3-FAM-01/02）：首发生成请求已发出，结果未知；之后只按原键查询，查不到也不重发
        code, s, t, _ = self.run_cmd('run', '--draft', did2)
        self.assertEqual((code, s['signal'], s.get('progress')), (2, 'jobPending', 'unconfirmed'))
        self.assertEqual(self.mock.charges, charges)

    def test_client_rejects_unregistered_field(self):
        with self.assertRaises(ValueError):
            studio.call('POST', '/skill-jobs', dict(prompt='x', model='other'), auth='x', idem='wps-' + 'a' * 32)

    def test_server_rejects_unregistered_field(self):
        did = self.confirmed_draft()
        self.paid_account(did, 2)
        self.run_cmd('run', '--draft', did)
        a = json.load(open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')))
        with self.assertRaises(studio.GatewayError) as cm:
            self.mock.transport('POST', studio.ORIGIN + '/platform-api/gemini/skill-jobs', dict(prompt='x', confirmed=True, model='m'),
                                {'X-Skill-Source': studio.SKILL_ID, 'X-Skill-Channel': studio.CHANNEL, 'Authorization': 'Bearer ' + a['skill_key'],
                                 'Idempotency-Key': 'wps-' + 'b' * 32}, 5, False)
        self.assertEqual(cm.exception.status, 400)

    def test_balance_menu_and_decline(self):
        code, s, t, _ = self.run_cmd('balance')
        self.assertEqual((code, s['signal']), (2, 'linkAccount'))  # 1.0.2：无账户给关联链接，不回死胡同
        self.assertIn('](https://aistore.zhaopintong.com/membership/gemini/register/', t)
        did = self.confirmed_draft()
        self.paid_account(did, 7)
        code, s, t, _ = self.run_cmd('balance')
        self.assertEqual((s['signal'], s['remaining_uses']), ('balance', 7))
        code, s, t, _ = self.run_cmd('decline')
        self.assertEqual(t.strip(), W.DECLINE)

    def test_untrusted_link_rejected(self):
        with self.assertRaises(studio.GatewayError):
            studio.trusted_link('https://evil.example/membership/gemini/')
        self.assertTrue(studio.trusted_link('https://myplanestore.com/membership/gemini/#ticket=a').startswith('https://aistore.zhaopintong.com/membership/gemini/#ticket=a'))


class Waiting(Base):
    def go(self, **scenario):
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        self.mock.scenario.update(scenario)
        return did, self.run_cmd('run', '--draft', did)

    def test_once(self):
        _, (c, s, t, _) = self.go()
        self.assertEqual(s['signal'], 'delivered')

    def test_two_rounds(self):
        _, (c, s, t, _) = self.go(pending_rounds=2)
        self.assertEqual(s['signal'], 'delivered')

    def test_still_pending_after_window(self):
        did, (c, s, t, _) = self.go(pending_rounds=50)
        self.assertEqual((c, s['signal'], s['progress']), (2, 'jobPending', 'processing'))
        polls = [x for x in self.mock.calls if x[1].startswith('/jobs/') and not x[1].endswith('/image')]
        self.assertEqual(len(polls), studio.POLL_ATTEMPTS)
        self.mock.jobs[list(self.mock.jobs)[0]]['rounds'] = 1
        c, s, t, _ = self.run_cmd('resume', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(self.mock.charges, 1)

    def test_glitch_then_recover(self):
        _, (c, s, t, _) = self.go(pending_rounds=1, poll_glitch=1)
        self.assertEqual(s['signal'], 'delivered')

    def test_never_reachable(self):
        _, (c, s, t, _) = self.go(pending_rounds=3, poll_down=True)
        self.assertEqual(s['progress'], 'unconfirmed')
        self.assertIn('当前进度未能确认', t)
        self.assertIn('费用以服务记录为准', t)

    def test_explicit_failure(self):
        _, (c, s, t, _) = self.go(pending_rounds=1, fail=True)
        self.assertEqual(s['signal'], 'jobFailed')
        self.assertIn('服务正在处理较多请求', t)
        self.assertIn('费用以服务记录为准', t)

    def test_download_fail_keeps_task(self):
        did, (c, s, t, _) = self.go(image_fail=1)
        self.assertEqual((c, s['signal']), (2, 'downloadPending'))
        self.assertIn('请不要重复生成', t)
        c, s, t, _ = self.run_cmd('resume', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(self.mock.charges, 1)
        self.assertFalse(any('inline_delivery' in json.dumps(x[2] or {}) for x in self.mock.calls))

    def test_size_mismatch_reported(self):
        self.mock.output_size = (1024, 1024)
        _, (c, s, t, _) = self.go()
        self.assertIn('实际出图尺寸是 1024×1024，不是 1024×1536', t)


class Telemetry(Base):
    def test_fields_once_and_flag(self):
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.run_cmd('demo')
        self.assertEqual(len(self.mock.telemetry_calls), 1)
        body = self.mock.telemetry_calls[0][0]
        self.assertEqual(tuple(body), telemetry.FIELDS)
        self.assertNotIn('machine_id', body)
        self.assertEqual((body['skill_id'], body['channel'], body['is_test']), ('mps-hanfu-portrait-studio', 'workbuddy_skill', True))
        self.assertTrue(telemetry.is_uuid4(body['installation_id']) and telemetry.is_uuid4(body['event_id']))

    def test_off_switch(self):
        os.environ['MPS_HANFU_PORTRAIT_JOURNEY'] = 'off'
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(self.mock.telemetry_calls, [])

    def test_failure_does_not_block_and_no_retry_loop(self):
        for status in (204, 503, 400):
            self.mock.telemetry_status = status
            code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
            self.assertEqual(code, 0)
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'first-dialogue.json')) as f:
            st = json.load(f)
        self.assertFalse(st['sent'])  # 204 不算成功
        self.assertTrue(st['attempted'])
        self.assertEqual(len(self.mock.telemetry_calls), 1)  # A3-TRV-03：第一次失败后不再重发
        self.mock.telemetry_status = None
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(len(self.mock.telemetry_calls), 1)

    def test_transport_exception_swallowed(self):
        def boom(*a):
            raise OSError('down')
        telemetry.TRANSPORT = boom
        code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(code, 0)

    def test_corrupt_identity_repaired_and_readonly_skipped(self):
        d = os.path.join(self.home, 'mps-hanfu-portrait-studio')
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'first-dialogue.json'), 'w').write('garbage')
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(len(self.mock.telemetry_calls), 1)
        os.remove(os.path.join(d, 'first-dialogue.json'))
        if hasattr(os, 'geteuid') and os.geteuid() != 0:
            os.chmod(d, 0o500)
            try:
                code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
            except Exception:
                code = None
            os.chmod(d, 0o700)
            self.assertEqual(len(self.mock.telemetry_calls), 1)  # 写不进去就跳过，不临时造标识
        else:
            self.assertEqual(telemetry.report_once(os.path.join(self.tmp, 'no', 'such', 'dir')), 'skipped')

    def test_every_early_branch_reports(self):
        for argv in (['status'], ['balance'], ['first-turn', '--text', 'x'], ['history'], ['ticket'],
                     ['feedback', '--category', 'other', '--text', 'x']):
            shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)
            before = len(self.mock.telemetry_calls)
            self.run_cmd(*argv)
            self.assertEqual(len(self.mock.telemetry_calls), before + 1, argv)

    def test_link_409_not_overwritten(self):
        d = tempfile.mkdtemp(dir=self.tmp)
        telemetry.report_once(d)
        telemetry.TRANSPORT = lambda *a: (409, b'{}')
        self.assertEqual(telemetry.link_account(d, 'a' * 43), 'conflict')
        self.assertEqual(telemetry.link_account(d, 'a' * 43), 'already')

    def test_audit_not_reported(self):
        import audit_images
        audit_images.check(self.photo)
        self.assertEqual(self.mock.telemetry_calls, [])


class Support(Base):
    """T49–T51：消费记录、提交工单、查工单（模拟已部署的三个接口）。"""

    def delivered_account(self, balance=5):
        did = self.confirmed_draft()
        self.paid_account(did, balance)
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        return did

    def other_account(self):
        other = 'o' * 43
        self.mock.authorize(other, 1)
        return other

    def test_balance_shows_recent_records(self):
        self.delivered_account(5)
        code, s, t, _ = self.run_cmd('balance')
        self.assertEqual((code, s['signal'], s['remaining_uses'], s['history_total'], s['history_loaded']), (0, 'balance', 4, 1, True))
        self.assertTrue(t.startswith('剩余可用次数：4 次'))
        self.assertIn('通用生图任务', t)
        self.assertIn('扣 1 次 · 已完成', t)
        self.assertIn('共 1 条，回复「查看所有」可看全部', t)
        self.assertIn(W.HISTORY_SCOPE, t)
        q = [c for c in self.mock.calls if c[1].startswith('/consumption-history')][0]
        self.assertEqual(q[1], '/consumption-history?page=1&page_size=3')
        self.assertEqual(q[3]['Authorization'][7:], self.secret())  # 账户凭证，不用 Skill 凭证

    def test_history_paging_and_states(self):
        self.delivered_account(10)
        did = self.confirmed_draft()
        self.mock.scenario['pending_rounds'] = 99
        self.run_cmd('run', '--draft', did)
        self.mock.scenario.clear()
        jids = list(self.mock.jobs)
        self.mock.ledger_unknown.add(jids[0])
        code, s, t, _ = self.run_cmd('history')
        self.assertEqual((s['signal'], s['total'], s['has_more']), ('history', 2, False))
        self.assertIn('预留 1 次，完成后结算 · 处理中', t)
        self.assertIn('扣次以服务记录为准', t)
        studio.HISTORY_PAGE_SIZE = 1
        try:
            code, s, t, _ = self.run_cmd('history', '--page', '1')
            self.assertEqual((s['has_more'], s['next_page']), (True, 2))
            self.assertIn('回复「下一页」', t)
        finally:
            studio.HISTORY_PAGE_SIZE = 20

    def test_history_failure_and_no_account(self):
        code, s, t, _ = self.run_cmd('history')
        self.assertEqual((code, s['signal']), (2, 'linkAccount'))
        self.assertIn('关联本身不扣费', t)
        self.delivered_account(3)
        self.mock.scenario['support_busy'] = True
        code, s, t, _ = self.run_cmd('balance')
        self.assertEqual((s['signal'], s['history_loaded']), ('balance', False))
        self.assertIn('剩余可用次数：2 次', t)
        self.assertIn('消费记录这次没取到', t)
        code, s, t, _ = self.run_cmd('history')
        self.assertEqual((code, s['signal']), (2, 'serviceUnavailable'))

    def test_skill_key_not_accepted_and_accounts_isolated(self):
        self.delivered_account(3)
        a = studio.load_account()
        with self.assertRaises(studio.GatewayError) as cm:
            self.mock.transport('GET', studio.ORIGIN + '/platform-api/gemini/consumption-history', None,
                                {'X-Skill-Source': studio.SKILL_ID, 'X-Skill-Channel': studio.CHANNEL,
                                 'Authorization': 'Bearer ' + a['skill_key']}, 5, False)
        self.assertEqual(cm.exception.status, 401)
        other = self.other_account()
        st, raw = self.mock.transport('GET', studio.ORIGIN + '/platform-api/gemini/consumption-history', None,
                                      {'X-Skill-Source': studio.SKILL_ID, 'X-Skill-Channel': studio.CHANNEL,
                                       'Authorization': 'Bearer ' + other}, 5, False)
        self.assertEqual(json.loads(raw)['total'], 0)

    def test_feedback_creates_ticket_without_charge(self):
        did = self.delivered_account(5)
        charges = self.mock.charges
        code, s, t, _ = self.run_cmd('feedback', '--category', 'image_quality', '--text', '发丝边缘有一点白边', '--draft', did)
        self.assertEqual((code, s['signal'], s['pending']), (0, 'ticketCreated', 0))
        tid = s['ticket_ids'][0]
        self.assertRegex(tid, r'^mpsg-[0-9a-f]{32}$')
        self.assertIn('反馈编号：' + tid, t)
        self.assertIn('目前没有承诺具体处理时限', t)
        self.assertIn('提交反馈不扣次数', t)
        self.assertEqual(self.mock.charges, charges)
        self.assertEqual(self.mock.users[self.secret()]['balance'], 4)
        tk = self.mock.tickets[tid]
        self.assertEqual((tk['text'], tk['category'], tk['job_id']), ('发丝边缘有一点白边', 'image_quality', self.mock.jobs and list(self.mock.jobs)[0]))
        call = [c for c in self.mock.calls if c[1] == '/support-tickets'][0]
        self.assertEqual(set(call[2]), {'category', 'text', 'job_id'})
        self.assertRegex(call[3]['Idempotency-Key'], r'^fb-[0-9a-f]{32}$')

    def test_feedback_lost_response_same_key_single_ticket(self):
        self.delivered_account(2)
        self.mock.scenario['ticket_lost_once'] = True
        code, s, t, _ = self.run_cmd('feedback', '--category', 'billing', '--text', '扣次和我想的不一样')
        self.assertEqual((code, s['signal'], s['pending']), (2, 'feedbackSaved', 1))
        self.assertIn('原话已经在本机记下', t)
        code, s, t, _ = self.run_cmd('feedback', '--retry')
        self.assertEqual(s['signal'], 'ticketCreated')
        self.assertEqual(len(self.mock.tickets), 1)  # 同一请求编号重放，不重复建单
        keys = {c[3]['Idempotency-Key'] for c in self.mock.calls if c[1] == '/support-tickets'}
        self.assertEqual(len(keys), 1)
        code, s, t, _ = self.run_cmd('feedback', '--retry')
        self.assertEqual(s['signal'], 'feedbackNone')

    def test_feedback_busy_and_no_account_saved(self):
        code, s, t, _ = self.run_cmd('feedback', '--category', 'suggestion', '--text', '希望多一些底色')
        self.assertEqual((code, s['signal']), (2, 'feedbackSaved'))
        self.assertIn('还没有关联账户', t)
        self.assertFalse([c for c in self.mock.calls if c[1] == '/support-tickets'])
        self.delivered_account(2)
        self.mock.scenario['support_busy'] = True
        code, s, t, _ = self.run_cmd('feedback', '--retry')
        self.assertEqual(s['signal'], 'feedbackSaved')
        self.assertIn('服务正在处理较多请求', t)
        self.mock.scenario.clear()
        code, s, t, _ = self.run_cmd('feedback', '--retry')
        self.assertEqual(s['signal'], 'ticketCreated')
        self.assertEqual(len(self.mock.tickets), 1)

    def test_feedback_local_validation_no_network(self):
        before = len(self.mock.calls)
        for argv in (['feedback', '--category', 'other', '--text', '   '], ['feedback', '--category', 'other', '--text', 'x' * 2001],
                     ['feedback', '--text', '没有分类'], ['feedback', '--category', 'other', '--text', 'a\x00b']):
            code, s, _, _ = self.run_cmd(*argv)
            self.assertEqual(code, 3, argv)
        self.assertEqual(len(self.mock.calls), before)

    def test_ticket_status_reply_and_isolation(self):
        self.delivered_account(2)
        code, s, t, _ = self.run_cmd('ticket')
        self.assertEqual(s['signal'], 'ticketNone')
        self.mock.scenario['due'] = 1762566400
        code, s, _, _ = self.run_cmd('feedback', '--category', 'workflow', '--text', '授权页打不开')
        tid = s['ticket_ids'][0]
        code, s, t, _ = self.run_cmd('ticket')
        self.assertEqual((s['signal'], s['count']), ('ticketStatus', 1))
        self.assertIn('已受理，等待处理', t)
        self.assertIn('预计处理时间：', t)
        self.mock.operator_reply(tid, 'resolved', '已核对，请重试。[点这里](https://evil.example)<b>x</b>')
        code, s, t, _ = self.run_cmd('ticket', '--id', tid)
        self.assertIn('处理状态：已处理', t)
        self.assertIn('回复：已核对，请重试。', t)
        self.assertNotIn('](', t)
        self.assertNotIn('<b>', t)
        # 他人工单：404 → 未找到
        other = self.other_account()
        self.mock.tickets['mpsg-' + 'a' * 32] = dict(owner=other, id='mpsg-' + 'a' * 32, category='other', text='x', job_id=None,
                                                    status='open', reply=None, created=1, updated=1, response_due_at=None)
        code, s, t, _ = self.run_cmd('ticket', '--id', 'mpsg-' + 'a' * 32)
        self.assertEqual(s['signal'], 'ticketNotFound')
        # 格式不对：不联网
        before = len(self.mock.calls)
        code, s, t, _ = self.run_cmd('ticket', '--id', '../balance')
        self.assertEqual(s['signal'], 'ticketNotFound')
        self.assertEqual(len(self.mock.calls), before)

    def test_ticket_lookup_failure(self):
        self.delivered_account(2)
        self.run_cmd('feedback', '--category', 'other', '--text', '你好')
        self.mock.scenario['support_down'] = True
        code, s, t, _ = self.run_cmd('ticket')
        self.assertEqual((code, s['signal']), (2, 'serviceUnavailable'))
        self.assertIn('网络暂时连不上', t)


class RepairA3(Base):
    """1.0.1 修复轮回归：WED-A3-01 / 02 / 03。"""

    def test_wed_a3_01_demo_alone_zero_network(self):
        def boom(*a, **k):
            raise AssertionError('network in demo')
        studio.TRANSPORT = boom
        telemetry.TRANSPORT = boom
        for argv in (['demo'], ['demo', 'garden']):
            code, s, _, _ = self.run_cmd(*argv)
            self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'first-dialogue.json')))
        # 首次真实对话仍上报一次
        telemetry.TRANSPORT = self.mock.telemetry_transport
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.run_cmd('demo')
        self.assertEqual(len(self.mock.telemetry_calls), 1)

    def test_wed_a3_02_photo_replaced_after_confirm(self):
        did = self.confirmed_draft()
        draft_file = os.path.join(self.home, 'mps-hanfu-portrait-studio', 'drafts', did + '.json')
        old_idem = json.load(open(draft_file))['idem']
        with open(self.photo, 'wb') as f:
            f.write(jpeg_bytes(640, 800))  # 同一路径换成另一张合成图
        self.mock.authorize(studio.ensure_install_secret(studio.load_account()), 5)
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (2, 'photoChanged'))
        self.assertIn(W.REASSURE_FREE.rstrip('。').split('，')[1], t)
        self.assertEqual(self.mock.charges, 0)
        self.assertFalse([c for c in self.mock.calls if '/skill-jobs' in c[1]])
        d = json.load(open(draft_file))
        self.assertEqual((d['idem'], d['owner_consent'], d['upload_consent'], d['pay_consent']), (None, False, False, False))
        # 旧确认不能再用
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'needsConfirmation')
        code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--owner-consent', 'yes', '--pay-consent', 'yes')
        self.assertEqual(s['signal'], 'needsPlan')
        # 重新 plan + confirm 后：新键对应新照片
        self.run_cmd('plan', '--draft', did, '--scene', 'daily')
        self.run_cmd('confirm', '--draft', did, '--owner-consent', 'yes', '--pay-consent', 'yes')
        new_idem = json.load(open(draft_file))['idem']
        self.assertNotEqual(new_idem, old_idem)
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(self.mock.charges, 1)

    def test_wed_a3_02_photo_replaced_between_plan_and_confirm(self):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        did = s['draft_id']
        self.run_cmd('plan', '--draft', did, '--scene', 'daily')
        with open(self.photo, 'wb') as f:
            f.write(jpeg_bytes(640, 800))
        code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--owner-consent', 'yes', '--pay-consent', 'yes')
        self.assertEqual((code, s['signal']), (2, 'photoChanged'))

    def test_wed_a3_03_delivery_links_space_and_hash(self):
        import re
        from urllib.parse import unquote
        try:
            from markdown_it import MarkdownIt
            md = MarkdownIt()
        except ImportError:
            md = None
        for name in ('my photos', 'Synthetic#Album', 'Travel%Demo'):
            folder = os.path.join(self.tmp, name)
            os.makedirs(folder)
            self.photo = os.path.join(folder, 'me.jpg')
            with open(self.photo, 'wb') as f:
                f.write(jpeg_bytes())
            did = self.confirmed_draft()
            self.mock.authorize(studio.ensure_install_secret(studio.load_account()), 5)
            code, s, t, _ = self.run_cmd('run', '--draft', did)
            self.assertEqual(s['signal'], 'delivered', t)
            self.assertTrue(os.path.isfile(s['paths'][0]))
            targets = [s['links'][0], s['gallery_link']]
            for target, real in zip(targets, (s['paths'][0], s['gallery'])):
                self.assertNotIn(' ', target)
                self.assertNotIn('#', target)
                self.assertIn('](' + target + ')', t)
                line = next(l for l in t.splitlines() if '](' + target + ')' in l)
                got = re.search(r'\]\(([^()\s]*)\)', line).group(1)
                path, _, frag = got.partition('#')
                path, _, query = path.partition('?')
                self.assertEqual((frag, query), ('', ''))
                self.assertEqual(os.path.abspath(unquote(path)).replace('\\', '/'), os.path.abspath(real).replace('\\', '/'))
                self.assertTrue(os.path.isfile(unquote(path)))
                if md is not None:
                    href = re.search(r'href="([^"]*)"', md.render(line)).group(1)
                    self.assertTrue(os.path.isfile(unquote(href)))


class PayConversion(Base):
    """1.0.2 SOP 第七章：全新环境账户命令有出路；失败原因按网络/繁忙如实区分。"""

    def offline(self, *a, **k):
        raise studio.GatewayError(0)

    def assert_link(self, t, path):
        import re
        m = re.search(r'\]\((https://[^)\s]+)\)', t)
        self.assertIsNotNone(m, t)
        self.assertTrue(m.group(1).startswith('https://aistore.zhaopintong.com' + path), m.group(1))

    def test_fresh_topup_gives_link_account(self):
        self.assertFalse(os.path.exists(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')))
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual((code, s['signal'], s['link_included']), (2, 'linkAccount', True))
        self.assert_link(t, '/membership/gemini/register/')
        self.assertIn('扫码确认后会直接进入充值页', t)
        self.assertIn('关联本身不扣费', t)
        self.assertNotIn('免费', t)
        self.assertEqual(len(self.secret()), 43)  # 安装标识已生成并持久化
        qe = [c for c in self.mock.calls if c[1] == '/quick-entry']
        self.assertEqual(len(qe), 1)
        self.assertNotIn('Authorization', qe[0][3])  # 一次性关联入口无 Bearer
        self.assertEqual(qe[0][2], {'install_secret': self.secret()})
        self.assertEqual(self.mock.charges, 0)

    def test_fresh_topup_offline_honest(self):
        studio.TRANSPORT = self.offline
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual((code, s['signal']), (3, 'serviceUnavailable'))
        self.assertEqual(t.strip(), '网络暂时没连上，没有扣任何次数，稍后再说一次「充值」。')
        self.assertNotIn('较多请求', t)

    def test_fresh_topup_server_busy(self):
        def busy(*a, **k):
            raise studio.GatewayError(503)
        studio.TRANSPORT = busy
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertIn('服务正在处理较多请求', t)
        self.assertNotIn('网络', t)

    def test_topup_secret_unregistered_401_falls_back(self):
        self.run_cmd('topup')  # 已有本机标识但用户还没扫码，/membership-link 401
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual((code, s['signal']), (2, 'linkAccount'))
        self.assert_link(t, '/membership/gemini/register/')

    def test_topup_registered_zero_balance_checkout(self):
        self.run_cmd('topup')
        self.mock.authorize(self.secret(), 0)
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual((code, s['signal']), (2, 'topupLink'))
        self.assert_link(t, '/membership/')

    def test_topup_ready_account_link(self):
        self.run_cmd('topup')
        self.mock.authorize(self.secret(), 3)
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual(s['signal'], 'topupLink')
        self.assertEqual(self.mock.membership_links, 1)

    def test_topup_membership_link_network_not_busy(self):
        self.run_cmd('topup')
        self.mock.authorize(self.secret(), 3)
        studio.TRANSPORT = self.offline
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertIn('网络暂时没连上', t)
        self.assertNotIn('较多请求', t)

    def test_topup_untrusted_link_not_relayed(self):
        real = self.mock.transport

        def evil(method, url, body, headers, timeout, binary):
            if url.endswith('/quick-entry'):
                return 200, json.dumps(dict(status='registration', url='https://evil.example/membership/gemini/register/')).encode()
            return real(method, url, body, headers, timeout, binary)
        studio.TRANSPORT = evil
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertNotIn('evil', t)
        self.assertNotIn('http', t)

    def test_fresh_status_and_balance_have_way_out(self):
        code, s, t, _ = self.run_cmd('status')
        self.assertEqual((code, s['signal']), (2, 'linkAccount'))
        self.assert_link(t, '/membership/gemini/register/')
        code, s, t, _ = self.run_cmd('balance')
        self.assertEqual(s['signal'], 'linkAccount')
        self.mock.authorize(self.secret(), 4)
        code, s, t, _ = self.run_cmd('balance')
        self.assertEqual((s['signal'], s['remaining_uses']), ('balance', 4))

    def test_fresh_status_offline(self):
        studio.TRANSPORT = self.offline
        code, s, t, _ = self.run_cmd('status')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertIn('网络暂时没连上，没有扣任何次数', t)
        code, s, t, _ = self.run_cmd('balance')
        self.assertIn('网络暂时没连上，没有扣任何次数', t)

    def test_fresh_history_gives_link(self):
        code, s, t, _ = self.run_cmd('history')
        self.assertEqual((code, s['signal']), (2, 'linkAccount'))
        self.assert_link(t, '/membership/gemini/register/')

    def test_run_needs_credits_link_failure_kind(self):
        did = self.confirmed_draft()
        self.paid_account(did, 0)
        studio.TRANSPORT = self.offline  # 取充值链接断网：返回状态 0，按网络没连上说明
        a = studio.load_account()
        url, status = studio._membership_link(a)
        self.assertEqual((url, status), (None, 0))
        self.assertEqual(studio._fail_kind(0), 'network')
        self.assertEqual(studio._fail_kind(503), 'busy')


class DemoAssets(unittest.TestCase):
    """T03/T53：包内示例图来自已授权生成的 10 张虚构成年人示例，派生哈希可追溯。"""

    def test_package_demos_trace_to_provenance(self):
        import hashlib
        src = os.path.join(HERE, '..', '..', 'demo-assets')
        prov = json.load(open(os.path.join(src, 'provenance.json'), encoding='utf-8'))
        self.assertEqual((prov['authorized_final_demos'], prov['delivered_demo_calls'], prov['succeeded'], len(prov['items'])), (10, 10, 10, 10))
        self.assertFalse(prov['rejected_reference_seed']['included_in_skill_package'])
        self.assertFalse(os.path.exists(os.path.join(PKG, 'assets', prov['rejected_reference_seed']['file'])))
        der = json.load(open(os.path.join(HERE, 'demos-derivation.json'), encoding='utf-8'))
        demos = json.load(open(os.path.join(PKG, 'assets', 'demos.json'), encoding='utf-8'))['demos']
        self.assertEqual(sorted(r['key'] for r in der['items']), sorted(d['key'] for d in demos))
        by_key = {i['key']: i for i in prov['items']}
        for r in der['items']:
            it = by_key[r['key']]
            self.assertTrue(it['fictional_adults'])
            self.assertFalse(r['byte_identical'])  # 1.0.2: authorized image-only compression
            self.assertEqual(r['source_sha256'], it['output_sha256'], r['key'])
            self.assertEqual((r['source_version'], r['package_version'], r['max_channel_error']), ('1.0.1', '1.0.2', 2))
            with open(os.path.join(src, r['source']), 'rb') as f:
                raw = f.read()
            expect = it['output_sha256'] if r['source'] == it['file'] else it['additional_export']['sha256']
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expect, r['key'])
            with open(os.path.join(PKG, 'assets', r['package_file']), 'rb') as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), r['package_sha256'], r['key'])
        for d in demos:
            w, h = png_local.size_of(open(os.path.join(PKG, 'assets', d['file']), 'rb').read())
            self.assertEqual(w > h, studio.SCENES[d['key']][2] == 'landscape', d['key'])


class ZipLayout(unittest.TestCase):
    """平台只支持两级目录：ZIP 内路径以包根为第 0 级，'/' 数不得超过 2。"""

    def zips(self):
        if ZIPS:
            return ZIPS
        dist = os.path.join(HERE, '..', 'dist')
        ver = studio.SKILL_VERSION
        p = os.path.join(dist, 'mps-hanfu-portrait-studio-%s.zip' % ver)
        return [p] if os.path.exists(p) else []

    def test_zip_dir_depth_at_most_two(self):
        import zipfile
        zs = self.zips()
        if not zs:
            self.skipTest('no ZIP for current version yet (pass --zip <file>)')
        for zp in zs:
            with zipfile.ZipFile(zp) as z:
                names = [n for n in z.namelist() if not n.endswith('/')]
            self.assertTrue(names, zp)
            self.assertEqual([n for n in names if n.count('/') > 2], [], zp)
            self.assertTrue(all(n.startswith('mps-hanfu-portrait-studio/') for n in names), zp)
            self.assertFalse([n for n in names if '/assets/demos/' in n], zp)
            self.assertEqual(len([n for n in names if n.startswith('mps-hanfu-portrait-studio/assets/') and n.endswith('.png')]), 10, zp)

    def test_zip_skill_examples_platform_limits(self):
        """ZIP 内 SKILL.md：examples_zh/examples_en 各 ≤3 且数量一致，version 与脚本一致。"""
        import re, zipfile
        zs = self.zips()
        if not zs:
            self.skipTest('no ZIP for current version yet (pass --zip <file>)')
        for zp in zs:
            with zipfile.ZipFile(zp) as z:
                front = z.read('mps-hanfu-portrait-studio/SKILL.md').decode('utf-8').split('---', 2)[1]
            def items(key):
                m = re.search(r'^' + key + r':\s*\n((?:\s+-\s+.*\n)+)', front, re.M)
                return re.findall(r'^\s+-\s+(.*)$', m.group(1), re.M) if m else []
            zh, en = items('examples_zh'), items('examples_en')
            self.assertTrue(1 <= len(zh) <= 3, (zp, len(zh)))
            self.assertTrue(len(en) <= 3, (zp, len(en)))
            self.assertEqual(len(zh), len(en), zp)
            self.assertIn('version: %s' % studio.SKILL_VERSION, front, zp)
            sys.path.insert(0, os.path.join(PKG, 'tests'))
            import test_skill_contract as C
            strip = lambda xs: [x.strip().strip('"') for x in xs]
            self.assertEqual(C.example_misaligned(strip(zh), strip(en)), [], zp)


class RepairPay103(Base):
    """1.0.3 A3-PAY-01/02 回归：全新环境 paid 走关联入口、到账只看服务端；失效短链不转述。"""
    offline = PayConversion.offline
    assert_link = PayConversion.assert_link

    def quick_entry_calls(self):
        return [c for c in self.mock.calls if c[1] == '/quick-entry']

    # ---- A3-PAY-01 ----
    def test_pay_01_fresh_paid_gives_link_account(self):
        self.assertFalse(os.path.exists(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')))
        code, s, t, _ = self.run_cmd('paid')
        self.assertEqual((code, s['signal'], s['link_included']), (2, 'linkAccount', True))
        self.assert_link(t, '/membership/gemini/register/')
        self.assertNotIn('已收到你的付款登记', t)
        self.assertNotIn('免费', t)
        self.assertEqual(len(self.secret()), 43)  # 安装标识已生成并持久化
        qe = self.quick_entry_calls()
        self.assertEqual(len(qe), 1)
        self.assertNotIn('Authorization', qe[0][3])
        self.assertEqual(qe[0][2], {'install_secret': self.secret()})
        self.assertEqual(self.mock.charges, 0)

    def test_pay_01_fresh_paid_offline_honest(self):
        studio.TRANSPORT = self.offline
        code, s, t, _ = self.run_cmd('paid')
        self.assertEqual((code, s['signal']), (3, 'serviceUnavailable'))
        self.assertEqual(t.strip(), '网络暂时没连上，没有扣任何次数，稍后再说一次「付好了」。')
        self.assertNotIn('付款登记', t)

    def test_pay_01_fresh_paid_busy(self):
        def busy(*a, **k):
            raise studio.GatewayError(503)
        studio.TRANSPORT = busy
        code, s, t, _ = self.run_cmd('paid')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertIn('服务正在处理较多请求', t)
        self.assertNotIn('网络', t)

    def test_pay_01_paid_secret_unregistered_401_falls_back(self):
        self.run_cmd('paid')  # 已有本机标识但还没扫码，/balance 401
        code, s, t, _ = self.run_cmd('paid')
        self.assertEqual((code, s['signal']), (2, 'linkAccount'))
        self.assert_link(t, '/membership/gemini/register/')

    def test_pay_01_paid_registered_zero_balance_not_credited(self):
        self.run_cmd('paid')
        self.mock.authorize(self.secret(), 0)
        code, s, t, _ = self.run_cmd('paid')
        self.assertEqual((code, s['signal'], s['remaining_uses']), (2, 'creditsPending', 0))
        self.assertIn('还没看到这笔到账', t)
        self.assertNotIn('付款登记', t)

    def test_pay_01_paid_registered_with_balance_confirmed(self):
        self.run_cmd('paid')
        self.mock.authorize(self.secret(), 4)
        code, s, t, _ = self.run_cmd('paid')
        self.assertEqual((code, s['signal'], s['remaining_uses']), (0, 'creditsConfirmed', 4))
        self.assertEqual(self.mock.charges, 0)

    def test_pay_01_paid_existing_account_offline(self):
        self.run_cmd('paid')
        self.mock.authorize(self.secret(), 4)
        studio.TRANSPORT = self.offline
        code, s, t, _ = self.run_cmd('paid')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertIn('网络暂时没连上', t)
        self.assertNotIn('付款登记', t)

    # ---- A3-PAY-02 ----
    def quick_entry_with(self, *expires):
        """按顺序给 /quick-entry 的注册链接附 expires_in；用完后沿用最后一个。"""
        real = self.mock.transport
        seq = list(expires)

        def tr(method, url, body, headers, timeout, binary):
            if url.endswith('/quick-entry'):
                code, raw = real(method, url, body, headers, timeout, binary)
                d = json.loads(raw)
                d['expires_in'] = seq.pop(0) if len(seq) > 1 else seq[0]
                return code, json.dumps(d).encode()
            return real(method, url, body, headers, timeout, binary)
        studio.TRANSPORT = tr

    def test_pay_02_expired_link_not_relayed(self):
        self.quick_entry_with(0)
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual((code, s['signal']), (3, 'serviceUnavailable'))
        self.assertNotIn('http', t)
        self.assertIn('已经过期', t)
        self.assertIn('没有扣任何次数', t)
        self.assertNotIn('网络', t)
        qe = self.quick_entry_calls()
        self.assertEqual(len(qe), 2)  # 沿原安装身份重取一次
        self.assertEqual(qe[0][2], qe[1][2])
        self.assertEqual(qe[1][2], {'install_secret': self.secret()})

    def test_pay_02_expired_then_fresh_refetched(self):
        self.quick_entry_with(0, 300)
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual((code, s['signal']), (2, 'linkAccount'))
        self.assert_link(t, '/membership/gemini/register/')
        self.assertEqual(len(self.quick_entry_calls()), 2)

    def test_pay_02_valid_link_relayed(self):
        self.quick_entry_with(300)
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual((code, s['signal']), (2, 'linkAccount'))
        self.assert_link(t, '/membership/gemini/register/')
        self.assertEqual(len(self.quick_entry_calls()), 1)

    def test_pay_02_bad_expiry_metadata_not_relayed(self):
        for bad in (-5, '300', None):
            self.quick_entry_with(bad)
            code, s, t, _ = self.run_cmd('topup')
            self.assertEqual(s['signal'], 'serviceUnavailable', bad)
            self.assertNotIn('http', t, bad)

    def test_pay_02_expired_link_other_commands(self):
        for cmd, word in (('status', '我的账户'), ('balance', '查余额'), ('history', '消费记录'), ('paid', '付好了')):
            self.quick_entry_with(0)
            code, s, t, _ = self.run_cmd(cmd)
            self.assertEqual(s['signal'], 'serviceUnavailable', cmd)
            self.assertNotIn('http', t, cmd)
            self.assertIn('已经过期', t, cmd)
        self.quick_entry_with(0)
        code, s, t, _ = self.run_cmd('auth')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertNotIn('http', t)

    def test_pay_02_external_domain_still_rejected(self):
        real = self.mock.transport

        def evil(method, url, body, headers, timeout, binary):
            if url.endswith('/quick-entry'):
                return 200, json.dumps(dict(status='registration', url='https://evil.example/membership/gemini/register/#entry=x', expires_in=300)).encode()
            return real(method, url, body, headers, timeout, binary)
        studio.TRANSPORT = evil
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertNotIn('evil', t)
        self.assertNotIn('http', t)

    def test_pay_02_checkout_expired_link(self):
        self.run_cmd('topup')
        self.mock.authorize(self.secret(), 0)
        self.quick_entry_with(0)
        code, s, t, _ = self.run_cmd('auth')  # checkout 分支：失效充值链接不转述
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertNotIn('http', t)
        self.assertIn('已经过期', t)
        self.quick_entry_with(300)
        code, s, t, _ = self.run_cmd('auth')
        self.assertEqual((s['signal'], s['link_included']), ('needsCredits', True))

    def test_pay_02_membership_link_expired(self):
        self.run_cmd('topup')
        self.mock.authorize(self.secret(), 3)
        real = self.mock.transport
        n = []

        def tr(method, url, body, headers, timeout, binary):
            code, raw = real(method, url, body, headers, timeout, binary)
            if url.endswith('/membership-link'):
                n.append(1)
                d = json.loads(raw)
                d['expires_in'] = 0
                raw = json.dumps(d).encode()
            return code, raw
        studio.TRANSPORT = tr
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual(s['signal'], 'serviceUnavailable')
        self.assertNotIn('http', t)
        self.assertIn('已经过期', t)
        self.assertEqual(len(n), 2)

    def test_pay_02_membership_link_valid_expiry(self):
        self.run_cmd('topup')
        self.mock.authorize(self.secret(), 3)
        real = self.mock.transport

        def tr(method, url, body, headers, timeout, binary):
            code, raw = real(method, url, body, headers, timeout, binary)
            if url.endswith('/membership-link'):
                d = json.loads(raw)
                d['expires_in'] = 300
                raw = json.dumps(d).encode()
            return code, raw
        studio.TRANSPORT = tr
        code, s, t, _ = self.run_cmd('topup')
        self.assertEqual(s['signal'], 'topupLink')
        self.assert_link(t, '/membership/')


class OriginalTaskSpec(Base):
    """规格 T02/T04/T13/T14 原任务专项（沿用全家福 1.0.1 回归）：提交前持久化未知状态、只查原任务、401 恢复、坏图只读补取、短链必须带有效期。"""

    def wrap(self, hook):
        real = self.mock.transport
        self.posts = []

        def t(method, url, body, headers, timeout, binary):
            if method == 'POST' and url.endswith('/skill-jobs'):
                self.posts.append((json.dumps(body, sort_keys=True), headers.get('Idempotency-Key')))
            return hook(real, method, url, body, headers, timeout, binary)
        studio.TRANSPORT = t

    def draft(self, did):
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'drafts', did + '.json')) as f:
            return json.load(f)

    def ready(self, balance=3):
        did = self.confirmed_draft()
        self.paid_account(did, balance)
        return did

    def test_submit_unknown_persisted_before_post_and_locked(self):
        did = self.ready()
        seen = {}

        def hook(real, method, url, body, headers, timeout, binary):
            if method == 'POST' and url.endswith('/skill-jobs'):
                d = self.draft(did)
                seen.update(state=d['state'], body=d.get('body_sha256'))
                real(method, url, body, headers, timeout, binary)
                raise RuntimeError('process killed after server accepted')
            return real(method, url, body, headers, timeout, binary)
        self.wrap(hook)
        with self.assertRaises(RuntimeError):
            self.run_cmd('run', '--draft', did)
        self.assertEqual(seen['state'], 'submit_unknown')
        self.assertRegex(seen['body'], r'^[0-9a-f]{64}$')
        self.assertEqual(self.draft(did)['state'], 'submit_unknown')
        # 结果未知期间：改方案、确认、重新生成一律锁定
        self.assertEqual(self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun')[1]['signal'], 'taskLocked')
        self.assertEqual(self.run_cmd('confirm', '--draft', did, '--owner-consent', 'yes', '--pay-consent', 'yes')[1]['signal'], 'needsPlan')
        self.assertEqual(self.run_cmd('regenerate', '--draft', did, '--pay-consent', 'yes')[1]['signal'], 'taskLocked')
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.mock.charges, 1)

    def test_409_and_5xx_query_original_only(self):
        for status in (409, 502, 0):
            shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)
            self.mock = mock_backend.Mock()
            studio.TRANSPORT = self.mock.transport
            telemetry.TRANSPORT = self.mock.telemetry_transport
            did = self.ready()

            def hook(real, method, url, body, headers, timeout, binary, status=status):
                if method == 'POST' and url.endswith('/skill-jobs'):
                    real(method, url, body, headers, timeout, binary)
                    raise studio.GatewayError(status)
                return real(method, url, body, headers, timeout, binary)
            self.wrap(hook)
            code, s, t, _ = self.run_cmd('run', '--draft', did)
            self.assertEqual(s['signal'], 'delivered', status)
            self.assertEqual((len(self.posts), self.mock.charges), (1, 1), status)

    def test_by_key_404_never_resubmits(self):
        did = self.ready()

        def hook(real, method, url, body, headers, timeout, binary):
            if method == 'POST' and url.endswith('/skill-jobs'):
                raise studio.GatewayError(0)  # 超时：服务端到底有没有受理不得而知
            return real(method, url, body, headers, timeout, binary)
        self.wrap(hook)
        for _ in range(3):
            code, s, t, _ = self.run_cmd('run', '--draft', did)
            self.assertEqual((code, s['signal'], s['progress']), (2, 'jobPending', 'unconfirmed'))
            self.assertIn('当前进度未能确认', t)
        code, s, t, _ = self.run_cmd('resume', '--draft', did)
        self.assertEqual(s['signal'], 'jobPending')
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.mock.charges, 0)

    # ---- A3-FAM-01/02（1.0.1）：首发提交 401 后只查原任务，凭证状态与任务状态分开 ----

    def _keyed_draft(self):
        """先交付一张取得技能凭证，再给第二张确认好的草稿；首发 POST 用的是已有凭证。"""
        did = self.ready()
        self.run_cmd('run', '--draft', did)
        return self.confirmed_draft()

    def _assert_kept(self, did, idem, digest):
        d = self.draft(did)  # 每次从磁盘重新加载私有状态（等同重启）
        self.assertEqual((d['state'], d['idem'], d['body_sha256']), ('submit_unknown', idem, digest))
        self.assertTrue(d['owner_consent'] and d['upload_consent'] and d['pay_consent'])
        self.assertEqual(self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun')[1]['signal'], 'taskLocked')
        self.assertEqual(self.run_cmd('confirm', '--draft', did, '--owner-consent', 'yes', '--pay-consent', 'yes')[1]['signal'], 'needsPlan')
        self.assertEqual(self.run_cmd('regenerate', '--draft', did, '--pay-consent', 'yes')[1]['signal'], 'taskLocked')
        d = self.draft(did)
        self.assertEqual((d['state'], d['idem'], d['body_sha256']), ('submit_unknown', idem, digest))

    def _first_post_401(self, query_fault=None, recover_fault=None, server_accepts=False):
        """首发 POST→401；可选：凭证恢复失败（recover_fault）、恢复后按原键查询失败（query_fault）。"""
        did = self._keyed_draft()
        base_posts = self.mock.charges
        st = {'post': 0}

        def hook(real, method, url, body, headers, timeout, binary):
            if method == 'POST' and url.endswith('/skill-jobs'):
                st['post'] += 1
                if server_accepts:
                    real(method, url, body, headers, timeout, binary)
                raise studio.GatewayError(401)
            if recover_fault is not None and method == 'POST' and url.endswith('/skill-key'):
                raise studio.GatewayError(recover_fault)
            if method == 'GET' and '/jobs/by-key/' in url and query_fault is not None:
                if query_fault == 'bad_id':
                    return 200, json.dumps({'id': 'not-a-uuid', 'status': 'pending'}).encode()
                raise studio.GatewayError(query_fault)
            return real(method, url, body, headers, timeout, binary)
        self.wrap(hook)
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        return did, code, s, t, st, base_posts

    def test_fam01_first_post_401_then_404_never_resubmits(self):
        did, code, s, t, st, base = self._first_post_401()  # 恢复成功；Mock 未建单，原键 GET→404
        self.assertEqual((code, s['signal'], s.get('progress')), (2, 'jobPending', 'unconfirmed'))
        self.assertIn('当前进度未能确认', t)
        self.assertEqual((len(self.posts), st['post']), (1, 1))
        self.assertTrue(any(c[1].startswith('/jobs/by-key/') for c in self.mock.calls))
        d = self.draft(did)
        idem, digest = d['idem'], d['body_sha256']
        self.assertEqual(self.posts[0][1], idem)
        self._assert_kept(did, idem, digest)
        for cmd in ('run', 'resume', 'run'):  # 之后继续只查原键
            code, s, _, _ = self.run_cmd(cmd, '--draft', did)
            self.assertEqual((code, s['signal']), (2, 'jobPending'))
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.mock.charges, base)
        self._assert_kept(did, idem, digest)

    def test_fam01_first_post_401_query_faults_never_resubmit(self):
        for fault, want in ((500, (2, 'jobPending')), (502, (2, 'jobPending')), (0, (2, 'jobPending')),
                            ('bad_id', (2, 'jobPending')), (401, (4, 'credentialsReset'))):
            shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)
            self.mock = mock_backend.Mock()
            studio.TRANSPORT = self.mock.transport
            telemetry.TRANSPORT = self.mock.telemetry_transport
            did, code, s, t, st, base = self._first_post_401(query_fault=fault)
            self.assertEqual((code, s['signal']), want, fault)
            if code == 4:
                self.assertTrue(s.get('task_kept'), fault)
            self.assertEqual((len(self.posts), st['post']), (1, 1), fault)
            d = self.draft(did)
            self._assert_kept(did, d['idem'], d['body_sha256'])
            self.assertEqual(len(self.posts), 1, fault)

    def test_fam01_first_post_401_but_accepted_continues_original(self):
        did, code, s, t, st, base = self._first_post_401(server_accepts=True)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.mock.charges, base + 1)

    def test_fam02_recovery_fails_keeps_task_locked(self):
        for fault in (0, 401, 502):
            shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)
            self.mock = mock_backend.Mock()
            studio.TRANSPORT = self.mock.transport
            telemetry.TRANSPORT = self.mock.telemetry_transport
            did, code, s, t, st, base = self._first_post_401(recover_fault=fault, server_accepts=True)
            self.assertEqual((code, s['signal'], s.get('task_kept')), (4, 'credentialsReset', True), fault)
            d = self.draft(did)
            idem, digest = d['idem'], d['body_sha256']
            self.assertEqual(self.posts[0][1], idem)
            self._assert_kept(did, idem, digest)
            # 恢复正常后：按原键查到原任务并交付，全程一次生成请求、一次扣费
            self.wrap(lambda real, *a: real(*a))
            code, s, _, _ = self.run_cmd('resume', '--draft', did)
            self.assertEqual(s['signal'], 'delivered', fault)
            self.assertEqual(len(self.posts), 0, fault)  # 新包装计数：恢复后没有任何生成请求
            self.assertEqual(self.mock.charges, base + 1, fault)
            self.assertEqual(self.draft(did)['idem'], idem)

    def test_fam02_recovery_fails_not_accepted_still_query_only(self):
        did, code, s, t, st, base = self._first_post_401(recover_fault=0)
        self.assertEqual((code, s.get('task_kept')), (4, True))
        d = self.draft(did)
        self._assert_kept(did, d['idem'], d['body_sha256'])
        self.wrap(lambda real, *a: real(*a))
        for _ in range(2):
            code, s, _, _ = self.run_cmd('resume', '--draft', did)
            self.assertEqual((code, s['signal'], s.get('progress')), (2, 'jobPending', 'unconfirmed'))
        self.assertEqual(len(self.posts), 0)
        self.assertEqual(self.mock.charges, base)
        self._assert_kept(did, d['idem'], d['body_sha256'])

    def test_poll_401_recovers_once_then_persistent_keeps_task(self):
        did = self.ready()
        n = {'401': 0}

        def hook(real, method, url, body, headers, timeout, binary):
            if method == 'GET' and '/jobs/' in url and not url.endswith('/image') and '/by-key/' not in url and not n['401']:
                n['401'] += 1
                raise studio.GatewayError(401)
            return real(method, url, body, headers, timeout, binary)
        self.mock.scenario['pending_rounds'] = 1
        self.wrap(hook)
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        self.assertTrue(any(c[1] == '/skill-key' for c in self.mock.calls))
        # 持续失效：退出码 4，原任务保留，不重发
        did2 = self.confirmed_draft()
        self.mock.scenario.update(pending_rounds=1, auth_expired_on_poll=True)
        code, s, t, _ = self.run_cmd('run', '--draft', did2)
        self.assertEqual((code, s['signal'], s.get('task_kept')), (4, 'credentialsReset', True))
        d = self.draft(did2)
        self.assertTrue(d['job_id'])
        self.mock.scenario['auth_expired_on_poll'] = False
        code, s, t, _ = self.run_cmd('resume', '--draft', did2)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(self.mock.charges, 2)

    def test_corrupt_png_kept_pending_then_get_only(self):
        did = self.ready()
        n = {'bad': 0}

        def hook(real, method, url, body, headers, timeout, binary):
            r = real(method, url, body, headers, timeout, binary)
            if url.endswith('/image') and not n['bad']:
                n['bad'] += 1
                raw = bytearray(r[1])
                i = raw.index(b'IDAT') + 8
                raw[i] ^= 0xff  # 损坏数据块：CRC 不再匹配
                return r[0], bytes(raw)
            return r
        self.wrap(hook)
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (2, 'downloadPending'))
        self.assertEqual(self.draft(did)['state'], 'download_pending')
        self.assertFalse(os.path.isdir(os.path.join(self.photos, '汉服写真结果')) and
                         os.listdir(os.path.join(self.photos, '汉服写真结果')))
        code, s, t, _ = self.run_cmd('resume', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        png_local.verify(open(s['paths'][0], 'rb').read())
        self.assertEqual((len(self.posts), self.mock.charges), (1, 1))

    def test_links_without_expiry_not_shown(self):
        def hook(real, method, url, body, headers, timeout, binary):
            st, raw = real(method, url, body, headers, timeout, binary)
            if url.endswith('/quick-entry') or url.endswith('/membership-link'):
                d = json.loads(raw)
                d.pop('expires_in', None)
                raw = json.dumps(d).encode()
            return st, raw
        self.wrap(hook)
        for cmd in ('topup', 'status', 'balance', 'paid', 'auth', 'history'):
            shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)  # 每条都是全新用户
            code, s, t, _ = self.run_cmd(cmd)
            self.assertNotIn('http', t, cmd)
            self.assertIn('这一步还没完成', t, cmd)

    def test_self_only_eligibility_and_three_consents(self):
        """规格 T02：只为本人、成年、单人；资格自述不替代三项同意；不合格不联网；不开放代购。"""
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        did = s['draft_id']
        for flag, reason, must in ((['--adult', 'no'], 'minor', '成年'),
                                   (['--self', 'no'], 'not_self', '本人的单人照')):
            code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'song_beizi', *flag)
            self.assertEqual((code, s['signal'], s['reason']), (3, 'notEligible', reason), flag)
            self.assertIn(must, t)
        code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'song_beizi', '--orderer', 'family_proxy')
        self.assertEqual(s['signal'], 'usage')
        code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'song_beizi')
        self.assertEqual(s['signal'], 'planReady')
        for must in ('1. 这张照片是你本人的单人照', '2. 同意把这张照片发送给图片服务及算力供应商处理', '3. 同意按张计费',
                     '付过款不能代替前两项同意'):
            self.assertIn(must, t)
        for owner, upload, pay in (('yes', 'no', 'yes'), ('no', 'yes', 'yes'), ('yes', 'yes', 'no')):
            code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--owner-consent', owner, '--upload-consent', upload, '--pay-consent', pay)
            self.assertEqual(s['signal'], 'needsConfirmation')
        self.assertEqual(self.mock.calls, [])

class RepairMat101(Base):
    """继承孕妈 1.0.1 修复回归：MAT-A3-02（确认后坏图/换图先本地拦下）与 MAT-A3-03（资格未问到先补问）。"""

    def draft(self, did):
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'drafts', did + '.json')) as f:
            return json.load(f)

    def _break(self, mode):
        if mode == 'delete':
            os.remove(self.photo)
        elif mode == 'truncate':
            with open(self.photo, 'wb') as f:
                f.write(self.photo_bytes[:len(self.photo_bytes) // 2])
        else:  # 另一张有效图
            with open(self.photo, 'wb') as f:
                f.write(jpeg_bytes(640, 960))

    def _fresh(self):
        shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)
        with open(self.photo, 'wb') as f:
            f.write(self.photo_bytes)
        self.mock = mock_backend.Mock()
        studio.TRANSPORT = self.mock.transport
        telemetry.TRANSPORT = self.mock.telemetry_transport

    def test_mat_a3_02_bad_photo_after_confirm_zero_business_http(self):
        # 三种账户处境：本机无账户（原先先给关联链接）、已关联但余额为零（原先先给充值引导）、有余额
        for account in ('none', 'zero', 'funded'):
            for mode in ('delete', 'truncate'):
                self._fresh()
                did = self.confirmed_draft()
                if account != 'none':
                    self.paid_account(did, 0 if account == 'zero' else 3)
                self._break(mode)
                self.mock.calls[:] = []
                code, s, t, _ = self.run_cmd('run', '--draft', did)
                self.assertEqual((code, s['signal']), (3, 'photoInvalid'), (account, mode))
                self.assertIn('me.jpg', t, (account, mode))
                self.assertEqual(self.mock.calls, [], (account, mode))  # 业务请求 0（首次匿名上报另计）
                self.assertEqual(self.mock.charges, 0)
                d = self.draft(did)
                self.assertTrue(d['idem'] and d['pay_consent'], (account, mode))  # 坏图不新建任务、不换键

    def test_mat_a3_02_changed_valid_photo_voids_confirmation_offline(self):
        for account in ('none', 'funded'):
            self._fresh()
            did = self.confirmed_draft()
            if account == 'funded':
                self.paid_account(did, 3)
            self._break('replace')
            self.mock.calls[:] = []
            code, s, t, _ = self.run_cmd('run', '--draft', did)
            self.assertEqual((code, s['signal']), (2, 'photoChanged'), account)
            self.assertEqual(self.mock.calls, [], account)
            d = self.draft(did)
            self.assertEqual((d['idem'], d['owner_consent'], d['upload_consent'], d['pay_consent']), (None, False, False, False))
            self.assertEqual(self.run_cmd('run', '--draft', did)[1]['signal'], 'needsConfirmation')
            self.assertEqual(self.mock.calls, [], account)

    def test_mat_a3_02_unchanged_photo_still_delivers(self):
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (0, 'delivered'))
        self.assertEqual(self.mock.charges, 1)

    def test_mat_a3_02_needs_credits_resume_checks_photo_first(self):
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        real = self.mock.transport

        def t402(method, url, body, headers, timeout, binary):
            if method == 'POST' and url.endswith('/skill-jobs'):
                raise studio.GatewayError(402)
            return real(method, url, body, headers, timeout, binary)
        studio.TRANSPORT = t402
        self.assertEqual(self.run_cmd('run', '--draft', did)[1]['signal'], 'needsCredits')
        studio.TRANSPORT = real
        self._break('truncate')
        self.mock.calls[:] = []
        code, s, _, _ = self.run_cmd('resume', '--draft', did)
        self.assertEqual((code, s['signal']), (3, 'photoInvalid'))
        self.assertEqual(self.mock.calls, [])

    def test_mat_a3_02_unknown_or_submitted_ignores_bad_local_photo(self):
        """已提交或结果未知的任务：本地图坏了也只查原任务，不发第二次生成请求、不解锁。"""
        for kind in ('unknown', 'submitted'):
            self._fresh()
            did = self.confirmed_draft()
            self.paid_account(did, 3)
            real = self.mock.transport
            posts = []
            pending = {'n': 0}

            def hook(method, url, body, headers, timeout, binary, kind=kind):
                if method == 'POST' and url.endswith('/skill-jobs'):
                    posts.append(headers.get('Idempotency-Key'))
                    r = real(method, url, body, headers, timeout, binary)
                    if kind == 'unknown':
                        raise studio.GatewayError(0)
                    return r
                if method == 'GET' and '/jobs/' in url and pending['n'] < 50:
                    pending['n'] += 1
                    raise studio.GatewayError(0)  # 首次运行期间一直查不到进度，任务保持已提交
                return real(method, url, body, headers, timeout, binary)
            studio.TRANSPORT = hook
            code, s, _, _ = self.run_cmd('run', '--draft', did)
            self.assertIn(s['signal'], ('jobPending', 'downloadPending'), kind)
            d = self.draft(did)
            self.assertTrue(d.get('job_id') or d.get('state') == 'submit_unknown', kind)
            self._break('truncate')
            # 结果未知期间换图/换档/改方案都不能解锁
            self.assertEqual(self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun')[1]['signal'], 'taskLocked', kind)
            pending['n'] = 99
            for cmd in ('run', 'resume'):
                code, s, _, _ = self.run_cmd(cmd, '--draft', did)
                if s['signal'] == 'delivered':
                    break
                self.assertIn(s['signal'], ('jobPending', 'downloadPending'), (kind, cmd))
            self.assertEqual(s['signal'], 'delivered', kind)
            self.assertEqual(len(posts), 1, kind)
            self.assertEqual(self.mock.charges, 1, kind)

    def test_mat_a3_03_adult_unknown_asks_once_then_continues(self):
        """继承 MAT-A3-03：本人、成年未问到时一次合并补问，不当成不符合。"""
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '想拍唐制齐胸襦裙', '--image', self.photo)
        did = s['draft_id']
        code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun', '--adult', 'unknown')
        self.assertEqual((code, s['signal'], s['missing']), (2, 'needsEligibility', ['adult']))
        self.assertIn('你是成年人吗', t)
        for bad in ('换一张', '证明材料', '身份证', '年龄证明'):
            self.assertNotIn(bad, t)
        self.assertIn('不需要任何证明', t)
        code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun', '--self', 'unknown', '--adult', 'unknown')
        self.assertEqual(s['missing'], ['self', 'adult'])
        for q in ('照片里是你本人吗', '你是成年人吗'):
            self.assertIn(q, t)
        self.assertEqual(t.count('？'), 2)  # 一次合并补问
        code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun', '--self', 'yes', '--adult', 'yes')
        self.assertEqual((code, s['signal']), (0, 'planReady'))
        # 明确不符合仍拒绝；明确的否定优先于其他未知项
        code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun', '--adult', 'no', '--self', 'unknown')
        self.assertEqual((code, s['signal'], s['reason']), (3, 'notEligible', 'minor'))
        self.assertNotIn('照片', t)
        code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun', '--self', 'no', '--adult', 'unknown')
        self.assertEqual(s['reason'], 'not_self')
        self.assertEqual(self.mock.calls, [])

class RepairSlv101(Base):
    """继承银发 1.0.1 修复 SLV-A3-01（规格 T14）：未提交草稿改方案早退时，旧三项同意与待提交键必须已持久作废；
    之后 run / resume / regenerate 都不能借旧确认提交旧图旧方案。用例在银发 1.0.0 代码上会失败（会发出旧图的生成请求）。"""

    EARLY = (
        (['--scene', 'tang_ruqun', '--self', 'unknown', '--adult', 'yes'], 'needsEligibility'),
        (['--scene', 'tang_ruqun', '--self', 'no', '--adult', 'yes'], 'notEligible'),
        (['--scene', 'tang_ruqun', '--self', 'yes', '--adult', 'unknown'], 'needsEligibility'),
        (['--scene', 'tang_ruqun', '--self', 'yes', '--adult', 'no'], 'notEligible'),
        (['--scene', 'tang_ruqun', '--form', 'ming'], 'formInvalid'),
        (['--scene', 'daily', '--form', 'quju'], 'formInvalid'),
        (['--scene', 'garden', '--form', 'ming', '--self', 'unknown'], 'needsEligibility'),
        (['--scene', 'no-such-scene'], 'sceneInvalid'),
        (['--scene', 'tang_ruqun', '--image', '@missing'], 'photoInvalid'),
        (['--scene', 'tang_ruqun', '--image', '@truncated'], 'photoInvalid'),
        (['--scene', 'tang_ruqun', '--face-clear', 'no'], 'needsClearerPhoto'),
        (['--scene', 'tang_ruqun', '--outfit', '长' * 41], 'textInvalid'),
    )

    def draft(self, did):
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'drafts', did + '.json')) as f:
            return json.load(f)

    def _fresh(self):
        shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)
        self.mock = mock_backend.Mock()
        studio.TRANSPORT = self.mock.transport
        telemetry.TRANSPORT = self.mock.telemetry_transport

    def _argv(self, extra):
        argv = list(extra)
        if '--image' in argv:
            i = argv.index('--image') + 1
            if argv[i].startswith('@'):
                b = os.path.join(self.photos, 'me %s#b.jpg' % argv[i][1:])  # 带空格和 # 的合成路径
                if argv[i] == '@truncated':
                    with open(b, 'wb') as f:
                        f.write(jpeg_bytes(640, 960)[:200])
                argv[i] = b
        return argv

    def _posts(self):
        return [c for c in self.mock.calls if c[0] == 'POST' and c[1] == '/skill-jobs']

    def _start(self, start):
        """照片 A、本人、棚拍：plan + 三项确认，账户有次数。start=needs_credits 时先遇到一次 402（无任务号）。"""
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        if start == 'needs_credits':
            real = self.mock.transport

            def t402(method, url, body, headers, timeout, binary):
                if method == 'POST' and url.endswith('/skill-jobs'):
                    raise studio.GatewayError(402)
                return real(method, url, body, headers, timeout, binary)
            studio.TRANSPORT = t402
            self.assertEqual(self.run_cmd('run', '--draft', did)[1]['signal'], 'needsCredits')
            studio.TRANSPORT = real
            d = self.draft(did)
            self.assertEqual((d['state'], d.get('job_id')), ('needs_credits', None))
        return did

    def test_slv_a3_01_early_exit_then_continue_sends_nothing(self):
        for start in ('confirmed', 'needs_credits'):
            for extra, want in self.EARLY:
                self._fresh()
                did = self._start(start)
                old_idem = self.draft(did)['idem']
                self.assertTrue(old_idem)
                self.mock.calls[:] = []
                code, s, t, _ = self.run_cmd('plan', '--draft', did, *self._argv(extra))
                self.assertEqual(s['signal'], want, (start, extra))
                self.assertEqual(self.mock.calls, [], (start, extra))  # 改方案本身零业务请求
                d = self.draft(did)
                self.assertEqual((d['owner_consent'], d['upload_consent'], d['pay_consent'], d['idem'], d['state']),
                                 (False, False, False, None, 'replanning'), (start, extra))
                # 「继续」/ 重启后再 run / 重新生成：只提示补齐，生成请求 0、扣次 0，旧图 A 不发
                for cmd in (('resume', '--draft', did), ('run', '--draft', did), ('resume', '--draft', did),
                            ('regenerate', '--draft', did, '--pay-consent', 'yes')):
                    code, s, t, _ = self.run_cmd(*cmd)
                    self.assertEqual((code, s['signal']), (2, 'needsReplan'), (start, extra, cmd[0]))
                    self.assertIn('原来的确认已经作废', t)
                    self.assertIn('没有产生任何扣费', t)
                self.assertEqual(self.mock.calls, [], (start, extra))
                self.assertEqual(self.mock.charges, 0, (start, extra))
                self.assertEqual(self.draft(did)['idem'], None)

    def test_slv_a3_01_needs_credits_topped_up_still_not_old_photo(self):
        """银发 1.0.0 前科：无任务号的待充值草稿改方案早退后，补充次数再「继续」会恢复旧确认并发旧图。本包不会。"""
        did = self._start('needs_credits')
        self.run_cmd('plan', '--draft', did, '--scene', 'garden', '--form', 'ming', '--self', 'unknown')
        self.mock.authorize(self.secret(), 5)  # 补充了次数
        self.mock.calls[:] = []
        for _ in range(2):
            self.assertEqual(self.run_cmd('resume', '--draft', did)[1]['signal'], 'needsReplan')
        self.assertEqual(self._posts(), [])
        self.assertEqual(self.mock.charges, 0)

    def test_slv_a3_01_new_plan_b_needs_fresh_three_consents(self):
        """新方案（照片 B、园林明风）信息补齐并重新三项明确同意后，才用新键提交新图。"""
        for start in ('confirmed', 'needs_credits'):
            self._fresh()
            did = self._start(start)
            old = self.draft(did)
            photo_b = os.path.join(self.photos, 'me b.jpg')
            with open(photo_b, 'wb') as f:
                f.write(jpeg_bytes(640, 960))
            plan_b = ['plan', '--draft', did, '--scene', 'garden', '--form', 'ming', '--adult', 'yes', '--image', photo_b]
            self.assertEqual(self.run_cmd(*plan_b, '--self', 'unknown')[1]['signal'], 'needsEligibility')
            self.assertEqual(self.draft(did)['images'], [photo_b])
            # 新信息补齐、方案保存成功：仍需重新确认，不能直接 run
            self.assertEqual(self.run_cmd(*plan_b, '--self', 'yes')[1]['signal'], 'planReady')
            self.assertEqual(self.run_cmd('run', '--draft', did)[1]['signal'], 'needsConfirmation')
            for pc, uc, pay in (('no', 'yes', 'yes'), ('yes', 'no', 'yes'), ('yes', 'yes', 'no')):
                self.assertEqual(self.run_cmd('confirm', '--draft', did, '--owner-consent', pc, '--upload-consent', uc,
                                              '--pay-consent', pay)[1]['signal'], 'needsConfirmation')
            before = len(self._posts())
            self.assertEqual(self.run_cmd('confirm', '--draft', did, '--pay-consent', 'yes')[1]['signal'], 'confirmed')
            new = self.draft(did)
            self.assertNotEqual(new['idem'], old['idem'])
            self.assertEqual((new['form'], new['scene'], new['images']), ('ming', 'garden', [photo_b]))
            code, s, _, _ = self.run_cmd('run', '--draft', did)
            self.assertEqual((code, s['signal']), (0, 'delivered'), start)
            posts = self._posts()[before:]
            self.assertEqual(len(posts), 1, start)
            self.assertEqual(posts[0][3].get('Idempotency-Key'), new['idem'])
            self.assertEqual(self.mock.charges, 1, start)
            with open(photo_b, 'rb') as f:
                import hashlib
                self.assertEqual(self.draft(did)['photo_sha256'], hashlib.sha256(f.read()).hexdigest())

    def test_slv_a3_01_same_plan_reconfirm_still_works(self):
        """早退后用户决定按原方案（照片 A、本人）做：重新 plan 并重新确认后照常交付，只扣一次。"""
        did = self._start('confirmed')
        self.assertEqual(self.run_cmd('plan', '--draft', did, '--scene', 'tang_ruqun', '--form', 'ming')[1]['signal'], 'formInvalid')
        self.assertEqual(self.run_cmd('plan', '--draft', did, '--scene', 'daily')[1]['signal'], 'planReady')
        self.assertEqual(self.run_cmd('confirm', '--draft', did, '--pay-consent', 'yes')[1]['signal'], 'confirmed')
        self.assertEqual(self.run_cmd('run', '--draft', did)[1]['signal'], 'delivered')
        self.assertEqual((len(self._posts()), self.mock.charges), (1, 1))

    def test_slv_a3_01_submitted_unknown_pending_replan_keeps_original(self):
        """红线：结果未知 / 已提交 / 待取回时改方案仍拒绝，不清原键、原请求体或锁；本地图坏了也只查原任务，无第二次生成请求。"""
        for kind in ('unknown', 'submitted', 'download_pending'):
            self._fresh()
            with open(self.photo, 'wb') as f:
                f.write(self.photo_bytes)
            did = self.confirmed_draft()
            self.paid_account(did, 3)
            real = self.mock.transport
            gate = {'open': False}

            def hook(method, url, body, headers, timeout, binary, kind=kind):
                if method == 'POST' and url.endswith('/skill-jobs'):
                    r = real(method, url, body, headers, timeout, binary)
                    if kind == 'unknown':
                        raise studio.GatewayError(0)
                    return r
                if not gate['open'] and method == 'GET' and '/jobs/' in url:
                    if kind == 'download_pending' and not url.endswith('/image'):
                        return real(method, url, body, headers, timeout, binary)
                    raise studio.GatewayError(0)
                return real(method, url, body, headers, timeout, binary)
            studio.TRANSPORT = hook
            self.run_cmd('run', '--draft', did)
            before = self.draft(did)
            self.assertTrue(before['state'] in studio.LOCKED_STATES, (kind, before['state']))
            with open(self.photo, 'wb') as f:
                f.write(self.photo_bytes[:100])
            for extra, _ in self.EARLY:
                s = self.run_cmd('plan', '--draft', did, *self._argv(extra))[1]
                self.assertEqual(s['signal'], 'taskLocked', (kind, extra))
                after = self.draft(did)
                for k in ('state', 'idem', 'job_id', 'body_sha256', 'pay_consent', 'images', 'scene', 'form'):
                    self.assertEqual(after.get(k), before.get(k), (kind, extra, k))
            gate['open'] = True
            for _ in range(3):
                s = self.run_cmd('resume', '--draft', did)[1]
                if s['signal'] == 'delivered':
                    break
            self.assertEqual(s['signal'], 'delivered', kind)
            self.assertEqual(len(self._posts()), 1, kind)
            self.assertEqual(self.mock.charges, 1, kind)


class FrontmatterYaml(unittest.TestCase):
    """MAT-A3-01：用标准 YAML 解析器检查源码 SKILL.md 及最终 ZIP 里的原始 frontmatter（重复键、字段类型、冒号空格反例）。"""

    def loader(self):
        import yaml

        class NoDup(yaml.SafeLoader):
            pass

        def mapping(loader, node, deep=False):
            keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
            if len(keys) != len(set(keys)):
                raise ValueError('duplicate key')
            return yaml.SafeLoader.construct_mapping(loader, node, deep)
        NoDup.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        return yaml, NoDup

    def check(self, raw, where):
        yaml, NoDup = self.loader()
        text = raw.decode('utf-8')
        self.assertTrue(text.startswith('---\n'), where)
        fm = yaml.load(text.split('---', 2)[1], Loader=NoDup)
        for k in ('name', 'display_name', 'display_name_en', 'description', 'description_zh', 'description_en', 'version', 'author'):
            self.assertIsInstance(fm.get(k), str, (where, k))
            self.assertTrue(fm[k].strip(), (where, k))
        self.assertEqual(set(fm) - {'name', 'display_name', 'display_name_en', 'description', 'description_zh', 'description_en',
                                    'version', 'author', 'allowed-tools', 'examples_zh', 'examples_en'}, set(), where)
        for k in ('examples_zh', 'examples_en'):
            self.assertIsInstance(fm[k], list, where)
            self.assertTrue(all(isinstance(x, str) and x.strip() for x in fm[k]), where)
        self.assertEqual(len(fm['examples_zh']), len(fm['examples_en']))
        self.assertLessEqual(len(fm['examples_zh']), 3)
        self.assertEqual(fm['version'], studio.SKILL_VERSION)
        if SPEC is not None:
            self.assertEqual(fm['description'], SPEC['frontmatter']['description'])  # 规格候选值原样保留
            self.assertEqual(fm['description_en'], SPEC['frontmatter']['description_en'])
        self.assertLess(len(raw), 15 * 1024, where)
        return fm

    def test_source_and_zip_frontmatter_parse(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest('PyYAML 不可用')
        with open(os.path.join(PKG, 'SKILL.md'), 'rb') as f:
            src = self.check(f.read(), 'source')
        import zipfile
        for z in ZIPS:
            with zipfile.ZipFile(z) as zf:
                names = [n for n in zf.namelist() if n.endswith('/SKILL.md')]
                self.assertEqual(len(names), 1, z)
                self.assertEqual(self.check(zf.read(names[0]), z), src)

    def test_duplicate_key_and_unquoted_colon_rejected(self):
        try:
            import yaml
        except ImportError:
            self.skipTest('PyYAML 不可用')
        _, NoDup = self.loader()
        with open(os.path.join(PKG, 'SKILL.md'), encoding='utf-8') as f:
            text = f.read()
        fm = text.split('---', 2)[1].replace('description_en: "Create', 'description_en: "Hanfu: Create', 1)
        self.assertEqual(yaml.safe_load(fm)['description_en'][:7], 'Hanfu: ')  # 正例：引用后的冒号空格合法
        en = yaml.safe_load(fm)['description_en']
        unquoted = fm.replace('description_en: "%s"' % en, 'description_en: %s' % en, 1)
        self.assertNotEqual(unquoted, fm)
        with self.assertRaises(yaml.YAMLError):
            yaml.safe_load(unquoted)
        with self.assertRaises((ValueError, yaml.YAMLError)):
            yaml.load(fm + 'name: dup\n', Loader=NoDup)
        self.assertEqual(yaml.safe_load('k: "a: b"')['k'], 'a: b')  # 正常例：引用后冒号空格合法


class HanfuSpec(Base):
    """汉服规格专项：T01 路由与边界提示、T12 形制/四基线与非实拍标注、T13 资格与边界、闺蜜各拍拆独立任务、T13 微信关联与支付 Mock（只 Mock）。"""

    def test_t01_suggested_scene_in_first_turn(self):
        studio.TRANSPORT = lambda *a, **k: (_ for _ in ()).throw(AssertionError('net'))
        for text, want, intent in (('想穿汉服拍组写真，唐制的齐胸襦裙最好看。', 'tang_ruqun', None),
                                   ('唐制半臂很飒，想拍一组半臂的写真。', 'tang_banbi', None),
                                   ('男生能拍汉服吗？想拍组侠客风的。', 'swordsman', None),
                                   ('过年穿汉服，想拍组新年汉服写真。', 'daily', None),
                                   ('去西安玩，想拍组汉服写真留念。', None, 'clarify_destination'),
                                   ('想拍凤冠霞帔', None, 'out_of_scope_wedding'),
                                   ('宋制马面裙', 'ming_mamian', 'form_conflict'),
                                   ('你好', None, None)):
            code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', text)
            self.assertEqual((code, s['suggested_scene'], s['intent']), (0, want, intent), text)
            self.assertNotIn('http', t)
        self.assertEqual(self.mock.calls, [])

    def test_t13_boundaries_without_network(self):
        """规格 T13：不是本人、未成年、多人、跨套系形制组合都不进入方案；不联网；拒绝话术覆盖婚服旗袍和服军装。"""
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '想拍曲裾', '--image', self.photo)
        did = s['draft_id']
        for extra, sig in ((['--self', 'no'], 'notEligible'), (['--adult', 'no'], 'notEligible'),
                           (['--single', 'no'], 'peopleUnsupported'), (['--form', 'tang'], 'formInvalid')):
            code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'quju', *extra)
            self.assertEqual(s['signal'], sig, extra)
            self.assertIn('没有产生任何扣费', t)
        code, s, t, _ = self.run_cmd('refuse')
        for must in ('婚服', '旗袍', '和服', '军装'):
            self.assertIn(must, t)
        self.assertEqual(self.mock.calls, [])

    def test_t12_form_and_baselines_only_in_prompt(self):
        """规格 T12/T15：形制、妆发与四基线只进 prompt；请求体恰六字段；上报与关联不含原话、形制或资格信息。"""
        did = self.confirmed_draft(scene='quju')
        code, s, t, _ = self.run_cmd('run', '--draft', did)  # 未授权：只走关联入口
        self.mock.authorize(self.secret(), 3)
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered', t)
        job = [c for c in self.mock.calls if c[1].endswith('/skill-jobs')][-1][2]
        self.assertEqual(set(job), {'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent'})
        p = job['prompt']
        self.assertTrue(p.startswith('真实性基线'))
        for must in ('人物身份基线', '文字基线', '安全基线', '经背后回前', '不混套系'):
            self.assertIn(must, p)
        for bad in ('age', 'form', 'dynasty', 'people_count', 'self', 'adult', 'model', 'n', 'quality'):
            self.assertNotIn(bad, job)
        self.assertTrue(self.mock.telemetry_calls)
        for body, _ in self.mock.telemetry_calls + self.mock.link_calls:
            dumped = json.dumps(body, ensure_ascii=False)
            for bad in ('想拍汉服写真', '曲裾', 'quju', '成年', 'adult'):
                self.assertNotIn(bad, dumped)
        for body, _ in self.mock.telemetry_calls:
            self.assertEqual(set(body), mock_backend.TELEMETRY_FIELDS)
        # 园林明风：整套服饰进 prompt，其他字段不变
        did = self.confirmed_draft(scene='garden')
        self.run_cmd('plan', '--draft', did, '--scene', 'garden', '--form', 'ming')
        self.run_cmd('confirm', '--draft', did, '--pay-consent', 'yes')
        self.assertEqual(self.run_cmd('run', '--draft', did)[1]['signal'], 'delivered')
        job = [c for c in self.mock.calls if c[1].endswith('/skill-jobs')][-1][2]
        self.assertIn('马面裙', job['prompt'])
        self.assertEqual(set(job), {'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent'})

    def test_t14_friends_each_split_into_independent_tasks(self):
        """规格 T13：闺蜜各拍各的 → 各自本人单人照、各自确认、各自一键、各自扣一次；合照不支持；不从合影裁人。"""
        other = os.path.join(self.photos, 'me2.png')
        shutil.copyfile(self.photo, other)
        dids = []
        for img in (self.photo, other):
            _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '闺蜜也想拍，但我们各拍各的单人写真', '--image', img)
            self.assertEqual(s['intent'], 'separate_self_tasks')
            did = s['draft_id']
            code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'daily')
            self.assertEqual(s['signal'], 'planReady')
            self.run_cmd('confirm', '--draft', did, '--pay-consent', 'yes')
            dids.append(did)
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '闺蜜合照', '--image', self.photo)
        code, s, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'daily', '--single', 'no')
        self.assertEqual((code, s['signal']), (3, 'peopleUnsupported'))
        self.assertIn('各自用本人的单人照分别来做', t)
        idems = [json.load(open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'drafts', d + '.json')))['idem'] for d in dids]
        self.assertEqual(len(set(idems)), 2)
        self.paid_account(dids[0], 2)
        for d in dids:
            self.assertEqual(self.run_cmd('run', '--draft', d)[1]['signal'], 'delivered')
        self.assertEqual(len([c for c in self.mock.calls if c[1] == '/skill-jobs']), 2)
        self.assertEqual(self.mock.charges, 2)

    def test_t12_demo_items_all_disclosed(self):
        code, s, t, _ = self.run_cmd('demo')
        self.assertEqual(code, 0)
        self.assertEqual([i['key'] for i in s['items']], list(studio.SCENES))
        for i in s['items']:
            self.assertIn('AI 生成汉服写真，非实拍', i['note'])
        self.assertTrue(t.startswith('都是效果示例图，不是你的真实结果'))

    def _expiry(self, seconds):
        orig = self.mock.transport

        def tr(method, url, body, headers, timeout, binary):
            st, raw = orig(method, url, body, headers, timeout, binary)
            d = json.loads(raw)
            if 'expires_in' in d:
                d['expires_in'] = seconds
            return st, json.dumps(d).encode()
        studio.TRANSPORT = tr

    def test_t13_link_expiry_comes_from_server_not_fixed(self):
        # 生图入口 1800 秒、OAuth 900 秒、会员 handoff 300 秒：客户端只认服务端给的正整数有效期，不统一套 30 分钟
        for seconds in (1800, 900, 300):
            self._expiry(seconds)
            shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)
            code, s, t, _ = self.run_cmd('topup')
            self.assertEqual((code, s['signal']), (2, 'linkAccount'), seconds)
            self.assertIn('](https://aistore.zhaopintong.com/membership/gemini/register/#entry=', t)
        src = open(os.path.join(PKG, 'scripts', 'studio.py'), encoding='utf-8').read()
        for bad in ('1800', '900', '30 分钟', '30分钟'):
            self.assertNotIn(bad, src)
        for t in (W.auth('https://x/'), W.account_link('https://x/')):
            self.assertNotIn('30 分钟', t)

    def test_t13_callback_links_account_while_client_closed(self):
        # 扫码回调由服务端完成关联；电脑这边不运行任何命令，之后查询仍为已关联；重复回调幂等
        did = self.confirmed_draft()
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'onboardingPreview')
        secret = self.secret()
        before = len(self.mock.calls)
        self.mock.authorize(secret, 0)   # 模拟手机扫码回调完成关联
        self.mock.authorize(secret, 0)   # 同一身份重复回调
        self.assertEqual(len(self.mock.calls), before)  # 客户端未参与
        self.assertEqual(len([k for k in self.mock.users if k == secret]), 1)
        code, s, _, _ = self.run_cmd('status')
        self.assertEqual((code, s['signal'], s['remaining_uses']), (0, 'registered', 0))
        code, s, t, _ = self.run_cmd('run', '--draft', did)  # 已关联、无次数：只给最后一步充值页，不出图
        self.assertEqual((code, s['signal'], s['link_included']), (2, 'needsCredits', True))
        self.assertFalse([c for c in self.mock.calls if c[1] == '/skill-jobs'])

    def test_t13_reported_payment_not_credited(self):
        # 页面登记已付款（reported）、扫码、截图、用户说付好了都不算到账：只认真实次数
        did = self.confirmed_draft()
        self.run_cmd('run', '--draft', did)
        self.mock.authorize(self.secret(), 0)
        for _ in range(2):
            code, s, t, _ = self.run_cmd('paid')
            self.assertEqual((code, s['signal']), (2, 'creditsPending'))
            self.assertIn('还没看到这笔到账', t)
        code, s, _, _ = self.run_cmd('resume', '--draft', did)
        self.assertNotEqual(s['signal'], 'delivered')
        self.assertFalse([c for c in self.mock.calls if c[1] == '/skill-jobs'])
        self.assertEqual(self.mock.charges, 0)
        self.mock.users[self.secret()]['balance'] = 1   # 真实入账后
        code, s, _, _ = self.run_cmd('paid')
        self.assertEqual((code, s['signal'], s['remaining_uses']), (0, 'creditsConfirmed', 1))
        code, s, _, _ = self.run_cmd('resume', '--draft', did)
        self.assertEqual((code, s['signal']), (0, 'delivered'))
        self.assertEqual(self.mock.charges, 1)

    def test_t15_request_body_has_only_six_fields(self):
        did = self.confirmed_draft(scene='quju', features='长卷发')
        self.paid_account(did, 2)
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        jobs = [c for c in self.mock.calls if c[1] == '/skill-jobs']
        self.assertEqual(len(jobs), 1)
        body = jobs[0][2]
        self.assertEqual(set(body), {'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent'})
        for bad in ('model', 'n', 'quality', 'people_count', 'age', 'identity_ids', 'provider_url', 'url'):
            self.assertNotIn(bad, body)
        self.assertEqual(len(body['references']), 1)
        self.assertEqual(set(body['references'][0]), {'mime', 'content'})
        self.assertNotIn('http', body['prompt'])



class InheritedRepairTrv101(Base):
    """1.0.1 修复 A3-TRV-01/02/03（TRV-04/05 在契约测试与 Confirmation 用例里）。"""
    wrap = OriginalTaskSpec.wrap
    draft = OriginalTaskSpec.draft
    ready = OriginalTaskSpec.ready

    def fresh(self):
        shutil.rmtree(os.path.join(self.home, 'mps-hanfu-portrait-studio'), ignore_errors=True)
        self.mock = mock_backend.Mock()
        studio.TRANSPORT = self.mock.transport
        telemetry.TRANSPORT = self.mock.telemetry_transport

    def account(self):
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')) as f:
            return json.load(f)

    def job_posts(self):
        return [c for c in self.mock.calls if c[0] == 'POST' and c[1] == '/skill-jobs']

    def bound_calls(self):
        return [c for c in self.mock.calls if c[1] == '/skill-key/bound']

    # ---- A3-TRV-01：绑定必须明确 bound=true，未确认不得新生成 ----

    BAD_BOUND = ('false', 'missing', 'timeout', 500, 401, 'garbage', 'truthy')
    # 1.0.2（A3-TRV-01-R1）：401 是凭证失效信号，单独作废本机凭证；其余未确认情形保留凭证、下次再确认
    UNCONFIRMED_BOUND = ('false', 'missing', 'timeout', 500, 'garbage', 'truthy')

    def test_trv01_bound_not_confirmed_never_generates(self):
        for mode in self.UNCONFIRMED_BOUND:
            self.fresh()
            did = self.ready()
            self.mock.scenario['bound'] = mode
            for _ in range(2):  # 第二次 = 重启后再跑（状态全部从磁盘重新加载）
                code, s, t, _ = self.run_cmd('run', '--draft', did)
                self.assertEqual((code, s['signal']), (3, 'serviceUnavailable'), mode)
                self.assertEqual(self.job_posts(), [], mode)
                a = self.account()
                self.assertTrue(a.get('skill_key'), mode)  # 合法凭证已私存
                self.assertIs(a.get('skill_key_bound'), False, mode)  # 但未确认
                d = self.draft(did)
                self.assertEqual(d['state'], 'confirmed', mode)  # 没有提交，不锁任务
                self.assertIn('还没有开始生成，没有扣次数', t, mode)
            self.assertEqual(len([c for c in self.mock.calls if c[1] == '/skill-key']), 1, mode)  # 凭证只领一次
            self.assertEqual(len(self.bound_calls()), 2, mode)  # 每次命令只确认一次，不自动重试
            self.assertEqual(self.mock.charges, 0, mode)
            # 补确认成功的正例：同一草稿、同一任务键继续
            idem = self.draft(did)['idem']
            self.mock.scenario.pop('bound')
            code, s, _, _ = self.run_cmd('run', '--draft', did)
            self.assertEqual(s['signal'], 'delivered', mode)
            self.assertIs(self.account().get('skill_key_bound'), True)
            self.assertEqual(len(self.job_posts()), 1, mode)
            self.assertEqual(self.job_posts()[0][3].get('Idempotency-Key'), idem)
            self.assertEqual(self.mock.charges, 1, mode)

    def test_trv01_bound_confirmed_before_first_post(self):
        did = self.ready()
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        paths = [c[1] for c in self.mock.calls if c[0] == 'POST']
        self.assertLess(paths.index('/skill-key/bound'), paths.index('/skill-jobs'))
        self.assertEqual(self.bound_calls()[0][2], {'key': self.account()['skill_key']})
        # 已确认后不再重复确认
        did2 = self.confirmed_draft()
        self.run_cmd('run', '--draft', did2)
        self.assertEqual(len(self.bound_calls()), 1)

    def test_trv01_cached_unbound_key_after_restart(self):
        did = self.ready()
        self.run_cmd('run', '--draft', did)
        p = os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json')
        for legacy in (False, None):  # 未确认标记；或缺标记（旧缓存）都按未确认处理
            a = self.account()
            if legacy is None:
                a.pop('skill_key_bound', None)
            else:
                a['skill_key_bound'] = legacy
            with open(p, 'w') as f:
                json.dump(a, f)
            self.mock.scenario['bound'] = 'false'
            did2 = self.confirmed_draft()
            before = len(self.job_posts())
            code, s, _, _ = self.run_cmd('run', '--draft', did2)
            self.assertEqual((code, s['signal']), (3, 'serviceUnavailable'), legacy)
            self.assertEqual(len(self.job_posts()), before, legacy)
            self.mock.scenario.pop('bound')
            code, s, _, _ = self.run_cmd('run', '--draft', did2)
            self.assertEqual(s['signal'], 'delivered', legacy)
            self.assertEqual(len(self.job_posts()), before + 1, legacy)

    def test_trv01_401_recovery_requires_bound(self):
        for mode in self.BAD_BOUND:
            self.fresh()
            did = self.ready()
            self.run_cmd('run', '--draft', did)  # 先拿到已确认的凭证并交付一张
            did2 = self.confirmed_draft()
            self.mock.scenario['bound'] = mode

            def hook(real, method, url, body, headers, timeout, binary):
                if method == 'POST' and url.endswith('/skill-jobs'):
                    raise studio.GatewayError(401)
                return real(method, url, body, headers, timeout, binary)
            self.wrap(hook)
            code, s, _, _ = self.run_cmd('run', '--draft', did2)
            self.assertEqual((code, s['signal'], s.get('task_kept')), (4, 'credentialsReset', True), mode)
            self.assertEqual(len(self.posts), 1, mode)
            d = self.draft(did2)
            idem, digest = d['idem'], d['body_sha256']
            self.assertEqual(d['state'], 'submit_unknown', mode)  # 原任务仍锁定，不因绑定失败解锁
            # 之后不论绑定是否恢复，都只按原键查询，不再发生成请求
            for fix in (False, True):
                if fix:
                    self.mock.scenario.pop('bound', None)
                code, s, _, _ = self.run_cmd('resume', '--draft', did2)
                self.assertIn(s['signal'], ('jobPending', 'credentialsReset'), (mode, fix))
                self.assertEqual(len(self.posts), 1, (mode, fix))
                d = self.draft(did2)
                self.assertEqual((d['state'], d['idem'], d['body_sha256']), ('submit_unknown', idem, digest), (mode, fix))

    # ---- A3-TRV-01-R1（1.0.2）：绑定 401 必须作废失效凭证，沿原安装身份换新凭证，不永久循环 ----

    def _rotated_setup(self, legacy):
        """先正常交付一张拿到已确认凭证；网页轮换凭证；再把本机缓存改成 legacy（None=旧版缺标记，False=已领未确认）。"""
        self.fresh()
        did = self.ready()
        self.run_cmd('run', '--draft', did)
        a = self.account()
        old = a['skill_key']
        self.assertEqual(self.mock.rotate_key(a['install_secret']), old)
        if legacy is None:
            a.pop('skill_key_bound', None)
        else:
            a['skill_key_bound'] = legacy
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json'), 'w') as f:
            json.dump(a, f)
        return a, old

    def test_trv01_r1_bound_401_clears_stale_key_then_recovers(self):
        for legacy in (None, False):
            a0, old = self._rotated_setup(legacy)
            did2 = self.confirmed_draft()
            idem = self.draft(did2)['idem']
            jobs0, keys0 = len(self.job_posts()), len([c for c in self.mock.calls if c[1] == '/skill-key'])
            code, s, t, _ = self.run_cmd('run', '--draft', did2)
            self.assertEqual((code, s['signal'], s.get('task_kept')), (4, 'credentialsReset', True), legacy)
            self.assertIn('授权本身不扣费', t)
            a = self.account()
            self.assertNotIn('skill_key', a, legacy)          # 失效凭证作废
            self.assertNotIn('skill_key_bound', a, legacy)    # 绑定标记作废
            self.assertEqual(a['install_secret'], a0['install_secret'], legacy)  # 原安装身份不变、不新建账户
            d = self.draft(did2)
            self.assertEqual((d['state'], d['idem']), ('confirmed', idem), legacy)  # 原确认单与任务键保留
            self.assertIsNone(d.get('body_sha256'), legacy)  # 未冻结请求体：确实没有提交
            self.assertEqual(len(self.job_posts()), jobs0, legacy)  # 0 次新生成
            # 下一次（重启后从磁盘加载）：沿原 install_secret 重新领新凭证，确认 bound=true，只生成一次
            code, s, _, _ = self.run_cmd('run', '--draft', did2)
            self.assertEqual(s['signal'], 'delivered', legacy)
            a = self.account()
            self.assertNotEqual(a['skill_key'], old, legacy)
            self.assertIs(a['skill_key_bound'], True, legacy)
            self.assertEqual(a['install_secret'], a0['install_secret'], legacy)
            self.assertEqual(len([c for c in self.mock.calls if c[1] == '/skill-key']), keys0 + 1, legacy)
            self.assertEqual(self.bound_calls()[-1][2], {'key': a['skill_key']}, legacy)
            posts = self.job_posts()
            self.assertEqual(len(posts), jobs0 + 1, legacy)
            self.assertEqual(posts[-1][3].get('Idempotency-Key'), idem, legacy)
            # 再跑不会重复生成、不会再次确认
            nb = len(self.bound_calls())
            self.run_cmd('run', '--draft', self.confirmed_draft())
            self.assertEqual(len(self.bound_calls()), nb)

    def test_trv01_r1_no_infinite_rebind_of_same_key(self):
        """1.0.1 的根因：401 后下次仍绑定同一旧凭证。现在旧凭证最多被确认一次。"""
        _, old = self._rotated_setup(False)
        before = len([c for c in self.bound_calls() if c[2] == {'key': old}])  # 轮换前那次正常确认
        did2 = self.confirmed_draft()
        for _ in range(3):
            self.run_cmd('run', '--draft', did2)
        stale = [c for c in self.bound_calls() if c[2] == {'key': old}]
        self.assertEqual(len(stale) - before, 1)  # 轮换后旧凭证只被确认一次（得 401 即作废），不再循环
        self.assertEqual(len([p for p in self.job_posts() if p[3].get('Idempotency-Key') == self.draft(did2)['idem']]), 1)

    def test_trv01_r1_unknown_task_only_queries_original_key(self):
        """已发出、结果未知的任务：凭证被轮换后恢复只 GET 原键，不再 POST 生成；新凭证须 bound=true 才使用。"""
        self.fresh()
        did = self.ready()
        self.run_cmd('run', '--draft', did)
        did2 = self.confirmed_draft()

        def hook(real, method, url, body, headers, timeout, binary):
            if method == 'POST' and url.endswith('/skill-jobs'):
                real(method, url, body, headers, timeout, binary)  # 服务端已受理，但客户端没收到响应
                raise studio.GatewayError(0)
            return real(method, url, body, headers, timeout, binary)
        self.wrap(hook)
        code, s, _, _ = self.run_cmd('run', '--draft', did2)
        studio.TRANSPORT = self.mock.transport
        d = self.draft(did2)
        idem, digest = d['idem'], d['body_sha256']
        a = self.account()
        self.mock.rotate_key(a['install_secret'])
        a['skill_key_bound'] = False
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'account.json'), 'w') as f:
            json.dump(a, f)
        jobs = len(self.job_posts())
        code, s, _, _ = self.run_cmd('resume', '--draft', did2)
        self.assertEqual(s['signal'], 'delivered', s)
        self.assertEqual(len(self.job_posts()), jobs)  # 0 次新生成
        d = self.draft(did2)
        self.assertEqual((d['idem'], d['body_sha256']), (idem, digest))
        gets = [c for c in self.mock.calls if c[0] == 'GET' and '/jobs/by-key/' in c[1]]
        self.assertTrue(gets and all(idem in c[1] or studio.quote(idem, safe='') in c[1] for c in gets))
        self.assertIs(self.account()['skill_key_bound'], True)

    def test_trv01_r1_non401_bound_failure_keeps_key_no_generation(self):
        """false/缺字段/网络错误等非 401：凭证保留但不得新生成（原 TRV-01 反例不回退）。"""
        for mode in ('false', 'missing', 'timeout', 500):
            a0, old = self._rotated_setup(False)
            # 换回一把有效但未确认的凭证，单独测非 401 情形
            a = self.account()
            self.mock.users[a['install_secret']]['key'] = old
            self.mock.keys[old] = a['install_secret']
            self.mock.scenario['bound'] = mode
            did2 = self.confirmed_draft()
            jobs = len(self.job_posts())
            code, s, _, _ = self.run_cmd('run', '--draft', did2)
            self.assertEqual((code, s['signal']), (3, 'serviceUnavailable'), mode)
            self.assertEqual(self.account().get('skill_key'), old, mode)
            self.assertIs(self.account().get('skill_key_bound'), False, mode)
            self.assertEqual(len(self.job_posts()), jobs, mode)
            self.mock.scenario.pop('bound')

    # ---- A3-TRV-02：损坏参考图本地拒绝、点名文件、零业务请求 ----

    def _bad_inputs(self):
        import struct
        import zlib
        png = mock_backend.make_png(256, 300)
        i = png.index(b'IDAT')
        n = struct.unpack('>I', png[i - 4:i])[0]
        body = png[i + 4:i + 4 + n]

        def with_idat(new):
            return (png[:i - 4] + struct.pack('>I', len(new)) + b'IDAT' + new
                    + struct.pack('>I', zlib.crc32(b'IDAT' + new) & 0xffffffff) + png[i + 8 + n:])
        jpg = jpeg_bytes(256, 300)
        sos = jpg.index(b'\xff\xda')
        return {
            'png-bad-crc.png': png[:i + 6] + bytes([png[i + 6] ^ 0x55]) + png[i + 7:],
            'png-zlib-cut.png': with_idat(body[:len(body) // 2]),
            'png-zlib-garbage.png': with_idat(body[:2] + b'\xff' * (len(body) - 2)),
            'png-no-iend.png': png[:-12],
            'png-truncated.png': png[:len(png) - 30],
            'png-short-rows.png': with_idat(zlib.compress(b'\x00' * 100)),
            'jpg-sof-only.jpg': jpg[:sos],
            'jpg-sof-eoi.jpg': jpg[:sos] + b'\xff\xd9',
            'jpg-scan-cut.jpg': jpg[:sos + 14 + (len(jpg) - sos - 16) // 2],
            'jpg-scan-cut-eoi.jpg': jpg[:sos + 14 + (len(jpg) - sos - 16) // 2] + b'\xff\xd9',
            'jpg-no-dht.jpg': jpg.replace(b'\xff\xc4', b'\xff\xfe', 1),
            # 1.0.2（A3-TRV-02-R1）：小 IHDR + 可展开 32MiB 的高压缩流，须有界拒绝
            'png-inflate-bomb.png': _bomb_png(32),
        }

    def test_trv02_damaged_inputs_rejected_before_any_request(self):
        for name, data in self._bad_inputs().items():
            self.fresh()
            p = os.path.join(self.photos, name)
            with open(p, 'wb') as f:
                f.write(data)
            _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '想拍汉服广袖流仙写真', '--image', p)
            code, s, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'flowing')
            self.assertEqual((code, s['signal'], s.get('problem')), (3, 'photoInvalid', 'damaged'), name)
            self.assertIn(name, t)
            self.assertEqual(self.mock.calls, [], name)  # 业务 HTTP 为 0

    def test_trv02_damaged_after_confirm_no_post(self):
        for name, data in self._bad_inputs().items():
            self.fresh()
            did = self.ready()
            with open(self.photo, 'wb') as f:
                f.write(data)  # 确认后同一路径被换成损坏文件
            n = len(self.mock.calls)
            code, s, t, _ = self.run_cmd('run', '--draft', did)
            self.assertEqual(code, 3, name)
            self.assertEqual(s['signal'], 'photoInvalid', name)
            self.assertIn('me.jpg', t)
            self.assertEqual(self.job_posts(), [], name)
            self.assertFalse([c for c in self.mock.calls[n:] if c[1] == '/skill-jobs'], name)
            with open(self.photo, 'wb') as f:
                f.write(self.photo_bytes)

    def test_trv02_valid_png_and_jpeg_still_pass(self):
        import audit_images
        cases = {'ok.png': mock_backend.make_png(256, 300), 'ok.jpg': jpeg_bytes(257, 301),
                 'ok-note.jpg': jpeg_bytes(640, 800, b'synthetic')}
        for name, data in cases.items():
            p = os.path.join(self.photos, name)
            with open(p, 'wb') as f:
                f.write(data)
            r = audit_images.check(p)
            self.assertTrue(r['ok'], (name, r))
            _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', p)
            code, s, _, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'daily')
            self.assertEqual((code, s['signal']), (0, 'planReady'), name)

    # ---- A3-TRV-03：首次对话上报同安装只尝试一次，失败后任何命令都不重报 ----

    def _fail_modes(self):
        def boom(*a):
            raise OSError('down')

        def timeout(*a):
            raise TimeoutError('slow')
        return {'exception': boom, 'timeout': timeout, 'non200': lambda *a: (503, b''),
                '204': lambda *a: (204, b''), 'badjson': lambda *a: (200, b'{oops'),
                'badreceipt': lambda *a: (200, json.dumps({'event_id': 'x', 'receipt': 'y'}).encode())}

    def test_trv03_failed_first_report_never_resent(self):
        for mode, fn in self._fail_modes().items():
            self.fresh()
            calls = []

            def t(*a, _fn=fn):
                calls.append(a)
                return _fn(*a)
            telemetry.TRANSPORT = t
            _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '想做哈尔滨写真', '--image', self.photo)
            did = s['draft_id']
            for argv in (['demo'], ['plan', '--draft', did, '--scene', 'daily'], ['confirm', '--draft', did, '--pay-consent', 'yes'],
                         ['run', '--draft', did], ['resume', '--draft', did], ['status'], ['balance'], ['history'],
                         ['first-turn', '--defer-entry', '--text', '你好']):
                self.run_cmd(*argv)
            self.assertEqual(len(calls), 1, mode)
            with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'first-dialogue.json')) as f:
                st = json.load(f)
            self.assertEqual((st.get('attempted'), st.get('sent')), (True, False), mode)
            self.assertEqual(telemetry.report_once(os.path.join(self.home, 'mps-hanfu-portrait-studio')), 'already')
            self.assertEqual(len(calls), 1, mode)

    def test_trv03_nested_resume_run_reports_once(self):
        os.environ['MPS_HANFU_PORTRAIT_JOURNEY'] = 'off'
        did = self.confirmed_draft()  # 关闭开关下建草稿：不产生上报状态
        self.assertFalse(os.path.exists(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'first-dialogue.json')))
        os.environ.pop('MPS_HANFU_PORTRAIT_JOURNEY')
        for mode, fn in self._fail_modes().items():
            p = os.path.join(self.home, 'mps-hanfu-portrait-studio', 'first-dialogue.json')
            if os.path.exists(p):
                os.remove(p)
            calls = []

            def t(*a, _fn=fn):
                calls.append(a)
                return _fn(*a)
            telemetry.TRANSPORT = t
            self.run_cmd('resume', '--draft', did)  # resume 内部会转入 run，两处入口共只尝试一次
            self.run_cmd('resume', '--draft', did)
            self.assertEqual(len(calls), 1, mode)

    def test_trv03_attempt_not_persisted_means_not_sent(self):
        real_save = telemetry._save
        calls = []
        telemetry.TRANSPORT = lambda *a: calls.append(a) or (200, b'')

        def save(path, d):
            if d.get('attempted'):
                return False  # 「已尝试」写不进去
            return real_save(path, d)
        telemetry._save = save
        try:
            d = os.path.join(self.tmp, 'tel')
            os.makedirs(d)
            self.assertEqual(telemetry.report_once(d), 'skipped')
            self.assertEqual(telemetry.report_once(d), 'skipped')
        finally:
            telemetry._save = real_save
        self.assertEqual(calls, [])

    def test_trv03_success_then_link_unchanged(self):
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        with open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'first-dialogue.json')) as f:
            st = json.load(f)
        self.assertTrue(st['sent'] and st['attempted'] and st['receipt'])
        did = self.ready()
        self.run_cmd('run', '--draft', did)
        self.assertEqual(len(self.mock.telemetry_calls), 1)
        self.assertTrue(self.mock.link_calls)

class RepairHnf100(Base):
    """汉服 1.0.0 A3 退回四项（HNF-A3-01..04）的回归：形制 + 自定义服饰叠加、否定越界词放行、反馈未知不自动重跑、侠客示例说明。"""

    SIX = {'prompt', 'size', 'confirmed', 'image_engine', 'references', 'reference_consent'}

    def _plan(self, scene, form, outfit, did=None):
        if did is None:
            _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '想拍汉服写真', '--image', self.photo, '--has-need')
            did = s['draft_id']
        args = ['plan', '--draft', did, '--scene', scene, '--outfit', outfit]
        if form:
            args += ['--form', form]
        return did, self.run_cmd(*args)

    def test_hnf01_form_kept_with_custom_outfit_all_combos(self):
        """HNF-A3-01：daily 唐/明（及宋）、garden 唐/明/曲裾（及宋）与非空 outfit 组合：形制结构、配套妆发和颜色细节
        同时进入方案摘要、开工复述和 prompt；非宋形制不再带默认宋风说明；请求体仍恰六字段。"""
        combos = [('daily', 'tang'), ('daily', 'ming'), ('daily', 'song'),
                  ('garden', 'tang'), ('garden', 'ming'), ('garden', 'quju'), ('garden', 'song')]
        first = True
        for scene, form in combos:
            outfit = '素蓝色' if scene == 'daily' else '深青色'
            did, (code, s, t, _) = self._plan(scene, form, outfit)
            self.assertEqual((code, s['signal']), (0, 'planReady'), (scene, form, t))
            structure = studio.FORMS[form][1][scene]
            self.assertIn('服饰与妆造：' + structure + '；颜色与细节：' + outfit, t, (scene, form))
            self.run_cmd('confirm', '--draft', did, '--pay-consent', 'yes')
            if first:
                self.paid_account(did, 20)
                first = False
            code, s, t, err = self.run_cmd('run', '--draft', did)
            self.assertEqual(s['signal'], 'delivered', (scene, form, t))
            self.assertIn('服饰与妆造：' + structure + '；颜色与细节：' + outfit, err, (scene, form))
            job = [c for c in self.mock.calls if c[1].endswith('/skill-jobs')][-1][2]
            self.assertEqual(set(job), self.SIX)
            p = job['prompt']
            for must in (structure, outfit, '只叠加在上述形制结构上', studio.FORM_MAKEUP[form],
                         '服饰整套采用' + studio.FORMS[form][0], '不混搭其他朝代'):
                self.assertIn(must, p, (scene, form, must))
            if form != 'song':
                self.assertNotIn('宋', p, (scene, form))
            self.assertNotIn('默认推荐', p)

    def test_hnf01_conflicting_outfit_disambiguates_not_dropped(self):
        """HNF-A3-01：补充服饰与选定形制（或主题自带形制）冲突 → outfitFormConflict 先消歧，不进入方案、不联网、不丢形制。"""
        for scene, form, outfit, clash in (('daily', 'ming', '唐风齐胸', ['tang']), ('garden', 'quju', '明制马面裙', ['ming']),
                                           ('daily', None, '明制马面', ['ming']), ('tang_ruqun', None, '宋制褙子', ['song']),
                                           ('swordsman', None, '明制', ['ming'])):
            before = len(self.mock.calls)
            did, (code, s, t, _) = self._plan(scene, form, outfit)
            self.assertEqual((code, s['signal'], s['conflict']), (2, 'outfitFormConflict', clash), (scene, form, outfit))
            self.assertIn('不同朝代的衣服不混在一起穿', t)
            self.assertIn('没有产生任何扣费', t)
            self.assertEqual(len(self.mock.calls), before)
            d = studio.load_draft(did)
            self.assertNotEqual(d.get('state'), 'planned')
            code, s, _, _ = self.run_cmd('run', '--draft', did)
            self.assertNotEqual(s['signal'], 'delivered')
            self.assertFalse([c for c in self.mock.calls[before:] if c[1].endswith('/skill-jobs')])
        # 被否定的形制词不算冲突；同形制的补充词也不算
        for scene, form, outfit in (('daily', 'ming', '不要齐胸，素蓝色'), ('garden', 'tang', '齐胸，杏色'), ('daily', None, '宋风浅绿')):
            self.assertEqual(self._plan(scene, form, outfit)[1][1]['signal'], 'planReady', (scene, form, outfit))

    def test_hnf02_negated_boundary_words_not_refused(self):
        """HNF-A3-02：否定/排除的婚服、和服、儿童等词 + 合法汉服 → 放行按主需求；明确要婚服等仍提示越界。"""
        cases = (('不要婚服，我要新年宋制汉服', 'daily', None),
                 ('不要和服，想拍明制马面裙', 'ming_mamian', None),
                 ('不是给孩子拍，是我自己想拍唐制齐胸', 'tang_ruqun', None),
                 ('婚服就不要了，园林里拍一张', 'garden', None),
                 ('不要旗袍也不要和服，拍个宋制褙子', 'song_beizi', None),
                 ('别拍成和服那样，要曲裾', 'quju', None),
                 ('不要婚服', None, 'clarify_main_need'),
                 ('想拍婚服', None, 'out_of_scope_wedding'),
                 ('我要凤冠霞帔的婚服写真', None, 'out_of_scope_wedding'),
                 ('想穿和服拍，不要宋制', None, 'out_of_scope_outfit'),
                 ('特别想拍婚服', None, 'out_of_scope_wedding'),
                 ('非常想穿和服', None, 'out_of_scope_outfit'),
                 ('带孩子一起拍汉服', None, 'out_of_scope_child'),
                 ('我和女儿一起拍', None, 'out_of_scope_child'))
        studio.TRANSPORT = lambda *a, **k: (_ for _ in ()).throw(AssertionError('net'))
        for text, scene, intent in cases:
            code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', text)
            self.assertEqual((code, s['suggested_scene'], s['intent']), (0, scene, intent), text)
        self.assertEqual(self.mock.calls, [])
        doc = open(os.path.join(PKG, 'references', 'scenes.md'), encoding='utf-8').read()
        for must in ('clarify_main_need', '被否定或排除的词不作拒绝依据', '不按单个词硬拒'):
            self.assertIn(must, doc)
        skill = open(os.path.join(PKG, 'SKILL.md'), encoding='utf-8').read()
        self.assertIn('用户否定的词（「不要婚服」）不作拒绝依据', skill)

    def test_hnf03_feedback_unknown_waits_for_explicit_user(self):
        """HNF-A3-03：反馈应答丢失（无编号）→ 原键原体保留、auto_retry=false、退出码 2；脚本自己不补交；
        只有用户明确「提交反馈」（--retry）才同键同体再交一次；有编号后只 ticket GET，不再 POST。"""
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        self.assertEqual(self.run_cmd('run', '--draft', did)[1]['signal'], 'delivered')
        jobs_before = len([c for c in self.mock.calls if c[1].endswith('/skill-jobs')])
        self.mock.scenario['ticket_lost_once'] = True
        code, s, t, _ = self.run_cmd('feedback', '--category', 'image_quality', '--text', '袖口颜色有点偏', '--draft', did)
        self.assertEqual((code, s['signal'], s['pending'], s['auto_retry']), (2, 'feedbackSaved', 1, False))
        self.assertIn('说「提交反馈」', t)
        posts = [c for c in self.mock.calls if c[1] == '/support-tickets']
        self.assertEqual(len(posts), 1)
        st = json.load(open(os.path.join(self.home, 'mps-hanfu-portrait-studio', 'support', 'state.json'), encoding='utf-8'))
        key, body = st['pending'][0]['key'], st['pending'][0]['body']
        # 其他命令（查余额、续查原任务）不会顺带补交反馈
        self.run_cmd('balance')
        self.run_cmd('resume', '--draft', did)
        self.assertEqual(len([c for c in self.mock.calls if c[1] == '/support-tickets']), 1)
        # 用户明确「提交反馈」：同键同体
        code, s, t, _ = self.run_cmd('feedback', '--retry')
        self.assertEqual((s['signal'], s['auto_retry']), ('ticketCreated', False))
        posts = [c for c in self.mock.calls if c[1] == '/support-tickets']
        self.assertEqual(len(posts), 2)
        self.assertEqual({p[3]['Idempotency-Key'] for p in posts}, {key})
        self.assertEqual(posts[1][2], body)
        self.assertEqual(len(self.mock.tickets), 1)
        tid = s['ticket_ids'][0]
        code, s, t, _ = self.run_cmd('ticket', '--id', tid)
        self.assertEqual(len([c for c in self.mock.calls if c[1] == '/support-tickets']), 2)
        self.assertTrue([c for c in self.mock.calls if c[0] == 'GET' and c[1] == '/support-tickets/' + tid])
        self.assertEqual(self.run_cmd('feedback', '--retry')[1]['signal'], 'feedbackNone')
        # 售后全程不重新提交生图
        self.assertEqual(len([c for c in self.mock.calls if c[1].endswith('/skill-jobs')]), jobs_before)

    def test_hnf03_skill_rerun_rule_excludes_feedback(self):
        """HNF-A3-03 静态执行规范：接管规则的泛化重跑明确排除 feedback（任务只查原任务）；反馈未知等用户明确说才 --retry；SKILL ≤ 15KiB。"""
        raw = open(os.path.join(PKG, 'SKILL.md'), 'rb').read()
        self.assertLessEqual(len(raw), 15 * 1024)
        skill = raw.decode('utf-8')
        self.assertNotIn('把同一条命令重跑一次（未确认的任务只会查询原任务）', skill)
        rule = next(l for l in skill.splitlines() if '没拿到结果时如实说' in l)
        self.assertIn('`feedback` 除外，不自动重跑', rule)
        self.assertIn('任务只查原任务', rule)
        fb = next(l for l in skill.splitlines() if l.startswith('- 反馈：'))
        for must in ('等用户明确说「提交反馈」才 `feedback --retry`', '不自动补交', '有编号只用 `ticket` 查'):
            self.assertIn(must, fb)
        self.assertNotIn('「提交反馈」→ `feedback --retry`', skill)

    def test_hnf04_swordsman_note_matches_image(self):
        """HNF-A3-04：侠客示例说明写实际可见的木质影棚，不写不存在的竹林；只改说明，图片原字节不变。"""
        demos = {d['key']: d for d in json.load(open(os.path.join(PKG, 'assets', 'demos.json'), encoding='utf-8'))['demos']}
        note = demos['swordsman']['note']
        self.assertNotIn('竹林', note)
        self.assertIn('木质影棚', note)
        self.assertIn('AI 生成汉服写真，非实拍', note)
        prov = json.load(open(os.path.join(PKG, '..', '..', 'demo-assets', 'provenance.json'), encoding='utf-8')) \
            if os.path.exists(os.path.join(PKG, '..', '..', 'demo-assets', 'provenance.json')) else None
        digest = hashlib.sha256(open(os.path.join(PKG, 'assets', 'swordsman.png'), 'rb').read()).hexdigest()
        if prov is not None:
            derivation = json.load(open(os.path.join(HERE, 'demos-derivation.json'), encoding='utf-8'))
            row = next(x for x in derivation['items'] if x['key'] == 'swordsman')
            self.assertEqual(digest, row['package_sha256'])
            self.assertIn(row['source_sha256'], json.dumps(prov))


if __name__ == '__main__':
    unittest.main(verbosity=1)
