"""One new account-scoped Temu trial; preserve historical grants and paid ledgers."""
import time


def install(shared):
    previous=shared.Enterprise

    class Enterprise(previous):
        def __init__(self,store,problem):
            super().__init__(store,problem)
            with store.connect() as c:
                c.execute('''CREATE TABLE IF NOT EXISTS temu_trial_policy(
                    user_id TEXT PRIMARY KEY, trial_total INTEGER NOT NULL CHECK(trial_total=1),
                    created INTEGER NOT NULL)''')

        def start(self,uid):
            with self.store.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                if not c.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():
                    raise self.problem(401,'请先关联原账户')
                if not c.execute('SELECT 1 FROM temu_enterprise_trials WHERE user_id=?',(uid,)).fetchone():
                    now=int(time.time())
                    # Keep the legacy table's CHECK(allowance=3) and existing rows intact.
                    c.execute('INSERT INTO temu_enterprise_trials VALUES(?,3,?)',(uid,now))
                    c.execute('INSERT INTO temu_trial_policy VALUES(?,1,?)',(uid,now))
            return self.quota(uid)

        def quota(self,uid,connection=None):
            if connection is None:
                with self.store.connect() as c:return self.quota(uid,c)
            value=super().quota(uid,connection)
            policy=connection.execute('SELECT trial_total FROM temu_trial_policy WHERE user_id=?',(uid,)).fetchone()
            if policy:
                value['trial_total']=int(policy[0])
                value['trial_remaining']=max(0,value['trial_total']-value['trial_used']-value['trial_pending'])
            return value

    shared.Enterprise=Enterprise
