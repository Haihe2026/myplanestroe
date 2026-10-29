"""Add isolated no-free-grant pilot service and reversible nginx route."""
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request
import json
unit=Path('/etc/systemd/system/image-pack.service')
nginx=Path('/etc/nginx/conf.d/image-assistant.conf')
backup=Path('/var/lib/image-assistant/backups')/('pack-1.7.0-'+str(int(time.time())))
backup.mkdir(parents=True,exist_ok=False)
old_nginx=nginx.read_text();(backup/'nginx.conf').write_text(old_nginx)
old_unit=unit.read_bytes() if unit.exists() else None
if old_unit: (backup/'image-pack.service').write_bytes(old_unit)
unit.write_text('''[Unit]
Description=Manually confirmed Gemini quota pack test service
After=network.target
[Service]
User=image-assistant
Group=image-assistant
WorkingDirectory=/opt/skill-platform/1.7.0/service
EnvironmentFile=/etc/image-assistant/provider.env
Environment=IMAGE_EDIT_CONFIRMED=yes
ExecStart=/opt/skill-platform/1.2.0/venv/bin/python /opt/skill-platform/1.7.0/service/run_pack.py --source /opt/skill-platform/1.2.0/service --db /var/lib/image-assistant/pack-test.db --port 18790
Restart=on-failure
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/image-assistant
[Install]
WantedBy=multi-user.target
''')
route='''    location ^~ /quota-pack/gemini/ {
        client_max_body_size 16m;
        limit_req zone=image_pilot burst=8 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:18790;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 220s;
        proxy_send_timeout 30s;
        proxy_connect_timeout 5s;
    }
'''
try:
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','image-pack'],check=True)
    for i in range(20):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18790/quota-pack/gemini/health',timeout=3) as r: health=json.load(r)
            assert health['provider_configured'];break
        except Exception:
            if i==19: raise
            time.sleep(1)
    if 'location ^~ /quota-pack/gemini/' not in old_nginx:
        marker='    location / { return 404; }'
        assert old_nginx.count(marker)==1
        nginx.write_text(old_nginx.replace(marker,route+marker))
    subprocess.run(['nginx','-t'],check=True)
    subprocess.run(['systemctl','reload','nginx'],check=True)
    print(json.dumps({'deployed':True,'provider_ready':True,'auto_grant':False,'payment_tested':False,'backup':str(backup)}))
except Exception:
    nginx.write_text(old_nginx)
    subprocess.run(['systemctl','disable','--now','image-pack'])
    if old_unit: unit.write_bytes(old_unit)
    else: unit.unlink(missing_ok=True)
    subprocess.run(['systemctl','daemon-reload']);subprocess.run(['systemctl','reload','nginx'])
    raise
