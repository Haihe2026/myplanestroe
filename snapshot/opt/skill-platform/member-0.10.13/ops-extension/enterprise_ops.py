"""Read-only enterprise feedback view, guarded by existing admin authentication."""
from contextlib import closing
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit


def report(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=10)) as c:
        c.row_factory=sqlite3.Row
        return dict(
            totals={r[0]:r[1] for r in c.execute('SELECT category,count(*) FROM temu_customer_feedback GROUP BY category')},
            items=[dict(r) for r in c.execute('SELECT user_id,job_id,category,body,created FROM temu_customer_feedback ORDER BY created DESC,feedback_id DESC LIMIT 500')],
            trials=[dict(r) for r in c.execute('''SELECT e.user_id,e.created,
              sum(CASE WHEN j.status='succeeded' THEN 1 ELSE 0 END) AS used,
              sum(CASE WHEN j.status='pending' THEN 1 ELSE 0 END) AS pending
              FROM temu_enterprise_trials e LEFT JOIN temu_trial_jobs t ON t.user_id=e.user_id
              LEFT JOIN jobs j ON j.id=t.job_id GROUP BY e.user_id ORDER BY e.created DESC LIMIT 500''')])


def extend_handler(original,db):
    def factory(*args,**kwargs):
        base=original(*args,**kwargs)
        class Handler(base):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
                if status==200 and mime.startswith('text/html') and isinstance(result,bytes):
                    result=result.replace(b'</head>',b'<script defer src="/ops/enterprise-feedback.js?v=0.10.3"></script></head>',1)
                return super().send(status,result,mime,cookie=cookie)
            def do_GET(self):
                path=urlsplit(self.path).path
                if path=='/ops/enterprise-feedback.js':
                    return self.send(200,Path(__file__).with_name('enterprise-feedback.js').read_bytes(),'application/javascript; charset=utf-8')
                if path!='/ops/api/enterprise-feedback':return super().do_GET()
                if not self.authenticated():return self.send(401,{'error':'请登录管理后台'})
                try:return self.send(200,report(db))
                except Exception:return self.send(503,{'error':'反馈记录暂不可用，请稍后刷新'})
        return Handler
    return factory
