"""Remove the explicitly authorized live verification account, not customer data."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

UID='00000000-0000-4000-8000-000000000000'
JOB='00000000-0000-4000-8000-000000000000'
IMAGE_HASH='REDACTED_FOR_HANDOFF'
ROOT=Path('/opt/skill-platform/assistant-1.3.0')
DB=Path('/var/lib/image-assistant/pilot.db')
EVENTS=Path('/var/lib/skill-monitor/events.db')
assert Path(__file__).resolve().parent==ROOT
backup=DB.parent/'backups'/('remove-test-'+str(int(time.time())))
backup.mkdir(mode=0o700)
limits_path=ROOT/'limits.json'
limits=json.loads(limits_path.read_text())
shutil.copy2(limits_path,backup/'limits.json')

def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout

assert not run(['ss','-Htan','state','established','( sport = :8787 )']).strip(),'Active requests; retry later'
run(['systemctl','stop','image-assistant'])
committed=False
try:
    for source,name in ((DB,'pilot.db'),(EVENTS,'events.db')):
        with sqlite3.connect(source) as c,sqlite3.connect(backup/name) as target:c.backup(target)
    c=sqlite3.connect(DB,timeout=15)
    c.row_factory=sqlite3.Row
    try:
        c.execute('ATTACH DATABASE ? AS events_db',(str(EVENTS),))
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT balance FROM users WHERE id=?',(UID,)).fetchone()
        assert row and row['balance']==9,'Balance changed; audit before deleting'
        assert c.execute('SELECT units FROM assistant_trial_grants WHERE user_id=?',(UID,)).fetchone()['units']==10
        jobs=c.execute('SELECT id,status,image FROM jobs WHERE user_id=?',(UID,)).fetchall()
        assert len(jobs)==1 and jobs[0]['id']==JOB and jobs[0]['status']=='succeeded'
        assert hashlib.sha256(jobs[0]['image']).hexdigest()==IMAGE_HASH
        assert c.execute('SELECT count(*) FROM member_orders WHERE user_id=?',(UID,)).fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM member_grants WHERE user_id=?',(UID,)).fetchone()[0]==0
        assert c.execute('SELECT count(*) FROM paid_jobs WHERE job_id=?',(JOB,)).fetchone()[0]==0
        before=[tuple(r) for r in c.execute('SELECT id,balance FROM users WHERE id!=? ORDER BY id',(UID,))]
        assigned=c.execute('SELECT coalesce(sum(units),0) FROM assistant_trial_grants').fetchone()[0]
        old_capacity=limits['IMAGE_ASSISTANT_TRIAL_POOL_UNITS']-assigned
        # Keep the successful provider call charged against the authorized trial budget.
        limits['IMAGE_ASSISTANT_TRIAL_POOL_UNITS']-=1
        limits['IMAGE_PILOT_MAX_IMAGES']-=1
        for table in ('api_jobs','grant_jobs','paid_jobs'):
            c.execute(f'DELETE FROM {table} WHERE job_id IN (SELECT id FROM jobs WHERE user_id=?)',(UID,))
        for table in ('sessions','trial_claims','ledger','jobs','web_tickets','web_sessions','paid_wallets',
                      'customer_keys','member_gifts','member_grants','annual_activations','annual_activation_requests','assistant_trial_grants'):
            c.execute(f'DELETE FROM {table} WHERE user_id=?',(UID,))
        c.execute('DELETE FROM events_db.events WHERE product=? AND user_id=?',('gemini',UID))
        c.execute('DELETE FROM users WHERE id=?',(UID,))
        assert before==[tuple(r) for r in c.execute('SELECT id,balance FROM users ORDER BY id')]
        assigned_after=c.execute('SELECT coalesce(sum(units),0) FROM assistant_trial_grants').fetchone()[0]
        new_capacity=limits['IMAGE_ASSISTANT_TRIAL_POOL_UNITS']-assigned_after
        assert new_capacity-old_capacity==9
        temp=limits_path.with_suffix('.json.next')
        temp.write_text(json.dumps(limits,indent=2))
        temp.chmod(0o644)
        temp.replace(limits_path)
        c.commit()
        committed=True
    except Exception:
        c.rollback()
        shutil.copy2(backup/'limits.json',limits_path)
        raise
    finally:c.close()
finally:
    run(['systemctl','start','image-assistant'])
assert committed
record={'deleted_account_prefix':UID[:12],'deleted_verification_jobs':1,'released_unused_points':9000,
        'consumed_points_not_refunded':1000,'available_trial_pool_points':new_capacity*1000,
        'other_users_and_balances_unchanged':True,'backup':str(backup),'cash_refund':False}
(ROOT/'test-account-cleanup.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
