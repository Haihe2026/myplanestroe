"""Guarded rollout of one-request registration invitations and a separate consent page."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path('/opt/skill-platform/member-0.8.0')
OLD = Path('/opt/skill-platform/member-0.7.0')
WEB = Path('/var/www/image-assistant/membership')
DROPIN = Path('/etc/systemd/system/skill-platform.service.d/70-member-0.8.0.conf')
DATABASES = dict(shared='/var/lib/skill-platform/shared.db',
                 gemini='/var/lib/image-assistant/pilot.db', temu='/var/lib/temu-image-assistant/trial.db')
assert Path(__file__).resolve().parent == ROOT
os.umask(0o077)


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(product='gemini', route='health'):
    with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/' + product + '/' + route, timeout=5) as response:
        return json.load(response)


def snapshot(database):
    tables = ('users','paid_wallets','member_orders','member_grants','ledger','grant_jobs','paid_jobs',
              'trial_claims','sessions','legacy_links','product_accounts','order_sources')
    result = {}
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as c:
        available = {row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in tables:
            if table in available:
                rows = sorted(json.dumps(row, default=str, separators=(',', ':')) for row in c.execute('SELECT * FROM ' + table))
                result[table] = hashlib.sha256('\n'.join(rows).encode()).hexdigest()
    return result


def immutable(manifest):
    for name, expected in manifest['immutable'].items():
        assert sha(WEB / name) == expected, 'Existing checkout asset drift: ' + name


def main():
    m = json.loads((ROOT / 'web-manifest.json').read_text())
    assert set(m['files']) == {'gemini/register/register.css', 'gemini/register/register.js', 'gemini/register/index.html'}
    assert not DROPIN.exists(), 'Existing rollout must not be overwritten'
    assert str(OLD / 'service/run_shared.py') in run(['systemctl', 'show', 'skill-platform', '-p', 'ExecStart', '--value'])
    immutable(m)
    for name in m['files']:
        target = WEB / name
        assert (sha(target) if target.exists() else None) == m['previous'][name], 'Static baseline drift: ' + name
        assert sha(ROOT / 'web' / name) == m['new'][name]
    for name, expected in m['backend_files'].items():
        assert sha(ROOT / name) == expected, 'Staged backend mismatch: ' + name
        assert (sha(OLD / name) if (OLD / name).exists() else None) == m['backend_baseline'][name], 'Live backend drift: ' + name
        if name.endswith('.py'):
            compile((ROOT / name).read_bytes(), name, 'exec')
        else:
            json.loads((ROOT / name).read_text())
    # Resolve module imports and local data before stopping the live gateway.
    run(['/opt/skill-platform/1.2.0/venv/bin/python', '-c',
         "import sys; sys.path[:0]=['/opt/skill-platform/member-0.8.0/core',"
         "'/opt/skill-platform/member-0.8.0/service','/opt/skill-platform/member-0.8.0/ops']; "
         'import server, shared_platform, telemetry'])
    for _ in range(30):
        active = run(['ss', '-Htan', 'state', 'established', '( sport = :8791 )'])
        with closing(sqlite3.connect(Path(DATABASES['shared']).resolve().as_uri() + '?mode=ro', uri=True)) as c:
            pending = c.execute("SELECT count(*) FROM jobs WHERE status='pending'").fetchone()[0]
        if not active and not pending:
            break
        time.sleep(2)
    else:
        raise RuntimeError('Image gateway is busy; production files were not changed')
    backup = Path('/var/backups/image-assistant') / ('payment-return-0.8.0-' + str(int(time.time())))
    backup.mkdir(parents=True)
    for name in m['files']:
        if (WEB / name).exists():
            target = backup / 'web' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(WEB / name, target)
    stopped = False
    try:
        run(['systemctl', 'stop', 'skill-platform'])
        stopped = True
        before = {product: snapshot(db) for product, db in DATABASES.items()}
        for product, db in DATABASES.items():
            with closing(sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)) as source:
                with closing(sqlite3.connect(backup / (product + '.db'))) as target:
                    source.backup(target)
        # The new source directory is additive. The previous source remains intact.
        ROOT.chmod(0o755)
        for folder in ('core', 'service', 'ops'):
            for path in [ROOT / folder, *(ROOT / folder).rglob('*')]:
                path.chmod(0o755 if path.is_dir() else 0o644)
        DROPIN.parent.mkdir(parents=True, exist_ok=True)
        DROPIN.write_text('[Service]\nExecStart=\nExecStart=/opt/skill-platform/1.2.0/venv/bin/python '
                          '/opt/skill-platform/member-0.8.0/service/run_shared.py '
                          '--db /var/lib/skill-platform/shared.db --gemini-db /var/lib/image-assistant/pilot.db '
                          '--temu-db /var/lib/temu-image-assistant/trial.db '
                          '--temu-source /opt/temu-image-assistant/0.2.2/service\n')
        DROPIN.chmod(0o644)
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'start', 'skill-platform'])
        stopped = False
        for _ in range(20):
            try:
                health = read()
                assert health['version'] == '0.8.0' and health['new_user_uses'] == 0 and health['shared_wallet']
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('New gateway did not become healthy')
        for name in sorted(m['files'], key=lambda name: name.endswith('.html')):
            target = WEB / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.parent.chmod(0o755)
            temporary = target.with_name(target.name + '.0.8.0-new')
            shutil.copy2(ROOT / 'web' / name, temporary)
            temporary.chmod(0o644)
            os.replace(temporary, target)
        for product in ('gemini', 'temu', 'xhs'):
            assert read(product)['version'] == '0.8.0'
        try:
            read(route='payment-status?since=0')
            raise AssertionError('Payment status must require the account bearer')
        except urllib.error.HTTPError as error:
            assert error.code == 401
        after = {product: snapshot(db) for product, db in DATABASES.items()}
        assert after == before, 'Account/financial state changed; check concurrent activity (no database rollback)'
        immutable(m)
        for name in m['files']:
            assert sha(WEB / name) == m['new'][name]
        assert str(ROOT / 'service/run_shared.py') in run(['systemctl', 'show', 'skill-platform', '-p', 'ExecStart', '--value'])
        services = ['nginx','image-assistant','temu-image-assistant','skill-platform','skill-monitor','skill-order-mail']
        assert run(['systemctl', 'is-active', *services]).splitlines() == ['active'] * len(services)
    except Exception:
        if not stopped:
            run(['systemctl', 'stop', 'skill-platform'])
        for name in m['files']:
            saved, target = backup / 'web' / name, WEB / name
            if saved.exists():
                shutil.copy2(saved, target)
            elif m['previous'][name] is None:
                target.unlink(missing_ok=True)
        DROPIN.unlink(missing_ok=True)
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'start', 'skill-platform'])
        raise
    record = dict(version='0.8.0', deployed=True, backup=str(backup),
                  changed_static=m['files'], account_and_financial_snapshots_unchanged=True,
                  payment_method='existing QR and manual email approval', qr_assets_unchanged=True,
                  old_backend_source_preserved=True, original_image_gateways_not_restarted=True,
                  services_active=True, actual_payments=0, actual_generation=0)
    (ROOT / 'deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    main()
