"""Guarded static-only manager view rollout."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path('/opt/skill-platform/ops-web-0.9.2')
WEB=Path('/opt/skill-platform/member-0.5.0/ops-web')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'manifest.json').read_text())
assert set(manifest)=={'index.html','app.js','style.css'}
for name,hashes in manifest.items():
    assert sha(WEB/name)==hashes['before'],'Live operations baseline changed: '+name
    assert sha(ROOT/'web'/name)==hashes['after']
backup=Path('/var/backups/skill-monitor')/('channels-page-'+str(int(time.time())))
backup.mkdir(parents=True,mode=0o700)
for name in manifest:shutil.copy2(WEB/name,backup/name)
try:
    for name in ('app.js','style.css','index.html'):
        target=WEB/name
        temporary=target.with_name(name+'.0.9.2-new')
        shutil.copy2(ROOT/'web'/name,temporary)
        temporary.chmod(0o644)
        os.replace(temporary,target)
        assert sha(target)==manifest[name]['after']
    assert subprocess.check_output(['systemctl','is-active','skill-monitor'],text=True).strip()=='active'
except BaseException:
    for name in manifest:shutil.copy2(backup/name,WEB/name)
    raise
result={'version':'0.9.2','deployed':True,'backup':str(backup),'files':list(manifest),'service_restarted':False,'database_writes':False,'workbuddy_selected_range_label':True}
(ROOT/'deployment.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
