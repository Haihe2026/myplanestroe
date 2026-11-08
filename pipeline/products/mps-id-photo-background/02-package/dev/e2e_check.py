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
PKG = os.path.join(HERE, '..', 'mps-id-photo-background')
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
for m in ('idphoto', 'telemetry', 'welcome_copy', 'png_local', 'audit_images'):
    sys.modules.pop(m, None)
import idphoto  # noqa: E402
import telemetry  # noqa: E402
import png_local  # noqa: E402
import welcome_copy as W  # noqa: E402
sys.path.insert(0, HERE)
import mock_backend  # noqa: E402
mock_backend.idphoto = idphoto  # 与被测包同一模块实例


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
        idphoto.STATE_HOME = self.home  # 不依赖 HOME/USERPROFILE，Windows 同样隔离
        os.environ['MPS_ID_PHOTO_TEST'] = '1'
        os.environ.pop('MPS_ID_PHOTO_JOURNEY', None)
        self.mock = mock_backend.Mock()
        idphoto.TRANSPORT = self.mock.transport
        telemetry.TRANSPORT = self.mock.telemetry_transport
        self._sleep = idphoto.time.sleep
        idphoto.time.sleep = lambda s: None
        self.photos = os.path.join(self.tmp, 'photos')
        os.makedirs(self.photos)
        self.photo = os.path.join(self.photos, 'me.jpg')
        with open(self.photo, 'wb') as f:
            f.write(jpeg_bytes())
        with open(self.photo, 'rb') as f:
            self.photo_bytes = f.read()

    def tearDown(self):
        idphoto.time.sleep = self._sleep
        idphoto.STATE_HOME = None
        os.environ.clear()
        os.environ.update(self.env)
        shutil.rmtree(self.tmp)

    def run_cmd(self, *argv):
        out, errs = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(errs):
            code = idphoto.main(list(argv))
        lines = out.getvalue().split('\n', 1)
        sig = json.loads(lines[0])
        return code, sig, (lines[1] if len(lines) > 1 else ''), errs.getvalue()

    def confirmed_draft(self, target=None, color='white'):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '帮我换白底', '--image', self.photo, '--has-need')
        did = s['draft_id']
        args = ['plan', '--draft', did, '--scene', 'white-one', '--color', color]
        if target:
            args += ['--target', target]
        code, s, _, _ = self.run_cmd(*args)
        self.assertEqual(code, 0, s)
        code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--photo-consent', 'yes', '--pay-consent', 'yes')
        self.assertEqual(code, 0)
        return did

    def secret(self):
        with open(os.path.join(self.home, 'mps-id-photo-background', 'account.json')) as f:
            return json.load(f)['install_secret']

    def paid_account(self, did, balance=5):
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (2, 'onboardingPreview'))
        self.mock.authorize(self.secret(), balance)


class FirstTurn(Base):
    def test_first_turn_zero_business_http(self):
        def boom(*a, **k):
            raise AssertionError('business request in first turn')
        idphoto.TRANSPORT = boom
        for text, img in (('你好', None), ('', self.photo), ('你能做什么', None), ('白底一寸，明天报名', self.photo)):
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
        _, _, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '换白底', '--image', self.photo, '--has-need')
        self.assertIn('这个方向可以吗？', t)

    def test_demo_paths_and_single(self):
        code, s, t, _ = self.run_cmd('demo', 'custom-pixels')
        self.assertEqual(len(s['items']), 1)
        p = s['items'][0]['path']
        self.assertTrue(os.path.isabs(p) and os.path.isfile(p))
        self.assertEqual(png_local.size_of(open(p, 'rb').read()), (295, 413))
        self.assertIn(W.DEMO_INTRO, t)
        code, s, _, _ = self.run_cmd('demo', 'nope')
        self.assertEqual(code, 3)

    def test_demo_links_survive_markdown(self):
        """回归：demo 链接按 Markdown 解析后路径仍存在（含点开头上级目录的家目录）。"""
        import re
        punct = re.escape('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')
        try:
            from markdown_it import MarkdownIt
            md = MarkdownIt()
        except ImportError:
            md = None
        home = os.path.join(self.tmp, '.dot-parent', 'Administrator')
        os.makedirs(home)
        idphoto.STATE_HOME = home
        code, s, _, _ = self.run_cmd('demo')
        self.assertEqual((code, len(s['items'])), (0, 10))
        for it in s['items']:
            p = it['path']
            self.assertNotIn('\\', p)
            self.assertNotIn('/.mps-', p)
            cell = '**[%s](%s)**<br>%s' % (it['title'], p, it['note'])
            target = re.sub(r'\\([' + punct + '])', r'\1', re.search(r'\]\(([^()\s]*)\)', cell).group(1))
            self.assertEqual(target, p)
            if md is not None:
                href = re.search(r'href="([^"]*)"', md.render(cell)).group(1)
                from urllib.parse import unquote
                self.assertEqual(unquote(href), p)
            self.assertTrue(os.path.isfile(target))

    def test_demo_missing_assets_exit3(self):
        real = idphoto.HERE
        idphoto.HERE = os.path.join(self.tmp, 'empty', 'scripts')
        try:
            code, s, t, _ = self.run_cmd('demo')
        finally:
            idphoto.HERE = real
        self.assertEqual((code, s['signal']), (3, 'demoUnavailable'))
        self.assertIn('这次暂时没能展示示例图', t)


