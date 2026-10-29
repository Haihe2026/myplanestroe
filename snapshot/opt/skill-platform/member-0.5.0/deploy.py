"""Versioned rollout with backups; never replace or reprice an existing wallet."""
from contextlib import closing
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import sqlite3
import subprocess
import time
import urllib.request

ROOT=Path('/opt/skill-platform/member-0.5.0')
assert Path(__file__).resolve().parent==ROOT
os.umask(0o077)

def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()
def health(port,route='/health'):
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+route,timeout=5) as response:return json.load(response)
def balances(path):
    with closing(sqlite3.connect(path)) as c:
        rows=c.execute('SELECT id,balance FROM users ORDER BY id').fetchall()
        return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

assert not run(['ss','-Htan','state','established','( sport = :8787 or sport = :8788 )']), 'Active request; wait before deployment'
pid=run(['systemctl','show','image-assistant','-p','MainPID','--value'])
assert pid.isdigit() and int(pid)>0
environment={}
for value in Path('/proc/'+pid+'/environ').read_bytes().split(b'\0'):
    if b'=' in value:
        k,v=value.split(b'=',1)
        environment[k.decode()]=v.decode()
keys={'IMAGE_PROVIDER_KEY','IMAGE_PROVIDER_CONFIRMED','IMAGE_EDIT_CONFIRMED','IMAGE_PUBLIC_TRIAL_ENABLED',
      'IMAGE_TRIAL_HMAC_KEY','IMAGE_API_RESALE_CONFIRMED','IMAGE_MANUAL_QR_ENABLED','SKILL_EVENTS_DB'}
settings={k:v for k,v in environment.items() if k in keys}
assert settings.get('IMAGE_MANUAL_QR_ENABLED')=='yes'
assert settings.get('IMAGE_PUBLIC_TRIAL_ENABLED')=='yes'
assert settings.get('IMAGE_PROVIDER_CONFIRMED')=='yes' and settings.get('IMAGE_EDIT_CONFIRMED')=='yes'
assert settings.get('IMAGE_TRIAL_HMAC_KEY') and settings.get('IMAGE_PROVIDER_KEY')
assert all('\n' not in v and '\r' not in v for v in settings.values())

backup=Path('/var/backups/image-assistant')/('shared-0.5.0-'+str(int(time.time())))
backup.mkdir(parents=True)
nginx=Path('/etc/nginx/conf.d/image-assistant.conf')
before=nginx.read_text()
assert 'location ^~ /platform-api/' not in before
assert '    location / { return 404; }' in before
site=Path('/var/www/image-assistant/membership')
targets={}
for product in ('gemini','temu','xhs'):
    for name in ('index.html','app.js','manual-payment.js','platform.js'):
        targets['web/'+product+'/'+name]=site/product/name
targets['web/gemini/api-keys.js']=site/'gemini/api-keys.js'
targets['web/gemini/api-guide.html']=site/'gemini/api-guide.html'
units={
 'gemini':Path('/etc/systemd/system/image-assistant.service.d/zzzz-shared-paid-first.conf'),
 'temu':Path('/etc/systemd/system/temu-image-assistant.service.d/zzzz-shared-paid-first.conf'),
 'shared':Path('/etc/systemd/system/skill-platform.service'),
 'ops':Path('/etc/systemd/system/skill-monitor.service.d/zzzz-shared-wallet.conf')}
assert not any(path.exists() for path in units.values()), 'Preserve existing installation; do not rerun deploy'
targets.update({'units/'+name:path for name,path in units.items()})
targets['nginx.conf']=nginx
original={}
for name,path in targets.items():
    original[name]=path.exists()
    if path.exists():
        saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved)
