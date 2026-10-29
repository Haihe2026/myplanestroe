"""Isolated prepaid test gateway and operator-only fulfillment command."""
import argparse
import json
import os
import sys
from http.server import ThreadingHTTPServer
from quota_pack import QuotaPack,pack_handler
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--db',required=True)
p.add_argument('--port',type=int,default=18790);p.add_argument('--confirm-account');p.add_argument('--order-id')
p.add_argument('--amount-fen',type=int);p.add_argument('--confirmed-payment',action='store_true')
a=p.parse_args();os.umask(0o077);sys.path.insert(0,a.source)
import server
store=server.Store(a.db);pack=QuotaPack(store,server.Problem)
if a.confirm_account:
    print(json.dumps(pack.confirm_purchase(a.confirm_account,a.order_id,a.amount_fen,a.confirmed_payment)))
else:
    ThreadingHTTPServer(('127.0.0.1',a.port),pack_handler(server.handler(store),pack)).serve_forever()
