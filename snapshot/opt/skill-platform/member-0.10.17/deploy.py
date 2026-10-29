"""Deploy only an additive ops asset bridge; leave gateway, mail and all prior releases intact."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path('/opt/skill-platform/member-0.10.17')
PRIOR = Path('/opt/skill-platform/member-0.10.16')
DROPIN = Path('/etc/systemd/system/skill-monitor.service.d/zzzzzzzzzzzzzz-enterprise-assets-0.10.17.conf')
COMMAND = ('/opt/skill-platform/1.2.0/venv/bin/python ' + str(ROOT / 'ops-extension/run_ops.py')
           + ' --config /etc/skill-monitor/config.json --shared-db /var/lib/skill-platform/shared.db'
           + ' --temu-source /opt/temu-image-assistant/0.2.2/service')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def run(args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def main():
    os.umask(0o077)
    assert not DROPIN.exists() and str(PRIOR) in run(['systemctl', 'show', 'skill-monitor', '-p', 'ExecStart', '--value'])
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, digest in manifest.items():
        assert sha(ROOT / name) == digest
    source = json.loads((ROOT / 'asset-source.json').read_text())
    assert sha(Path(source['source'])) == source['sha256'] == sha(ROOT / 'ops-extension/enterprise-feedback.js')
    assert not Path('/opt/skill-platform/member-0.10.14/ops-extension/enterprise-feedback.js').exists()
    prior_manifest = json.loads((PRIOR / 'manifest.json').read_text())
    assert all(sha(PRIOR / name) == digest for name, digest in prior_manifest['staged'].items())
    backup = Path('/var/backups/image-assistant') / ('enterprise-assets-0.10.17-' + str(int(time.time())))
    backup.mkdir(mode=0o700)
    spec = importlib.util.spec_from_file_location('prior_deployment_helpers', PRIOR / 'deploy.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    gate = old.MaintenanceGate(backup)
    stopped = recovered = False
    try:
        gate.enter()
        stopped = True
        run(['systemctl', 'stop', 'skill-monitor'])
        for p in [ROOT, *ROOT.rglob('*')]:
            p.chmod(0o755 if p.is_dir() else 0o644)
        DROPIN.write_text('[Service]\nExecStart=\nExecStart=' + COMMAND + '\n')
        DROPIN.chmod(0o644)
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'start', 'skill-monitor'])
        for _ in range(20):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8790/ops/enterprise-feedback.js', timeout=5) as response:
                    assert hashlib.sha256(response.read()).hexdigest() == source['sha256']
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError('Enterprise compatibility asset not available')
        try:
            urllib.request.urlopen('http://127.0.0.1:8790/ops/api/journey-v2/health', timeout=5).close()
            raise RuntimeError('Journey API lost authentication')
        except urllib.error.HTTPError as error:
            assert error.code == 401 and json.load(error)['error'] == 'ops_login_required'
        old.journey_health()
        assert str(ROOT) in run(['systemctl', 'show', 'skill-monitor', '-p', 'ExecStart', '--value'])
        assert all(sha(PRIOR / name) == digest for name, digest in prior_manifest['staged'].items())
        assert not Path('/opt/skill-platform/member-0.10.14/ops-extension/enterprise-feedback.js').exists()
        assert run(['systemctl', 'is-active', *old.SERVICES, 'nginx']).splitlines() == ['active'] * 6
        gate.leave()
    except Exception:
        if stopped:
            errors = []
            if subprocess.run(['systemctl', 'stop', 'skill-monitor'], capture_output=True).returncode:
                errors.append('stop')
            try:
                DROPIN.unlink(missing_ok=True)
            except OSError:
                errors.append('override')
            if subprocess.run(['systemctl', 'daemon-reload'], capture_output=True).returncode:
                errors.append('reload')
            if subprocess.run(['systemctl', 'start', 'skill-monitor'], capture_output=True).returncode:
                errors.append('start')
            try:
                assert not DROPIN.exists()
                assert str(PRIOR) in run(['systemctl', 'show', 'skill-monitor', '-p', 'ExecStart', '--value'])
                pid = int(run(['systemctl', 'show', 'skill-monitor', '-p', 'MainPID', '--value']))
                assert str(PRIOR).encode() in Path('/proc/' + str(pid) + '/cmdline').read_bytes()
                assert run(['systemctl', 'is-active', 'skill-monitor']) == 'active'
            except Exception:
                errors.append('verification')
            recovered = not errors
            if not recovered:
                raise RuntimeError('Ops recovery incomplete; maintenance gate retained')
        raise
    finally:
        if gate.installed and (not stopped or recovered):
            gate.leave()
    record = dict(version='0.10.17', deployed=True, deployed_at=int(time.time()),
                  backup=str(backup), scope='restore_missing_unchanged_enterprise_public_asset',
                  journey_version='0.10.16', asset_sha256=source['sha256'],
                  prior_release_files_unchanged=True, only_monitor_restarted=True,
                  gateway_mail_and_payment_unchanged=True, real_business_writes=0,
                  nginx_restored=True, services_active=True)
    (ROOT / 'deployment.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
