"""One account-scoped Gemini personal trial; never added to the shared paid balance."""
import inspect
from contextvars import ContextVar
import json
import os
import textwrap
import time
import urllib.parse

TRIAL_MODE=ContextVar('gemini_personal_trial_mode',default=None)


def pool_limit():
    return max(0, int(os.environ.get('GEMINI_PERSONAL_TRIAL_POOL_IMAGES', '20')))


class Trial:
    def __init__(self, store, problem):
        self.store, self.problem = store, problem
        with store.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS gemini_personal_trials(
                    user_id TEXT PRIMARY KEY,allowance INTEGER NOT NULL CHECK(allowance=1),created INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS gemini_personal_trial_jobs(
                    job_id TEXT PRIMARY KEY,user_id TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS gemini_personal_trial_user ON gemini_personal_trial_jobs(user_id);
            ''')

    def start(self, uid):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
                raise self.problem(401, '请先关联原账户')
            # Eligibility is inserted only in the new-account registration transaction.
            # Reading/claiming on an existing account must never create a grant.
        return self.store.quota(uid, 'gemini')

    def quota(self, uid, connection=None):
        if connection is None:
            with self.store.connect() as c:
                return self.quota(uid,c)
        c=connection
        enrolled=bool(c.execute('SELECT 1 FROM gemini_personal_trials WHERE user_id=?',(uid,)).fetchone())
        counts=dict(c.execute('''SELECT j.status,count(*) FROM gemini_personal_trial_jobs t
            JOIN jobs j ON j.id=t.job_id WHERE t.user_id=? GROUP BY j.status''',(uid,)))
        used,pending=counts.get('succeeded',0),counts.get('pending',0)
        remaining=max(0,1-used-pending) if enrolled else 0
        allocated=c.execute('''SELECT count(*) FROM gemini_personal_trial_jobs t JOIN jobs j ON j.id=t.job_id
            WHERE j.status IN ('pending','succeeded')''').fetchone()[0]
        limit=pool_limit()
        return dict(total=1 if enrolled else 0,used=used,pending=pending,remaining=remaining,
            available=bool(remaining and (limit==0 or allocated<limit)),
            eligibility='new_account' if enrolled else 'existing_account',
            product='gemini',engine='gemini-personal-sunburst')

    def available(self,c,uid):
        import shared_platform as shared
        import sunburst
        if shared.CURRENT_PRODUCT.get()!='gemini' or sunburst.CURRENT_ENGINE.get()!=sunburst.GEMINI_ENGINE:
            return False
        if TRIAL_MODE.get()=='paid':
            return False
        quota=self.quota(uid,c)
        if quota['remaining']<1:
            if TRIAL_MODE.get()=='free':
                raise self.problem(402,'新用户免费权益不可用，未扣付费次数；请核对账户或确认新的付费方案')
            return False
        if not quota['available']:
            raise self.problem(503,'本轮免费体验池暂满，权益未消耗；不会自动改为付费')
        return True


def replace_once(text,old,new):
    if text.count(old)!=1:
        raise RuntimeError('Trial adapter baseline mismatch; do not start against unknown accounting code')
    return text.replace(old,new,1)


def patch_accounting(server):
    """Retain the proven transaction and refund paths, adding only a separate trial branch."""
    text=textwrap.dedent(inspect.getsource(server.Store.generate))
    text=replace_once(text,'        trial_job = False\n','        trial_job = False\n        gemini_trial_job = False\n')
    text=replace_once(text,'        total = c.execute(', '        if hasattr(self, "gemini_trial") and self.gemini_trial.available(c, uid):\n            trial_job = True\n            gemini_trial_job = True\n        total = c.execute(')
    text=replace_once(text,"        if trial_job:\n            c.execute('INSERT INTO temu_trial_jobs VALUES(?,?)', (jid,uid))",
        "        if gemini_trial_job:\n            c.execute('INSERT INTO gemini_personal_trial_jobs VALUES(?,?)', (jid,uid))\n        elif trial_job:\n            c.execute('INSERT INTO temu_trial_jobs VALUES(?,?)', (jid,uid))")
    text=replace_once(text,"'temu_trial_reserve' if trial_job else 'reserve'",
        "'gemini_personal_trial_reserve' if gemini_trial_job else 'temu_trial_reserve' if trial_job else 'reserve'")
    namespace={}
    exec(compile(text,__file__+':generate','exec'),server.__dict__,namespace)
    server.Store.generate=namespace['generate']
    text=textwrap.dedent(inspect.getsource(server.Store.refund_confirmed_failure))
    text=replace_once(text,"        if hasattr(self, 'enterprise') and c.execute(",
        "        if hasattr(self, 'gemini_trial') and c.execute('SELECT 1 FROM gemini_personal_trial_jobs WHERE job_id=?', (jid,)).fetchone():\n            c.execute(\"INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,0,'gemini_personal_trial_failure_release',?)\", (row['user_id'],jid,int(time.time())))\n            return\n        if hasattr(self, 'enterprise') and c.execute(")
    namespace={}
    exec(compile(text,__file__+':refund','exec'),server.__dict__,namespace)
    server.Store.refund_confirmed_failure=namespace['refund_confirmed_failure']


def patch_registration(server,shared):
    """Record eligibility atomically, only for genuinely new Gemini account identities."""
    text=textwrap.dedent(inspect.getsource(shared.SharedStore.register_product))
    old="        c.execute('INSERT OR IGNORE INTO product_accounts VALUES(?,?,?)', (product, uid, int(time.time())))"
    new=old+"\n        if created and product == 'gemini' and not any(known.values()):\n            c.execute('INSERT OR IGNORE INTO gemini_personal_trials VALUES(?,1,?)', (uid,now))"
    text=replace_once(text,old,new)
    namespace={}
    exec(compile(text,__file__+':register','exec'),shared.__dict__,namespace)
    shared.SharedStore.register_product=namespace['register_product']


def install(server,shared):
    if getattr(shared,'_gemini_trial_installed',False):
        return
    shared._gemini_trial_installed=True
    patch_accounting(server)
    patch_registration(server,shared)
    old_init,old_quota,old_handler=shared.SharedStore.__init__,shared.SharedStore.quota,shared.handler

    def init(self,*args,**kwargs):
        old_init(self,*args,**kwargs)
        self.gemini_trial=Trial(self,server.Problem)

    def quota(self,uid,product):
        data=old_quota(self,uid,product)
        if product=='gemini' and hasattr(self,'gemini_trial'):
            data=dict(data,gemini_trial=self.gemini_trial.quota(uid))
        return data

    def handler(store,validator=None):
        parent=old_handler(store,validator)
        class Handler(parent):
            def run_request(self):
                if urllib.parse.urlsplit(self.path).path!='/platform-api/gemini/personal-trial':
                    return super().run_request()
                self.connection.settimeout(15)
                try:
                    if self.command!='POST':
                        raise server.Problem(405,'请使用POST关联本账户体验')
                    token=self.headers.get('Authorization','').removeprefix('Bearer ')
                    uid=store.user(token)
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=1024 or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                        raise server.Problem(400,'请使用空JSON对象')
                    body=json.loads(self.rfile.read(size))
                    if body!={}:
                        raise server.Problem(400,'体验次数由服务器固定，不接受客户端设置')
                    return self.send(200,store.gemini_trial.start(uid))
                except server.Problem as error:
                    return self.send(error.status,dict(error=error.message))
                except (ValueError,TypeError):
                    return self.send(400,dict(error='请求格式需要检查'))
            do_POST=run_request
            do_GET=run_request
        return Handler

    shared.SharedStore.__init__=init
    shared.SharedStore.quota=quota
    shared.handler=handler
