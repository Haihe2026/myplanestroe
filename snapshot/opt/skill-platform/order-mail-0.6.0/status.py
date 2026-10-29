"""Read-only operational status, excluding credentials, message bodies and users."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess

config = json.loads(Path('/etc/skill-order-mail/config.json').read_text())
with closing(sqlite3.connect(Path(config['state_db']).as_uri() + '?mode=ro', uri=True)) as db:
    db.row_factory = sqlite3.Row
    output = {
        'outbox': [dict(row) for row in db.execute('SELECT kind,status,count(*) n FROM outbox GROUP BY kind,status')],
        'inbox': [dict(row) for row in db.execute('SELECT decision,count(*) n FROM inbox GROUP BY decision')],
        'last_poll': db.execute("SELECT value FROM settings WHERE key='last_poll'").fetchone(),
    }
    output['last_poll'] = output['last_poll'][0] if output['last_poll'] else None
output['worker'] = subprocess.run(['systemctl', 'is-active', 'skill-order-mail'], capture_output=True, text=True).stdout.strip()
print(json.dumps(output))
