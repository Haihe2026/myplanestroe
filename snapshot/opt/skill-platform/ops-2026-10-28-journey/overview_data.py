"""Authenticated aggregate projection only; never writes or enrolls an account."""
from pathlib import Path
from contextlib import closing
from datetime import datetime, timedelta, timezone
import sqlite3, time

TZ = timezone(timedelta(hours=8))

def overview(path, days=14, now=None):
    if type(days) is not int or not 1 <= days <= 90:
        raise ValueError('invalid_days')
    now = int(time.time()) if now is None else now
    first = datetime.fromtimestamp(now, TZ).date() - timedelta(days=days-1)
    since = int(datetime.combine(first, datetime.min.time(), TZ).timestamp())
    result = dict(generated_at=now, unique_accounts=None, pending_orders=None, trend=None,
                  scope='共享生图服务；按任务创建日统计，不代表完成时间；未标记测试可能包含在内。', missing=[])
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True, timeout=4)) as c:
        c.execute('PRAGMA query_only=ON')
        c.execute('BEGIN')
        try:
            result['unique_accounts'] = c.execute('SELECT count(*) FROM users').fetchone()[0]
        except sqlite3.Error:
            result['missing'].append('accounts')
        try:
            result['pending_orders'] = c.execute("SELECT count(*) FROM member_orders WHERE status='reported'").fetchone()[0]
        except sqlite3.Error:
            result['missing'].append('orders')
        try:
            rows = c.execute("""SELECT date(j.created,'unixepoch','+8 hours') day,p.product,count(*) n
                FROM jobs j JOIN job_products p ON p.job_id=j.id
                WHERE j.created>=? AND j.created<=? AND p.product IN ('gemini','temu')
                GROUP BY day,p.product ORDER BY day""", (since,now)).fetchall()
            points = {((first+timedelta(days=i)).isoformat(),p):0 for i in range(days) for p in ('gemini','temu')}
            for day, product, count in rows:
                if (day,product) in points: points[day,product]=count
            # Explicit zeros are from a successful full-range SQL query, not backfilled channel snapshots.
            result['trend']=[dict(date=(first+timedelta(days=i)).isoformat(), **{
                p:points[((first+timedelta(days=i)).isoformat(),p)] for p in ('gemini','temu')}) for i in range(days)]
        except sqlite3.Error:
            result['missing'].append('trend')
    return result
