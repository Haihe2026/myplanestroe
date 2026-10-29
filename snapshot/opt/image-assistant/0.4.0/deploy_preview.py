"""Operator deployment of membership preview, retaining DB and rollback configuration."""
import pathlib
import shutil
import sqlite3
import subprocess
import time

stamp = str(int(time.time()))
root = pathlib.Path('/opt/image-assistant/0.4.0')
backup = pathlib.Path('/var/backups/image-assistant') / stamp
backup.mkdir(parents=True, mode=0o700)
with sqlite3.connect('/var/lib/image-assistant/pilot.db') as source:
    with sqlite3.connect(str(backup / 'pilot.db')) as destination:
        source.backup(destination)
nginx = pathlib.Path('/etc/nginx/conf.d/image-assistant.conf')
override = pathlib.Path('/etc/systemd/system/image-assistant.service.d/backend.conf')
shutil.copy2(nginx, backup / 'nginx.conf')
shutil.copy2(override, backup / 'backend.conf')
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
before, after = config.rsplit(anchor, 1)
nginx.write_text(before + addition + anchor + after)
try:
    subprocess.run(['nginx','-t'], check=True)
    override.write_text('[Service]\nWorkingDirectory=/opt/image-assistant/0.4.0/service\nExecStart=\nExecStart=/usr/bin/python3 /opt/image-assistant/0.4.0/service/server.py --db /var/lib/image-assistant/pilot.db\n')
    subprocess.run(['systemctl','daemon-reload'], check=True)
    subprocess.run(['systemctl','restart','image-assistant'], check=True)
    time.sleep(2)
    subprocess.run(['systemctl','is-active','--quiet','image-assistant'], check=True)
    subprocess.run(['systemctl','reload','nginx'], check=True)
except Exception:
    shutil.copy2(backup / 'nginx.conf', nginx)
    shutil.copy2(backup / 'backend.conf', override)
    subprocess.run(['systemctl','daemon-reload'])
    subprocess.run(['systemctl','restart','image-assistant'])
    raise
print('Membership preview deployed. Backup: ' + str(backup))
