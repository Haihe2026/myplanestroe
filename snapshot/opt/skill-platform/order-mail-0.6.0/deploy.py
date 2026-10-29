"""Guarded additive deployment; payment gateways keep running unchanged."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

ROOT = Path('/opt/skill-platform/order-mail-0.6.0')
OPS = Path('/opt/skill-platform/member-0.5.0/ops-web')
assert Path(__file__).resolve().parent == ROOT
os.umask(0o077)


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(config):
    values = {}
    for namespace, product in config['products'].items():
        with closing(sqlite3.connect(Path(product['path']).as_uri() + '?mode=ro', uri=True)) as db:
            values[namespace] = {}
            for table in ('users', 'member_orders', 'member_grants', 'paid_wallets', 'ledger', 'member_gifts', 'ops_settlements'):
                rows = db.execute('SELECT * FROM ' + table + ' ORDER BY 1').fetchall()
                values[namespace][table] = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    return values


def main():
    config = json.loads(Path('/etc/skill-order-mail/config.json').read_text())
    manifest = json.loads((ROOT / 'ops-manifest.json').read_text())
    for name, hashes in manifest.items():
        assert digest(OPS / name) == hashes['old'], 'Ops source changed: ' + name
        assert digest(ROOT / 'ops-web' / name) == hashes['new']
    assert not Path('/etc/systemd/system/skill-order-mail.service').exists(), 'Existing worker must be upgraded separately'
    backup = Path('/var/backups/skill-order-mail') / str(int(time.time()))
    backup.mkdir(parents=True, mode=0o700)
    before = fingerprint(config)
    for namespace, product in config['products'].items():
        with closing(sqlite3.connect(Path(product['path']).as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(backup / (namespace + '.db'))) as target:
                source.backup(target)
    for name in manifest:
        shutil.copy2(OPS / name, backup / name)
    payment_paths = [Path('/var/www/image-assistant/membership') / product / filename
                     for product in ('gemini', 'temu') for filename in ('manual-payment.js', 'payment-qr.png')]
    original_payments = {str(p): digest(p) for p in payment_paths}
    run('install', '-d', '-m', '0700', '-o', 'image-assistant', '-g', 'image-assistant', '/var/lib/skill-order-mail')
    # Add audit tables only. No account/order/ledger content is changed here.
    from email_settlement import EmailSettlement
    EmailSettlement(config['products']).initialize()
    assert fingerprint(config) == before, 'Existing financial rows changed; inspect concurrent activity before continuing'
    unit = Path('/etc/systemd/system/skill-order-mail.service')
    try:
        for name in manifest:
            target = OPS / name
            staging = target.with_name(target.name + '.mail-0.6.0-new')
            shutil.copy2(ROOT / 'ops-web' / name, staging)
            staging.chmod(0o644)
            os.replace(staging, target)
        shutil.copy2(ROOT / 'skill-order-mail.service', unit)
        unit.chmod(0o644)
        run('systemctl', 'daemon-reload')
        run('systemctl', 'enable', '--now', 'skill-order-mail.service')
        time.sleep(3)
        states = run('systemctl', 'is-active', 'nginx', 'image-assistant', 'temu-image-assistant', 'skill-platform', 'skill-monitor', 'skill-order-mail').splitlines()
        assert states == ['active'] * 6
        assert {str(p): digest(p) for p in payment_paths} == original_payments
    except Exception:
        subprocess.run(['systemctl', 'disable', '--now', 'skill-order-mail.service'], capture_output=True)
        for name in manifest:
            shutil.copy2(backup / name, OPS / name)
        unit.unlink(missing_ok=True)
        subprocess.run(['systemctl', 'daemon-reload'], capture_output=True)
        # Never restore a database snapshot over users' concurrent transactions.
        raise
    result = {'version': '0.6.0', 'deployed': True, 'backup': str(backup),
              'existing_financial_rows_preserved_at_install': True, 'payment_assets_unchanged': True,
              'payment_gateways_restarted': False, 'mail_worker_active': True, 'poll_seconds': 30,
              'provider': 'manual_email', 'approval': 'DKIM-authenticated exact Gmail reply to matching original order notification',
              'real_order_approval_tested': False, 'test_reply_pending': True}
    (ROOT / 'deployment.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
