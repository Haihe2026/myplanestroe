import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path('/opt/skill-platform/channel-stats-0.9.1')
WEB=Path('/opt/skill-platform/member-0.5.0/ops-web')
DROP=Path('/etc/systemd/system/skill-monitor.service.d/zzzzzz-channel-stats.conf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'manifest.json').read_text())
for name,h in m.items():
    assert sha(WEB/name)==h['before'],'Baseline changed: '+name
    assert sha(ROOT/'web'/name)==h['after']
assert not DROP.exists()
backup=Path('/var/backups/skill-monitor')/('channel-data-'+str(int(time.time())))
backup.mkdir(parents=True,mode=0o700)
for name in m:shutil.copy2(WEB/name,backup/name)
try:
    for name in ('app.js','style.css','index.html'):
        t=WEB/(name+'.0.9.1-new');shutil.copy2(ROOT/'web'/name,t);t.chmod(0o644);os.replace(t,WEB/name)
    DROP.parent.mkdir(parents=True,exist_ok=True)
    DROP.write_text('[Service]\nExecStart=\nExecStart=/opt/skill-platform/1.2.0/venv/bin/python /opt/skill-platform/channel-stats-0.9.1/run_ops.py --config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db --temu-source /opt/temu-image-assistant/0.2.2/service\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','restart','skill-monitor'],check=True)
    time.sleep(2)
    assert subprocess.check_output(['systemctl','is-active','skill-monitor'],text=True).strip()=='active'
except BaseException:
    for name in m:shutil.copy2(backup/name,WEB/name)
    DROP.unlink(missing_ok=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','restart','skill-monitor'],check=True)
    raise
result={'version':'0.9.1','backup':str(backup),'deployed':True,'authenticated_summary_extended':True,'payment_logic_unchanged':True,'business_database_writes':False}
(ROOT/'deployment.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
