import argparse
import importlib.util
import os
from pathlib import Path
import sys
from http.server import ThreadingHTTPServer

p = argparse.ArgumentParser()
p.add_argument('--db', required=True)
p.add_argument('--gemini-db', required=True)
p.add_argument('--temu-db', required=True)
p.add_argument('--temu-source', required=True)
p.add_argument('--port', type=int, default=8791)
a = p.parse_args()
os.umask(0o077)
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
import server
from shared_platform import SharedStore, handler
# Load only the independent Temu input validator. Never run its CLI or provider.
sys.path.append(a.temu_source)
spec = importlib.util.spec_from_file_location('temu_validation', Path(a.temu_source) / 'server.py')
temu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(temu)
def validate_temu(body):
    try:
        return temu.validate(body)
    except temu.pilot.Problem as error:
        raise server.Problem(error.status,error.message) from None

store = SharedStore(a.db, {'gemini': a.gemini_db, 'temu': a.temu_db})
sys.path.insert(0,str(Path(__file__).parent.parent/'ops'))
import telemetry
events=os.environ.get('SKILL_EVENTS_DB','/var/lib/skill-monitor/events.db')
telemetry.initialize(events)
ThreadingHTTPServer(('127.0.0.1', a.port), telemetry.observed_handler(handler(store, validate_temu),store,'shared',events)).serve_forever()
