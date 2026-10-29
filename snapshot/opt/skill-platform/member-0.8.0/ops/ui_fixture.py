"""Synthetic local browser-test server. Never uses production databases."""
import tempfile
from pathlib import Path
from http.server import ThreadingHTTPServer
from test_settlement import fixture, Settlement, ManualMembership
from monitor import handler, Report
from telemetry import initialize

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);db=root/'test.db';events=root/'events.db'
    fixture(db);initialize(events)
    server=ThreadingHTTPServer(('127.0.0.1',18890),handler(
        Report({'gemini':str(db)},str(events)), 'synthetic-password-for-local-test-only',
        Path(__file__).resolve().parents[1]/'web', False, Settlement(db,ManualMembership.confirm_manual)))
    print('READY',flush=True)
    try:server.serve_forever()
    finally:server.server_close()
