"""Reversible additive rollout; preserve existing DB and provider configuration."""
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

source = Path('/opt/skill-platform/1.5.0/service')
target = Path('/etc/systemd/system/image-assistant.service.d/z-annual.conf')
backup = Path('/var/lib/image-assistant/backups') / ('annual-1.5.0-' + str(int(time.time())))
backup.mkdir(parents=True, exist_ok=False)
with sqlite3.connect('/var/lib/image-assistant/pilot.db') as c, sqlite3.connect(backup / 'pilot.db') as b:
    c.backup(b)
old = target.read_bytes() if target.exists() else None
if old is not None: (backup / 'z-annual.conf').write_bytes(old)
subprocess.run(['/opt/skill-platform/1.2.0/venv/bin/python', '-m', 'py_compile',
                *map(str, source.glob('*.py'))], check=True)
target.write_text('''[Service]
Environment=IMAGE_ANNUAL_ENABLED=yes
Environment=IMAGE_ANNUAL_IP_DAILY_LIMIT=3
ExecStart=
ExecStart=/opt/skill-platform/1.2.0/venv/bin/python /opt/skill-platform/1.5.0/service/run_annual.py --source /opt/skill-platform/1.2.0/service --telemetry-source /opt/skill-platform/0.3.0/service --db /var/lib/image-assistant/pilot.db --port 8787
''')
try:
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'restart', 'image-assistant'], check=True)
    for i in range(20):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8787/health', timeout=5) as r: health = json.load(r)
            assert health['provider_configured']
            break
        except Exception:
            if i == 19: raise
            time.sleep(1)
    request = urllib.request.Request('http://127.0.0.1:8787/skill-pay/account', data=b'{}', headers={'Content-Type': 'application/json'})
    try: urllib.request.urlopen(request, timeout=5); raise AssertionError('Invalid body accepted')
    except urllib.error.HTTPError as e: assert e.code == 400
    print(json.dumps({'deployed': True, 'health': health, 'backup': str(backup)}))
except Exception:
    if old is None: target.unlink(missing_ok=True)
    else: target.write_bytes(old)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'restart', 'image-assistant'], check=True)
    raise
