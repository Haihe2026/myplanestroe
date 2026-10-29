"""Deploy the event runner only; retain all prior source and service overrides."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path('/opt/skill-platform/order-mail-0.6.2')
PREVIOUS = Path('/opt/skill-platform/order-mail-0.6.1')
DROPIN = Path('/etc/systemd/system/skill-order-mail.service.d/events.conf')


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def deploy():
    os.umask(0o077)
    for name in ('mail_worker.py', 'mail_auth.py', 'email_settlement.py'):
        assert (ROOT / name).read_bytes() == (PREVIOUS / name).read_bytes(), name
    backup = Path('/var/backups/skill-order-mail') / ('events-' + str(int(time.time())))
    backup.mkdir(parents=True, mode=0o700)
    if DROPIN.exists():
        shutil.copy2(DROPIN, backup / DROPIN.name)
    (backup / 'previous-exec.txt').write_text(command('systemctl', 'show', 'skill-order-mail', '-p', 'ExecStart'))
    try:
        DROPIN.write_text('[Service]\nExecStart=\nExecStart=/opt/skill-platform/order-mail-0.6.0/venv/bin/python /opt/skill-platform/order-mail-0.6.2/event_runner.py\n')
        os.chmod(DROPIN, 0o644)
        command('systemctl', 'daemon-reload')
        command('systemctl', 'restart', 'skill-order-mail')
        time.sleep(3)
        assert command('systemctl', 'is-active', 'skill-order-mail') == 'active'
        assert '/order-mail-0.6.2/event_runner.py' in command('systemctl', 'show', 'skill-order-mail', '-p', 'ExecStart')
        output = command('/opt/skill-platform/order-mail-0.6.0/venv/bin/python', '/opt/skill-platform/order-mail-0.6.0/status.py')
        status = json.loads(output)
        assert status['worker'] == 'active'
        assert 0 <= time.time() - int(status['last_poll']) < 180
        report = {'version': '0.6.2', 'deployed': True, 'backup': str(backup),
                  'notification_trigger': 'Linux database change events and startup recovery',
                  'business_database_writes_by_deployment': False,
                  'mail_auth_and_settlement_sources_unchanged': True,
                  'mailbox_reply_check_seconds': 30, 'status': status}
        (ROOT / 'deployment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps(report, ensure_ascii=False))
    except BaseException:
        previous = backup / DROPIN.name
        if previous.exists():
            shutil.copy2(previous, DROPIN)
        else:
            DROPIN.unlink(missing_ok=True)
        command('systemctl', 'daemon-reload')
        command('systemctl', 'restart', 'skill-order-mail')
        raise


if __name__ == '__main__':
    deploy()
