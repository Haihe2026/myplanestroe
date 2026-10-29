"""Synthetic isolated admin fixture; terminated by the browser test."""
import os
from pathlib import Path
import sys
import tempfile
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'core'),str(ROOT/'service'),str(ROOT/'ops')]
from test_shared import Provider
import server
from shared_platform import SharedStore
from shared_reports import Reports,Settlements
from settlement import Settlement
from monitor import handler
from telemetry import initialize

os.environ.update(IMAGE_PUBLIC_TRIAL_ENABLED='yes',IMAGE_TRIAL_HMAC_KEY='synthetic-key-only',IMAGE_MANUAL_QR_ENABLED='yes')
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);old={p:server.Store(root/(p+'.db'),Provider()) for p in ('gemini','temu')}
    store=SharedStore(root/'shared.db',{p:s.database for p,s in old.items()},Provider())
    secret='a'*43
    store.register_product('gemini',secret,'192.0.2.1',True)
    uid=store.user(secret)
    order=store.membership.order(uid,'ultra','gemini')
    store.membership.report_paid(uid,order['id'])
    with store.connect() as c:c.execute('UPDATE member_orders SET id=? WHERE id=?',('a'*32,order['id']));c.execute('UPDATE order_sources SET order_id=? WHERE order_id=?',('a'*32,order['id']))
    initialize(root/'events.db')
    settler=Settlements({'shared':Settlement(store.database,store.membership.confirm_manual.__func__,'shared')})
    service=ThreadingHTTPServer(('127.0.0.1',18890),handler(Reports({p:s.database for p,s in old.items()},str(root/'events.db'),store.database),
        'synthetic-password-for-local-test-only',ROOT/'ops-web',False,settler))
    print('READY',flush=True)
    try:service.serve_forever()
    finally:service.server_close()
