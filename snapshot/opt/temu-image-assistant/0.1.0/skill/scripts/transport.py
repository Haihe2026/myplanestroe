import argparse

import json

import os

import urllib.parse

import urllib.error

import urllib.request

import uuid

import secrets

from pathlib import Path

class UserProblem(Exception):
    pass

def display_points(result):
    value = result.get('balance_points', result.get('balance', 0) * 1000)
    if not isinstance(value, int) or value < 0:
        raise UserProblem('积分余额需要核查。')
    return str(value)

def summary(command, result):
    if command == 'health':
        return '服务连接正常。' + ('' if result.get('provider_configured') else '生图暂未开通，本次未扣分。')
    if command == 'balance':
        return '剩余' + display_points(result) + '积分。'
    if command == 'status':
        return '服务连接正常，剩余' + display_points(result) + '积分。' + ('' if result.get('provider_configured') else '\n生图暂未开通，本次未扣分。')
    return ('已领取5000生图积分，可生成5张标准图片。' if result.get('granted') else '试用已就绪，剩余' + display_points(result) + '积分。')

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

def request(path, payload=None, idem=None, authenticated=True, binary=False):
    headers = {'Content-Type': 'application/json'}
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
        raise UserProblem('首次调用将创建匿名试用账户并赠送5000积分；请先告知用户使用须知。')
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
    result = request('/register', {'install_secret': secret, 'accepted': True}, authenticated=False)
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

def finish(state):
    if not state.get('id'):
        print('请求结果待确认，请联系管理员核查，暂不要重复生成。')
        return
    jid = str(uuid.UUID(state['id']))
    result = request('/jobs/' + jid)
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
    print('已生成，剩余' + display_points(request('/balance')) + '积分。')
