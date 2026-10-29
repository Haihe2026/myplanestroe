"""Guarded deployment, never run by tests or import. --check performs reads only.
No database snapshot is restored on rollback: later customer writes must survive.
"""
from pathlib import Path
import argparse,json,subprocess,sqlite3,shutil,time,urllib.request,os
OLD_ENTRY=Path('/opt/skill-platform/member-0.10.38-candidate/run_shared.py')
NEW=Path('/opt/skill-platform/member-0.10.39')
DB=Path('/var/lib/skill-platform/shared.db')
WEB=Path('/var/www/image-assistant/membership/pet')
SOURCE=Path(__file__).resolve().parents[1]
UNIT=Path('/etc/systemd/system/skill-platform.service.d')
def run(*args):return subprocess.check_output(args,text=True).strip()
def preflight():
    if not OLD_ENTRY.is_file():raise RuntimeError('Missing actual prior entry: '+str(OLD_ENTRY))
    entry=run('systemctl','show','skill-platform','-p','ExecStart','--value')
    if str(OLD_ENTRY) not in entry:raise RuntimeError('Baseline differs; refusing to overwrite the current service')
    if not DB.is_file():raise RuntimeError('Missing shared DB')
    if NEW.exists():raise RuntimeError('Version directory already exists; inspect it before deploying')
    for n in ['run_shared.py','pet_billing.py','pet_gateway.py','pet_vision.py','product_config.py','pet-config.json']:
        if not (SOURCE/n).is_file():raise RuntimeError('Missing source '+n)
        if n.endswith('.py'):compile((SOURCE/n).read_text(encoding='utf-8-sig'),n,'exec')
    if not (SOURCE/'web/membership/pet/index.html').is_file():raise RuntimeError('Missing pages')
    # Do not assume the old nginx product allowlist includes the new prefix.
    nginx=run('nginx','-T')
    if '/platform-api/pet/' not in nginx and '(gemini|temu|xhs|pet)' not in nginx:
        raise RuntimeError('Nginx pet route not configured. Add the reviewed exact pet location before deployment; no automatic regex rewrite.')
    names=sorted(p.name for p in UNIT.glob('*.conf'))
    name='z'*(max([len(s)-len(s.lstrip('z')) for s in names],default=0)+1)+'-pet-0.10.39.conf'
    if len(name)>240:raise RuntimeError('Drop-in name too long; review service configuration')
    return {'old_entry':str(OLD_ENTRY),'dropin':str(UNIT/name),'old_execstart':entry,'existing_dropins':names}
def health(expect_pet=True):
    """Deployment and rollback share the same bounded startup wait."""
    for attempt in range(20):
        try:
            products=('pet','gemini','temu') if expect_pet else ('gemini','temu')
            for product in products:
                with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/'+product+'/health',timeout=2) as response:
                    data=json.loads(response.read())
                if data.get('status')!='ok':raise RuntimeError('Unhealthy '+product)
                if product=='pet' and (data.get('version')!='0.10.39' or data.get('isolated_quota') is not True):raise RuntimeError('Wrong pet service')
            return
        except Exception:
            if attempt<19:time.sleep(.5)
    raise RuntimeError('Pet/image health checks failed' if expect_pet else 'Prior service health checks failed after startup retries')

def restore_pages(backup,manifest):
    """Restore the complete saved page set, independent of service availability."""
    errors=[]
    saved=backup/'pages'
    # Restore even a backed-up file which no longer exists in the web directory.
    if saved.is_dir():
        for old in saved.rglob('*'):
            if not old.is_file():continue
            target=WEB/old.relative_to(saved)
            try:
                target.parent.mkdir(parents=True,exist_ok=True)
                temp=target.with_name(target.name+'.rollback-new')
                shutil.copy2(old,temp);os.replace(temp,target)
            except Exception as error:errors.append('restore '+str(target)+': '+str(error))
    for name in manifest['new_pages']:
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            errors.append('Invalid page path in rollback manifest');continue
        target=WEB/relative
        if (saved/relative).is_file():continue
        try:
            if target.is_file():target.unlink()
        except Exception as error:errors.append('remove '+str(target)+': '+str(error))
    if errors:raise RuntimeError('; '.join(errors))

