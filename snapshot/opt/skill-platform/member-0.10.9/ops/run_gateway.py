"""Wrap the existing gateway without replacing its billing implementation."""
import argparse
import os
import sys
from http.server import ThreadingHTTPServer
from telemetry import initialize, observed_handler

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
p.add_argument('--product', choices=['gemini', 'temu'], required=True)
p.add_argument('--db', required=True)
p.add_argument('--port', type=int, required=True)
a = p.parse_args()
os.umask(0o077)
sys.path.insert(0, a.source)
import server
events = os.environ.get('SKILL_EVENTS_DB', '/var/lib/skill-monitor/events.db')
initialize(events)
store = server.Store(a.db) if a.product == 'gemini' else server.Store(a.db, server.EditProvider())
ThreadingHTTPServer(('127.0.0.1', a.port), observed_handler(server.handler(store), store, a.product, events)).serve_forever()
