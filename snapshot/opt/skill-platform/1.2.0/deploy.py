"""Versioned backend rollout with rollback; does not invoke image generation."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

ROOT=Path('/opt/skill-platform/1.2.0')
assert Path(__file__).resolve().parent==ROOT
os.umask(0o077)
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout
python=ROOT/'venv/bin/python'
if not python.exists():run(['/usr/bin/python3','-m','venv',str(ROOT/'venv')])
run([str(python),'-m','pip','install','Pillow==12.2.0'])
result=subprocess.run([str(python),'-B','-m','unittest','discover','-p','test_*.py'],cwd=ROOT/'service',capture_output=True,text=True)
assert result.returncode==0,result.stderr
print(result.stderr.strip())
for path in ROOT.rglob('*'):
    if path.is_dir():path.chmod(0o755)
    elif not path.is_symlink():path.chmod(0o755 if path.parent.name=='bin' else 0o644)
ROOT.chmod(0o755)
connections=run(['ss','-Htan','state','established','( sport = :8787 )'])
assert not connections.strip(),'Active requests; retry deployment later'
backup=Path('/var/backups/image-assistant')/('reference-edit-'+str(int(time.time())))
backup.mkdir(parents=True)
nginx=Path('/etc/nginx/conf.d/image-assistant.conf')
drop=Path('/etc/systemd/system/image-assistant.service.d/reference-edit.conf')
assert not drop.exists(),'Already rolled out; do not overwrite'
shutil.copy2(nginx,backup/'nginx.conf')
with sqlite3.connect('/var/lib/image-assistant/pilot.db') as source,sqlite3.connect(backup/'pilot.db') as target:source.backup(target)
text=nginx.read_text()
assert 'location = /jobs {' not in text
block='''    location = /jobs {
        client_max_body_size 16m;
        limit_req zone=image_pilot burst=4 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 220s;
        proxy_send_timeout 30s;
        proxy_connect_timeout 5s;
    }
    location ^~ /jobs/by-key/ {
        proxy_pass http://127.0.0.1:8787;
        limit_req zone=image_pilot burst=8 nodelay;
        limit_req_status 429;
        proxy_read_timeout 30s;
    }
'''
assert '    location / { return 404; }' in text
try:
    nginx.write_text(text.replace('    location / { return 404; }',block+'    location / { return 404; }'))
    run(['nginx','-t'])
    drop.write_text('[Service]\nEnvironment=IMAGE_EDIT_CONFIRMED=yes\nExecStart=\nExecStart='+str(python)+' /opt/skill-platform/0.3.0/service/run_gateway.py --source '+str(ROOT/'service')+' --product gemini --db /var/lib/image-assistant/pilot.db --port 8787\n')
    drop.chmod(0o644)
    run(['systemctl','daemon-reload']);run(['systemctl','restart','image-assistant'])
    health=None
    for _ in range(15):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8787/health',timeout=5) as response:health=json.load(response)
            break
        except OSError:time.sleep(1)
    assert health and health['version']=='1.2.0' and health['reference_editing'] is True,health
    run(['systemctl','reload','nginx'])
except Exception:
    shutil.copy2(backup/'nginx.conf',nginx)
    drop.unlink(missing_ok=True)
    run(['systemctl','daemon-reload']);run(['systemctl','restart','image-assistant'])
    run(['nginx','-t']);run(['systemctl','reload','nginx'])
    raise
record={'deployed':True,'version':'1.2.0','backup':str(backup),'reference_editing':True,'new_paid_generation_tested':False,'database_replaced':False,'real_merchant_photo_tested':False}
(ROOT/'deployment.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