class Confirmation(Base):
    def test_no_consent_no_task(self):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        did = s['draft_id']
        self.run_cmd('plan', '--draft', did, '--scene', 'white-one')
        code, s, _, _ = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (3, 'needsConfirmation'))
        for photo, pay in (('no', 'yes'), ('yes', 'no'), ('', '')):
            code, s, _, _ = self.run_cmd('confirm', '--draft', did, '--photo-consent', photo, '--pay-consent', pay)
            self.assertEqual(s['signal'], 'needsConfirmation')
        self.assertEqual(self.mock.calls, [])

    def test_plan_copy(self):
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', self.photo)
        code, s, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'blue-two', '--target', '295x413')
        self.assertIn('确认开始', t)
        self.assertIn('按张计费', t)
        self.assertIn('发送去处理', t)

    def test_bad_photo_named_no_network(self):
        bad = os.path.join(self.photos, 'broken.png')
        open(bad, 'wb').write(b'not an image')
        _, s, _, _ = self.run_cmd('first-turn', '--defer-entry', '--text', 'x', '--image', bad)
        code, s, t, _ = self.run_cmd('plan', '--draft', s['draft_id'], '--scene', 'white-one')
        self.assertEqual((code, s['signal']), (3, 'photoInvalid'))
        self.assertIn('broken.png', t)
        self.assertEqual(self.mock.calls, [])

    def test_target_must_be_given_not_inferred(self):
        did = self.confirmed_draft()
        d = json.load(open(os.path.join(self.home, 'mps-id-photo-background', 'drafts', did + '.json')))
        self.assertIsNone(d['target'])


