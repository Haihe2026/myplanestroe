"""Credential-file pilot client; never embeds a provider key."""
import argparse
import json
import os
import urllib.parse
import urllib.error
import urllib.request
import uuid
import secrets
import sys
import base64
import hashlib
from pathlib import Path


class UserProblem(Exception):
    pass


def display_points(result):
    value = result.get('balance_points', result.get('balance', 0) * 1000)
    if not isinstance(value, int) or value < 0:
        raise UserProblem('积分余额需要核查。')
    return str(value)


def public_result(result):
    return {k: v for k, v in result.items() if k not in ('token', 'balance')}


def summary(command, result):
    if command == 'health':
        return '服务连接正常。' + ('' if result.get('provider_configured') else '生图暂未开通，本次未扣分。')
    if command == 'balance':
        return '剩余' + display_points(result) + '积分。'
    if command == 'status':
        return '服务连接正常，剩余' + display_points(result) + '积分。' + ('' if result.get('provider_configured') else '\n生图暂未开通，本次未扣分。')
    if result.get('created') and not result.get('granted'):
        reason = '当前网络的免费领取次数已达上限' if result.get('trial_status') == 'network_limit' else '本轮免费名额已满'
        return '账户已创建，' + reason + '，本次未赠送积分；可以选购套餐后继续使用。'
    return ('首次注册已领取' + display_points(result) + '生图积分。' if result.get('granted') else '账户已就绪，剩余' + display_points(result) + '积分。')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def base():
    url = os.environ.get('IMAGE_SERVICE_URL', 'https://myplanestore.com').rstrip('/')
    p = urllib.parse.urlsplit(url)
    local = p.scheme == 'http' and p.hostname == '127.0.0.1' and p.port == 18787
    if not (p.scheme == 'https' or local) or not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in ('', '/'):
        raise UserProblem('服务地址配置有误，请联系管理员。')
    return url


def credential_path():
    value = os.environ.get('IMAGE_CREDENTIAL_FILE', str(Path.home() / '.gemini-image-assistant' / 'credential'))
    return Path(value)


CATALOG = json.loads((Path(__file__).parent.parent / 'references/roles.json').read_text(encoding='utf-8'))
ROLES = {key: value['name'] for key, value in CATALOG['roles'].items()}
ROLES.update(CATALOG['compatibility_roles'])
PLATFORMS = CATALOG['platforms']


def profile_path():
    return credential_path().parent / 'profile.json'


def onboarding(action=None):
    path = credential_path().parent / 'onboarding.json'
    if action:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        value = {'state': 'skipped' if action == 'skip' else action}
        if path.exists():
            path.write_text(json.dumps(value), encoding='utf-8')
        else:
            write_new(path, json.dumps(value))
    elif profile_path().exists():
        value = {'state': 'selected'}
    elif path.exists():
        value = json.loads(path.read_text(encoding='utf-8'))
        if value.get('state') not in ('offered', 'skipped', 'selected'):
            raise UserProblem('引导状态需要管理员检查。')
    else:
        value = {'state': 'first_use'}
    value['show_optional_choice'] = value['state'] == 'first_use'
    return value


def read_profile():
    path = profile_path()
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('role') not in ROLES or value.get('platform') not in PLATFORMS:
        raise UserProblem('岗位偏好需要重新选择。')
    for field, choices in (('roles', ROLES), ('platforms', PLATFORMS)):
        if field in value:
            items = value[field]
            if not isinstance(items, list) or not items or any(not isinstance(x, str) or x not in choices for x in items):
                raise UserProblem('岗位偏好需要重新选择。')
            if value[field[:-1]] != items[0]:
                raise UserProblem('岗位偏好需要重新选择。')
    return value


