"""Narrow Temu entry/key rollout; never changes QR, settlement, or financial rows."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

ROOT=Path('/opt/skill-platform/member-0.10.1')
OLD=Path('/opt/skill-platform/member-0.10.0')
WEB=Path('/var/www/image-assistant/membership')
DROPIN=Path('/etc/systemd/system/skill-platform.service.d/81-temu-0.10.1.conf')
DBS={'shared':'/var/lib/skill-platform/shared.db','gemini':'/var/lib/image-assistant/pilot.db','temu':'/var/lib/temu-image-assistant/trial.db'}
FILES=['temu/register/index.html','temu/register/register.js','temu/register/register.css']
IMMUTABLE=['gemini/payment-qr.png','temu/payment-qr.png','gemini/manual-payment.js','temu/manual-payment.js','gemini/index.html','temu/index.html','account-center.js']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()

def health(product):
    with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/'+product+'/health',timeout=5) as response:return json.load(response)

def snapshot(path):
    with closing(sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        return {t:hashlib.sha256('\n'.join(sorted(json.dumps(r,default=str,separators=(',',':')) for r in db.execute('SELECT * FROM '+t))).encode()).hexdigest() for t, in db.execute("SELECT name FROM sqlite_master WHERE type='table'") if t.replace('_','').isalnum()}

def main():
    assert Path(__file__).resolve().parent==ROOT and not DROPIN.exists()
    manifest=json.loads((ROOT/'manifest.json').read_text())
    assert str(OLD/'service/run_shared.py') in run(['systemctl','show','skill-platform','-p','ExecStart','--value'])
    for name,digest in manifest['baseline'].items():assert sha(OLD/name)==digest,'Baseline drift: '+name
    for name,digest in manifest['staged'].items():assert sha(ROOT/name)==digest,'Staged mismatch: '+name
    for name in FILES:assert not (WEB/name).exists(),'Existing Temu registration page must not be overwritten'
    immutable={name:sha(WEB/name) for name in IMMUTABLE}
    run(['/opt/skill-platform/1.2.0/venv/bin/python','-c',"import sys; sys.path[:0]=['/opt/skill-platform/member-0.10.1/service','/opt/skill-platform/member-0.10.1/core','/opt/skill-platform/member-0.10.1/ops']; import shared_platform,registration_entries,skill_access,telemetry"])
    for _ in range(20):
        with closing(sqlite3.connect(Path(DBS['shared']).as_uri()+'?mode=ro',uri=True)) as db:pending=db.execute("SELECT count(*) FROM jobs WHERE status='pending'").fetchone()[0]
        if not pending and not run(['ss','-Htan','state','established','( sport = :8791 )']):break
        time.sleep(2)
    else:raise RuntimeError('Gateway busy; no rollout performed')
    backup=Path('/var/backups/image-assistant')/('temu-entry-0.10.1-'+str(int(time.time())))
    backup.mkdir(parents=True,mode=0o700)
    try:
        run(['systemctl','stop','skill-platform'])
        before={p:snapshot(db) for p,db in DBS.items()}
        for product,path in DBS.items():
            with closing(sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)) as source:
                with closing(sqlite3.connect(backup/(product+'.db'))) as target:source.backup(target)
        ROOT.chmod(0o755)
        for directory in ('core','service','ops'):
            for p in [ROOT/directory,*(ROOT/directory).rglob('*')]:p.chmod(0o755 if p.is_dir() else 0o644)
        for name in FILES:
            target=WEB/name;target.parent.mkdir(parents=True,exist_ok=True);target.parent.chmod(0o755)
            shutil.copy2(ROOT/'web'/name,target);target.chmod(0o644)
        DROPIN.write_text('[Service]\nExecStart=\nExecStart=/opt/skill-platform/1.2.0/venv/bin/python /opt/skill-platform/member-0.10.1/service/run_shared.py --db /var/lib/skill-platform/shared.db --gemini-db /var/lib/image-assistant/pilot.db --temu-db /var/lib/temu-image-assistant/trial.db --temu-source /opt/temu-image-assistant/0.2.2/service\n')
        DROPIN.chmod(0o644);run(['systemctl','daemon-reload']);run(['systemctl','start','skill-platform'])
        for _ in range(15):
            try:
                assert all(health(p)['version']=='0.10.1' for p in ('gemini','temu','xhs'));break
            except Exception:time.sleep(1)
        else:raise RuntimeError('Gateway failed health check')
        assert all(sha(WEB/p)==digest for p,digest in immutable.items()),'Checkout changed'
        after={p:snapshot(db) for p,db in DBS.items()}
        assert before==after,'Database state changed; no database rollback is permitted'
        services=['skill-platform','skill-monitor','skill-order-mail','image-assistant','temu-image-assistant','nginx']
        assert run(['systemctl','is-active',*services]).splitlines()==['active']*len(services)
    except Exception:
        DROPIN.unlink(missing_ok=True)
        for name in FILES:(WEB/name).unlink(missing_ok=True)
        run(['systemctl','daemon-reload']);run(['systemctl','restart','skill-platform'])
        raise
    record=dict(version='0.10.1',deployed=True,backup=str(backup),account_financial_and_key_rows_unchanged=True,checkout_assets_unchanged=True,mail_worker_unchanged=True,added_static=FILES,actual_payments=0,actual_generation=0,services_active=True)
    (ROOT/'deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
    print(json.dumps(record,ensure_ascii=False))

if __name__=='__main__':main()
