"""Guarded enterprise rollout; no real orders, quota claims or generation in verification."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

ROOT=Path('/opt/skill-platform/member-0.10.3')
OLD=Path('/opt/skill-platform/member-0.10.1')
WEB=Path('/var/www/image-assistant/membership')
DBS={'shared':'/var/lib/skill-platform/shared.db','gemini':'/var/lib/image-assistant/pilot.db','temu':'/var/lib/temu-image-assistant/trial.db'}
DROPINS={
 'skill-platform':Path('/etc/systemd/system/skill-platform.service.d/90-enterprise-0.10.3.conf'),
 'skill-monitor':Path('/etc/systemd/system/skill-monitor.service.d/zzzzzzzzz-enterprise-0.10.3.conf'),
 'skill-order-mail':Path('/etc/systemd/system/skill-order-mail.service.d/90-enterprise-0.10.3.conf')}
COMMANDS={
 'skill-platform':'/opt/skill-platform/1.2.0/venv/bin/python '+str(ROOT/'service/run_shared.py')+' --db /var/lib/skill-platform/shared.db --gemini-db /var/lib/image-assistant/pilot.db --temu-db /var/lib/temu-image-assistant/trial.db --temu-source /opt/temu-image-assistant/0.2.2/service',
 'skill-monitor':'/opt/skill-platform/1.2.0/venv/bin/python '+str(ROOT/'ops-extension/run_ops.py')+' --config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db --temu-source /opt/temu-image-assistant/0.2.2/service',
 'skill-order-mail':'/opt/skill-platform/order-mail-0.6.0/venv/bin/python '+str(ROOT/'ops-extension/run_mail.py')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/'+path,timeout=5) as r:return json.load(r)
def snapshot(path):
    with closing(sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)) as c:
        c.execute('PRAGMA query_only=ON')
        return {t:hashlib.sha256('\n'.join(sorted(json.dumps(r,default=str,separators=(',',':')) for r in c.execute('SELECT * FROM '+t))).encode()).hexdigest() for t, in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if t.replace('_','').isalnum()}

def main():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    assert Path(__file__).parent==ROOT and all(not p.exists() for p in DROPINS.values())
    expected={'skill-platform':str(OLD/'service/run_shared.py'),'skill-monitor':'/opt/skill-platform/ops-test-marks-0.10.2/run_ops.py','skill-order-mail':'/opt/skill-platform/order-mail-0.6.2/event_runner.py'}
    for service,path in expected.items():assert path in run(['systemctl','show',service,'-p','ExecStart','--value'])
    for name,digest in manifest['baseline'].items():assert sha(Path(name))==digest,'Baseline drift: '+name
    for name,digest in manifest['staged'].items():assert sha(ROOT/name)==digest,'Stage mismatch: '+name
    immutable=['gemini/index.html','gemini/app.js','gemini/payment-qr.png','gemini/manual-payment.js','temu/payment-qr.png','account-center.js','xhs/index.html']
    unchanged={name:sha(WEB/name) for name in immutable}
    for _ in range(30):
        with closing(sqlite3.connect(Path(DBS['shared']).as_uri()+'?mode=ro',uri=True)) as c:pending=c.execute("SELECT count(*) FROM jobs WHERE status='pending'").fetchone()[0]
        if not pending and not run(['ss','-Htan','state','established','( sport = :8791 )']):break
        time.sleep(2)
    else:raise RuntimeError('Gateway busy; no rollout')
    backup=Path('/var/backups/image-assistant')/('temu-enterprise-0.10.3-'+str(int(time.time())))
    backup.mkdir(mode=0o700)
    web_names=[p.relative_to(ROOT/'web').as_posix() for p in (ROOT/'web').rglob('*') if p.is_file()]
    existed={name:(WEB/name).exists() for name in web_names}
    activated=False
    try:
        run(['systemctl','stop','skill-order-mail','skill-monitor','skill-platform'])
        before={k:snapshot(v) for k,v in DBS.items()}
        for name,db in DBS.items():
            with closing(sqlite3.connect(Path(db).as_uri()+'?mode=ro',uri=True)) as source:
                with closing(sqlite3.connect(backup/(name+'.db'))) as target:source.backup(target)
        for name in web_names:
            source=WEB/name
            if existed[name]:
                target=backup/'web'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        for directory in ('core','service','ops','ops-extension'):
            for p in [ROOT/directory,*(ROOT/directory).rglob('*')]:p.chmod(0o755 if p.is_dir() else 0o644)
        ROOT.chmod(0o755)
        for name in web_names:
            target=WEB/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'web'/name,target);target.chmod(0o644)
        for name,p in DROPINS.items():p.write_text('[Service]\nExecStart=\nExecStart='+COMMANDS[name]+'\n');p.chmod(0o644)
        activated=True
        run(['systemctl','daemon-reload']);run(['systemctl','start','skill-platform'])
        for _ in range(20):
            try:
                assert get('temu/health')['version']=='0.10.3';break
            except Exception:time.sleep(1)
        else:raise RuntimeError('New gateway health failed')
        assert [(p['price_fen'],p['images']) for p in get('temu/membership-api/plans')['plans']]==[(8900,100),(19800,240),(36500,500)]
        assert len(get('gemini/membership-api/plans')['plans'])==4
        after={k:snapshot(v) for k,v in DBS.items()}
        assert all(all(after[k].get(t)==h for t,h in tables.items()) for k,tables in before.items()),'Existing business rows changed'
        added=set(after['shared'])-set(before['shared'])
        assert added=={'temu_enterprise_trials','temu_trial_jobs','temu_customer_feedback'}
        with closing(sqlite3.connect(DBS['shared'])) as c:
            assert all(c.execute('SELECT count(*) FROM '+t).fetchone()[0]==0 for t in added)
        run(['systemctl','start','skill-monitor','skill-order-mail'])
        time.sleep(2)
        services=['skill-platform','skill-monitor','skill-order-mail','image-assistant','temu-image-assistant','nginx']
        assert run(['systemctl','is-active',*services]).splitlines()==['active']*len(services)
        assert all(sha(WEB/p)==h for p,h in unchanged.items())
    except Exception:
        if activated:
            run(['systemctl','stop','skill-platform','skill-monitor','skill-order-mail'])
            for p in DROPINS.values():p.unlink(missing_ok=True)
            for name in web_names:
                if existed[name] and (backup/'web'/name).exists():shutil.copy2(backup/'web'/name,WEB/name)
                elif not existed[name]:(WEB/name).unlink(missing_ok=True)
            run(['systemctl','daemon-reload'])
        run(['systemctl','start','skill-platform','skill-monitor','skill-order-mail'])
        raise
    record=dict(version='0.10.3',deployed=True,backup=str(backup),existing_rows_unchanged_at_migration=True,new_tables=sorted(added),gemini_plans_unchanged=True,qr_images_unchanged=True,mail_catalog_extended_only=True,services_active=True,real_orders_created=0,real_generations=0,production_trial_claims=0)
    (ROOT/'deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
    print(json.dumps(record,ensure_ascii=False))

if __name__=='__main__':main()