def menu(kind, industry, page, page_size):
    if kind == 'industry':
        pairs = list(CATALOG['industries'].items())
    elif kind == 'platform':
        pairs = list(PLATFORMS.items())
    elif kind == 'role':
        if industry not in CATALOG['industries']:
            raise UserProblem('请选择行业后再选择岗位。')
        pairs = [(key, value['name']) for key, value in CATALOG['roles'].items() if value['industry'] == industry]
    else:
        raise UserProblem('选择类型无效。')
    pages = (len(pairs) + page_size - 1) // page_size
    if page < 1 or page > pages:
        raise UserProblem('选择页码无效。')
    items = [{'id': key, 'label': label} for key, label in pairs[(page - 1) * page_size:page * page_size]]
    if pages > 1:
        items.append({'id': '__page__', 'label': '下一页' if page < pages else '回到第一页', 'page': page + 1 if page < pages else 1})
    return {'kind': kind, 'page': page, 'pages': pages, 'options': items}


def request(path, payload=None, idem=None, authenticated=True, binary=False):
    headers = {'Content-Type': 'application/json'}
    channel_file = Path(__file__).parent.parent / 'channel.json'
    if channel_file.exists():
        channel = json.loads(channel_file.read_text(encoding='utf-8')).get('channel')
        if channel in ('workbuddy_skill', 'workbuddy_expert', 'skillhub'):
            headers['X-Skill-Channel'] = channel
    device = os.environ.get('IMAGE_CLIENT_DEVICE', 'unknown')
    if device in ('desktop', 'mobile', 'cloud'):
        headers['X-Skill-Device'] = device
    if authenticated:
        headers['Authorization'] = 'Bearer ' + credential_path().read_text(encoding='utf-8').strip()
    if idem:
        headers['Idempotency-Key'] = idem
    req = urllib.request.Request(base() + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=240) as response:
        data = response.read(17 * 1024 * 1024 + 1)
    if len(data) > 17 * 1024 * 1024:
        raise ValueError('响应过大')
    return data if binary else json.loads(data)


def write_new(path, text):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(text)


def account_request(path, payload=None):
    if not credential_path().exists():
        raise UserProblem('请先完成首次使用，再查询原账户额度。')
    try:
        return request(path, payload)
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise
        # Restore the existing identity only; never delete credentials or regrant credits.
        start(True)
        return request(path, payload)


def membership_link():
    result = account_request('/membership-link', {})
    parsed = urllib.parse.urlsplit(result.get('url', ''))
    ticket = urllib.parse.parse_qs(parsed.fragment).get('ticket', [''])[0]
    if (parsed.scheme != 'https' or parsed.netloc != 'myplanestore.com'
            or parsed.path not in ('/membership/', '/membership/gemini/') or parsed.query
            or len(ticket) != 43 or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in ticket)
            or type(result.get('expires_in')) is not int or not 0 < result['expires_in'] <= 300):
        raise UserProblem('会员链接校验失败，请稍后重试，不要打开异常地址。')
    result['url'] = 'https://myplanestore.com/membership/gemini/#ticket=' + ticket
    return result


def membership_info():
    result = purchase_offer()
    if not result['ready']:
        return result['notice']
    return '[开通套餐](' + result['url'] + ')\n扫码付款后人工核款到账。核款后回本技能刷新积分即可继续使用。'


def purchase_offer():
    result = request('/membership-api/plans', authenticated=False)
    if type(result.get('payment_ready')) is not bool:
        raise UserProblem('收款状态需要核查，暂未下单。')
    offer = {'ready': result['payment_ready'], 'mode': 'website_manual',
             'label': '开通套餐', 'notice': '扫码付款后人工核款到账，不自动扣款。' if result['payment_ready'] else '收款暂未开放，已有积分可继续使用。'}
    if offer['ready']:
        offer.update(membership_link())
    return offer


def purchase(confirmed, supported, request_id):
    raise UserProblem('本版由 MyPlaneStore 网页扫码付款、人工核款。请运行 open-membership 获取同账户购买链接。未创建应用内订单。')


def secure_local(path):
    if os.name == 'nt':
        import subprocess
        owner = subprocess.run(['whoami'], capture_output=True, text=True, check=True).stdout.strip()
        result = subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', owner + ':F'],
                                capture_output=True)
        if result.returncode:
            raise UserProblem('无法保护本机试用账户，请检查文件权限。')
    else:
        path.chmod(0o600 if path.is_file() else 0o700)


