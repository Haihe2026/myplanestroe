"""端到端检查：真实客户端代码 + 进程内模拟后端。合成账户，真实上游调用 0。

运行：python3 dev/e2e_check.py   （可加 --package <解压后的技能目录> 对干净解压的 ZIP 重跑）
"""
import contextlib
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, '..', 'mps-travel-portrait-studio')
if '--package' in sys.argv:
    i = sys.argv.index('--package')
    PKG = os.path.abspath(sys.argv[i + 1])
    del sys.argv[i:i + 2]
ZIPS = []
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


def jpeg_bytes(w=600, h=800):
    # 最小合法 JPEG 头（SOF0 含尺寸），足够本地与模拟后端校验
    return (b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xc0\x00\x11\x08' + h.to_bytes(2, 'big') + w.to_bytes(2, 'big') + b'\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01'
            b'\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00' + b'\x00' * 64 + b'\xff\xd9')


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=os.environ.get('MPS_E2E_TMP'))  # 可指定可写目录
        self.home = os.path.join(self.tmp, 'home')
        os.makedirs(self.home)
        self.env = dict(os.environ)
        os.environ['HOME'] = self.home
        studio.STATE_HOME = self.home  # 不依赖 HOME/USERPROFILE，Windows 同样隔离
        os.environ['MPS_TRAVEL_PORTRAIT_TEST'] = '1'
        os.environ.pop('MPS_TRAVEL_PORTRAIT_JOURNEY', None)
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
        shutil.rmtree(self.tmp)

    def run_cmd(self, *argv):
        argv = list(argv)
        if argv and argv[0] == 'plan':
            # 旅行写真 plan 必填项：未显式给出时按合规的本人单人照补齐（专项用例会显式覆盖）
            if '--subject' not in argv:
                argv += ['--subject', 'self']
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

    def confirmed_draft(self, scene='harbin', shape=None, features=None):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '想做旅行写真', '--image', self.photo, '--has-need')
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
        with open(os.path.join(self.home, 'mps-travel-portrait-studio', 'account.json')) as f:
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
        code, s, t, _ = self.run_cmd('demo', 'santorini')
        self.assertEqual(len(s['items']), 1)
        p = s['items'][0]['path']
        self.assertTrue(os.path.isabs(p) and os.path.isfile(p))
        w, h = png_local.size_of(open(p, 'rb').read())
        self.assertLess(w, h)  # 旅行示例均为竖版 2:3
        self.assertIn('AI 生成旅行主题写真，非实地拍摄', s['items'][0]['note'])
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
        acc = os.path.join(self.home, 'mps-travel-portrait-studio', 'account.json')
        try:
            return self.run_cmd('demo', *argv)
        finally:
            studio.HERE, studio.TRANSPORT, telemetry.TRANSPORT = real_here, real_t, real_tt
            self.assertFalse(os.path.exists(acc))  # 零凭证访问

    def _out(self):
        d = os.path.join(self.home, 'mps-travel-portrait-studio', 'demos')
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def test_fam03_default_missing_one_exit3(self):
        pkg = self._pkg_copy()
        os.remove(os.path.join(pkg, 'assets', 'kyoto.png'))
        self.assertEqual(len(json.load(open(os.path.join(pkg, 'assets', 'demos.json'), encoding='utf-8'))['demos']), 10)
        code, s, t, _ = self._demo_in(pkg)
        self.assertEqual((code, s['signal']), (3, 'demoUnavailable'))
        self.assertNotIn('items', s)
        self.assertEqual(s.get('missing'), ['kyoto'])
        self.assertIn('这次暂时没能展示示例图', t)
        self.assertEqual(self._out(), [])  # 输出前校验：一张都不复制
        code, s, _, _ = self._demo_in(pkg, 'kyoto')  # 单项指定缺失图
        self.assertEqual((code, s['signal']), (3, 'demoUnavailable'))
        code, s, _, _ = self._demo_in(pkg, 'santorini')  # 单项指定存在图
        self.assertEqual((code, len(s['items'])), (0, 1))
        shutil.copyfile(os.path.join(PKG, 'assets', 'kyoto.png'), os.path.join(pkg, 'assets', 'kyoto.png'))  # 补齐
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
            code, s, _, _ = self._demo_in(pkg, 'santorini')
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
        self.run_cmd('plan', '--draft', did, '--scene', 'harbin')
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (3, 'needsConfirmation'))
        for photo, pay in (('no', 'yes'), ('yes', 'no'), ('', '')):
            code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--owner-consent', photo, '--pay-consent', pay)
            self.assertEqual(s['signal'], 'needsConfirmation')
        self.assertEqual(self.mock.calls, [])

    def test_plan_copy(self):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        code, s, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'sanya', '--subject', 'guardian',
                                     '--features', '短发戴眼镜', '--outfit', '浅蓝色连衣裙')
        self.assertIn('确认开始', t)
        self.assertIn('按张计费', t)
        self.assertIn('发送去处理', t)
        self.assertIn('监护人', t)
        self.assertIn('AI 生成旅行主题写真，非实地拍摄', t)
        self.assertIn('我会按你确认的样子保留人物：短发戴眼镜', t)
        self.assertIn('「三亚海岛暖冬」旅行主题写真，单人，服装：浅蓝色连衣裙，竖版 2:3，1 张', t)
        for bad in ('¥', '元', '提示词', '模板'):
            self.assertNotIn(bad, t)

    def test_bad_photo_named_no_network(self):
        bad = os.path.join(self.photos, 'broken.png')
        open(bad, 'wb').write(b'not an image')
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', bad)
        code, s, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'harbin')
        self.assertEqual((code, s['signal']), (3, 'photoInvalid'))
        self.assertIn('broken.png', t)
        self.assertEqual(self.mock.calls, [])

    def test_shape_defaults_and_people_range(self):
        did = self.confirmed_draft()
        d = json.load(open(os.path.join(self.home, 'mps-travel-portrait-studio', 'drafts', did + '.json')))
        self.assertEqual((d['size'], d['subject']), ('1024x1536', 'self'))
        did = self.confirmed_draft(scene='santorini', shape='landscape')
        d = json.load(open(os.path.join(self.home, 'mps-travel-portrait-studio', 'drafts', did + '.json')))
        self.assertEqual(d['size'], '1536x1024')
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        code, s2, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'kyoto', '--single', 'no')
        self.assertEqual((code, s2['signal']), (3, 'peopleUnsupported'))
        for must in ('只做单人照', '全家福写真照相馆', '没有产生任何扣费'):
            self.assertIn(must, t)
        code, s2, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'kyoto', '--face-clear', 'no')
        self.assertEqual((code, s2['signal']), (2, 'needsClearerPhoto'))
        self.assertIn('没有产生任何扣费', t)
        self.assertEqual(self.mock.calls, [])

    def test_refuse_copy(self):
        code, s, t, _ = self.run_cmd('refuse')
        self.assertEqual((code, s['signal']), (0, 'refused'))
        for must in ('监护人', '不换脸', '名人或他人', '合成到一起', '到访凭证'):
            self.assertIn(must, t)
        self.assertEqual(self.mock.calls, [])


