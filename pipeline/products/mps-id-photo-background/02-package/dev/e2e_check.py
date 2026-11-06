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
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, 'home')
        os.makedirs(self.home)
        self.env = dict(os.environ)
        os.environ['HOME'] = self.home
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
        with open(os.path.join(self.home, '.mps-id-photo-background', 'account.json')) as f:
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
        d = json.load(open(os.path.join(self.home, '.mps-id-photo-background', 'drafts', did + '.json')))
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
        d = json.load(open(os.path.join(self.home, '.mps-id-photo-background', 'drafts', did + '.json')))
        a = json.load(open(os.path.join(self.home, '.mps-id-photo-background', 'account.json')))
        body, _ = idphoto._job_body(d)
        r = idphoto.call('POST', '/skill-jobs', body, auth=a['skill_key'], idem=d['idem'])
        self.assertTrue(r['replayed'])
        self.assertEqual(self.mock.charges, 1)

    def test_skill_key_expired_reset_exit4(self):
        did = self.confirmed_draft()
        self.paid_account(did, 3)
        self.run_cmd('run', '--draft', did)  # 取得 Skill 凭证
        acc = os.path.join(self.home, '.mps-id-photo-background', 'account.json')
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
        a = json.load(open(os.path.join(self.home, '.mps-id-photo-background', 'account.json')))
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
        st = json.load(open(os.path.join(self.home, '.mps-id-photo-background', 'first-dialogue.json')))
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
        d = os.path.join(self.home, '.mps-id-photo-background')
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'first-dialogue.json'), 'w').write('garbage')
        self.run_cmd('first-turn', '--defer-entry', '--text', '你好')
        self.assertEqual(len(self.mock.telemetry_calls), 1)
        os.remove(os.path.join(d, 'first-dialogue.json'))
        if os.geteuid() != 0:
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
        for argv in (['demo'], ['status'], ['balance'], ['first-turn', '--text', 'x']):
            shutil.rmtree(os.path.join(self.home, '.mps-id-photo-background'), ignore_errors=True)
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
