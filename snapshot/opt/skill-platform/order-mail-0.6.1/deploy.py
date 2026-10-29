"""Tighten the approval policy; do not roll back to the any-reply behavior."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

ROOT = Path('/opt/skill-platform/order-mail-0.6.1')
PREVIOUS = Path('/opt/skill-platform/order-mail-0.6.0')
assert Path(__file__).resolve().parent == ROOT
os.umask(0o077)


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    for name, hashes in manifest.items():
        assert hashlib.sha256((PREVIOUS / name).read_bytes()).hexdigest() == hashes['old']
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == hashes['new']
    assert manifest['email_settlement.py']['old'] == manifest['email_settlement.py']['new']
    run('systemctl', 'stop', 'skill-order-mail')
    backup = Path('/var/backups/skill-order-mail') / ('approval-command-' + str(int(time.time())))
    backup.mkdir(parents=True, mode=0o700)
    config = json.loads(Path('/etc/skill-order-mail/config.json').read_text())
    with closing(sqlite3.connect(config['state_db'])) as db:
        with closing(sqlite3.connect(backup / 'state.db')) as target:
            db.backup(target)
        with db:
            rows = db.execute("SELECT key,body FROM outbox WHERE status='queued' AND kind IN ('order','test')").fetchall()
            for key, body in rows:
                body = body.replace('回复本邮件即可，无需固定口令。', '回复本邮件，正文填写：允许该客户发放。')
                body = body.replace('内容随意。', '正文填写：允许该客户发放。')
                body = body.replace('确认真实收款后回复对应订单邮件，即自动发放一次。', '确认真实收款后，在对应订单邮件中回复“允许该客户发放”，即自动发放一次。')
                db.execute('UPDATE outbox SET body=? WHERE key=?', (body, key))
    dropin = Path('/etc/systemd/system/skill-order-mail.service.d/approval-command.conf')
    assert not dropin.exists()
    dropin.parent.mkdir(exist_ok=True, mode=0o755)
    shutil.copy2(ROOT / 'approval-command.conf', dropin)
    dropin.chmod(0o644)
    run('systemctl', 'daemon-reload')
    try:
        run('systemctl', 'start', 'skill-order-mail')
        time.sleep(4)
        assert run('systemctl', 'is-active', 'skill-order-mail').strip() == 'active'
        command = run('systemctl', 'show', 'skill-order-mail', '--property=ExecStart')
        assert '/order-mail-0.6.1/mail_worker.py' in command
    except Exception:
        subprocess.run(['systemctl', 'stop', 'skill-order-mail'], capture_output=True)
        # Keep the strict override: never resume permissive approval after an error.
        raise
    result = {'version': '0.6.1', 'deployed': True, 'backup': str(backup),
              'approval_command': '允许该客户发放', 'quoted_history_does_not_approve': True,
              'identity_order_and_idempotency_checks_retained': True, 'financial_rows_modified_by_deployment': False,
              'worker_active': True, 'original_payment_services_restarted': False}
    (ROOT / 'deployment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
