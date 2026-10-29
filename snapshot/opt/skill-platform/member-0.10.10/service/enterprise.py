"""Product-scoped Temu trials and customer feedback, separate from paid balances."""
import json
import os
import time

from permanent_plans import TEMU_PLANS as PLANS, LEGACY_TEMU_PLANS as LEGACY_PLANS
CATEGORIES = ('product_identity', 'background', 'composition', 'detail', 'workflow', 'other')
QUESTION = '这张图还有哪里需要优化？可以告诉我商品还原、背景、构图或细节上的想法，我会记录到这次任务，方便后续改进。'


class Enterprise:
    def __init__(self, store, problem):
        self.store, self.problem = store, problem
        with store.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS temu_enterprise_trials(
                  user_id TEXT PRIMARY KEY, allowance INTEGER NOT NULL CHECK(allowance=3), created INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS temu_trial_jobs(job_id TEXT PRIMARY KEY,user_id TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS temu_trial_jobs_user ON temu_trial_jobs(user_id);
                CREATE TABLE IF NOT EXISTS temu_customer_feedback(
                  user_id TEXT NOT NULL,job_id TEXT NOT NULL,feedback_id TEXT NOT NULL,
                  category TEXT NOT NULL,body TEXT NOT NULL,created INTEGER NOT NULL,
                  PRIMARY KEY(user_id,feedback_id));
            ''')

    def start(self, uid):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
                raise self.problem(401, '请先关联原账户')
            c.execute('INSERT OR IGNORE INTO temu_enterprise_trials VALUES(?,3,?)', (uid, int(time.time())))
        return self.quota(uid)

    def quota(self, uid, connection=None):
        if connection is None:
            with self.store.connect() as c:
                return self.quota(uid, c)
        c = connection
        enrolled = bool(c.execute('SELECT 1 FROM temu_enterprise_trials WHERE user_id=?', (uid,)).fetchone())
        counts = dict(c.execute('''SELECT j.status,count(*) FROM temu_trial_jobs t
            JOIN jobs j ON j.id=t.job_id WHERE t.user_id=? GROUP BY j.status''', (uid,)))
        used, pending = counts.get('succeeded', 0), counts.get('pending', 0)
        return dict(trial_total=3 if enrolled else 0, trial_used=used, trial_pending=pending,
                    trial_remaining=max(0, 3-used-pending) if enrolled else 0, trial_product='temu')

    def available(self, c, uid):
        if self.quota(uid, c)['trial_remaining'] < 1:
            return False
        allocated = c.execute('''SELECT count(*) FROM temu_trial_jobs t JOIN jobs j ON j.id=t.job_id
            WHERE j.status IN ('pending','succeeded')''').fetchone()[0]
        if allocated >= int(os.environ.get('TEMU_ENTERPRISE_TRIAL_POOL_IMAGES', '300')):
            raise self.problem(503, '企业体验任务较多，请稍后沿原需求继续')
        return True

    def feedback(self, uid, body):
        jid, fid, category, text = (body.get(k) for k in ('job_id', 'feedback_id', 'category', 'text'))
        if (not isinstance(jid, str) or not 1 <= len(jid) <= 64
                or not isinstance(fid, str) or not 16 <= len(fid) <= 100
                or category not in CATEGORIES or not isinstance(text, str)
                or not 1 <= len(text.strip()) <= 2000):
            raise self.problem(400, '请提供对应图片、反馈分类与具体意见')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('''SELECT j.status FROM jobs j JOIN job_products p ON p.job_id=j.id
                WHERE j.id=? AND j.user_id=? AND p.product='temu' ''', (jid, uid)).fetchone()
            if not row or row[0] != 'succeeded':
                raise self.problem(404, '请对本人已完成的Temu图片提交反馈')
            old = c.execute('SELECT job_id,category,body FROM temu_customer_feedback WHERE user_id=? AND feedback_id=?', (uid, fid)).fetchone()
            if old and tuple(old) != (jid, category, text.strip()):
                raise self.problem(409, '这条反馈标识已使用，请保留原记录')
            c.execute('INSERT OR IGNORE INTO temu_customer_feedback VALUES(?,?,?,?,?,?)',
                      (uid, jid, fid, category, text.strip(), int(time.time())))
        return dict(saved=True, replayed=bool(old), feedback_id=fid)

    def history(self, uid):
        with self.store.connect() as c:
            items = [dict(r) for r in c.execute('''SELECT j.id,j.status,j.created,
                CASE WHEN t.job_id IS NULL THEN 'paid_or_legacy' ELSE 'trial' END AS usage_type,
                (SELECT count(*) FROM temu_customer_feedback f WHERE f.job_id=j.id AND f.user_id=j.user_id) AS feedback_count
                FROM jobs j JOIN job_products p ON p.job_id=j.id LEFT JOIN temu_trial_jobs t ON t.job_id=j.id
                WHERE j.user_id=? AND p.product='temu' ORDER BY j.created DESC,j.id DESC LIMIT 100''', (uid,))]
        return dict(self.quota(uid), items=items, feedback_question=QUESTION)

    def report(self):
        with self.store.connect() as c:
            return dict(
                totals=dict(c.execute('SELECT category,count(*) FROM temu_customer_feedback GROUP BY category')),
                items=[dict(r) for r in c.execute('''SELECT user_id,job_id,feedback_id,category,body,created
                    FROM temu_customer_feedback ORDER BY created DESC,feedback_id DESC LIMIT 500''')],
                trials=[dict(r) for r in c.execute('''SELECT e.user_id,e.created,
                    sum(CASE WHEN j.status='succeeded' THEN 1 ELSE 0 END) AS used,
                    sum(CASE WHEN j.status='pending' THEN 1 ELSE 0 END) AS pending
                    FROM temu_enterprise_trials e LEFT JOIN temu_trial_jobs t ON t.user_id=e.user_id
                    LEFT JOIN jobs j ON j.id=t.job_id GROUP BY e.user_id ORDER BY e.created DESC LIMIT 500''')])
