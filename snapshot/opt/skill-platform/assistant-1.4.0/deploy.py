"""Deploy disabled SMS entry and retain current website/payment/image sources."""
import json
import os
from pathlib import Path
import secrets
import grp
import shutil
import sqlite3
import subprocess
import time
import urllib.request

ROOT = Path('/opt/skill-platform/assistant-1.4.0')
assert Path(__file__).resolve().parent == ROOT
os.umask(0o077)
def run(args): return subprocess.run(args, check=True, capture_output=True, text=True).stdout
nginx = Path('/etc/nginx/conf.d/image-assistant.conf')
drop = Path('/etc/systemd/system/image-assistant.service.d/zzz-phone-authorization.conf')
web = Path('/var/www/image-assistant/auth')
assert not drop.exists(), 'Preserve existing deployment'
assert not run(['ss','-Htan','state','established','( sport = :8787 )']).strip(), 'Active generation; retry later'
backup = Path('/var/lib/image-assistant/backups') / ('phone-auth-1.4.0-' + str(int(time.time())))
backup.mkdir(parents=True)
shutil.copy2(nginx, backup / 'nginx.conf')
with sqlite3.connect('/var/lib/image-assistant/pilot.db') as source, sqlite3.connect(backup / 'pilot.db') as target:
    source.backup(target)
config = Path('/etc/image-assistant-sms.json')
if config.exists():
    settings = json.loads(config.read_text())
    assert settings.get('enabled') is False and len(settings.get('phone_hmac_key','')) >= 32, 'Preserve configured SMS credentials'
else:
    settings = json.loads((ROOT / 'sms-config.example.json').read_text())
    settings['phone_hmac_key'] = secrets.token_urlsafe(48)
    config.write_text(json.dumps(settings, ensure_ascii=False), encoding='utf-8')
os.chown(config, 0, grp.getgrnam('image-assistant').gr_gid)
config.chmod(0o640)
original = nginx.read_text()
block = '''    location ^~ /phone-auth/ {
        client_max_body_size 4k;
        limit_req zone=image_pilot burst=6 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }
    location /auth/ {
        root /var/www/image-assistant;
        index index.html;
        add_header Cache-Control "no-store" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'" always;
    }
'''
assert '    location / { return 404; }' in original
assert '/phone-auth/' not in original
try:
    shutil.copytree(ROOT / 'web', web, dirs_exist_ok=True)
    for path in web.rglob('*'):
        path.chmod(0o755 if path.is_dir() else 0o644)
    web.chmod(0o755)
    for path in ROOT.rglob('*'):
        if path.is_dir(): path.chmod(0o755)
        elif path.suffix in ('.py','.json','.md','.html','.js','.css'): path.chmod(0o644)
    ROOT.chmod(0o755)
    nginx.write_text(original.replace('    location / { return 404; }', block + '    location / { return 404; }'))
    run(['nginx','-t'])
    drop.write_text('[Service]\nEnvironment=IMAGE_SMS_CONFIG_FILE=/etc/image-assistant-sms.json\nExecStart=\nExecStart=/opt/skill-platform/1.2.0/venv/bin/python ' + str(ROOT / 'run_gateway.py') +
        ' --source /opt/skill-platform/assistant-1.3.0/service --annual-source /opt/skill-platform/1.5.0/service --telemetry-source /opt/skill-platform/0.3.0/service --limits /opt/skill-platform/assistant-1.3.0/limits.json --db /var/lib/image-assistant/pilot.db --port 8787\n')
    drop.chmod(0o644)
    run(['systemctl','daemon-reload'])
    run(['systemctl','restart','image-assistant'])
    for _ in range(15):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8787/phone-auth/status', timeout=3) as response: status = json.load(response)
            assert status['ready'] is False
            break
        except OSError: time.sleep(1)
    else: raise RuntimeError('Authorization endpoint not reachable')
    with urllib.request.urlopen('http://127.0.0.1:8787/health', timeout=5) as response: health = json.load(response)
    assert health['provider_configured'] and health['reference_editing'] and health['assistant_version'] == '1.3.0'
    run(['systemctl','reload','nginx'])
except Exception:
    shutil.copy2(backup / 'nginx.conf', nginx)
    drop.unlink(missing_ok=True)
    # Failed deployments keep the static files and private config for diagnosis.
    run(['systemctl','daemon-reload'])
    run(['systemctl','restart','image-assistant'])
    run(['nginx','-t'])
    run(['systemctl','reload','nginx'])
    raise
record = {'deployed':True,'version':'1.4.0','backup':str(backup),'sms_ready':False,
    'auth_url':'https://myplanestore.com/auth/','membership_pages_changed':False,
    'image_source_changed':False,'quota_limits_changed':False,'database_replaced':False,'actual_sms_sent':0}
(ROOT / 'deployment.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record))
