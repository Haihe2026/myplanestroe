"""Read-only Skill feedback freshness; never fetch marketplace/download statistics."""
from pathlib import Path
import os,sqlite3,time
from contextlib import closing
def summary(path=None):
    target=Path(path or os.environ.get('FIRST_DIALOGUES_DB','/var/lib/skill-monitor/first-dialogues.sqlite3'))
    with closing(sqlite3.connect(target.resolve().as_uri()+'?mode=ro',uri=True,timeout=3)) as c:
        c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
        row=c.execute('SELECT count(*) events,max(received_at) latest_received_at FROM first_dialogues WHERE is_test=0').fetchone()
        groups=[dict(x) for x in c.execute('SELECT skill_id,skill_name,channel,count(*) events,max(received_at) latest_received_at FROM first_dialogues WHERE is_test=0 GROUP BY skill_id,skill_name,channel ORDER BY max(received_at) DESC')]
    return dict(source='skill_first_dialogue',generated_at=int(time.time()),**dict(row),groups=groups)
