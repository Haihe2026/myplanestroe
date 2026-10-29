"""Run the unchanged 0.10.14 gateway with an outer analytics-only wrapper."""
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
OLD = Path(os.environ.get('JOURNEY_BASE_ROOT', '/opt/skill-platform/member-0.10.14'))
sys.path[:0] = [str(ROOT), str(OLD / 'service'), str(OLD / 'core'), str(OLD / 'ops')]
import telemetry
from journey.gateway import observed_handler
original = telemetry.observed_handler
telemetry.observed_handler = lambda parent, store, product, event_db: observed_handler(
    original(parent, store, product, event_db), store)
runpy.run_path(str(OLD / 'service/run_shared.py'), run_name='__main__')