class AccountBilling(Base):
    def test_full_flow_auth_topup_deliver(self):
        did = self.confirmed_draft(target='295x413')
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
        code, s, t, _ = self.run_cmd('paid')
        self.assertIn('已收到你的付款登记', t)
        self.mock.users[secret]['balance'] = 3
        code, s, t, err = self.run_cmd('run', '--draft', did)
        self.assertEqual((code, s['signal']), (0, 'delivered'), t)
        self.assertEqual(len(s['paths']), 2)
        self.assertTrue(all(os.path.isfile(p) for p in s['paths']))
        self.assertEqual(png_local.size_of(open(s['paths'][1], 'rb').read()), (295, 413))
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
        d = json.load(open(os.path.join(self.home, 'mps-id-photo-background', 'drafts', did + '.json')))
        a = json.load(open(os.path.join(self.home, 'mps-id-photo-background', 'account.json')))
        body, _ = idphoto._job_body(d)
        r = idphoto.call('POST', '/skill-jobs', body, auth=a['skill_key'], idem=d['idem'])
        self.assertTrue(r['replayed'])
        self.assertEqual(self.mock.charges, 1)

    def test_skill_key_expired_reset_exit4(self):
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        self.run_cmd('run', '--draft', did)  # 取得 Skill 凭证
        acc = os.path.join(self.home, 'mps-id-photo-background', 'account.json')
        self.assertEqual(stat.S_IMODE(os.stat(acc).st_mode), 0o600)
        self.mock.keys.clear()
        did2 = self.confirmed_draft()
        code, s, t, _ = self.run_cmd('run', '--draft', did2)
        self.assertEqual((code, s['signal']), (4, 'credentialsReset'))
        self.assertNotIn('skill_key', json.load(open(acc)))
        self.assertEqual(json.load(open(acc))['install_secret'], self.secret())  # 原安装身份保留
        for u in self.mock.users.values():
            u['key'] = None
        code, s, t, _ = self.run_cmd('run', '--draft', did2)
        self.assertEqual(s['signal'], 'delivered')

    def test_client_rejects_unregistered_field(self):
        with self.assertRaises(ValueError):
            idphoto.call('POST', '/skill-jobs', dict(prompt='x', model='other'), auth='x', idem='idp-' + 'a' * 32)

    def test_server_rejects_unregistered_field(self):
        did = self.confirmed_draft()
        self.paid_account(did, 2)
        self.run_cmd('run', '--draft', did)
        a = json.load(open(os.path.join(self.home, 'mps-id-photo-background', 'account.json')))
        with self.assertRaises(idphoto.GatewayError) as cm:
            self.mock.transport('POST', idphoto.ORIGIN + '/platform-api/gemini/skill-jobs', dict(prompt='x', confirmed=True, model='m'),
                                {'X-Skill-Source': idphoto.SKILL_ID, 'X-Skill-Channel': idphoto.CHANNEL, 'Authorization': 'Bearer ' + a['skill_key'],
                                 'Idempotency-Key': 'idp-' + 'b' * 32}, 5, False)
        self.assertEqual(cm.exception.status, 400)

    def test_balance_menu_and_decline(self):
        code, s, t, _ = self.run_cmd('balance')
        self.assertEqual(s['signal'], 'noAccount')
        did = self.confirmed_draft()
        self.paid_account(did, 7)
        code, s, t, _ = self.run_cmd('balance')
        self.assertEqual((s['signal'], s['remaining_uses']), ('balance', 7))
        code, s, t, _ = self.run_cmd('decline')
        self.assertEqual(t.strip(), W.DECLINE)

    def test_untrusted_link_rejected(self):
        with self.assertRaises(idphoto.GatewayError):
            idphoto.trusted_link('https://evil.example/membership/gemini/')
        self.assertTrue(idphoto.trusted_link('https://myplanestore.com/membership/gemini/#ticket=a').startswith('https://aistore.zhaopintong.com/membership/gemini/#ticket=a'))


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
        self.assertEqual(len(polls), idphoto.POLL_ATTEMPTS)
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
        self.assertIn('实际出图尺寸是 1024×1024', t)


class Telemetry(Base):
    def test_fields_once_and_flag(self):
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.run_cmd('demo')
        self.assertEqual(len(self.mock.telemetry_calls), 1)
        body = self.mock.telemetry_calls[0][0]
        self.assertEqual(tuple(body), telemetry.FIELDS)
        self.assertNotIn('machine_id', body)
        self.assertEqual((body['skill_id'], body['channel'], body['is_test']), ('mps-id-photo-background', 'workbuddy_skill', True))
        self.assertTrue(telemetry.is_uuid4(body['installation_id']) and telemetry.is_uuid4(body['event_id']))

    def test_off_switch(self):
        os.environ['MPS_ID_PHOTO_JOURNEY'] = 'off'
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(self.mock.telemetry_calls, [])

    def test_failure_does_not_block_and_no_retry_loop(self):
        for status in (204, 503, 400):
            self.mock.telemetry_status = status
            code, s, t, _ = self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
            self.assertEqual(code, 0)
        st = json.load(open(os.path.join(self.home, 'mps-id-photo-background', 'first-dialogue.json')))
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
        d = os.path.join(self.home, 'mps-id-photo-background')
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
        for argv in (['demo'], ['status'], ['balance'], ['first-turn', '--text', 'x'], ['history'], ['ticket'],
                     ['feedback', '--category', 'other', '--text', 'x']):
            shutil.rmtree(os.path.join(self.home, 'mps-id-photo-background'), ignore_errors=True)
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
        idphoto.HISTORY_PAGE_SIZE = 1
        try:
            code, s, t, _ = self.run_cmd('history', '--page', '1')
            self.assertEqual((s['has_more'], s['next_page']), (True, 2))
            self.assertIn('回复「下一页」', t)
        finally:
            idphoto.HISTORY_PAGE_SIZE = 20

    def test_history_failure_and_no_account(self):
        code, s, t, _ = self.run_cmd('history')
        self.assertEqual(s['signal'], 'noAccount')
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
        a = idphoto.load_account()
        with self.assertRaises(idphoto.GatewayError) as cm:
            self.mock.transport('GET', idphoto.ORIGIN + '/platform-api/gemini/consumption-history', None,
                                {'X-Skill-Source': idphoto.SKILL_ID, 'X-Skill-Channel': idphoto.CHANNEL,
                                 'Authorization': 'Bearer ' + a['skill_key']}, 5, False)
        self.assertEqual(cm.exception.status, 401)
        other = self.other_account()
        st, raw = self.mock.transport('GET', idphoto.ORIGIN + '/platform-api/gemini/consumption-history', None,
                                      {'X-Skill-Source': idphoto.SKILL_ID, 'X-Skill-Channel': idphoto.CHANNEL,
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
            self.assertTrue(it['fictional_adult'])
            with open(os.path.join(src, r['source']), 'rb') as f:
                raw = f.read()
            expect = it['output_sha256'] if r['source'] == it['file'] else it['additional_export']['sha256']
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expect, r['key'])
            with open(os.path.join(PKG, 'assets', r['package_file']), 'rb') as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), r['package_sha256'], r['key'])
        self.assertEqual(png_local.size_of(open(os.path.join(PKG, 'assets', 'custom-pixels.png'), 'rb').read()), (295, 413))


