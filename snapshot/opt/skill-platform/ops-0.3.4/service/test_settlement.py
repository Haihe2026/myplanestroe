import contextlib
from concurrent.futures import ThreadPoolExecutor
import http.cookiejar
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'gemini-image-assistant/versions/1.3.0/service'))
from manual_payments import ManualMembership
from settlement import Settlement, SettlementError
from monitor import handler, Report
from telemetry import initialize

OID='a'*32
SECOND='b'*32
TX='REDACTED_FOR_HANDOFF'


def fixture(path):
    with contextlib.closing(sqlite3.connect(path)) as c, c:
        c.executescript('''
        CREATE TABLE users(id TEXT PRIMARY KEY,balance INTEGER NOT NULL CHECK(balance>=0));
        CREATE TABLE member_orders(id TEXT PRIMARY KEY,user_id TEXT,product TEXT,plan TEXT,amount_fen INTEGER,
            units INTEGER,status TEXT,created INTEGER,paid_at INTEGER,transaction_id TEXT UNIQUE,provider TEXT);
        CREATE TABLE member_grants(order_id TEXT PRIMARY KEY,user_id TEXT,remaining INTEGER,expires INTEGER);
        CREATE TABLE paid_wallets(user_id TEXT PRIMARY KEY,remaining INTEGER);
        CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id TEXT,job_id TEXT,amount INTEGER,kind TEXT,created INTEGER);
        CREATE TABLE member_gifts(user_id TEXT,gift_id TEXT,reason TEXT,granted INTEGER,PRIMARY KEY(user_id,gift_id));
        CREATE TABLE jobs(id TEXT,user_id TEXT,status TEXT,created INTEGER);
        INSERT INTO users VALUES('synthetic-user',3);
        ''')
        for oid in (OID,SECOND):
            c.execute("INSERT INTO member_orders VALUES(?,'synthetic-user','gemini-image-assistant','ultra',4900,54,'reported',?,NULL,NULL,NULL)", (oid,int(time.time())))


def payload(**kw):
    return dict(dict(product='gemini',order_id=OID,amount_fen=4900,transaction_id=TX,verified=True),**kw)


