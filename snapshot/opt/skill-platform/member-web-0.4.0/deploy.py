"""Publish static layout only; verify payment assets remain byte-identical."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

ROOT = Path('/opt/skill-platform/member-web-0.4.0')
assert Path(__file__).resolve().parent == ROOT
os.umask(0o077)
site = Path('/var/www/image-assistant/membership')
auth = Path('/var/www/image-assistant/auth')
manifest = json.loads((ROOT / 'build-manifest.json').read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
for name, value in manifest['files'].items():
    assert digest(site / name) == value, 'Live payment files changed since source snapshot: ' + name
assert digest(auth / 'app.js') == digest(ROOT / 'source/auth/app.js')
targets = {'index.html':site / 'index.html','compact.css':site / 'compact.css',
           'compact.js':site / 'compact.js','entry.js':site / 'entry.js',
           'gemini/index.html':site / 'gemini/index.html','temu/index.html':site / 'temu/index.html',
           'xhs/index.html':site / 'xhs/index.html','auth/index.html':auth / 'index.html'}
for product in ('gemini','temu','xhs','auth'):
    live = auth / 'index.html' if product=='auth' else site / product / 'index.html'
    assert digest(live)==digest(ROOT / 'source' / product / 'index.html'), 'Page changed since source snapshot: ' + product
backup = Path('/var/backups/image-assistant') / ('compact-0.4.0-' + str(int(time.time())))
backup.mkdir(parents=True)
previous = {}
for name, target in targets.items():
    previous[name] = target.exists()
    if target.exists():
        saved = backup / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, saved)
try:
    for name, target in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.compact-new')
        shutil.copy2(ROOT / 'web' / name, temporary)
        temporary.chmod(0o644)
        os.replace(temporary, target)
    for name, value in manifest['files'].items():
        assert digest(site / name) == value
    assert digest(auth / 'app.js') == digest(ROOT / 'source/auth/app.js')
except Exception:
    for name, target in targets.items():
        if previous[name]: shutil.copy2(backup / name, target)
        else: target.unlink(missing_ok=True)
    raise
record = {'version':'0.4.0','deployed':True,'backup':str(backup),'files':list(targets),
    'payment_scripts_and_qr_unchanged':True,'payment_endpoints_changed':False,'sms_logic_changed':False,
    'billing_database_changed':False,'real_payment_tested':False}
(ROOT / 'deployment.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record))