def start(accepted):
    if not accepted:
        raise UserProblem('首次调用将创建匿名账户并赠送10000积分；请先告知用户使用须知。')
    target = credential_path()
    folder = target.parent
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    secure_local(folder)
    identity_path = folder / 'trial-identity'
    if target.exists():
        secret = target.read_text(encoding='utf-8').strip()
    else:
        if not identity_path.exists():
            try:
                write_new(identity_path, secrets.token_urlsafe(32))
            except FileExistsError:
                pass
        secure_local(identity_path)
        secret = identity_path.read_text(encoding='utf-8').strip()
    result = request('/assistant/register', {'install_secret': secret, 'accepted': True}, authenticated=False)
    token = result.pop('token')
    if token != secret:
        raise UserProblem('试用账户响应异常，请稍后核查。')
    if not target.exists():
        try:
            write_new(target, token)
        except FileExistsError:
            if target.read_text(encoding='utf-8').strip() != token:
                raise UserProblem('本机存在另一试用账户，请核查。')
    secure_local(target)
    return result


def finish(state, fresh_result=None):
    if not state.get('id'):
        if state.get('idem'):
            state.update(request('/jobs/by-key/' + urllib.parse.quote(state['idem'], safe='')))
        else:
            print('请求结果待确认，请保留状态文件核查，暂不要重复生成。')
            return
    jid = str(uuid.UUID(state['id']))
    # Only the current HTTP response can skip a status lookup, never saved state.
    result = fresh_result if (fresh_result and fresh_result.get('id') == jid
                              and fresh_result.get('status') == 'succeeded') else request('/jobs/' + jid)
    if result['status'] != 'succeeded':
        print('图片结果待核查，积分暂占，请勿重复生成。' if result['status'] == 'pending' else '本次生成未成功，已退回积分。')
        return
    target = Path(state['output'])
    if not target.exists():
        image = request('/jobs/' + jid + '/image', binary=True)
        if not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('返回图片格式异常')
        with target.open('xb') as f:
            f.write(image)
    print('图片：' + str(target.resolve()))
    balance = fresh_result if (result is fresh_result
                               and type(result.get('balance_points')) is int
                               and result['balance_points'] >= 0) else account_request('/balance')
    remaining = display_points(balance)
    print('已生成，剩余' + remaining + '积分。')
    if int(remaining) < 1000:
        show_purchase_notice()


def show_purchase_notice():
    try:
        print(membership_info())
    except Exception:
        print('购买入口暂时无法获取。请稍后打开会员中心，已有任务不会重新提交。')


def prepare_references(job):
    job = dict(job)
    if 'references' in job:
        raise UserProblem('请提供本地reference_files，不要在任务文件嵌入图片内容或远程链接。')
    if 'reference_files' not in job:
        return job
    files = job.pop('reference_files')
    if job.get('reference_consent') is not True:
        raise UserProblem('请先确认将商品照片发送至生图服务和算力供应商。')
    if not isinstance(files, list) or not 1 <= len(files) <= 3:
        raise UserProblem('请选择1至3张同一商品的照片。')
    refs, total = [], 0
    for value in files:
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise UserProblem('参考图须为已授权的本地文件绝对路径。')
        path = Path(value)
        if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            raise UserProblem('参考图不存在或超过5MB。')
        with path.open('rb') as stream:
            raw = stream.read(5 * 1024 * 1024 + 1)
        total += len(raw)
        if len(raw) > 5 * 1024 * 1024 or total > 10 * 1024 * 1024:
            raise UserProblem('单图最多5MB，总计最多10MB。')
        mime = 'image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else None
        if not mime:
            raise UserProblem('参考图只支持PNG/JPG，其他格式请先转换。')
        refs.append({'mime':mime, 'content':base64.b64encode(raw).decode('ascii')})
    job['references'] = refs
    return job


