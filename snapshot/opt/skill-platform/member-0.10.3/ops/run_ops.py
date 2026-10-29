import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
from http.server import ThreadingHTTPServer

p=argparse.ArgumentParser()
p.add_argument('--config',required=True)
p.add_argument('--shared-db',required=True)
p.add_argument('--temu-source',required=True)
a=p.parse_args()
os.umask(0o077)
sys.path.insert(0,str(Path(__file__).parent.parent/'core'))
from manual_payments import ManualMembership
from settlement import Settlement
from shared_reports import Reports, Settlements
from monitor import handler
config=json.loads(Path(a.config).read_text())
if len(config['password'])<32:raise ValueError('Strong admin credential required')
spec=importlib.util.spec_from_file_location('temu_manual',Path(a.temu_source)/'manual_payments.py')
temu=importlib.util.module_from_spec(spec)
spec.loader.exec_module(temu)
adapters={
    'gemini':Settlement(config['products']['gemini'],ManualMembership.confirm_manual),
    'temu':Settlement(config['products']['temu'],temu.ManualMembership.confirm_manual,'temu','temu-image-assistant'),
    'shared':Settlement(a.shared_db,ManualMembership.confirm_manual,'shared')}
ThreadingHTTPServer(('127.0.0.1',8790),handler(Reports(config['products'],config['events'],a.shared_db),
    config['password'],Path(__file__).parent.parent/'ops-web',settler=Settlements(adapters))).serve_forever()
