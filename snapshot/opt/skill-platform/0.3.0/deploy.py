"""Server-side setup. Run as root after uploading this versioned directory."""
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import sqlite3
import subprocess
import time

ROOT=Path('/opt/skill-platform/0.3.0')
assert Path(__file__).resolve().parent==ROOT
os.umask(0o077)
backup=Path('/var/backups/image-assistant')/('ops-'+str(int(time.time())))
backup.mkdir(parents=True)
nginx=Path('/etc/nginx/conf.d/image-assistant.conf')
shutil.copy2(nginx,backup/'nginx.conf')
account=pwd.getpwnam('image-assistant')
data=Path('/var/lib/skill-monitor');data.mkdir(exist_ok=True)
os.chown(data,account.pw_uid,account.pw_gid)
conf=Path('/etc/skill-monitor');conf.mkdir(exist_ok=True)
os.chown(conf,0,account.pw_gid);conf.chmod(0o750)
products={'gemini':'/var/lib/image-assistant/pilot.db','temu':'/var/lib/temu-image-assistant/trial.db'}
for name,path in products.items():
    with sqlite3.connect(path) as source,sqlite3.connect(backup/(name+'.db')) as target:
        source.backup(target)
    # Pending records may be uncertain completed jobs, not active requests. Do not alter them.
config=conf/'config.json'
if not config.exists():
    config.write_text(json.dumps({'password':secrets.token_urlsafe(36),'products':products,'events':str(data/'events.db')}))
os.chown(config,account.pw_uid,account.pw_gid);config.chmod(0o600)
shutil.copy2('/var/www/image-assistant/membership/platform-mark.svg',ROOT/'web/logo.svg')
# All code is non-secret; config remains outside the served tree.
for item in ROOT.rglob('*'):
    item.chmod(0o755 if item.is_dir() else 0o644)
ROOT.chmod(0o755)
for name,port,product,path in [('image-assistant',8787,'gemini','/opt/skill-platform/0.2.0/service'),('temu-image-assistant',8788,'temu','/opt/temu-image-assistant/0.2.2/service')]:
    drop=Path('/etc/systemd/system')/(name+'.service.d')/'operations.conf'
    drop.parent.mkdir(exist_ok=True)
    if drop.exists():shutil.copy2(drop,backup/(name+'-operations.conf'))
    python='/usr/bin/python3' if product=='gemini' else '/opt/temu-image-assistant/venv/bin/python'
    drop.write_text('[Service]\nReadWritePaths=/var/lib/skill-monitor\nExecStart=\nExecStart='+python+' '+str(ROOT/'service/run_gateway.py')+' --source '+path+' --product '+product+' --db '+products[product]+' --port '+str(port)+'\n')
unit=Path('/etc/systemd/system/skill-monitor.service')
unit.write_text('''[Unit]
Description=Private Skill operations dashboard
After=network.target
[Service]
User=image-assistant
Group=image-assistant
ExecStart=/usr/bin/python3 /opt/skill-platform/0.3.0/service/monitor.py --config /etc/skill-monitor/config.json
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
UMask=0077
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
[Install]
WantedBy=multi-user.target
''')
text=nginx.read_text()
assert 'location ^~ /ops/' not in text, 'Already installed; review instead of duplicating'
block='''    location = /ops { return 302 /ops/; }
    location ^~ /ops/ {
        proxy_pass http://127.0.0.1:8790;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        limit_req zone=image_pilot burst=12 nodelay;
        limit_req_status 429;
        proxy_read_timeout 30s;
    }
    location ^~ /skill-pay/ {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header X-Real-IP $remote_addr;
        limit_req zone=image_pilot burst=8 nodelay;
        limit_req_status 429;
        proxy_read_timeout 30s;
    }
'''
assert '    location / { return 404; }' in text
nginx.write_text(text.replace('    location / { return 404; }',block+'    location / { return 404; }'))
try:subprocess.run(['nginx','-t'],check=True)
except Exception:
    shutil.copy2(backup/'nginx.conf',nginx)
    raise
subprocess.run(['systemctl','daemon-reload'],check=True)
for name in ('image-assistant','temu-image-assistant'):
    subprocess.run(['systemctl','restart',name],check=True)
subprocess.run(['systemctl','enable','--now','skill-monitor'],check=True)
subprocess.run(['systemctl','reload','nginx'],check=True)
print('Backup: '+str(backup))
print('Deployment completed; verify health, authentication and native payment gate.')
