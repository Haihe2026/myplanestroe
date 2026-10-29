"""Operator deployment of membership preview, retaining DB and rollback configuration."""
import pathlib
import shutil
import sqlite3
import subprocess
import time

stamp = str(int(time.time()))
root = pathlib.Path('/opt/image-assistant/0.5.0')
backup = pathlib.Path('/var/backups/image-assistant') / stamp
backup.mkdir(parents=True, mode=0o700)
with sqlite3.connect('/var/lib/image-assistant/pilot.db') as source:
    with sqlite3.connect(str(backup / 'pilot.db')) as destination:
        source.backup(destination)
nginx = pathlib.Path('/etc/nginx/conf.d/image-assistant.conf')
override = pathlib.Path('/etc/systemd/system/image-assistant.service.d/backend.conf')
shutil.copy2(nginx, backup / 'nginx.conf')
shutil.copy2(override, backup / 'backend.conf')
envfile = pathlib.Path('/etc/image-assistant/provider.env')
shutil.copy2(envfile, backup / 'provider.env')
config = nginx.read_text()
anchor = '    location / {'
if anchor not in config:
    raise RuntimeError('Unexpected nginx layout; no change applied')
addition = '''    location /membership/ {
        root /var/www/image-assistant;
        index index.html;
        add_header Cache-Control "no-store" always;
        add_header Referrer-Policy "no-referrer" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'" always;
    }
    location /membership-api/ {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header X-Real-IP $remote_addr;
        limit_req zone=image_pilot burst=8 nodelay;
        proxy_read_timeout 30s;
    }
    location = /membership-link {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header X-Real-IP $remote_addr;
        limit_req zone=image_pilot burst=8 nodelay;
    }
'''
web = pathlib.Path('/var/www/image-assistant/membership')
web.mkdir(exist_ok=True)
for path in (root / 'web').iterdir():
    shutil.copy2(path, web / path.name)
    (web / path.name).chmod(0o644)
web.chmod(0o755)
if 'location /membership/' not in config:
    before, after = config.rsplit(anchor, 1)
    config = before + addition + anchor + after
if 'location = /v1/images/generations' not in config:
    before, after = config.rsplit(anchor, 1)
    config = before + '''    location = /v1/images/generations {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header X-Real-IP $remote_addr;
        limit_req zone=image_pilot burst=8 nodelay;
        limit_req_status 429;
        proxy_read_timeout 220s;
    }
''' + anchor + after
nginx.write_text(config)
try:
    subprocess.run(['nginx','-t'], check=True)
    # Operator confirmed upstream resale permission on 2026-10-11; payment stays closed.
    lines = [line for line in envfile.read_text().splitlines() if not line.startswith('IMAGE_API_RESALE_CONFIRMED=')]
    envfile.write_text('\n'.join(lines)+'\nIMAGE_API_RESALE_CONFIRMED=yes\n')
    envfile.chmod(0o600)
    override.write_text('[Service]\nWorkingDirectory=/opt/image-assistant/0.5.0/service\nExecStart=\nExecStart=/usr/bin/python3 /opt/image-assistant/0.5.0/service/server.py --db /var/lib/image-assistant/pilot.db\n')
    subprocess.run(['systemctl','daemon-reload'], check=True)
    subprocess.run(['systemctl','restart','image-assistant'], check=True)
    time.sleep(2)
    subprocess.run(['systemctl','is-active','--quiet','image-assistant'], check=True)
    subprocess.run(['systemctl','reload','nginx'], check=True)
except Exception:
    shutil.copy2(backup / 'nginx.conf', nginx)
    shutil.copy2(backup / 'backend.conf', override)
    shutil.copy2(backup / 'provider.env', envfile)
    subprocess.run(['systemctl','daemon-reload'])
    subprocess.run(['systemctl','restart','image-assistant'])
    raise
print('Membership preview deployed. Backup: ' + str(backup))
