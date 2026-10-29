"""Deploy journey observation without changing payment or quota logic."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import ssl
import urllib.error
import urllib.request


ROOT = Path('/opt/skill-platform/member-0.10.16')
OLD = Path('/opt/skill-platform/member-0.10.14')
WEB = Path('/var/www/image-assistant/membership')
OPS = Path('/opt/skill-platform/member-0.5.0/ops-web')
DBS = {
    'shared': '/var/lib/skill-platform/shared.db',
    'gemini': '/var/lib/image-assistant/pilot.db',
    'temu': '/var/lib/temu-image-assistant/trial.db',
}
SERVICES = ['skill-platform', 'skill-monitor', 'skill-order-mail',
            'image-assistant', 'temu-image-assistant']
COMMANDS = {
    'skill-platform': '/opt/skill-platform/1.2.0/venv/bin/python ' + str(ROOT / 'service/run_shared.py')
        + ' --db /var/lib/skill-platform/shared.db --gemini-db /var/lib/image-assistant/pilot.db'
        + ' --temu-db /var/lib/temu-image-assistant/trial.db --temu-source /opt/temu-image-assistant/0.2.2/service',
    'skill-monitor': '/opt/skill-platform/1.2.0/venv/bin/python ' + str(ROOT / 'ops-extension/run_ops.py')
        + ' --config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db'
        + ' --temu-source /opt/temu-image-assistant/0.2.2/service',
}
DROPINS = {s: Path('/etc/systemd/system') / (s + '.service.d/zzzzzzzzzzzzz-journey-0.10.16.conf')
           for s in COMMANDS}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/' + path, timeout=5) as response:
        return json.load(response)


def started(service):
    pid = int(run(['systemctl', 'show', service, '-p', 'MainPID', '--value']))
    assert pid > 0
    stat = Path('/proc/' + str(pid) + '/stat').read_text()
    ticks = int(stat[stat.rfind(')') + 1:].split()[19])
    return time.time() - (time.monotonic() - ticks / os.sysconf('SC_CLK_TCK'))


def snapshot(db):
    with closing(sqlite3.connect(Path(db).as_uri() + '?mode=ro', uri=True)) as c:
        c.row_factory = sqlite3.Row
        data = {}
        for table, in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            assert table.replace('_', '').isalnum()
            rows = [dict(row) for row in c.execute('SELECT * FROM ' + table)]
            data[table] = hashlib.sha256(json.dumps(sorted(rows, key=repr), sort_keys=True,
                                      default=str, separators=(',', ':')).encode()).hexdigest()
        return data


def nginx_children():
    pid = int(run(['systemctl', 'show', 'nginx', '-p', 'MainPID', '--value']))
    children = Path('/proc/' + str(pid) + '/task/' + str(pid) + '/children').read_text().split()
    return {int(child) for child in children if Path('/proc/' + child + '/cmdline').exists()
            and b'nginx: worker process' in Path('/proc/' + child + '/cmdline').read_bytes()}


class MaintenanceGate:
    """Gracefully replace nginx workers before stopping any business process."""
    def __init__(self, backup):
        self.path = Path('/etc/nginx/conf.d/image-assistant.conf')
        self.original = self.path.read_bytes()
        anchor = b'    server_tokens off;\n'
        assert self.original.count(anchor) == 1
        # Server-level return only; static membership/auth pages remain available.
        guard = b'    if ($uri !~ "^/(membership/|auth/|\\.well-known/)") { return 503; }\n'
        self.gated = self.original.replace(anchor, anchor + guard, 1)
        (backup / 'nginx.conf').write_bytes(self.original)
        self.installed = False

    def replace(self, data):
        temp = self.path.with_name('image-assistant.conf.journey-0.10.16.tmp')
        assert not temp.exists()
        temp.write_bytes(data)
        temp.chmod(0o644)
        os.replace(temp, self.path)

    def enter(self):
        workers = nginx_children()
        self.replace(self.gated)
        self.installed = True
        run(['nginx', '-t'])
        run(['systemctl', 'reload', 'nginx'])
        # New connections use the gated config; old workers finish their existing requests.
        context = ssl._create_unverified_context()
        for _ in range(20):
            try:
                req = urllib.request.Request('https://127.0.0.1/platform-api/gemini/health',
                                             headers={'Host': 'myplanestore.com'})
                urllib.request.urlopen(req, timeout=3, context=context).close()
            except urllib.error.HTTPError as error:
                if error.code == 503:
                    break
            time.sleep(0.25)
        else:
            raise RuntimeError('Maintenance gate not confirmed')
        for _ in range(300):
            if not any(Path('/proc/' + str(pid)).exists() for pid in workers):
                return
            time.sleep(1)
        raise RuntimeError('Existing nginx requests did not drain; services left running')

    def leave(self):
        if not self.installed:
            return
        assert self.path.read_bytes() == self.gated, 'Nginx changed concurrently; do not overwrite'
        self.replace(self.original)
        run(['nginx', '-t'])
        run(['systemctl', 'reload', 'nginx'])
        self.installed = False


def journey_health():
    code = '''import sys,json
sys.path.insert(0,'/opt/skill-platform/member-0.10.16')
from journey.store import Journey
from journey.report import Report
j=Journey('/var/lib/skill-monitor/journey-0.10.16.db')
health=j.health()
assert health['ok'] is True
r=Report(j,'/var/lib/skill-platform/shared.db',{'gemini':'/var/lib/image-assistant/pilot.db','temu':'/var/lib/temu-image-assistant/trial.db'})
summary=r.summary(1)
assert summary['scope']=='period_stage_counts_not_cohort_conversion'
print(json.dumps({'ok':True,'source_groups':len(summary['groups']),'coverage':'new_observations_plus_authoritative_orders'}))
'''
    result = json.loads(run(['runuser', '-u', 'image-assistant', '--',
                            '/opt/skill-platform/1.2.0/venv/bin/python', '-c', code]))
    actual = get('gemini/journey-health')
    assert actual['version'] == '0.10.16' and actual['journey']['ok'] is True
    try:
        urllib.request.urlopen('http://127.0.0.1:8790/ops/api/journey-v2/health', timeout=5).close()
        raise RuntimeError('Analytics admin health is not authenticated')
    except urllib.error.HTTPError as error:
        assert error.code == 401 and json.load(error)['error'] == 'ops_login_required'
    with urllib.request.urlopen('http://127.0.0.1:8790/ops/journey/panel.js', timeout=5) as response:
        assert hashlib.sha256(response.read()).hexdigest() == sha(ROOT / 'web/journey/panel.js')
    try:
        urllib.request.urlopen('http://127.0.0.1:8791/platform-api/gemini/membership-api/journey-page', timeout=5).close()
        raise RuntimeError('Journey page route accepted an unsupported method')
    except urllib.error.HTTPError as error:
        assert error.code == 405 and json.load(error)['error'] == 'method_not_allowed'
    result['actual_http_routes_verified'] = True
    return result


def ensure_idle():
    process_times = {name: started({'shared': 'skill-platform', 'gemini': 'image-assistant',
                                  'temu': 'temu-image-assistant'}[name]) for name in DBS}
    for _ in range(30):
        active = historical = 0
        for name, db in DBS.items():
            with closing(sqlite3.connect(Path(db).as_uri() + '?mode=ro', uri=True)) as c:
                active += c.execute("SELECT count(*) FROM jobs WHERE status='pending' AND created>=?",
                                    (process_times[name] - 1,)).fetchone()[0]
                historical += c.execute("SELECT count(*) FROM jobs WHERE status='pending' AND created<?",
                                        (process_times[name] - 1,)).fetchone()[0]
        busy = any(run(['ss', '-Htan', 'state', 'established', '( sport = :' + str(port) + ' )'])
                   for port in (8791, 8787, 8788))
        if not active and not busy:
            return process_times, historical
        time.sleep(2)
    raise RuntimeError('Active client work; deployment not started')


def main():
    os.umask(0o077)
    assert Path(__file__).parent == ROOT and all(not p.exists() for p in DROPINS.values())
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, digest in manifest['baseline'].items():
        assert sha(Path(name)) == digest, 'Live baseline drift: ' + name
    for name, digest in manifest['staged'].items():
        assert sha(ROOT / name) == digest, 'Stage mismatch: ' + name
    for service in COMMANDS:
        assert str(OLD) in run(['systemctl', 'show', service, '-p', 'ExecStart', '--value'])
    assert str(OLD) in run(['systemctl', 'show', 'skill-order-mail', '-p', 'ExecStart', '--value'])
    targets = {name: Path(target) for name, target in manifest['web'].items()}
    for target in targets.values():
        assert target.is_relative_to(WEB) or target.is_relative_to(OPS)
        if str(target) not in manifest['baseline']:
            assert not target.exists(), 'New target already exists: ' + str(target)
    immutable = {str(p): sha(p) for root in (OLD, WEB, OPS) for p in root.rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p not in targets.values()}
    # Check once before gating to avoid entering maintenance during an active render.
    ensure_idle()
    backup = Path('/var/backups/image-assistant') / ('journey-0.10.16-' + str(int(time.time())))
    backup.mkdir(mode=0o700)
    for name, target in targets.items():
        if target.exists():
            dest = backup / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, dest)
    gate = MaintenanceGate(backup)
    changed = False
    stopped = False
    recovered = False
    try:
        gate.enter()
        process_times, historical = ensure_idle()
        # Set before calling stop: a partially successful systemctl must still recover.
        stopped = True
        run(['systemctl', 'stop', *SERVICES])
        for name, db in DBS.items():
            with closing(sqlite3.connect(Path(db).as_uri() + '?mode=ro', uri=True)) as c:
                assert c.execute("SELECT count(*) FROM jobs WHERE status='pending' AND created>=?",
                                 (process_times[name] - 1,)).fetchone()[0] == 0, 'Active task; restart aborted'
        snapshots = {name: snapshot(db) for name, db in DBS.items()}
        backup_dbs = {**DBS, 'events': '/var/lib/skill-monitor/events.db'}
        journey_db = Path('/var/lib/skill-monitor/journey-0.10.16.db')
        if journey_db.exists():
            backup_dbs['journey'] = str(journey_db)
        for name, db in backup_dbs.items():
            with closing(sqlite3.connect(Path(db).as_uri() + '?mode=ro', uri=True)) as source:
                with closing(sqlite3.connect(backup / (name + '.db'))) as target:
                    source.backup(target)
            (backup / (name + '.db')).chmod(0o600)
        for path in [ROOT, *ROOT.rglob('*')]:
            path.chmod(0o755 if path.is_dir() else 0o644)
        changed = True
        for name, target in targets.items():
            missing = []
            parent = target.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            for parent in missing:
                parent.chmod(0o755)
            temp = target.with_name(target.name + '.journey-0.10.16.tmp')
            assert not temp.exists()
            shutil.copy2(ROOT / name, temp)
            temp.chmod(0o644)
            os.replace(temp, target)
        for service, target in DROPINS.items():
            target.write_text('[Service]\nExecStart=\nExecStart=' + COMMANDS[service] + '\n')
            target.chmod(0o644)
        assert all(snapshot(db) == snapshots[name] for name, db in DBS.items())
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'start', 'skill-platform', 'image-assistant', 'temu-image-assistant'])
        for _ in range(20):
            try:
                assert get('gemini/health')['shared_wallet'] is True
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError('Gateway health failed')
        for product in ('gemini', 'temu', 'xhs'):
            plans = get(product + '/membership-api/plans')['plans']
            expected = [(8900, 180), (19800, 400), (36500, 730)] if product == 'temu' else [
                (2900, 60), (3900, 80), (4900, 100), (99900, 2000)]
            assert [(p['price_fen'], p['images']) for p in plans] == expected
            assert all(p['period'] == 'permanent' and p['valid_days'] is None for p in plans)
        run(['systemctl', 'start', 'skill-monitor'])
        time.sleep(2)
        assert run(['systemctl', 'is-active', 'skill-platform', 'skill-monitor',
                    'image-assistant', 'temu-image-assistant', 'nginx']).splitlines() == ['active'] * 5
        for service in COMMANDS:
            assert str(ROOT) in run(['systemctl', 'show', service, '-p', 'ExecStart', '--value'])
        assert str(OLD) in run(['systemctl', 'show', 'skill-order-mail', '-p', 'ExecStart', '--value'])
        assert all(sha(Path(p)) == digest for p, digest in immutable.items())
        assert all(sha(target) == manifest['staged'][name] for name, target in targets.items())
        observation_health = journey_health()
        # The gate is still closed, so no external request can race this business snapshot check.
        assert all(snapshot(db) == snapshots[name] for name, db in DBS.items()), 'Business rows changed during deployment'
        run(['systemctl', 'start', 'skill-order-mail'])
        assert run(['systemctl', 'is-active', *SERVICES, 'nginx']).splitlines() == ['active'] * 6
        gate.leave()
    except Exception:
        if stopped:
            # Recovery steps are independent: one failure must not skip all later repairs.
            recovery_errors = []
            for service in ('skill-platform', 'skill-monitor'):
                result = subprocess.run(['systemctl', 'stop', service], capture_output=True)
                if result.returncode:
                    recovery_errors.append('stop:' + service)
            if changed:
                for name, target in targets.items():
                    try:
                        original = backup / name
                        if original.exists():
                            shutil.copy2(original, target)
                        else:
                            target.unlink(missing_ok=True)
                    except OSError:
                        recovery_errors.append('static:' + name)
                        print('static_recovery_failed', flush=True)
            for path in DROPINS.values():
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    recovery_errors.append('override:' + path.name)
                    print('service_override_recovery_failed', flush=True)
            if subprocess.run(['systemctl', 'daemon-reload'], capture_output=True).returncode:
                recovery_errors.append('daemon_reload')
            for service in SERVICES:
                if subprocess.run(['systemctl', 'start', service], capture_output=True).returncode:
                    recovery_errors.append('start:' + service)
            try:
                for name, target in targets.items():
                    if str(target) in manifest['baseline']:
                        assert sha(target) == manifest['baseline'][str(target)]
                    else:
                        assert not target.exists()
                assert not any(path.exists() for path in DROPINS.values())
                for service in COMMANDS:
                    assert str(OLD) in run(['systemctl', 'show', service, '-p', 'ExecStart', '--value'])
                    pid = int(run(['systemctl', 'show', service, '-p', 'MainPID', '--value']))
                    assert str(OLD).encode() in Path('/proc/' + str(pid) + '/cmdline').read_bytes()
            except Exception:
                recovery_errors.append('baseline_verification')
            recovered = not recovery_errors and subprocess.run(['systemctl', 'is-active', *SERVICES],
                capture_output=True, text=True).stdout.splitlines() == ['active'] * len(SERVICES)
            if not recovered:
                raise RuntimeError('Service recovery incomplete; maintenance gate retained')
        raise
    finally:
        if gate.installed and (not stopped or recovered):
            gate.leave()
    record = dict(version='0.10.16', deployed=True, backup=str(backup),
                  financial_code_unchanged=True, no_business_db_migration=True,
                  historical_pending_preserved=historical, qr_unchanged=True,
                  mail_service_and_policy_unchanged=True, real_orders_created=0,
                  real_generations=0, services_active=True, journey_health=observation_health,
                  graceful_request_drain=True, nginx_config_restored=True)
    (ROOT / 'deployment.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
