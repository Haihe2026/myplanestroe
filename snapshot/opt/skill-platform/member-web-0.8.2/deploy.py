"""Backed-up, guarded static rollout; never creates orders or alters financial tables."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path('/opt/skill-platform/member-web-0.8.2')
WEB = Path('/var/www/image-assistant/membership')
assert Path(__file__).resolve().parent == ROOT
os.umask(0o077)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def immutable(manifest):
    for name, expected in manifest['immutable'].items():
        assert sha(WEB / name) == expected, 'Unrelated asset drift: ' + name


manifest = json.loads((ROOT / 'web-manifest.json').read_text())
expected = {'account-center.js', 'account-center.css', *(p + '/' + f for p in ('gemini', 'temu', 'xhs') for f in ('index.html', 'manual-payment.js'))}
assert set(manifest['files']) == expected
immutable(manifest)
for name in manifest['files']:
    target = WEB / name
    assert (sha(target) if target.exists() else None) == manifest['previous'][name], 'Live baseline drift: ' + name
    assert sha(ROOT / 'web' / name) == manifest['new'][name]
backup = Path('/var/backups/image-assistant') / ('account-center-web-0.8.2-' + str(int(time.time())))
backup.mkdir(parents=True)
for name in manifest['files']:
    if (WEB / name).exists():
        target = backup / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WEB / name, target)
try:
    for name in sorted(manifest['files'], key=lambda value: value.endswith('.html')):
        target = WEB / name; temporary = target.with_name(target.name + '.0.8.2-new')
        shutil.copy2(ROOT / 'web' / name, temporary); temporary.chmod(0o644); os.replace(temporary, target)
    immutable(manifest)
    for name in manifest['files']:
        assert sha(WEB / name) == manifest['new'][name]
    services = ['nginx', 'skill-platform', 'image-assistant', 'temu-image-assistant', 'skill-order-mail']
    result = subprocess.run(['systemctl', 'is-active', *services], check=True, capture_output=True, text=True)
    assert result.stdout.splitlines() == ['active'] * len(services)
except Exception:
    for name in manifest['files']:
        if (backup / name).exists(): shutil.copy2(backup / name, WEB / name)
        elif manifest['previous'][name] is None: (WEB / name).unlink(missing_ok=True)
    raise
record = dict(version='0.8.2', deployed=True, backup=str(backup), static_files=manifest['files'],
    services_restarted=False, database_writes=False, payment_apis_and_qr_unchanged=True,
    real_orders=0, real_payments=0, actual_generation=0)
(ROOT / 'deployment.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record))
