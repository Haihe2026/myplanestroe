"""Static checkout presentation rollout with guarded inputs and rollback."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

ROOT = Path('/opt/skill-platform/member-web-0.5.1')
SITE = Path('/var/www/image-assistant/membership')
assert Path(__file__).resolve().parent == ROOT
os.umask(0o077)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payment_hashes(manifest):
    result = {}
    for product, files in manifest['immutable_payment_files'].items():
        for name, expected in files.items():
            key = ('gemini' if product == 'xhs' and name == 'payment-qr.png' else product) + '/' + name
            result[key] = digest(SITE / key)
            assert result[key] == expected, 'Payment file changed since source snapshot: ' + key
    return result


def main():
    manifest = json.loads((ROOT / 'build-manifest.json').read_text())
    allowed = {'compact.js', 'recharge.css', 'gemini/index.html', 'temu/index.html', 'xhs/index.html'}
    assert set(manifest['presentation_files']) == allowed
    previous_payments = payment_hashes(manifest)
    for name, sha in manifest['previous_sha256'].items():
        target = SITE / name
        assert (digest(target) if target.exists() else None) == sha, 'Page changed since snapshot: ' + name
        assert digest(ROOT / 'web' / name) == manifest['new_sha256'][name]
    backup = Path('/var/backups/image-assistant') / ('checkout-green-0.5.1-' + str(int(time.time())))
    backup.mkdir(parents=True)
    for name, sha in manifest['previous_sha256'].items():
        if sha is not None:
            destination = backup / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SITE / name, destination)
    try:
        # Publish supporting assets first, then pages that reference their new version.
        for name in ['recharge.css', 'compact.js', 'gemini/index.html', 'temu/index.html', 'xhs/index.html']:
            target = SITE / name
            staging = target.with_name(target.name + '.green-0.5.1-new')
            shutil.copy2(ROOT / 'web' / name, staging)
            staging.chmod(0o644)
            os.replace(staging, target)
        assert payment_hashes(manifest) == previous_payments
        for name, sha in manifest['new_sha256'].items():
            assert digest(SITE / name) == sha
            with urllib.request.urlopen('https://myplanestore.com/membership/' + name + '?verify=0.5.1', timeout=20) as response:
                assert hashlib.sha256(response.read()).hexdigest() == sha, 'HTTPS content mismatch: ' + name
        for product in ('gemini', 'temu', 'xhs'):
            with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/' + product + '/health', timeout=5) as response:
                health = json.load(response)
            assert health['shared_wallet'] and health['new_user_uses'] == 0
        services = subprocess.run(['systemctl', 'is-active', 'nginx', 'image-assistant', 'temu-image-assistant', 'skill-platform', 'skill-monitor'], capture_output=True, text=True, check=True).stdout.splitlines()
        assert services == ['active'] * 5
    except Exception:
        for name, sha in manifest['previous_sha256'].items():
            target = SITE / name
            if sha is None:
                target.unlink(missing_ok=True)
            else:
                shutil.copy2(backup / name, target)
        raise
    record = dict(version='0.5.1', deployed=True, backup=str(backup), files=list(allowed), payment_scripts_and_qr_unchanged=True, xhs_initial_qr_reference_fixed=True, payment_endpoints_changed=False, billing_database_touched=False, backend_restarted=False, services_active=True, https_hashes_verified=True, actual_payments=0, actual_generation=0)
    (ROOT / 'deployment.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
