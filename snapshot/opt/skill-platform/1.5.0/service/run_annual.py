"""Add annual allocation without replacing image logic or telemetry."""
import argparse
import os
import sys
from http.server import ThreadingHTTPServer
from annual_quota import AnnualQuota
from annual_accounts import AnnualAccounts, annual_handler
p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--telemetry-source', required=True)
p.add_argument('--db', required=True)
p.add_argument('--port', type=int, default=8787)
a = p.parse_args()
os.umask(0o077)
sys.path.insert(0, a.source)
sys.path.insert(0, a.telemetry_source)
import server
from telemetry import initialize, observed_handler
store = server.Store(a.db)
quota = AnnualQuota(store)
accounts = AnnualAccounts(store, quota, server.Problem)
events = os.environ.get('SKILL_EVENTS_DB', '/var/lib/skill-monitor/events.db')
initialize(events)
ThreadingHTTPServer(('127.0.0.1', a.port), observed_handler(
    annual_handler(server.handler(store), accounts), store, 'gemini', events)).serve_forever()
