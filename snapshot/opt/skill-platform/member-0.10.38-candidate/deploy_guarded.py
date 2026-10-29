"""Guarded activation. No orders, balances or existing credentials modified."""
from pathlib import Path
import hashlib
import base64
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import time
import urllib.request

run=lambda args:subprocess.check_output(args,text=True).strip()
root=Path('/opt/skill-platform/member-0.10.38-candidate')
pid=run(['systemctl','show','skill-platform','-p','MainPID','--value'])
args=[s.decode() for s in Path('/proc/'+pid+'/cmdline').read_bytes().split(bytes([0])) if s]
old='/opt/skill-platform/member-0.10.36-candidate/run_shared.py'
assert old in args,'Concurrent service change'
drop=Path('/etc/systemd/system/skill-platform.service.d')/('z'*68+'-photo-consent-0.10.38.conf')
assert not drop.exists()
assert all(drop.name>p.name for p in drop.parent.glob('*.conf'))
webroot=Path('/var/www/image-assistant/membership')
files=json.loads((root/'web-payload.json').read_text())
oldweb={}
for f in files:
 p=webroot/f['file'];oldweb[p]=p.read_bytes() if p.exists() else None
 actual=hashlib.sha256(oldweb[p]).hexdigest() if oldweb[p] is not None else None
 assert actual==f['before'],'Concurrent web change: '+f['file']
nginx=Path('/etc/nginx/conf.d/image-assistant.conf');original=nginx.read_bytes()
anchor=b'    server_tokens off;\n';assert original.count(anchor)==1
backup=Path('/var/backups/skill-platform')/('photo-consent-0.10.38-'+str(int(time.time())))
backup.mkdir(mode=0o700)
db='/var/lib/skill-platform/shared.db'
src=sqlite3.connect(db);dst=sqlite3.connect(backup/'shared.db');src.backup(dst);src.close();dst.close()
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/'+path,timeout=8) as r:return json.load(r)
plans=get('gemini/membership-api/plans')
health=get('gemini/health')
(backup/'nginx.conf').write_bytes(original)
def replace(path,data):
    tmp=path.with_name(path.name+'.baby32.tmp');tmp.write_bytes(data);tmp.chmod(0o644);os.replace(tmp,path)
def workers():
    p=run(['systemctl','show','nginx','-p','MainPID','--value'])
    return [x for x in Path('/proc/'+p+'/task/'+p+'/children').read_text().split() if Path('/proc/'+x+'/cmdline').exists() and b'nginx: worker process' in Path('/proc/'+x+'/cmdline').read_bytes()]
activated=False;gated=False
try:
    for p,raw in oldweb.items():
        if raw is not None:
            b=backup/'web'/p.relative_to(webroot);b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(raw)
    active=workers()
    replace(nginx,original.replace(anchor,anchor+b'    if ($uri ~ "^/platform-api/") { return 503; }\n',1));gated=True
    run(['nginx','-t']);run(['systemctl','reload','nginx'])
    # Stop if an actual request is still active; do not kill image generation.
    deadline=time.monotonic()+20
    while any(Path('/proc/'+p).exists() for p in active):
        if time.monotonic()>deadline:raise RuntimeError('Active requests did not drain; deployment postponed')
        time.sleep(.25)
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT count(*) FROM jobs WHERE status='pending' AND created>?",(time.time()-600,)).fetchone()[0]==0,'Recent unresolved jobs; postpone'
    # Existing page bytes already verified; retain original page
    drop.write_text('[Service]\nExecStart=\nExecStart='+shlex.join([str(root/'run_shared.py') if a==old else a for a in args])+'\n')
    run(['systemctl','daemon-reload']);activated=True;run(['systemctl','restart','skill-platform'])
    for _ in range(20):
        try:
            assert get('gemini/health')==health
            assert get('gemini/membership-api/plans')==plans
            break
        except Exception:time.sleep(.5)
    else:raise RuntimeError('Post-activation health failed')
    for f in files:
        p=webroot/f['file'];p.parent.mkdir(parents=True,exist_ok=True)
        replace(p,base64.b64decode(f['data']))
        assert hashlib.sha256(p.read_bytes()).hexdigest()==f['after']
    replace(nginx,original);run(['nginx','-t']);run(['systemctl','reload','nginx']);gated=False
    print(json.dumps({'deployed':True,'version':'0.10.38','backup':str(backup),'plans_unchanged':True,'health_unchanged':True,'balances_migrated':False,'old_pending_jobs_untouched':True}))
except Exception:
    for p,raw in oldweb.items():
        if raw is None:p.unlink(missing_ok=True)
        else:replace(p,raw)
    if activated:
        drop.unlink(missing_ok=True);run(['systemctl','daemon-reload']);run(['systemctl','restart','skill-platform'])
    if gated:replace(nginx,original);run(['nginx','-t']);run(['systemctl','reload','nginx'])
    # Keep account binding rows and all existing data; no rollback of customer transactions.
    raise
