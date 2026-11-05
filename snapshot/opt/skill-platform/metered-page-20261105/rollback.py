from pathlib import Path
import sys,subprocess,json
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'0.10.20'))
from capture import SSH
backup=json.loads((R/'deployment-receipt.json').read_text(encoding='utf-8'))['backup']
code=r'''
from pathlib import Path
import json,shutil,subprocess,time,urllib.request
b=Path(BACKUP);assert b.is_dir() and str(b).startswith('/var/backups/myplanestore/metered-page-')
m=json.loads((b/'manifest.json').read_text());drop=Path((b/'drop-in.txt').read_text());assert drop.parent==Path('/etc/systemd/system/skill-platform.service.d')
try:drop.unlink(missing_ok=True)
finally:
 for p,existed in m.items():
  path=Path(p)
  if existed:shutil.copy2(b/p.lstrip('/'),path)
  else:path.unlink(missing_ok=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
for n in ['skill-platform','skill-monitor']:subprocess.run(['systemctl','restart',n],check=True)
for i in range(25):
 try:
  for port,path in [(8791,'/platform-api/listing/v1/pricing'),(8791,'/platform-api/grok-video/health'),(8790,'/ops/')]:
   with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as x:assert x.status==200
  print('Rollback healthy; pages restored; ledgers retained');break
 except Exception:
  if i==24:raise
  time.sleep(1)
'''.replace('BACKUP',repr(backup))
p=subprocess.run(SSH+['python3 -'],input=code,text=True,capture_output=True,encoding='utf-8',timeout=110);print(p.stdout);print(p.stderr);p.check_returncode()
