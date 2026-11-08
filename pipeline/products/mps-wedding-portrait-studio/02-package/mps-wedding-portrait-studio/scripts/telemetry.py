"""首次对话上报：每个安装只发一次，只发8个元数据字段，有界2秒、不重试、失败即弃。

关闭开关：环境变量 MPS_WEDDING_STUDIO_JOURNEY=off
"""
import datetime
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid

SKILL_ID = 'mps-wedding-portrait-studio'
SKILL_NAME = '婚纱写真照相馆'
SKILL_VERSION = '1.0.0'
CHANNEL = 'workbuddy_skill'
TELEMETRY_ORIGIN = 'https://aistore.zhaopintong.com'
TELEMETRY_PATH = '/platform-api/telemetry/v1/first-dialogue'
TELEMETRY_TIMEOUT_S = 2
FIELDS = ('event_id', 'installation_id', 'skill_id', 'skill_name', 'skill_version', 'channel', 'client_occurred_at', 'is_test')
OFF_SWITCH = 'MPS_WEDDING_STUDIO_JOURNEY'
RECEIPT_RE = re.compile(r'[A-Za-z0-9_-]{43}')


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _default_transport(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method='POST')
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.read(4096)
    except urllib.error.HTTPError as e:
        return e.code, b''


TRANSPORT = _default_transport  # 测试时替换


def is_uuid4(value):
    try:
        u = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return str(u) == value and u.version == 4


def _state_file(state_dir):
    return os.path.join(state_dir, 'first-dialogue.json')


def _load(path):
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict) and is_uuid4(d.get('installation_id')) and is_uuid4(d.get('event_id')):
            return d
    except (OSError, ValueError):
        pass
    return None


def _save(path, d):
    """原子写入；失败返回 False。"""
    tmp = path + '.tmp'
    try:
        if os.path.islink(path) or os.path.islink(tmp):
            return False
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(d, f)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def is_test():
    return os.environ.get('MPS_WEDDING_STUDIO_TEST') == '1'


def report_once(state_dir):
    """返回 'off' / 'already' / 'sent' / 'skipped' / 'failed'。永不抛异常。"""
    try:
        if os.environ.get(OFF_SWITCH, '').lower() == 'off':
            return 'off'
        path = _state_file(state_dir)
        d = _load(path)
        if d is None:
            d = dict(installation_id=str(uuid.uuid4()), event_id=str(uuid.uuid4()), sent=False)
            if not _save(path, d) or _load(path) is None:
                return 'skipped'  # 写不进去就跳过，不临时造标识
        if d.get('sent'):
            return 'already'
        body = dict(event_id=d['event_id'], installation_id=d['installation_id'], skill_id=SKILL_ID,
                    skill_name=SKILL_NAME, skill_version=SKILL_VERSION, channel=CHANNEL,
                    client_occurred_at=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec='seconds'),
                    is_test=is_test())
        assert tuple(body) == FIELDS
        start = time.monotonic()
        try:
            status, raw = TRANSPORT(TELEMETRY_ORIGIN + TELEMETRY_PATH, body, {'Content-Type': 'application/json'}, TELEMETRY_TIMEOUT_S)
        except Exception:
            return 'failed'
        if time.monotonic() - start > TELEMETRY_TIMEOUT_S + 0.5 or status != 200:
            return 'failed'
        try:
            r = json.loads(raw)
        except (ValueError, UnicodeError):
            return 'failed'
        if not isinstance(r, dict) or not is_uuid4(r.get('event_id')) or not isinstance(r.get('receipt'), str) or not RECEIPT_RE.fullmatch(r['receipt']):
            return 'failed'
        d.update(sent=True, server_event_id=r['event_id'], receipt=r['receipt'])
        return 'sent' if _save(path, d) else 'failed'
    except Exception:
        return 'failed'


def link_account(state_dir, account_secret):
    """账户关联后把首次对话接到账户上；只传 event_id/receipt/product。永不抛异常。"""
    try:
        if os.environ.get(OFF_SWITCH, '').lower() == 'off' or not account_secret:
            return 'off'
        path = _state_file(state_dir)
        d = _load(path)
        if not d or not d.get('sent') or not d.get('receipt'):
            return 'skipped'
        if d.get('linked') or d.get('link_conflict'):
            return 'already'
        body = dict(event_id=d['server_event_id'], receipt=d['receipt'], product='gemini')
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + account_secret}
        try:
            status, raw = TRANSPORT(TELEMETRY_ORIGIN + TELEMETRY_PATH + '/link', body, headers, TELEMETRY_TIMEOUT_S)
        except Exception:
            return 'failed'
        if status == 409:
            d['link_conflict'] = True
            _save(path, d)
            return 'conflict'
        if status != 200:
            return 'failed'
        try:
            ok = json.loads(raw).get('linked') is True
        except (ValueError, AttributeError, UnicodeError):
            ok = False
        if not ok:
            return 'failed'
        d['linked'] = True
        return 'linked' if _save(path, d) else 'failed'
    except Exception:
        return 'failed'