def save_private_text(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    secure_local(path.parent)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        write_new(temporary, value)
        secure_local(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_private_json(path, value):
    save_private_text(path, json.dumps(value, ensure_ascii=False))


def auth_path():
    return credential_path().parent / 'phone-authorization.json'


def authorization_start():
    payload = {}
    if credential_path().exists():
        payload['existing_credential'] = credential_path().read_text(encoding='utf-8').strip()
    result = request('/phone-auth/create', payload, authenticated=False)
    if result.get('ready') is not True:
        print('手机号验证暂未开放，已有账户可继续使用。')
        return
    parsed = urllib.parse.urlsplit(result.get('url', ''))
    ticket = urllib.parse.parse_qs(parsed.fragment).get('ticket', [''])[0]
    if (parsed.scheme != 'https' or parsed.netloc != 'myplanestore.com' or parsed.path != '/auth/' or parsed.query
            or len(ticket) != 43 or len(result.get('poll_secret', '')) != 43
            or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in ticket)):
        raise UserProblem('授权链接校验失败，请稍后重试。')
    uuid.UUID(result['id'])
    save_private_json(auth_path(), {'id': result['id'], 'poll_secret': result['poll_secret']})
    print('[打开手机号授权页面](' + result['url'] + ')')
    print('请在网页完成验证码验证，然后回来说“已验证，继续”。原图片需求已保留。')


def authorization_finish():
    state = json.loads(auth_path().read_text(encoding='utf-8'))
    result = request('/phone-auth/poll', state, authenticated=False)
    if result.get('status') != 'verified':
        print('还在等待网页验证，完成后可继续。')
        return
    token = result.get('token')
    if not isinstance(token, str) or len(token) != 43 or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in token):
        raise UserProblem('授权结果需要核查。')
    path = credential_path()
    # Server preserves the old account or explicitly refuses a conflicting binding.
    save_private_text(path, token)
    auth_path().unlink(missing_ok=True)
    print('手机号验证完成，剩余' + display_points(result) + '积分。可以继续刚才的图片。')


def reference_hashes(job):
    values = job.get('reference_files', [])
    if not isinstance(values, list) or len(values) > 3:
        raise UserProblem('请选择至多3张商品照片。')
    result = []
    for value in values:
        path = Path(value)
        if not path.is_absolute() or not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            raise UserProblem('请检查商品照片的本地路径与大小。')
        with path.open('rb') as stream:
            raw = stream.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise UserProblem('单张商品照片最多5MB。')
        result.append(hashlib.sha256(raw).hexdigest())
    return result


def create_task(job, root):
    if not isinstance(job, dict) or 'references' in job:
        raise UserProblem('任务需要JSON对象，参考图使用本地文件路径。')
    root = Path(root).resolve()
    if not root.is_dir():
        raise UserProblem('请指定已存在的图片保存目录。')
    hashes = reference_hashes(job)
    folder = root / ('image-' + uuid.uuid4().hex)
    folder.mkdir(mode=0o700)
    state = {'idem': uuid.uuid4().hex, 'output': str(folder / 'image.png'), 'status': 'draft',
             'job': job, 'reference_hashes': hashes}
    path = folder / 'task.json'
    save_private_json(path, state)
    return path