class ZipLayout(unittest.TestCase):
    """平台只支持两级目录：ZIP 内路径以包根为第 0 级，'/' 数不得超过 2。"""

    def zips(self):
        if ZIPS:
            return ZIPS
        dist = os.path.join(HERE, '..', 'dist')
        ver = idphoto.SKILL_VERSION
        p = os.path.join(dist, 'mps-id-photo-background-%s.zip' % ver)
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
            self.assertTrue(all(n.startswith('mps-id-photo-background/') for n in names), zp)
            self.assertFalse([n for n in names if '/assets/demos/' in n], zp)
            self.assertEqual(len([n for n in names if n.startswith('mps-id-photo-background/assets/') and n.endswith('.png')]), 10, zp)

    def test_zip_skill_examples_platform_limits(self):
        """ZIP 内 SKILL.md：examples_zh/examples_en 各 ≤3 且数量一致，version 与脚本一致。"""
        import re, zipfile
        zs = self.zips()
        if not zs:
            self.skipTest('no ZIP for current version yet (pass --zip <file>)')
        for zp in zs:
            with zipfile.ZipFile(zp) as z:
                front = z.read('mps-id-photo-background/SKILL.md').decode('utf-8').split('---', 2)[1]
            def items(key):
                m = re.search(r'^' + key + r':\s*\n((?:\s+-\s+.*\n)+)', front, re.M)
                return re.findall(r'^\s+-\s+(.*)$', m.group(1), re.M) if m else []
            zh, en = items('examples_zh'), items('examples_en')
            self.assertTrue(1 <= len(zh) <= 3, (zp, len(zh)))
            self.assertTrue(len(en) <= 3, (zp, len(en)))
            self.assertEqual(len(zh), len(en), zp)
            self.assertIn('version: %s' % idphoto.SKILL_VERSION, front, zp)
            sys.path.insert(0, os.path.join(PKG, 'tests'))
            import test_skill_contract as C
            strip = lambda xs: [x.strip().strip('"') for x in xs]
            self.assertEqual(C.example_misaligned(strip(zh), strip(en)), [], zp)


class LocalImage(unittest.TestCase):
    def test_crop_resize_exact(self):
        png = mock_backend.make_png(1024, 1536, (10, 20, 30))
        out = png_local.crop_resize(png, 295, 413)
        w, h, rows = png_local.decode(out)
        self.assertEqual((w, h), (295, 413))
        self.assertEqual(rows[100][:3], bytes((10, 20, 30)))

    def test_target_too_large(self):
        with self.assertRaises(ValueError):
            png_local.crop_resize(mock_backend.make_png(100, 150), 200, 300)


if __name__ == '__main__':
    unittest.main(verbosity=1)