class AccountBilling(Base):
    def test_full_flow_auth_topup_deliver(self):
        did = self.confirmed_draft(scene='sanya', features='短发戴眼镜')
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
        self.assertTrue(s['paths'][0].endswith('me-sanya.png'))
        self.assertIn('「三亚海岛暖冬」', t)
        self.assertIn('AI 生成旅行主题写真，非实地拍摄', t)
        self.assertNotIn('实际出图尺寸', t)
        gallery = open(s['gallery'], encoding='utf-8').read()
        self.assertIn('AI 生成旅行主题写真，非实地拍摄', gallery)
        job = [c for c in self.mock.calls if c[1].endswith('/skill-jobs')][-1][2]
        self.assertEqual(job['size'], '1024x1536')
        for must in ('恰好 1 位人物', '短发戴眼镜', '三亚海岛暖冬', '不换脸'):
            self.assertIn(must, job['prompt'])
        for bad in ('28', '东亚', '女性'):
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
        d = json.load(open(os.path.join(self.home, 'mps-travel-portrait-studio', 'drafts', did + '.json')))
        a = json.load(open(os.path.join(self.home, 'mps-travel-portrait-studio', 'account.json')))
        body, _ = studio._job_body(d)
        r = studio.call('POST', '/skill-jobs', body, auth=a['skill_key'], idem=d['idem'])
        self.assertTrue(r['replayed'])
        self.assertEqual(self.mock.charges, 1)

    def test_skill_key_expired_reset_exit4(self):
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        self.run_cmd('run', '--draft', did)  # 取得 Skill 凭证
        acc = os.path.join(self.home, 'mps-travel-portrait-studio', 'account.json')
        self.assertEqual(stat.S_IMODE(os.stat(acc).st_mode), 0o600)
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
        a = json.load(open(os.path.join(self.home, 'mps-travel-portrait-studio', 'account.json')))
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
        self.assertEqual((body['skill_id'], body['channel'], body['is_test']), ('mps-travel-portrait-studio', 'workbuddy_skill', True))
        self.assertTrue(telemetry.is_uuid4(body['installation_id']) and telemetry.is_uuid4(body['event_id']))

    def test_off_switch(self):
        os.environ['MPS_TRAVEL_PORTRAIT_JOURNEY'] = 'off'
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(self.mock.telemetry_calls, [])

    def test_failure_does_not_block_and_no_retry_loop(self):
        for status in (204, 503, 400):
            self.mock.telemetry_status = status
            code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
            self.assertEqual(code, 0)
        st = json.load(open(os.path.join(self.home, 'mps-travel-portrait-studio', 'first-dialogue.json')))
        self.assertFalse(st['sent'])  # 204 不算成功
        ids = {c[0]['installation_id'] for c in self.mock.telemetry_calls}
        self.assertEqual(len(ids), 1)  # 沿原标识
        self.mock.telemetry_status = None
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(len(self.mock.telemetry_calls), 4)

    def test_transport_exception_swallowed(self):
        def boom(*a):
            raise OSError('down')
        telemetry.TRANSPORT = boom
        code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(code, 0)

    def test_corrupt_identity_repaired_and_readonly_skipped(self):
        d = os.path.join(self.home, 'mps-travel-portrait-studio')
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
            shutil.rmtree(os.path.join(self.home, 'mps-travel-portrait-studio'), ignore_errors=True)
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
        for argv in (['demo'], ['demo', 'santorini']):
            code, s, _, _ = self.run_cmd(*argv)
            self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.home, 'mps-travel-portrait-studio', 'first-dialogue.json')))
        # 首次真实对话仍上报一次
        telemetry.TRANSPORT = self.mock.telemetry_transport
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.run_cmd('demo')
        self.assertEqual(len(self.mock.telemetry_calls), 1)

    def test_wed_a3_02_photo_replaced_after_confirm(self):
        did = self.confirmed_draft()
        draft_file = os.path.join(self.home, 'mps-travel-portrait-studio', 'drafts', did + '.json')
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
        self.run_cmd('plan', '--draft', did, '--scene', 'harbin')
        self.run_cmd('confirm', '--draft', did, '--owner-consent', 'yes', '--pay-consent', 'yes')
        new_idem = json.load(open(draft_file))['idem']
        self.assertNotEqual(new_idem, old_idem)
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(self.mock.charges, 1)

    def test_wed_a3_02_photo_replaced_between_plan_and_confirm(self):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        did = s['draft_id']
        self.run_cmd('plan', '--draft', did, '--scene', 'harbin')
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
                self.assertEqual(os.path.abspath(unquote(path)), os.path.abspath(real).replace('\\', '/'))
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
        self.assertFalse(os.path.exists(os.path.join(self.home, 'mps-travel-portrait-studio', 'account.json')))
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
        self.assertEqual((prov['authorized_limit'], prov['upstream_generation_calls'], prov['succeeded']), (10, 10, 10))
        der = json.load(open(os.path.join(HERE, 'demos-derivation.json'), encoding='utf-8'))
        demos = json.load(open(os.path.join(PKG, 'assets', 'demos.json'), encoding='utf-8'))['demos']
        self.assertEqual(sorted(r['key'] for r in der['items']), sorted(d['key'] for d in demos))
        by_key = {i['key']: i for i in prov['items']}
        for r in der['items']:
            it = by_key[r['key']]
            self.assertTrue(it['fictional_adults'])
            self.assertTrue(r['byte_identical'])
            self.assertEqual(r['package_sha256'], it['output_sha256'], r['key'])  # 规格：原字节复制
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
        p = os.path.join(dist, 'mps-travel-portrait-studio-%s.zip' % ver)
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
            self.assertTrue(all(n.startswith('mps-travel-portrait-studio/') for n in names), zp)
            self.assertFalse([n for n in names if '/assets/demos/' in n], zp)
            self.assertEqual(len([n for n in names if n.startswith('mps-travel-portrait-studio/assets/') and n.endswith('.png')]), 10, zp)

    def test_zip_skill_examples_platform_limits(self):
        """ZIP 内 SKILL.md：examples_zh/examples_en 各 ≤3 且数量一致，version 与脚本一致。"""
        import re, zipfile
        zs = self.zips()
        if not zs:
            self.skipTest('no ZIP for current version yet (pass --zip <file>)')
        for zp in zs:
            with zipfile.ZipFile(zp) as z:
                front = z.read('mps-travel-portrait-studio/SKILL.md').decode('utf-8').split('---', 2)[1]
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
        self.assertFalse(os.path.exists(os.path.join(self.home, 'mps-travel-portrait-studio', 'account.json')))
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
        with open(os.path.join(self.home, 'mps-travel-portrait-studio', 'drafts', did + '.json')) as f:
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
        self.assertEqual(self.run_cmd('plan', '--draft', did, '--scene', 'kyoto')[1]['signal'], 'taskLocked')
        self.assertEqual(self.run_cmd('confirm', '--draft', did, '--owner-consent', 'yes', '--pay-consent', 'yes')[1]['signal'], 'needsPlan')
        self.assertEqual(self.run_cmd('regenerate', '--draft', did, '--pay-consent', 'yes')[1]['signal'], 'taskLocked')
        code, s, t, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual(s['signal'], 'delivered')
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.mock.charges, 1)

    def test_409_and_5xx_query_original_only(self):
        for status in (409, 502, 0):
            shutil.rmtree(os.path.join(self.home, 'mps-travel-portrait-studio'), ignore_errors=True)
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
        self.assertEqual(self.run_cmd('plan', '--draft', did, '--scene', 'kyoto')[1]['signal'], 'taskLocked')
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
            shutil.rmtree(os.path.join(self.home, 'mps-travel-portrait-studio'), ignore_errors=True)
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
            shutil.rmtree(os.path.join(self.home, 'mps-travel-portrait-studio'), ignore_errors=True)
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
        self.assertFalse(os.path.isdir(os.path.join(self.photos, '旅行打卡写真结果')) and
                         os.listdir(os.path.join(self.photos, '旅行打卡写真结果')))
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
            shutil.rmtree(os.path.join(self.home, 'mps-travel-portrait-studio'), ignore_errors=True)  # 每条都是全新用户
            code, s, t, _ = self.run_cmd(cmd)
            self.assertNotIn('http', t, cmd)
            self.assertIn('这一步还没完成', t, cmd)

    def test_guardian_wording_and_three_consents(self):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        did = s['draft_id']
        code, s, t, _ = self.run_cmd('plan', '--draft', did, '--scene', 'xian', '--subject', 'guardian')
        self.assertIn('由你作为监护人提供', t)
        for owner, upload, pay in (('yes', 'no', 'yes'), ('no', 'yes', 'yes'), ('yes', 'yes', 'no')):
            code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--owner-consent', owner, '--upload-consent', upload, '--pay-consent', pay)
            self.assertEqual(s['signal'], 'needsConfirmation')
        self.assertEqual(self.mock.calls, [])


