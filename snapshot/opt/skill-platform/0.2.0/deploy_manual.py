"""Deploy manual settlement with a restorable service/config/database snapshot."""
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

root=Path("/opt/skill-platform/0.2.0")
db=Path("/var/lib/image-assistant/pilot.db")
override=Path("/etc/systemd/system/image-assistant.service.d/backend.conf")
envfile=Path("/etc/image-assistant/provider.env")
web=Path("/var/www/image-assistant/membership")
backup=Path("/var/backups/image-assistant")/("manual-"+str(int(time.time())))
with sqlite3.connect(db) as c:
    pending=c.execute("SELECT count(*) FROM jobs WHERE status='pending' AND created>?",(time.time()-300,)).fetchone()[0]
    if pending:
        raise RuntimeError("Recent image jobs still pending; retry deployment after they finish.")
backup.mkdir(mode=0o700)
shutil.copy2(override,backup/"backend.conf")
shutil.copy2(envfile,backup/"provider.env")
shutil.copytree(web,backup/"web")
subprocess.run(["systemctl","stop","image-assistant"],check=True)
try:
    with sqlite3.connect(db) as source, sqlite3.connect(backup/"pilot.db") as dest:
        source.backup(dest)
    lines=[line for line in envfile.read_text().splitlines() if not line.startswith("IMAGE_MANUAL_QR_ENABLED=")]
    envfile.write_text("\n".join(lines)+"\nIMAGE_MANUAL_QR_ENABLED=yes\n")
    envfile.chmod(0o600)
    override.write_text("[Service]\nWorkingDirectory=/opt/skill-platform/0.2.0/service\nExecStart=\nExecStart=/usr/bin/python3 /opt/skill-platform/0.2.0/service/server.py --db /var/lib/image-assistant/pilot.db\n")
    subprocess.run(["systemctl","daemon-reload"],check=True)
    subprocess.run(["systemctl","start","image-assistant"],check=True)
    last=None
    for _ in range(10):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8787/health",timeout=3) as r:health=json.load(r)
            with urllib.request.urlopen("http://127.0.0.1:8787/membership-api/plans",timeout=3) as r:plans=json.load(r)
            assert health["platform_version"]=="0.2.0" and plans["payment_ready"] and plans["payment_mode"]=="manual_qr"
            last=None
            break
        except Exception as error:
            last=error
            time.sleep(.5)
    if last:raise last
    for path in sorted((root/"web").iterdir(),key=lambda p:p.name=="index.html"):
        if path.is_file():
            shutil.copy2(path,web/path.name)
            (web/path.name).chmod(0o644)
    subprocess.run(["nginx","-t"],check=True)
except Exception:
    shutil.copy2(backup/"backend.conf",override)
    shutil.copy2(backup/"provider.env",envfile)
    for path in (backup/"web").iterdir():
        if path.is_file():shutil.copy2(path,web/path.name)
    subprocess.run(["systemctl","daemon-reload"],check=True)
    subprocess.run(["systemctl","restart","image-assistant"],check=True)
    raise
print(json.dumps({"deployed":"0.2.0","backup":str(backup),"manual_qr":True}))
