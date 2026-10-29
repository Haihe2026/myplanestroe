"""Add optional phone authorization around the unchanged image/payment service."""
import argparse
import json
import os
import sys
from pathlib import Path
from http.server import ThreadingHTTPServer

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--annual-source', required=True)
p.add_argument('--telemetry-source', required=True)
p.add_argument('--limits', required=True)
p.add_argument('--db', required=True)
p.add_argument('--port', type=int, default=8787)
a = p.parse_args()
os.umask(0o077)
limits = json.loads(Path(a.limits).read_text())
allowed = {'IMAGE_PILOT_MAX_IMAGES','IMAGE_ASSISTANT_TRIAL_POOL_UNITS','IMAGE_LEGACY_TRIAL_MAX_IMAGES',
           'IMAGE_ASSISTANT_ACCOUNT_IP_DAILY_LIMIT','IMAGE_ASSISTANT_TRIAL_IP_DAILY_LIMIT'}
assert set(limits) == allowed
for key, value in limits.items():
    assert type(value) is int and 0 <= value <= 1000000
    os.environ[key] = str(value)
sys.path[:0] = [a.source, str(Path(__file__).parent / 'service'), a.annual_source, a.telemetry_source]
import server
import telemetry
from annual_quota import AnnualQuota
from annual_accounts import AnnualAccounts, annual_handler
from phone_auth import PhoneAuth, phone_handler

old_event = telemetry.event_name
def event_name(path, method):
    if (path, method) == ('/assistant/register', 'POST'):
        return 'activation_attempt'
    return {('/phone-auth/create', 'POST'): 'phone_authorization_open',
            ('/phone-auth/send', 'POST'): 'phone_code_requested',
            ('/phone-auth/verify', 'POST'): 'phone_verification_attempt',
            ('/phone-auth/poll', 'POST'): 'phone_authorization_check'}.get((path, method)) or old_event(path, method)
telemetry.event_name = event_name
store = server.Store(a.db)
accounts = AnnualAccounts(store, AnnualQuota(store), server.Problem)
events = os.environ.get('SKILL_EVENTS_DB', '/var/lib/skill-monitor/events.db')
telemetry.initialize(events)
auth = PhoneAuth(store, server.Problem)
parent = phone_handler(annual_handler(server.handler(store), accounts), auth)
ThreadingHTTPServer(('127.0.0.1', a.port), telemetry.observed_handler(parent, store, 'gemini', events)).serve_forever()
