"""Guarded activation. No orders, balances or existing credentials modified."""
from pathlib import Path
import hashlib
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import time
import urllib.request

run=lambda args:subprocess.check_output(args,text=True).strip()
root=Path('/opt/skill-platform/member-0.10.34-candidate')
pid=run(['systemctl','show','skill-platform','-p','MainPID','--value'])
args=[s.decode() for s in Path('/proc/'+pid+'/cmdline').read_bytes().split(bytes([0])) if s]
old='/opt/skill-platform/member-0.10.33-candidate/run_shared.py'
assert old in args,'Concurrent service change'
drop=Path('/etc/systemd/system/skill-platform.service.d')/('z'*63+'-phone-0.10.34.conf')
assert not drop.exists()
assert all(drop.name>p.name for p in drop.parent.glob('*.conf'))
nginx=Path('/etc/nginx/conf.d/image-assistant.conf');original=nginx.read_bytes()
anchor=b'    server_tokens off;\n';assert original.count(anchor)==1
backup=Path('/var/backups/skill-platform')/('phone-0.10.34-'+str(int(time.time())))
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
    replace(nginx,original);run(['nginx','-t']);run(['systemctl','reload','nginx']);gated=False
    print(json.dumps({'deployed':True,'version':'0.10.34','backup':str(backup),'plans_unchanged':True,'health_unchanged':True,'balances_migrated':False,'old_pending_jobs_untouched':True}))
except Exception:
    if activated:
        drop.unlink(missing_ok=True);run(['systemctl','daemon-reload']);run(['systemctl','restart','skill-platform'])
    if gated:replace(nginx,original);run(['nginx','-t']);run(['systemctl','reload','nginx'])
    # Keep account binding rows and all existing data; no rollback of customer transactions.
    raise