class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=self.root/'test.db'
        fixture(self.db);self.settler=Settlement(self.db,ManualMembership.confirm_manual)

    def tearDown(self):self.tmp.cleanup()

    def sql(self,query):
        with contextlib.closing(sqlite3.connect(self.db)) as c, c:return c.execute(query).fetchall()

    def test_atomic_credit_and_audit(self):
        result=self.settler.confirm(payload(),'synthetic-admin')
        self.assertTrue(result['credited']);self.assertEqual(result['balance_points'],57000)
        self.assertAlmostEqual(result['expires_at']-time.time(),30*86400,delta=3)
        self.assertEqual(self.sql('SELECT points,actor FROM ops_settlements'),[(54000,'synthetic-admin')])
        self.assertEqual(self.sql('SELECT remaining FROM paid_wallets'),[(54,)])
        self.assertEqual(self.sql('SELECT amount FROM ledger'),[(54,)])

    def test_retry_same_order_is_idempotent(self):
        self.settler.confirm(payload(),'one')
        self.assertFalse(self.settler.confirm(payload(),'two')['credited'])
        self.assertEqual(self.sql('SELECT balance FROM users'),[(57,)])
        self.assertEqual(self.sql('SELECT count(*) FROM ops_settlements'),[(1,)])

    def test_duplicate_transaction_other_order_rejected(self):
        self.settler.confirm(payload(),'one')
        with self.assertRaises(SettlementError):self.settler.confirm(payload(order_id=SECOND),'one')
        self.assertEqual(self.sql('SELECT balance FROM users'),[(57,)])

    def test_concurrent_retries_credit_once(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            results=list(executor.map(lambda _:self.settler.confirm(payload(),'one'),range(4)))
        self.assertEqual(sum(r['credited'] for r in results),1)
        self.assertEqual(self.sql('SELECT balance FROM users'),[(57,)])

    def test_invalid_inputs_never_credit(self):
        for changes in [dict(amount_fen=1),dict(amount_fen=True),dict(verified=False),dict(product='temu'),
                        dict(transaction_id='bad'),dict(order_id='bad'),dict(order_id='c'*32)]:
            with self.subTest(changes=changes),self.assertRaises(SettlementError):self.settler.confirm(payload(**changes),'one')
        self.assertEqual(self.sql('SELECT balance FROM users'),[(3,)])

    def test_audit_failure_rolls_back_entire_grant(self):
        self.sql("CREATE TRIGGER fail_audit BEFORE INSERT ON ops_settlements BEGIN SELECT RAISE(ABORT,'synthetic fault'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.settler.confirm(payload(),'one')
        self.assertEqual(self.sql('SELECT balance FROM users'),[(3,)])
        self.assertEqual(self.sql('SELECT count(*) FROM ledger'),[(0,)])
        self.assertEqual(self.sql('SELECT count(*) FROM member_grants'),[(0,)])
        self.assertEqual(self.sql("SELECT status FROM member_orders WHERE id='"+OID+"'"),[('reported',)])

    def test_nonexistent_account_not_credited(self):
        self.sql('DELETE FROM users')
        with self.assertRaises(SettlementError):self.settler.confirm(payload(),'one')
        self.assertEqual(self.sql('SELECT count(*) FROM ledger'),[(0,)])

    def test_credited_points_consumed_by_real_gateway_with_fake_provider(self):
        import base64
        from server import Store
        class FakeProvider:
            ready=True
            def __call__(self, prompt, size):
                return base64.b64decode('REDACTED_FOR_HANDOFF/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        path=self.root/'gateway.db'
        with patch.dict('os.environ',{'IMAGE_MANUAL_QR_ENABLED':'yes','IMAGE_PILOT_MAX_IMAGES':'0'}):
            store=Store(path,FakeProvider())
            with store.connect() as c:c.execute("INSERT INTO users VALUES('synthetic-user',0)")
            order=store.membership.order('synthetic-user','ultra')
            settlement=Settlement(path,ManualMembership.confirm_manual)
            settlement.confirm(payload(order_id=order['id']),'test')
            result=store.generate('synthetic-user',{'prompt':'Synthetic test only','confirmed':True},'synthetic-once-only')
            self.assertEqual(result['status'],'succeeded')
            self.assertEqual(result['balance_points'],53000)
            with store.connect() as c:
                self.assertEqual(c.execute('SELECT remaining FROM paid_wallets').fetchone()[0],53)
                self.assertEqual(c.execute('SELECT remaining FROM member_grants').fetchone()[0],53)

    def test_http_auth_origin_and_confirmation(self):
        events=self.root/'events.db';initialize(events)
        report=Report({'gemini':str(self.db)},str(events))
        service=ThreadingHTTPServer(('127.0.0.1',0),handler(report,'x'*40,self.root,False,self.settler))
        thread=threading.Thread(target=service.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(service.server_port)+'/ops/api/'
        opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def post(route,data,origin='http://127.0.0.1:18890'):
            return opener.open(urllib.request.Request(base+route,json.dumps(data).encode(),headers={'Origin':origin,'Content-Type':'application/json'}))
        try:
            with self.assertRaises(urllib.error.HTTPError) as e:post('settle',payload())
            self.assertEqual(e.exception.code,401)
            with post('login',{'password':'x'*40}):pass
            with self.assertRaises(urllib.error.HTTPError) as e:post('settle',payload(),'https://evil.invalid')
            self.assertEqual(e.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError) as e:post('settle',payload(verified=False))
            self.assertEqual(e.exception.code,400)
            with post('settle',payload()) as r:self.assertTrue(json.load(r)['credited'])
            with post('settle',payload()) as r:self.assertFalse(json.load(r)['credited'])
            with opener.open(base+'orders?status=paid') as r:self.assertEqual(json.load(r)['total'],1)
            with post('logout',{}):pass
            with self.assertRaises(urllib.error.HTTPError) as e:post('settle',payload(order_id=SECOND,transaction_id='2'*32))
            self.assertEqual(e.exception.code,401)
        finally:service.shutdown();service.server_close();thread.join()


if __name__=='__main__':unittest.main()
