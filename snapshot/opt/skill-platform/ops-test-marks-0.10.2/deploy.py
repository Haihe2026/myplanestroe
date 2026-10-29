import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path('/opt/skill-platform/ops-test-marks-0.10.2')
WEB=Path('/opt/skill-platform/member-0.5.0/ops-web')
DROP=Path('/etc/systemd/system/skill-monitor.service.d/zzzzzzzz-test-order-marks.conf')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'manifest.json').read_text())
assert not DROP.exists(),'Existing rollout must be handled separately'
for name,h in m.items():
    assert sha(WEB/name)==h['before'],'Live static baseline changed: '+name
    assert sha(ROOT/'web'/name)==h['after']
for name in ('run_ops.py','test_mark.py'):compile((ROOT/name).read_bytes(),name,'exec')
backup=Path('/var/backups/skill-monitor')/('test-order-marks-'+str(int(time.time())))
backup.mkdir(parents=True,mode=0o700)
for name in m:shutil.copy2(WEB/name,backup/name)
(backup/'previous-exec.txt').write_text(subprocess.check_output(['systemctl','show','skill-monitor','-p','ExecStart'],text=True))
try:
    for name in ('app.js','style.css','index.html'):
        temp=WEB/(name+'.0.10.2-new');shutil.copy2(ROOT/'web'/name,temp);temp.chmod(0o644);os.replace(temp,WEB/name)
    DROP.write_text('[Service]\nExecStart=\nExecStart=/opt/skill-platform/1.2.0/venv/bin/python /opt/skill-platform/ops-test-marks-0.10.2/run_ops.py --config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db --temu-source /opt/temu-image-assistant/0.2.2/service\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','restart','skill-monitor'],check=True)
    time.sleep(2)
    assert subprocess.check_output(['systemctl','is-active','skill-monitor'],text=True).strip()=='active'
    assert '/ops-test-marks-0.10.2/run_ops.py' in subprocess.check_output(['systemctl','show','skill-monitor','-p','ExecStart'],text=True)
except BaseException:
    for name in m:shutil.copy2(backup/name,WEB/name)
    DROP.unlink(missing_ok=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','restart','skill-monitor'],check=True)
    raise
result={'version':'0.10.2','deployed':True,'backup':str(backup),'admin_test_mark_enabled':True,'production_orders_marked':0,'payment_and_quota_rules_unchanged':True,'automations_changed':False}
(ROOT/'deployment.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
