import contextlib
import http.cookiejar
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from monitor import Report, handler, database
from telemetry import initialize, record, event_name, observed_handler


def fixture(path):
    with contextlib.closing(sqlite3.connect(path)) as c, c:
        c.executescript('''CREATE TABLE users(id TEXT,balance INTEGER);
          CREATE TABLE jobs(id TEXT,user_id TEXT,status TEXT,created INTEGER);
          CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id TEXT,kind TEXT,amount INTEGER,created INTEGER);
          CREATE TABLE member_orders(id TEXT,user_id TEXT,plan TEXT,amount_fen INTEGER,units INTEGER,status TEXT,created INTEGER,paid_at INTEGER,provider TEXT);
          CREATE TABLE member_grants(user_id TEXT,remaining INTEGER,expires INTEGER);
          INSERT INTO users VALUES('synthetic-user',37);''')
        now=int(time.time())
        c.execute("INSERT INTO ledger(user_id,kind,amount,created) VALUES('synthetic-user','trial_grant',5,?)",(now,))
        c.execute("INSERT INTO jobs VALUES('job-synthetic','synthetic-user','succeeded',?)",(now,))
        c.execute("INSERT INTO member_grants VALUES('synthetic-user',32,?)",(now-1,))
        c.execute("INSERT INTO member_orders VALUES('order-synthetic','synthetic-user','plus',2900,32,'paid',?,?,'manual_qr')",(now,now))


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.db=self.root/'source.db'
        fixture(self.db)
        self.events=self.root/'events.db'
        initialize(self.events)
        self.report=Report({'gemini':str(self.db),'temu':str(self.root/'missing.db')},str(self.events))

    def tearDown(self):
        self.tmp.cleanup()

    def test_business_metrics_do_not_infer_missing_source(self):
        data=self.report.summary(2)
        self.assertEqual(data['products'][0]['users'],1)
        self.assertEqual(data['products'][0]['paid']['amount_fen'],2900)
        self.assertFalse(data['products'][1]['connected'])
        self.assertFalse(data['native_payment_ready'])
        self.assertEqual(data['products'][0]['events'],[])

    def test_expired_credits_adjusted_without_writing(self):
        self.assertEqual(self.report.users('gemini','',1)['users'][0]['balance_points'],5000)
        self.assertEqual(self.report.journey('gemini','synthetic-user')['balance_points'],5000)
        with database(self.db) as c:
            self.assertEqual(c.execute('SELECT balance FROM users').fetchone()[0],37)
            with self.assertRaises(sqlite3.OperationalError):
                c.execute('UPDATE users SET balance=999')

    def test_search_is_parameterized(self):
        self.assertEqual(self.report.users('gemini',"' OR 1=1 --",1)['total'],0)
        self.assertEqual(self.report.users('gemini','%',1)['total'],0)
        with self.assertRaises(ValueError):self.report.users('../private','',1)

    def test_events_allowlist_no_raw_headers(self):
        record(self.events,'gemini',None,'activation_attempt',429,'malicious-secret','phone-user-agent',23)
        result=self.report.event_summary('gemini',0)
        self.assertEqual(result[0]['device'],'unknown')
        self.assertEqual(result[0]['channel'],'unknown')
        self.assertNotIn('secret',json.dumps(result))
        self.assertIsNone(event_name('/somewhere?token=REDACTED_FOR_HANDOFF','GET'))

    def test_telemetry_failure_does_not_change_business_response(self):
        class Parent:
            def send(self,status,result,*args,**kwargs):return status,result
            def run_request(self):return self.send(200,{'ok':True})
        wrapped=observed_handler(Parent,None,'gemini',str(self.root/'missing/events.db'))
        instance=wrapped()
        instance.path='/balance';instance.command='GET';instance.headers={}
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(instance.run_request(),(200,{'ok':True}))

    def test_native_order_gate_never_calls_provider(self):
        class Parent:
            def send(self,status,result,*args,**kwargs):return status,result
        class Store:
            def user(self,token):return 'synthetic-user'
        wrapped=observed_handler(Parent,Store(),'gemini',str(self.events))
        instance=wrapped();instance.path='/skill-pay/orders';instance.command='POST';instance.headers={}
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(instance.run_request()[0],503)

    def test_login_cookie_csrf_and_logout(self):
        service=ThreadingHTTPServer(('127.0.0.1',0),handler(self.report,'x'*40,self.root,False))
        thread=threading.Thread(target=service.serve_forever,daemon=True);thread.start()
        url='http://127.0.0.1:'+str(service.server_port)
        opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def post(path,body,origin='http://127.0.0.1:18890'):
            return opener.open(urllib.request.Request(url+path,json.dumps(body).encode(),headers={'Origin':origin,'Content-Type':'application/json'}))
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:opener.open(url+'/ops/api/summary')
            self.assertEqual(error.exception.code,401)
            with self.assertRaises(urllib.error.HTTPError) as error:post('/ops/api/login',{'password':'x'*40},'https://evil.invalid')
            self.assertEqual(error.exception.code,403)
            with post('/ops/api/login',{'password':'x'*40}) as response:
                self.assertIn('HttpOnly',response.headers['Set-Cookie'])
            with opener.open(url+'/ops/api/summary') as response:self.assertEqual(response.status,200)
            with opener.open(url+'/ops/api/journey?product=gemini&uid=synthetic-user') as response:
                self.assertNotIn('hash',response.read().decode())
            with post('/ops/api/logout',{}) as response:self.assertEqual(response.status,200)
            with self.assertRaises(urllib.error.HTTPError):opener.open(url+'/ops/api/summary')
        finally:
            service.shutdown();service.server_close();thread.join()


if __name__=='__main__':unittest.main()
