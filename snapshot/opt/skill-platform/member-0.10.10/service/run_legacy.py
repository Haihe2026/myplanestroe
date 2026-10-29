"""Preserve old billing and identity, stopping new automatic giveaways."""
import argparse
import os
import json
from pathlib import Path
import sys
from http.server import ThreadingHTTPServer

p = argparse.ArgumentParser()
p.add_argument('--product', choices=['gemini', 'temu'], required=True)
p.add_argument('--source', required=True)
p.add_argument('--db', required=True)
p.add_argument('--port', type=int, required=True)
a = p.parse_args()
os.umask(0o077)
sys.path.insert(0, a.source)
import server
if a.product == 'gemini':
    for key, value in json.loads(Path('/opt/skill-platform/assistant-1.3.0/limits.json').read_text()).items():
        os.environ[key] = str(value)
from types import MethodType
from paid_registration import register
if a.product == 'temu':
    # The shared zero-grant adapter imports the service's exception/point functions.
    server.Problem = server.pilot.Problem
    server.digest = server.pilot.digest
    server.points = server.pilot.points
store = server.Store(a.db) if a.product == 'gemini' else server.Store(a.db, server.EditProvider())
store.register = MethodType(register, store)
sys.path.insert(0,str(Path(__file__).parent.parent/'ops'))
import telemetry
events = os.environ.get('SKILL_EVENTS_DB', '/var/lib/skill-monitor/events.db')
telemetry.initialize(events)
parent = server.handler(store)
if a.product == 'gemini':
    sys.path.extend(['/opt/skill-platform/1.5.0/service', '/opt/skill-platform/assistant-1.4.0/service'])
    from annual_quota import AnnualQuota
    from annual_accounts import AnnualAccounts, annual_handler
    from phone_auth import PhoneAuth, phone_handler
    class PaidAnnualAccounts(AnnualAccounts):
        def account(self, secret, accepted, ip):
            result=self.store.register(secret,ip,accepted,0)
            old=self.quota.status(self.store.user(secret))
            return dict(result,awarded_points=0,annual_balance_points=old.get('balance_points',0),
                expires_at=old.get('expires_at'),expired=old.get('active') is False,
                payment_verified=False,activation_policy='paid_first')
    parent = phone_handler(annual_handler(parent, PaidAnnualAccounts(store, AnnualQuota(store), server.Problem)), PhoneAuth(store, server.Problem))
class PaidFirst(parent):
    def run_request(self):
        if self.path in ('/activate','/temu/activate'):
            return self.send(403,{'error':'旧试用领取入口已停用，请用原凭证恢复账户；已有次数保留。'})
        if self.path in ('/health','/temu/health') and self.command == 'GET':
            return self.send(200,dict(status='ok',provider_configured=store.provider.ready,
                reference_editing=getattr(store.provider,'edit_ready',store.provider.ready),
                public_registration=store.public_trial_enabled(),assistant_trial_points=0,
                new_user_uses=0,version='paid-first-0.5.0',point_scale=1000,image_cost_points=1000))
        return super().run_request()
    do_GET = run_request
    do_POST = run_request
ThreadingHTTPServer(('127.0.0.1', a.port), telemetry.observed_handler(PaidFirst, store, a.product, events)).serve_forever()
