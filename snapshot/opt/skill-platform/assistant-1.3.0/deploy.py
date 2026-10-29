"""Versioned production upgrade with DB backup and configuration rollback."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

ROOT=Path('/opt/skill-platform/assistant-1.3.0')
assert Path(__file__).resolve().parent==ROOT
os.umask(0o077)

def run(args):
    return subprocess.run(args,check=True,capture_output=True,text=True).stdout

python=Path('/opt/skill-platform/1.2.0/venv/bin/python')
nginx=Path('/etc/nginx/conf.d/image-assistant.conf')
drop=Path('/etc/systemd/system/image-assistant.service.d/zz-personal-assistant.conf')
assert not drop.exists(),'Deployment already exists; do not overwrite'
assert not run(['ss','-Htan','state','established','( sport = :8787 )']).strip(),'Active image requests; retry later'
backup=Path('/var/lib/image-assistant/backups')/('assistant-1.3.0-'+str(int(time.time())))
backup.mkdir(parents=True)
shutil.copy2(nginx,backup/'nginx.conf')
web=Path('/var/www/image-assistant/membership')
shutil.copytree(web/'gemini',backup/'gemini')
shutil.copy2(web/'payment-qr.png',backup/'payment-qr.png')
with sqlite3.connect('/var/lib/image-assistant/pilot.db') as source,sqlite3.connect(backup/'pilot.db') as target:
    source.backup(target)
    used=source.execute("SELECT count(*) FROM jobs WHERE status IN ('pending','succeeded') AND id NOT IN (SELECT job_id FROM paid_jobs)").fetchone()[0]
    outstanding=source.execute('SELECT coalesce(sum(max(u.balance-coalesce(p.remaining,0),0)),0) FROM users u LEFT JOIN paid_wallets p ON p.user_id=u.id').fetchone()[0]
# Preserve all existing free balances, then reserve at most 100 new internal units.
cap=max(20,used+outstanding)+100
for path in ROOT.rglob('*'):
    if path.is_dir():path.chmod(0o755)
    elif path.suffix in ('.py','.json','.md','.png','.html','.js'):path.chmod(0o644)
ROOT.chmod(0o755)
text=nginx.read_text()
block='''    location = /assistant/register {
        limit_req zone=image_pilot burst=8 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }
'''
assert 'location = /assistant/register' not in text
assert '    location / { return 404; }' in text
try:
    nginx.write_text(text.replace('    location / { return 404; }',block+'    location / { return 404; }'))
    run(['nginx','-t'])
    drop.write_text('[Service]\nEnvironment=IMAGE_PILOT_MAX_IMAGES='+str(cap)+'\nEnvironment=IMAGE_ASSISTANT_TRIAL_POOL_UNITS=100\nEnvironment=IMAGE_LEGACY_TRIAL_MAX_IMAGES=20\nEnvironment=IMAGE_ASSISTANT_ACCOUNT_IP_DAILY_LIMIT=10\nExecStart=\nExecStart='+str(python)+' '+str(ROOT/'run_gateway.py')+' --source '+str(ROOT/'service')+' --annual-source /opt/skill-platform/1.5.0/service --telemetry-source /opt/skill-platform/0.3.0/service --db /var/lib/image-assistant/pilot.db --port 8787\n')
    drop.chmod(0o644)
    run(['systemctl','daemon-reload'])
    run(['systemctl','restart','image-assistant'])
    health=None
    for _ in range(15):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8787/health',timeout=5) as response:health=json.load(response)
            break
        except OSError:time.sleep(1)
    assert health and health.get('assistant_version')=='1.3.0' and health.get('provider_configured') and health.get('reference_editing'),health
    for name in ('index.html','app.js','manual-payment.js','payment-qr.png'):
        shutil.copy2(ROOT/'web'/name,web/'gemini'/name)
        (web/'gemini'/name).chmod(0o644)
    shutil.copy2(ROOT/'web/payment-qr.png',web/'payment-qr.png')
    (web/'payment-qr.png').chmod(0o644)
    run(['systemctl','reload','nginx'])
except Exception:
    shutil.copy2(backup/'nginx.conf',nginx)
    drop.unlink(missing_ok=True)
    shutil.copytree(backup/'gemini',web/'gemini',dirs_exist_ok=True)
    shutil.copy2(backup/'payment-qr.png',web/'payment-qr.png')
    run(['systemctl','daemon-reload']);run(['systemctl','restart','image-assistant'])
    run(['nginx','-t']);run(['systemctl','reload','nginx'])
    raise
record={'deployed':True,'version':'1.3.0','backup':str(backup),'free_pool_budget_rmb_estimate':20,
    'new_free_pool_units':100,'global_free_generation_cap':cap,'database_replaced':False,
    'qr_replaced':True,'real_payment_tested':False}
(ROOT/'deployment.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