class TravelSpec(Base):
    """旅行规格专项：T01 路由、T12 非实拍标注、T13 微信关联与支付 Mock（只 Mock，不请求真实微信或生产）。"""

    def test_t01_suggested_scene_in_first_turn(self):
        studio.TRANSPORT = lambda *a, **k: (_ for _ in ()).throw(AssertionError('net'))
        for text, want in (('去不了哈尔滨，想用我的单人照做一张冰雪主题写真', 'harbin'), ('想穿和服拍樱花', 'kyoto'),
                           ('只想拍樱花', 'sakura'), ('西安古城夜景', 'xian'), ('古城夜景', 'oldtown'), ('你好', None)):
            code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', text)
            self.assertEqual((code, s['suggested_scene']), (0, want), text)
            self.assertNotIn('http', t)

    def test_t12_demo_items_all_disclosed(self):
        code, s, t, _ = self.run_cmd('demo')
        self.assertEqual(code, 0)
        self.assertEqual([i['key'] for i in s['items']], list(studio.SCENES))
        for i in s['items']:
            self.assertIn('AI 生成旅行主题写真，非实地拍摄', i['note'])
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
            shutil.rmtree(os.path.join(self.home, 'mps-travel-portrait-studio'), ignore_errors=True)
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
        did = self.confirmed_draft(scene='grassland', features='长卷发')
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


if __name__ == '__main__':
    unittest.main(verbosity=1)
