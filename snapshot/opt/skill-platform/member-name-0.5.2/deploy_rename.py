"""Guarded display-name rollout; no identifiers, credentials or financial data edits."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

ROOT = Path('/opt/skill-platform/member-name-0.5.2')
assert Path(__file__).resolve().parent == ROOT
OLD, NEW = 'Gemini生图助手', 'Gemini生图器'
os.umask(0o077)
DATABASES = dict(shared='/var/lib/skill-platform/shared.db', gemini='/var/lib/image-assistant/pilot.db', temu='/var/lib/temu-image-assistant/trial.db')


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(route):
    with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/gemini/' + route, timeout=5) as response:
        return json.load(response)


def snapshot(database):
    tables = ('users','paid_wallets','member_orders','member_grants','ledger','grant_jobs','paid_jobs','trial_claims','sessions','legacy_links','product_accounts','order_sources')
    result = {}
    with closing(sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)) as connection:
        available = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in tables:
            if table in available:
                rows = connection.execute('SELECT * FROM ' + table).fetchall()
                normalized = sorted(json.dumps(row, default=str, separators=(',',':')) for row in rows)
                result[table] = hashlib.sha256('\n'.join(normalized).encode()).hexdigest()
    return result


def immutable(manifest):
    for filename, sha in manifest['unchanged'].items():
        assert digest(Path(filename)) == sha, 'Payment asset changed: ' + filename


def main():
    manifest = json.loads((ROOT / 'rename-manifest.json').read_text())
    allowed = {
        '/var/www/image-assistant/membership/' + suffix for suffix in ('index.html','gemini/index.html','temu/index.html','xhs/index.html','gemini/api-guide.html','gemini/manual-payment.js')
    } | {'/var/www/image-assistant/auth/index.html'} | {
        '/opt/skill-platform/member-0.5.0/' + suffix for suffix in ('core/platform_catalog.py','ops-web/app.js','ops-web/index.html')
    }
    assert {row['target'] for row in manifest['files']} == allowed
    immutable(manifest)
    for row in manifest['files']:
        assert digest(Path(row['target'])) == row['previous_sha256'], 'Source snapshot changed: ' + row['target']
        assert digest(ROOT / row['source']) == row['new_sha256']
    registry = next(row for row in manifest['files'] if row['source'] == 'core/platform_catalog.py')
    original = Path(registry['target']).read_text()
    updated = (ROOT / registry['source']).read_text()
    assert original.replace(OLD, NEW) == updated
    compile(updated, registry['source'], 'exec')
    # Wait for a quiet shared gateway rather than interrupting an image request.
    for _ in range(25):
        active = run(['ss','-Htan','state','established','( sport = :8791 )'])
        with closing(sqlite3.connect(Path(DATABASES['shared']).resolve().as_uri() + '?mode=ro', uri=True)) as connection:
            pending = connection.execute("SELECT count(*) FROM jobs WHERE status='pending'").fetchone()[0]
        if not active and pending == 0:
            break
        time.sleep(2)
    else:
        raise RuntimeError('Shared gateway is busy; no production files modified')
    backup = Path('/var/backups/image-assistant') / ('gemini-rename-0.5.2-' + str(int(time.time())))
    backup.mkdir(parents=True)
    for row in manifest['files']:
        saved = backup / row['source']
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(row['target'], saved)
    stopped = False
    before = {}
    try:
        run(['systemctl','stop','skill-platform'])
        stopped = True
        before = {product:snapshot(database) for product,database in DATABASES.items()}
        for row in sorted(manifest['files'], key=lambda row: row['source'].endswith('.html')):
            target = Path(row['target'])
            temporary = target.with_name(target.name + '.rename-0.5.2-new')
            shutil.copy2(ROOT / row['source'], temporary)
            temporary.chmod(0o644)
            os.replace(temporary, target)
        run(['systemctl','start','skill-platform'])
        stopped = False
        for _ in range(20):
            try:
                health = read('health')
                catalog = read('membership-api/catalog')
                item = next(p for p in catalog['products'] if p['id'] == 'gemini-image-assistant')
                assert health['new_user_uses'] == 0 and health['shared_wallet']
                assert item['name'] == NEW
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('New display name not visible from shared catalog')
        after = {product:snapshot(database) for product,database in DATABASES.items()}
        assert after == before, 'Account or wallet changed during rollout; investigate concurrent activity'
        immutable(manifest)
        for row in manifest['files']:
            assert digest(Path(row['target'])) == row['new_sha256']
        states = run(['systemctl','is-active','nginx','image-assistant','temu-image-assistant','skill-platform','skill-monitor']).splitlines()
        assert states == ['active'] * 5
    except Exception:
        if not stopped:
            run(['systemctl','stop','skill-platform'])
        for row in manifest['files']:
            shutil.copy2(backup / row['source'], row['target'])
        run(['systemctl','start','skill-platform'])
        raise
    record = dict(version='0.5.2',deployed=True,display_name=NEW,backup=str(backup),slug='jyai-gemini-image-assistant',product_id='gemini-image-assistant',account_and_financial_snapshots_unchanged=True,payment_qrs_and_checkout_code_unchanged=True,shared_registry_name=NEW,services_active=True,old_image_gateways_restarted=False,actual_payments=0,actual_generation=0)
    (ROOT / 'deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    main()
