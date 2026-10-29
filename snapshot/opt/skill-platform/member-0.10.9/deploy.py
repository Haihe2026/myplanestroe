"""Guarded rollout with exact expiry-only migration and business-data invariants."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request

ROOT=Path('/opt/skill-platform/member-0.10.9')
WEB=Path('/var/www/image-assistant/membership')
OPS=Path('/opt/skill-platform/member-0.5.0/ops-web')
DBS={'shared':'/var/lib/skill-platform/shared.db','gemini':'/var/lib/image-assistant/pilot.db','temu':'/var/lib/temu-image-assistant/trial.db'}
DROPINS={service:Path('/etc/systemd/system')/(service+'.service.d/zzzzzzzzzz-permanent-0.10.9.conf') for service in ('skill-platform','skill-monitor','skill-order-mail')}
COMMANDS={
 'skill-platform':'/opt/skill-platform/1.2.0/venv/bin/python '+str(ROOT/'service/run_shared.py')+' --db /var/lib/skill-platform/shared.db --gemini-db /var/lib/image-assistant/pilot.db --temu-db /var/lib/temu-image-assistant/trial.db --temu-source /opt/temu-image-assistant/0.2.2/service',
 'skill-monitor':'/opt/skill-platform/1.2.0/venv/bin/python '+str(ROOT/'ops-extension/run_ops.py')+' --config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db --temu-source /opt/temu-image-assistant/0.2.2/service',
 'skill-order-mail':'/opt/skill-platform/order-mail-0.6.0/venv/bin/python '+str(ROOT/'ops-extension/run_mail.py')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/'+path,timeout=5) as response:return json.load(response)
def digest_rows(rows):return hashlib.sha256(json.dumps(sorted(rows,key=repr),sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()
def snapshot(connection,normalize=()):
    result={};normalized=set(normalize)
    for table, in connection.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        assert table.replace('_','').isalnum()
        rows=[dict(r) for r in connection.execute('SELECT * FROM '+table)]
        if table=='member_grants':
            for row in rows:
                if row['order_id'] in normalized:row['expires']=None
        result[table]=digest_rows(rows)
    return result

def main():
    assert Path(__file__).parent==ROOT and all(not p.exists() for p in DROPINS.values())
    manifest=json.loads((ROOT/'manifest.json').read_text())
    for name,h in manifest['baseline'].items():assert sha(Path(name))==h,'Live baseline drift: '+name
    for name,h in manifest['staged'].items():assert sha(ROOT/name)==h,'Staged mismatch: '+name
    expected={'skill-platform':'/opt/skill-platform/member-0.10.3/service/run_shared.py',
              'skill-monitor':'/opt/skill-platform/member-0.10.3/ops-extension/run_ops.py',
              'skill-order-mail':'/opt/skill-platform/order-mail-0.6.2/event_runner.py'}
    for service,path in expected.items():assert path in run(['systemctl','show',service,'-p','ExecStart','--value'])
    for _ in range(30):
        pending=0
        for db in (DBS['shared'],DBS['gemini']):
            with closing(sqlite3.connect(Path(db).as_uri()+'?mode=ro',uri=True)) as c:pending+=c.execute("SELECT count(*) FROM jobs WHERE status='pending'").fetchone()[0]
        if not pending and not run(['ss','-Htan','state','established','( sport = :8791 )']):break
        time.sleep(2)
    else:raise RuntimeError('Generation service busy; no rollout')
    backup=Path('/var/backups/image-assistant')/('permanent-0.10.9-'+str(int(time.time())))
    backup.mkdir(mode=0o700)
    targets={**{'web/'+n:WEB/n for n in manifest['web']},**{'ops-web/'+n:OPS/n for n in ('index.html','app.js')}}
    immutable={str(p):sha(p) for root in (WEB,OPS) for p in root.rglob('*') if p.is_file() and p not in targets.values()}
    for name,target in targets.items():
        p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,p)
    migrations={};activated=False;stopped=False
    sys.path.insert(0,str(ROOT/'core'))
    from migrate_permanent import migrate
    try:
        run(['systemctl','stop','skill-order-mail','skill-monitor','skill-platform','image-assistant']);stopped=True
        for name,db in DBS.items():
            with closing(sqlite3.connect(Path(db).as_uri()+'?mode=ro',uri=True)) as source:
                with closing(sqlite3.connect(backup/(name+'.db'))) as target:source.backup(target)
        cutoff=int(time.time())
        for name in ('shared','gemini'):
            with closing(sqlite3.connect(DBS[name])) as c,c:
                c.row_factory=sqlite3.Row;c.execute('BEGIN IMMEDIATE')
                before=snapshot(c)
                changes=migrate(c,cutoff)
                migrations[name]=changes
                with closing(sqlite3.connect(backup/(name+'.db'))) as old:
                    old.row_factory=sqlite3.Row
                    expected=snapshot(old,[r['order_id'] for r in changes])
                assert snapshot(c)==expected,'Unexpected business change: '+name
        (backup/'migration-undo.json').write_text(json.dumps(migrations))
        for directory in ('core','service','ops','ops-extension'):
            for p in [ROOT/directory,*(ROOT/directory).rglob('*')]:p.chmod(0o755 if p.is_dir() else 0o644)
        ROOT.chmod(0o755)
        for name,target in targets.items():
            temp=target.with_name(target.name+'.permanent-0.10.9.tmp');assert not temp.exists()
            shutil.copy2(ROOT/name,temp);temp.chmod(0o644);os.replace(temp,target)
        for service,p in DROPINS.items():p.write_text('[Service]\nExecStart=\nExecStart='+COMMANDS[service]+'\n');p.chmod(0o644)
        activated=True;run(['systemctl','daemon-reload']);run(['systemctl','start','skill-platform','image-assistant'])
        for _ in range(20):
            try:
                assert get('gemini/health')['version']=='0.10.9';break
            except Exception:time.sleep(1)
        else:raise RuntimeError('Gateway health not ready')
        regular=get('gemini/membership-api/plans')['plans'];temu=get('temu/membership-api/plans')['plans']
        assert [(p['price_fen'],p['images']) for p in regular]==[(2900,60),(3900,80),(4900,100),(99900,2000)]
        assert all(p['period']=='permanent' and p['valid_days'] is None for p in regular)
        assert [(p['price_fen'],p['images'],p['period']) for p in temu]==[(8900,100,'month'),(19800,240,'month'),(36500,500,'month')]
        run(['systemctl','start','skill-monitor','skill-order-mail'])
        time.sleep(2)
        services=['skill-platform','skill-monitor','skill-order-mail','image-assistant','temu-image-assistant','nginx']
        assert run(['systemctl','is-active',*services]).splitlines()==['active']*len(services)
        for service,command in COMMANDS.items():assert str(ROOT) in run(['systemctl','show',service,'-p','ExecStart','--value'])
        assert all(sha(Path(p))==h for p,h in immutable.items())
    except Exception:
        if stopped:
            run(['systemctl','stop','skill-platform','skill-monitor','skill-order-mail','image-assistant'])
            for name,changes in migrations.items():
                with closing(sqlite3.connect(DBS[name])) as c,c:
                    for row in changes:c.execute('UPDATE member_grants SET expires=? WHERE order_id=? AND expires IS NULL',(row['expires'],row['order_id']))
            for name,target in targets.items():shutil.copy2(backup/name,target)
            for p in DROPINS.values():p.unlink(missing_ok=True)
            run(['systemctl','daemon-reload']);run(['systemctl','start','skill-platform','image-assistant','skill-monitor','skill-order-mail'])
        raise
    record=dict(version='0.10.9',deployed=True,backup=str(backup),gemini_plans=[dict(price_fen=p['price_fen'],uses=p['images'],period=p['period']) for p in regular],old_grants_extended={name:len(rows) for name,rows in migrations.items()},old_units_and_balances_unchanged=True,expired_grants_not_restored=True,temu_plans_unchanged=True,qr_assets_unchanged=True,mail_authentication_unchanged=True,real_orders_created=0,real_generations=0,services_active=True)
    (ROOT/'deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
    print(json.dumps(record,ensure_ascii=False))

if __name__=='__main__':main()