def execute_task(path):
    path = Path(path).resolve()
    lock = path.with_name('task.lock')
    try:
        write_new(lock, 'locked')
    except FileExistsError:
        raise UserProblem('原任务正在处理，请等待；中断后需核对任务状态再清理锁。') from None
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
        print('任务状态文件：' + str(path))
        if state.get('status') in ('submitting', 'pending', 'succeeded', 'failed') or state.get('id'):
            finish(state)
            return
        job = state['job']
        if job.get('confirmed') is not True:
            raise UserProblem('请先确认图片方案，再继续制作。')
        if reference_hashes(job) != state['reference_hashes']:
            raise UserProblem('商品照片已改变，请重新确认素材并创建新任务。')
        if not credential_path().exists():
            state['status'] = 'needs_authorization'
            save_private_json(path, state)
            ready = request('/phone-auth/status', authenticated=False).get('ready') is True
            print('图片需求已保留。' + ('请打开手机号授权页面，验证后继续。' if ready else '请完成首次使用授权后继续。'))
            return
        if int(display_points(account_request('/balance'))) < 1000:
            state['status'] = 'needs_credits'
            save_private_json(path, state)
            print('积分不足，图片需求已保留，本次未开始生成。')
            show_purchase_notice()
            return
        payload = prepare_references(job)
        health = request('/health', authenticated=False)
        if health.get('provider_configured') is not True:
            raise UserProblem('生图暂不可用，需求已保留。')
        if payload.get('references') and health.get('reference_editing') is not True:
            raise UserProblem('参考图编辑暂未开放，需求已保留。')
        state['status'] = 'submitting'
        save_private_json(path, state)
        try:
            result = request('/jobs', payload, state['idem'])
        except urllib.error.HTTPError as error:
            if error.code == 402:
                state['status'] = 'needs_credits'
                save_private_json(path, state)
            raise
        state.update(result)
        save_private_json(path, state)
        finish(state, fresh_result=result)
    finally:
        lock.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['open-authorization', 'authorization-finish', 'prepare', 'continue-task', 'purchase-offer', 'purchase', 'open-membership', 'membership-info', 'refresh', 'membership', 'account', 'start', 'activate', 'health', 'balance', 'status', 'onboarding', 'catalog', 'menu', 'profile', 'plan', 'generate', 'resume'])
    p.add_argument('--confirm-purchase', action='store_true')
    p.add_argument('--payment-supported', action='store_true')
    p.add_argument('--request-id')
    p.add_argument('--accept-terms', action='store_true')
    p.add_argument('--job')
    p.add_argument('--output-root')
    p.add_argument('--state')
    p.add_argument('--diagnostics', action='store_true')
    p.add_argument('--role', choices=ROLES)
    p.add_argument('--platform', choices=PLATFORMS)
    p.add_argument('--roles', nargs='+', choices=ROLES)
    p.add_argument('--platforms', nargs='+', choices=PLATFORMS)
    p.add_argument('--clear', action='store_true')
    p.add_argument('--industry', choices=list(CATALOG['industries']) + ['other'])
    p.add_argument('--kind', choices=['industry', 'role', 'platform'])
    p.add_argument('--page', type=int, default=1)
    p.add_argument('--page-size', type=int, choices=[2, 3], default=2)
    p.add_argument('--action', choices=['offered', 'skip'])
    a = p.parse_args()
    if a.command == 'open-authorization':
        authorization_start()
    elif a.command == 'authorization-finish':
        authorization_finish()
    elif a.command == 'continue-task':
        execute_task(a.state)
    elif a.command == 'purchase-offer':
        print(json.dumps(purchase_offer(), ensure_ascii=False))
    elif a.command == 'purchase':
        print(json.dumps(purchase(a.confirm_purchase, a.payment_supported, a.request_id), ensure_ascii=False))
    elif a.command == 'open-membership':
        print(membership_info())
    elif a.command == 'membership':
        print(membership_info())
    elif a.command == 'membership-info':
        print(membership_info())
    elif a.command == 'refresh':
        print(summary('balance', account_request('/balance')))
    elif a.command == 'account':
        print(json.dumps({'ready': credential_path().exists()}, ensure_ascii=False))
    elif a.command == 'start':
        result = start(a.accept_terms)
        print(json.dumps(public_result(result), ensure_ascii=False) if a.diagnostics else summary('start', result))
        if not a.diagnostics and int(display_points(result)) < 1000:
            show_purchase_notice()
    elif a.command == 'onboarding':
        print(json.dumps(onboarding(a.action), ensure_ascii=False))
    elif a.command == 'menu':
        print(json.dumps(menu(a.kind, a.industry, a.page, a.page_size), ensure_ascii=False))
    elif a.command == 'catalog':
        if a.diagnostics:
            print(json.dumps(CATALOG, ensure_ascii=False))
        else:
            for industry, label in CATALOG['industries'].items():
                if a.industry and a.industry != industry:
                    continue
                names = [v['name'] for v in CATALOG['roles'].values() if v['industry'] == industry]
                print(label + '：' + '、'.join(names))
            print('电商平台：' + '、'.join(PLATFORMS.values()))
    elif a.command == 'profile':
        path = profile_path()
        if a.clear:
            path.unlink(missing_ok=True)
            print('岗位偏好已清除。')
        elif a.role or a.roles:
            if (a.role and a.roles) or (a.platform and a.platforms):
                raise UserProblem('请使用单选或多选参数，不要混用。')
            roles = list(dict.fromkeys(a.roles or [a.role]))
            platforms = list(dict.fromkeys(a.platforms or [a.platform or 'general']))
            industries = list(dict.fromkeys(CATALOG['roles'].get(r, {}).get('industry', 'other') for r in roles))
            if a.industry and industries != [a.industry]:
                raise UserProblem('行业与岗位不一致，请重新选择。')
            value = {'role': roles[0], 'platform': platforms[0], 'industry': industries[0]}
            if len(roles) > 1 or len(platforms) > 1:
                value.update(roles=roles, platforms=platforms, industries=industries)
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if path.exists():
                path.write_text(json.dumps(value), encoding='utf-8')
            else:
                write_new(path, json.dumps(value))
            print('已记住岗位：' + '、'.join(ROLES[r] for r in roles) + '；平台：' + '、'.join(PLATFORMS[v] for v in platforms) + '。')
        else:
            value = read_profile()
            if a.diagnostics:
                print(json.dumps(value, ensure_ascii=False))
            elif value:
                print('常用岗位：' + '、'.join(ROLES[r] for r in value.get('roles', [value['role']])) + '；平台：' + '、'.join(PLATFORMS[v] for v in value.get('platforms', [value['platform']])) + '。')
            else:
                print('尚未选择岗位。请先选行业，再选具体岗位；输入岗位名称也可以。')
    elif a.command == 'activate':
        target = credential_path()
        if target.exists():
            raise UserProblem('试用已激活，无需重复领取。')
        invite = os.environ.get('IMAGE_INVITE_FILE')
        if not invite:
            raise UserProblem('尚未配置试用凭证，请联系管理员。')
        result = request('/activate', {'code': Path(invite).read_text(encoding='utf-8').strip()}, authenticated=False)
        write_new(target, result.pop('token'))
        print(json.dumps(public_result(result), ensure_ascii=False) if a.diagnostics else summary('activate', result))
    elif a.command in ('health', 'balance', 'status'):
        if a.command == 'status':
            result = request('/health', authenticated=False)
            result.update(request('/balance'))
        else:
            result = request('/' + a.command, authenticated=a.command != 'health')
        print(json.dumps(public_result(result), ensure_ascii=False) if a.diagnostics else summary(a.command, result))
    elif a.command == 'resume':
        finish(json.loads(Path(a.state).read_text(encoding='utf-8')))
    else:
        job = json.loads(Path(a.job).read_text(encoding='utf-8'))
        preference = read_profile()
        for field in ('role', 'platform'):
            if field not in job and field in preference:
                if len(preference.get(field + 's', [])) > 1:
                    raise UserProblem('请根据这次用途匹配一个常用岗位和平台后再生成。')
                job[field] = preference[field]
        if a.command == 'plan':
            if a.diagnostics:
                print(json.dumps({'需求方案': job, '联网': False, '本服务预期消耗积分': 1000}, ensure_ascii=False))
            else:
                print('方案已整理：单张图片，' + str(job.get('size', '1024x1024')) + '。')
                print('确认后生成消耗1000积分，本次规划未扣分。')
            return
        if a.command == 'prepare':
            print('任务状态文件：' + str(create_task(job, a.output_root)))
            print('图片需求已保存，可在授权或充值后继续。')
            return
        execute_task(create_task(job, a.output_root))
        return


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except UserProblem as e:
        print(str(e))
        raise SystemExit(1)
    except urllib.error.HTTPError as e:
        messages = {401: '账户会话失效，请恢复原账户后重试，已有积分不会重置。', 402: '积分已用完，本次未提交生图。',
                    422: '当前任务暂不支持，本次未扣分。', 429: '请求过于频繁或当前服务繁忙，请稍后重试；这不代表积分已用完。',
                    503: '生图暂未开通，本次未扣分。'}
        print(messages.get(e.code, '操作未完成，请联系管理员核查，暂不要重复生成。'))
        if e.code == 402:
            show_purchase_notice()
        raise SystemExit(1)
    except FileNotFoundError:
        print('缺少账户或任务文件，请先启动自动领取或检查任务文件。')
        raise SystemExit(1)
    except Exception:
        print('操作未完成，请检查连接或联系管理员核查，暂不要重复生成。')
        raise SystemExit(1)
