"""Publish two static files; never restart billing or modify balances."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

ROOT = Path('/opt/skill-platform/member-web-0.5.3')
SITE = Path('/var/www/image-assistant/membership')
assert Path(__file__).resolve().parent == ROOT
os.umask(0o077)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / 'build-manifest.json').read_text())
    assert manifest['files'] == ['trust.css', 'gemini/index.html']
    for name, sha in manifest['previous_sha256'].items():
        target = SITE / name
        assert (digest(target) if target.exists() else None) == sha, 'Production changed: ' + name
        assert digest(ROOT / 'web' / name) == manifest['new_sha256'][name]
    for name, sha in manifest['immutable_payment_files'].items():
        assert digest(SITE / name) == sha, 'Payment asset changed: ' + name
    backup = Path('/var/backups/image-assistant') / ('trust-0.5.3-' + str(int(time.time())))
    backup.mkdir(parents=True)
    for name, sha in manifest['previous_sha256'].items():
        if sha is not None:
            destination = backup / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SITE / name, destination)
    try:
        for name in manifest['files']:
            target = SITE / name
            staging = target.with_name(target.name + '.trust-0.5.3-new')
            shutil.copy2(ROOT / 'web' / name, staging)
            staging.chmod(0o644)
            os.replace(staging, target)
        for name, sha in manifest['new_sha256'].items():
            assert digest(SITE / name) == sha
            with urllib.request.urlopen('https://myplanestore.com/membership/' + name + '?verify=0.5.3', timeout=30) as response:
                assert hashlib.sha256(response.read()).hexdigest() == sha
        for name, sha in manifest['immutable_payment_files'].items():
            assert digest(SITE / name) == sha
        services = subprocess.run(['systemctl', 'is-active', 'nginx', 'image-assistant', 'temu-image-assistant', 'skill-platform', 'skill-monitor'], capture_output=True, text=True, check=True).stdout.splitlines()
        assert services == ['active'] * 5
    except Exception:
        for name, sha in manifest['previous_sha256'].items():
            if sha is None:
                (SITE / name).unlink(missing_ok=True)
            else:
                shutil.copy2(backup / name, SITE / name)
        raise
    record = dict(version='0.5.3', deployed=True, backup=str(backup), files=manifest['files'],
                  qr_and_payment_scripts_unchanged=True, backend_restarted=False,
                  billing_database_touched=False, services_active=True, https_hashes_verified=True,
                  actual_payments=0, actual_generation=0)
    (ROOT / 'deployment.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