legacy={'gemini':'/var/lib/image-assistant/pilot.db','temu':'/var/lib/temu-image-assistant/trial.db'}
checks={}
qr={p:hashlib.sha256((site/p/'payment-qr.png').read_bytes()).hexdigest() for p in ('gemini','temu')}
user=pwd.getpwnam('image-assistant')
try:
    run(['systemctl','stop','image-assistant','temu-image-assistant','skill-monitor'])
    for name,path in legacy.items():
        checks[name]=balances(path)
        with closing(sqlite3.connect(path)) as source,closing(sqlite3.connect(backup/(name+'.db'))) as dest:source.backup(dest)
    shared=Path('/var/lib/skill-platform');shared.mkdir(exist_ok=True)
    os.chown(shared,user.pw_uid,user.pw_gid);shared.chmod(0o700)
    config=Path('/etc/skill-platform-shared.env')
    assert not config.exists(),'Preserve existing private shared configuration'
    # Use JSON-quoted values for systemd EnvironmentFile; do not print or transfer secrets.
    config.write_text('\n'.join(k+'='+json.dumps(v) for k,v in settings.items())+'\n')
    os.chown(config,0,user.pw_gid);config.chmod(0o640)
    for path in ROOT.rglob('*'):
        if '__pycache__' not in path.parts:path.chmod(0o755 if path.is_dir() else 0o644)
    ROOT.chmod(0o755)
    gifts=ROOT/'gifts';gifts.mkdir(exist_ok=True)
    source=Path('/opt/skill-platform/assistant-1.3.0/gifts/scam-check-360.zip')
    if source.exists():shutil.copy2(source,gifts/'scam-check-360.zip');(gifts/'scam-check-360.zip').chmod(0o644)
    gifts.chmod(0o755)
    # The shared core resolves its gift path one level above core/.
    for product,port,source in [('gemini',8787,'/opt/skill-platform/assistant-1.3.0/service'),('temu',8788,'/opt/temu-image-assistant/0.2.2/service')]:
        path=units[product];path.parent.mkdir(exist_ok=True)
        python='/opt/skill-platform/1.2.0/venv/bin/python' if product=='gemini' else '/opt/temu-image-assistant/venv/bin/python'
        path.write_text('[Service]\nExecStart=\nExecStart='+python+' '+str(ROOT/'service/run_legacy.py')+' --source '+source+' --product '+product+' --db '+legacy[product]+' --port '+str(port)+'\n')
    common='''[Unit]
Description=Shared Skill image wallet
After=network.target
[Service]
User=image-assistant
Group=image-assistant
EnvironmentFile=/etc/skill-platform-shared.env
ExecStart=/opt/skill-platform/1.2.0/venv/bin/python /opt/skill-platform/member-0.5.0/service/run_shared.py --db /var/lib/skill-platform/shared.db --gemini-db /var/lib/image-assistant/pilot.db --temu-db /var/lib/temu-image-assistant/trial.db --temu-source /opt/temu-image-assistant/0.2.2/service
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/skill-platform /var/lib/image-assistant /var/lib/temu-image-assistant /var/lib/skill-monitor
UMask=0077
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
[Install]
WantedBy=multi-user.target
'''
    units['shared'].write_text(common)
    units['ops'].parent.mkdir(exist_ok=True)
    units['ops'].write_text('[Service]\nReadWritePaths=/var/lib/skill-platform\nExecStart=\nExecStart=/opt/skill-platform/1.2.0/venv/bin/python '+str(ROOT/'ops/run_ops.py')+' --config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db --temu-source /opt/temu-image-assistant/0.2.2/service\n')
    for path in units.values():path.chmod(0o644)
    run(['systemctl','daemon-reload'])
    run(['systemctl','start','skill-platform','image-assistant','temu-image-assistant'])
    for _ in range(20):
        try:
            state=health(8791,'/platform-api/gemini/health')
            assert state['new_user_uses']==0 and state['provider_configured'] and state['reference_editing']
            assert health(8787)['new_user_uses']==0 and health(8788)['new_user_uses']==0
            break
        except Exception:time.sleep(1)
    else:raise RuntimeError('Image gateways not healthy')
    run(['systemctl','start','skill-monitor'])
    # Validate every old user balance before publishing the new route.
    assert all(balances(path)==checks[name] for name,path in legacy.items()), 'Old balances changed; stop rollout'
    block='''    location ^~ /platform-api/ {
        client_max_body_size 16m;
        limit_req zone=image_pilot burst=12 nodelay;
        limit_req_status 429;
        proxy_pass http://127.0.0.1:8791;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 240s;
    }
'''
    nginx.write_text(before.replace('    location / { return 404; }',block+'    location / { return 404; }'))
    run(['nginx','-t'])
    for name,target in targets.items():
        if not name.startswith('web/'):continue
        tmp=target.with_name(target.name+'.shared-new');shutil.copy2(ROOT/name,tmp);tmp.chmod(0o644);os.replace(tmp,target)
    assert all(hashlib.sha256((site/p/'payment-qr.png').read_bytes()).hexdigest()==qr[p] for p in qr)
    run(['systemctl','enable','skill-platform'])
    run(['systemctl','reload','nginx'])
except Exception:
    run(['systemctl','stop','skill-platform'])
    for name,target in targets.items():
        if original[name]:shutil.copy2(backup/name,target)
        else:target.unlink(missing_ok=True)
    run(['systemctl','daemon-reload'])
    run(['systemctl','restart','image-assistant','temu-image-assistant','skill-monitor'])
    run(['nginx','-t']);run(['systemctl','reload','nginx'])
    raise
record=dict(deployed=True,version='0.5.0',backup=str(backup),old_balances_sha256=checks,
    old_balances_unchanged=True,qr_unchanged=True,new_user_uses=0,actual_payments=0,
    shared_paid_wallet=True,xhs_free=True,real_provider_generation_tested=False)
(ROOT/'deployment.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
