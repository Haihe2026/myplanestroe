"""Guarded common catalog deployment; no order or balance migrations."""
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

ROOT=Path('/opt/skill-platform/member-0.10.14')
WEB=Path('/var/www/image-assistant/membership')
OPS=Path('/opt/skill-platform/member-0.5.0/ops-web')
DBS={'shared':'/var/lib/skill-platform/shared.db','gemini':'/var/lib/image-assistant/pilot.db','temu':'/var/lib/temu-image-assistant/trial.db'}
SERVICES=['skill-platform','skill-monitor','skill-order-mail','image-assistant','temu-image-assistant']
DROPINS={s:Path('/etc/systemd/system')/(s+'.service.d/zzzzzzzzzzzz-common-0.10.14.conf') for s in SERVICES[:3]}
COMMANDS={
 'skill-platform':'/opt/skill-platform/1.2.0/venv/bin/python '+str(ROOT/'service/run_shared.py')+' --db /var/lib/skill-platform/shared.db --gemini-db /var/lib/image-assistant/pilot.db --temu-db /var/lib/temu-image-assistant/trial.db --temu-source /opt/temu-image-assistant/0.2.2/service',
 'skill-monitor':'/opt/skill-platform/1.2.0/venv/bin/python '+str(ROOT/'ops-extension/run_ops.py')+' --config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db --temu-source /opt/temu-image-assistant/0.2.2/service',
 'skill-order-mail':'/opt/skill-platform/order-mail-0.6.0/venv/bin/python '+str(ROOT/'ops-extension/run_mail.py')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/'+path,timeout=5) as response:return json.load(response)
def process_started(service):
    pid=int(run(['systemctl','show',service,'-p','MainPID','--value']));assert pid>0
    stat=Path('/proc/'+str(pid)+'/stat').read_text()
    ticks=int(stat[stat.rfind(')')+1:].split()[19])
    return time.time()-(time.monotonic()-ticks/os.sysconf('SC_CLK_TCK'))
def snapshot(connection):
    result={}
    for table, in connection.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        assert table.replace('_','').isalnum()
        rows=[dict(row) for row in connection.execute('SELECT * FROM '+table)]
        result[table]=hashlib.sha256(json.dumps(sorted(rows,key=repr),sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
    return result

def main():
    assert Path(__file__).parent==ROOT and all(not p.exists() for p in DROPINS.values())
    manifest=json.loads((ROOT/'manifest.json').read_text())
    for name,h in manifest['baseline'].items():assert sha(Path(name))==h,'Live baseline changed: '+name
    for name in manifest['new_web']:assert not (WEB/name).exists(),'New asset already exists: '+name
    for name,h in manifest['staged'].items():assert sha(ROOT/name)==h,'Stage mismatch: '+name
    for service in COMMANDS:assert '/opt/skill-platform/member-0.10.13/' in run(['systemctl','show',service,'-p','ExecStart','--value'])
    historical=0
    for _ in range(30):
        active=0;historical=0
        for name,db in DBS.items():
            started=process_started({'shared':'skill-platform','gemini':'image-assistant','temu':'temu-image-assistant'}[name])
            with closing(sqlite3.connect(Path(db).as_uri()+'?mode=ro',uri=True)) as c:
                active+=c.execute("SELECT count(*) FROM jobs WHERE status='pending' AND created>=?",(started-1,)).fetchone()[0]
                historical+=c.execute("SELECT count(*) FROM jobs WHERE status='pending' AND created<?",(started-1,)).fetchone()[0]
        busy=any(run(['ss','-Htan','state','established','( sport = :'+str(port)+' )']) for port in (8791,8787,8788))
        if not active and not busy:break
        time.sleep(2)
    else:raise RuntimeError('Active generation; deployment not started')
    backup=Path('/var/backups/image-assistant')/('common-0.10.14-'+str(int(time.time())))
    backup.mkdir(mode=0o700)
    targets={**{'web/'+n:WEB/n for n in manifest['web']},**{'ops-web/'+n:OPS/n for n in manifest['ops_web']}}
    immutable={str(p):sha(p) for root in (WEB,OPS) for p in root.rglob('*') if p.is_file() and p not in targets.values()}
    for name,target in targets.items():
        if target.exists():
            p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,p)
    stopped=False
    try:
        # Freeze all writers for backups and explicit proof that deploy performs no DB migration.
        run(['systemctl','stop',*SERVICES]);stopped=True
        snapshots={}
        for name,db in DBS.items():
            with closing(sqlite3.connect(Path(db).as_uri()+'?mode=ro',uri=True)) as source:
                source.row_factory=sqlite3.Row;snapshots[name]=snapshot(source)
                with closing(sqlite3.connect(backup/(name+'.db'))) as target:source.backup(target)
        for directory in ('core','service','ops','ops-extension'):
            for p in [ROOT/directory,*(ROOT/directory).rglob('*')]:p.chmod(0o755 if p.is_dir() else 0o644)
        ROOT.chmod(0o755)
        for name,target in targets.items():
            temp=target.with_name(target.name+'.common-0.10.14.tmp');assert not temp.exists()
            shutil.copy2(ROOT/name,temp);temp.chmod(0o644);os.replace(temp,target)
        for service,p in DROPINS.items():p.write_text('[Service]\nExecStart=\nExecStart='+COMMANDS[service]+'\n');p.chmod(0o644)
        for name,db in DBS.items():
            with closing(sqlite3.connect(Path(db).as_uri()+'?mode=ro',uri=True)) as c:
                c.row_factory=sqlite3.Row;assert snapshot(c)==snapshots[name],'Business DB changed during deployment'
        run(['systemctl','daemon-reload']);run(['systemctl','start','skill-platform','image-assistant','temu-image-assistant'])
        for _ in range(20):
            try:
                assert get('gemini/health')['version']=='0.10.14';break
            except Exception:time.sleep(1)
        else:raise RuntimeError('New gateway health failed')
        for product in ('gemini','temu','xhs'):
            plans=get(product+'/membership-api/plans')['plans']
            if product=='temu':
                assert [p['id'] for p in plans]==['temu_permanent_'+p for p in ('89','198','365')]
                assert [(p['price_fen'],p['images']) for p in plans]==[(8900,180),(19800,400),(36500,730)]
            else:
                assert [p['id'] for p in plans]==['shared_permanent_'+p for p in ('29','39','49','999')]
                assert [(p['price_fen'],p['images']) for p in plans]==[(2900,60),(3900,80),(4900,100),(99900,2000)]
            assert all(p['period']=='permanent' and p['valid_days'] is None for p in plans)
        run(['systemctl','start','skill-monitor','skill-order-mail']);time.sleep(2)
        assert run(['systemctl','is-active',*SERVICES,'nginx']).splitlines()==['active']*6
        for service in COMMANDS:assert str(ROOT) in run(['systemctl','show',service,'-p','ExecStart','--value'])
        assert all(sha(Path(p))==h for p,h in immutable.items())
        assert all(sha(target)==manifest['staged'][name] for name,target in targets.items())
    except Exception:
        if stopped:
            run(['systemctl','stop',*SERVICES])
            for name,target in targets.items():
                old=backup/name
                if old.exists():shutil.copy2(old,target)
                else:target.unlink(missing_ok=True)
            for p in DROPINS.values():p.unlink(missing_ok=True)
            run(['systemctl','daemon-reload']);run(['systemctl','start',*SERVICES])
        raise
    record=dict(version='0.10.14',deployed=True,backup=str(backup),common_catalog=['29/60','39/80','49/100','999/2000'],temu_enterprise_catalog=['89/180','198/400','365/730'],temu_separate_page=True,permanent=True,old_orders_and_balances_unchanged=True,no_db_migration=True,historical_pending_preserved=historical,qr_unchanged=True,mail_identity_and_command_unchanged=True,real_orders_created=0,real_generations=0,services_active=True)
    (ROOT/'deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));print(json.dumps(record,ensure_ascii=False))

if __name__=='__main__':main()
