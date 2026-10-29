"""Static-only guarded rollout. No service restart, account/order API or database write."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path('/opt/skill-platform/member-web-0.8.1')
WEB=Path('/var/www/image-assistant/membership')
assert Path(__file__).resolve().parent==ROOT
os.umask(0o077)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def immutable(manifest):
    for name,value in manifest['immutable'].items():assert sha(WEB/name)==value,'Existing asset drift: '+name


manifest=json.loads((ROOT/'web-manifest.json').read_text())
assert set(manifest['files'])=={'gemini/index.html','gemini/manual-payment.js'}
immutable(manifest)
for name in manifest['files']:
    assert sha(WEB/name)==manifest['previous'][name],'Live baseline drift: '+name
    assert sha(ROOT/'web'/name)==manifest['new'][name]
backup=Path('/var/backups/image-assistant')/('payment-return-web-0.8.1-'+str(int(time.time())))
backup.mkdir(parents=True)
for name in manifest['files']:
    destination=backup/name;destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(WEB/name,destination)
try:
    for name in sorted(manifest['files'],key=lambda value:value.endswith('.html')):
        destination=WEB/name;temporary=destination.with_name(destination.name+'.0.8.1-new')
        shutil.copy2(ROOT/'web'/name,temporary);temporary.chmod(0o644);os.replace(temporary,destination)
    immutable(manifest)
    for name in manifest['files']:assert sha(WEB/name)==manifest['new'][name]
    services=['nginx','skill-platform','image-assistant','temu-image-assistant','skill-order-mail']
    result=subprocess.run(['systemctl','is-active',*services],check=True,capture_output=True,text=True)
    assert result.stdout.splitlines()==['active']*len(services)
except Exception:
    for name in manifest['files']:shutil.copy2(backup/name,WEB/name)
    raise
record=dict(version='0.8.1',deployed=True,backup=str(backup),static_files=manifest['files'],
            services_restarted=False,database_writes=False,qr_and_payment_apis_unchanged=True,
            native_workbuddy_close_and_wakeup_tested=False,real_payments=0)
(ROOT/'deployment.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
