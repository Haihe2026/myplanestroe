"""Preserve annual clients and telemetry while upgrading the personal assistant."""
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
p.add_argument('--db', required=True)
p.add_argument('--port', type=int, default=8787)
a = p.parse_args()
os.umask(0o077)
limits = json.loads(Path(__file__).with_name('limits.json').read_text())
allowed = {'IMAGE_PILOT_MAX_IMAGES','IMAGE_ASSISTANT_TRIAL_POOL_UNITS','IMAGE_LEGACY_TRIAL_MAX_IMAGES',
           'IMAGE_ASSISTANT_ACCOUNT_IP_DAILY_LIMIT','IMAGE_ASSISTANT_TRIAL_IP_DAILY_LIMIT'}
assert set(limits) == allowed
for key, value in limits.items():
    assert type(value) is int and 0 <= value <= 1000000
    os.environ[key] = str(value)
sys.path[:0] = [a.source, a.annual_source, a.telemetry_source]
import server
import telemetry
from annual_quota import AnnualQuota
from annual_accounts import AnnualAccounts, annual_handler

original_event = telemetry.event_name
telemetry.event_name = lambda path, method: 'activation_attempt' if (path, method) == ('/assistant/register', 'POST') else original_event(path, method)
store = server.Store(a.db)
accounts = AnnualAccounts(store, AnnualQuota(store), server.Problem)
events = os.environ.get('SKILL_EVENTS_DB', '/var/lib/skill-monitor/events.db')
telemetry.initialize(events)
ThreadingHTTPServer(('127.0.0.1', a.port), telemetry.observed_handler(
    annual_handler(server.handler(store), accounts), store, 'gemini', events)).serve_forever()
