import hashlib,json,os,shutil,time
from pathlib import Path
ROOT=Path('/opt/skill-platform/member-web-0.9.3')
WEB=Path('/var/www/image-assistant/membership')
m=json.loads((ROOT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in m['files']:
    path=WEB/name
    assert (sha(path) if path.exists() else None)==m['previous'][name],'Live baseline changed: '+name
    assert sha(ROOT/'web'/name)==m['new'][name]
backup=Path('/var/backups/image-assistant')/('brandbar-0.9.3-'+str(int(time.time())))
backup.mkdir(parents=True,mode=0o700)
for name in m['files']:
    if (WEB/name).exists():
        target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(WEB/name,target)
try:
    for name in sorted(m['files'],key=lambda name:name.endswith('.html')):
        target=WEB/name;temp=target.with_name(target.name+'.0.9.3-new')
        shutil.copy2(ROOT/'web'/name,temp);temp.chmod(0o644);os.replace(temp,target)
        assert sha(target)==m['new'][name]
except BaseException:
    for name in m['files']:
        if (backup/name).exists():shutil.copy2(backup/name,WEB/name)
        elif m['previous'][name] is None:(WEB/name).unlink(missing_ok=True)
    raise
result={'version':'0.9.3','deployed':True,'backup':str(backup),'files':m['files'],'services_restarted':False,'database_writes':False}
(ROOT/'deployment.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