def rollback(backup):
    m=json.loads((backup/'manifest.json').read_text());drop=Path(m['dropin'])
    if drop.parent!=UNIT or not drop.name.endswith('-pet-0.10.39.conf'):raise RuntimeError('Invalid rollback manifest')
    current=run('systemctl','show','skill-platform','-p','ExecStart','--value')
    if str(NEW/'run_shared.py') not in current and str(OLD_ENTRY) not in current:raise RuntimeError('A newer service is active; manual rollback review required')
    errors=[]
    try:
        if drop.exists():drop.unlink()
    except Exception as error:errors.append('drop-in removal: '+str(error))
    # Always attempt pages BEFORE service restart/health, including when drop removal fails.
    try:restore_pages(backup,m)
    except Exception as error:errors.append('page restoration: '+str(error))
    try:
        run('systemctl','daemon-reload');run('systemctl','restart','skill-platform')
        active=run('systemctl','show','skill-platform','-p','ExecStart','--value')
        if str(OLD_ENTRY) not in active:raise RuntimeError('Prior full candidate entry did not return')
        health(expect_pet=False)
    except Exception as error:errors.append('service restoration: '+str(error))
    if errors:raise RuntimeError('Rollback needs attention; page restoration was attempted independently; shared DB untouched. '+ '; '.join(errors))
    print('Rolled back code/pages and verified prior service health. Shared DB kept, including all later orders and pet history.')

def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group();g.add_argument('--check',action='store_true');g.add_argument('--rollback',type=Path);args=parser.parse_args()
    if args.rollback:return rollback(args.rollback.resolve())
    m=preflight()
    if args.check:print(json.dumps(m,indent=2));return
    backup=Path('/var/backups/myplanestore/pet-0.10.39-'+str(int(time.time())));backup.mkdir(parents=True,mode=0o700)
    # sqlite backup captures committed WAL data consistently; never copy only shared.db.
    with sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(backup/'shared.db') as dest:source.backup(dest)
    os.chmod(backup/'shared.db',0o600)
    if WEB.exists():shutil.copytree(WEB,backup/'pages')
    pages=list((SOURCE/'web/membership/pet').rglob('*'));m['new_pages']=[str(p.relative_to(SOURCE/'web/membership/pet')) for p in pages if p.is_file()]
    (backup/'manifest.json').write_text(json.dumps(m,indent=2))
    NEW.mkdir()
    for p in SOURCE.iterdir():
        if p.name in ('run_shared.py','run_ops.py','pet_billing.py','pet_gateway.py','pet_vision.py','pet_vision_adapter.py','pet_triage.py','product_config.py','pet-config.json','pet_ops.py','pet-orders.js'):shutil.copy2(p,NEW/p.name)
    try:
        Path(m['dropin']).write_text('[Service]\nExecStart=\nExecStart=/opt/skill-platform/1.2.0/venv/bin/python '+str(NEW/'run_shared.py')+' --db '+str(DB)+' --gemini-db /var/lib/image-assistant/pilot.db --temu-db /var/lib/temu-image-assistant/trial.db --temu-source /opt/temu-image-assistant/0.2.2/service\n')
        run('systemctl','daemon-reload');run('systemctl','restart','skill-platform');health()
        for p in pages:
            if p.is_file():
                target=WEB/p.relative_to(SOURCE/'web/membership/pet');target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.new');shutil.copyfile(p,temp);os.chmod(temp,0o644);os.replace(temp,target)
    except Exception:rollback(backup);raise
    print(json.dumps({'backup':str(backup),'version':'0.10.39','payments':'remain disabled until pet operator adapter acceptance','vision':'disabled unless adapter, reviewer, file key and flag are all ready'}))
if __name__=='__main__':main()
