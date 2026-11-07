import ast
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from concurrent.futures import ThreadPoolExecutor
import uuid
from gemini_support import Support,Error,install,Rate,readonly


class Problem(Exception):pass


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='gemini-support-test-')
        self.root=Path(self.temp.name);self.db=self.root/'finance.sqlite3'
        with sqlite3.connect(self.db) as c:
            c.executescript('''CREATE TABLE users(id TEXT PRIMARY KEY,balance INTEGER NOT NULL CHECK(balance>=0));
            CREATE TABLE sessions(hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL);
            CREATE TABLE jobs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,idem TEXT NOT NULL,request_hash TEXT NOT NULL,status TEXT NOT NULL,image BLOB,created INTEGER,UNIQUE(user_id,idem));
            CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id TEXT,job_id TEXT,amount INTEGER,kind TEXT,created INTEGER);
            CREATE TABLE job_products(job_id TEXT PRIMARY KEY,product TEXT NOT NULL);
            INSERT INTO users VALUES('account-a',8),('account-b',9);''')
            for token,uid in [('a'*43,'account-a'),('b'*43,'account-b')]:
                c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,int(time.time())+3600))
            self.jobs={}
            fixtures=[('success','account-a','gemini','succeeded',[-1],104),
                      ('pending','account-a','gemini','pending',[-1],103),
                      ('failed','account-a','gemini','failed',[-1,1],102),
                      ('unknown','account-a','gemini','succeeded',[],101),
                      ('temu','account-a','temu','succeeded',[-1],105),
                      ('other','account-b','gemini','succeeded',[-1],106)]
            for label,uid,product,status,amounts,stamp in fixtures:
                jid=str(uuid.uuid4());self.jobs[label]=jid
                c.execute('INSERT INTO jobs VALUES(?,?,?,?,?,NULL,?)',(jid,uid,label,'synthetic-hash',status,stamp))
                c.execute('INSERT INTO job_products VALUES(?,?)',(jid,product))
                for amount in amounts:c.execute('INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,?,?,?)',(uid,jid,amount,'reserve' if amount<0 else 'confirmed_failure_refund',stamp))
        c.close()
        self.before=self.db.read_bytes()
        self.support=Support(self.db,self.root/'support/tickets.sqlite3');self.support.initialize()
        def user(token):
            # Existing Store.user algorithm, copied without changing token ownership/expiry.
            with readonly(self.db) as c:
                row=c.execute('SELECT user_id FROM sessions WHERE hash=? AND expires>?',
                              (hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
            if not row:raise Problem()
            return row['user_id']
        class Parent(BaseHTTPRequestHandler):
            def run_request(self):self.send(418,{'unchanged_parent':self.path})
            def log_message(self,*a):pass
            def send(self,status,result):
                data=json.dumps(result).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        self.handler=install(Parent,SimpleNamespace(database=str(self.db),user=user),SimpleNamespace(Problem=Problem),self.support)
        self.http=ThreadingHTTPServer(('127.0.0.1',0),self.handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join(timeout=2)
        self.assertEqual(self.db.read_bytes(),self.before,'Financial DB was changed')
        self.temp.cleanup()

    def call(self,path,method='GET',body=None,token='a'*43,headers=None):
        h={} if headers is None else dict(headers)
        if token is not None:h['Authorization']='Bearer '+token
        if body is not None:
            raw=body if isinstance(body,bytes) else json.dumps(body).encode();h.setdefault('Content-Type','application/json')
        else:raw=None
        c=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=3)
        c.request(method,'/platform-api/gemini'+path,body=raw,headers=h)
        r=c.getresponse();status=r.status;result=json.loads(r.read());c.close();return status,result

    def make(self,key='synthetic-ticket-0001',**fields):
        return self.call('/support-tickets','POST',dict(category='billing',text='模拟：请核对本次扣次',**fields),headers={'Idempotency-Key':key})

    def test_history_tenant_product_and_pagination(self):
        code,data=self.call('/consumption-history?page=1&page_size=2')
        self.assertEqual(code,200);self.assertEqual(data['total'],4)
        self.assertEqual([i['job_id'] for i in data['items']],[self.jobs['success'],self.jobs['pending']])
        code,next_page=self.call('/consumption-history?page=2&page_size=2')
        self.assertEqual(len(next_page['items']),2)
        self.assertNotIn(self.jobs['temu'],json.dumps(data));self.assertNotIn(self.jobs['other'],json.dumps(data))

    def test_history_actual_charge_reservation_refund_unknown(self):
        _,data=self.call('/consumption-history');rows={x['job_id']:x for x in data['items']}
        self.assertEqual(rows[self.jobs['success']]['charged_uses'],1)
        self.assertIsNone(rows[self.jobs['pending']]['charged_uses'])
        self.assertEqual(rows[self.jobs['pending']]['reserved_uses'],1)
        self.assertEqual(rows[self.jobs['failed']]['charged_uses'],0)
        self.assertEqual(rows[self.jobs['failed']]['refunded_uses'],1)
        self.assertIsNone(rows[self.jobs['unknown']]['charged_uses'])

    def test_history_no_prompt_image_or_user_data(self):
        _,data=self.call('/consumption-history');text=json.dumps(data)
        for forbidden in ['request_hash','prompt','account-a','account-b','image_bytes','synthetic-hash']:
            self.assertNotIn(forbidden,text)

    def test_invalid_history_parameters(self):
        for query in ['page=0','page=-1','page=1.5','page_size=51','user_id=account-b','page=1&page=2','page_size=','broken']:
            self.assertEqual(self.call('/consumption-history?'+query)[0],400,query)

    def test_account_credentials_only_all_three_routes(self):
        for token in [None,'c'*43,'mpskill_'+'0'*32+'_'+'a'*43,'mpimg_'+'a'*50]:
            for path,method,body in [('/consumption-history','GET',None),('/support-tickets','POST',{}),('/support-tickets/mpsg-'+'0'*32,'GET',None)]:
                self.assertEqual(self.call(path,method,body,token)[0],401)

    def test_ticket_round_trip_and_no_invented_deadline(self):
        code,data=self.make(job_id=self.jobs['success']);self.assertEqual(code,200)
        ticket=data['ticket'];self.assertTrue(ticket['id'].startswith('mpsg-'));self.assertIsNone(ticket['response_due_at']);self.assertIsNone(ticket['reply'])
        self.assertEqual(self.call('/support-tickets/'+ticket['id'])[1]['ticket'],ticket)

    def test_ticket_cannot_read_other_account(self):
        _,created=self.make();tid=created['ticket']['id']
        self.assertEqual(self.call('/support-tickets/'+tid,token='b'*43)[0],404)
        self.assertEqual(self.call('/support-tickets/mpsg-'+'0'*32)[0],404)

    def test_ticket_job_ownership_and_product(self):
        for label in ['other','temu']:
            self.assertEqual(self.make(key='synthetic-ticket-'+label,job_id=self.jobs[label])[0],404)

    def test_ticket_idempotency_and_conflicting_body(self):
        _,first=self.make();_,replay=self.make()
        self.assertEqual(first['ticket']['id'],replay['ticket']['id']);self.assertTrue(replay['replayed'])
        code,_=self.call('/support-tickets','POST',{'category':'other','text':'模拟：不同内容'},headers={'Idempotency-Key':'synthetic-ticket-0001'})
        self.assertEqual(code,409)
        with self.support.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM gemini_support_tickets').fetchone()[0],1)

    def test_concurrent_same_key_single_ticket(self):
        body={'category':'other','text':'模拟：并发提交'}
        with ThreadPoolExecutor(8) as pool:
            rows=list(pool.map(lambda _:self.support.create('account-a',body,'synthetic-concurrent-key'),range(16)))
        self.assertEqual(len({r['ticket']['id'] for r in rows}),1)
        self.assertEqual(sum(not r['replayed'] for r in rows),1)

    def test_original_text_kept_and_not_executable(self):
        text='模拟：原话\n保留换行 <script>not executable</script> '
        row=self.support.create('account-a',{'category':'other','text':text},'synthetic-original-text')
        self.assertEqual(row['ticket']['text'],text)

    def test_operator_response_readable_and_audited(self):
        _,r=self.make();tid=r['ticket']['id']
        self.support.operator_reply(tid,'resolved','模拟：已核对，仅测试回复','test_operator')
        _,r=self.call('/support-tickets/'+tid)
        self.assertEqual(r['ticket']['status'],'resolved');self.assertIn('仅测试回复',r['ticket']['reply'])
        with self.support.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM gemini_support_audit WHERE ticket_id=?',(tid,)).fetchone()[0],2)

    def test_response_time_only_when_operator_configured(self):
        s=Support(self.db,self.support.database,response_hours=24,clock=lambda:100000)
        row=s.create('account-a',{'category':'other','text':'模拟：承诺配置'},'synthetic-response-hours')
        self.assertEqual(row['ticket']['response_due_at'],186400)
        for hours in [0,721,True,-1]:
            with self.assertRaises(ValueError):Support(self.db,self.root/'bad.sqlite3',hours)

    def test_strict_ticket_fields_and_content(self):
        cases=[{},[],{'category':'invalid','text':'x'},{'category':'other','text':''},{'category':'other','text':'x'*2001},
               {'category':'other','text':'x','user_id':'account-b'},{'category':'other','text':'x','status':'resolved'},
               {'category':'other','text':'x','reply':'pretend'},{'category':'other','text':'bad\x00'}]
        for i,body in enumerate(cases):
            with self.assertRaises(Error) as error:self.support.create('account-a',body,'synthetic-case-%04d'%i)
            self.assertEqual(error.exception.status,400)

    def test_malformed_json_content_type_and_query(self):
        for raw in [b'{',b'\xff',b'null',b'[]']:
            self.assertEqual(self.call('/support-tickets','POST',raw,headers={'Idempotency-Key':'synthetic-json-case'})[0],400)
        self.assertEqual(self.call('/support-tickets','POST',b'{}',headers={'Content-Type':'text/plain'})[0],400)
        self.assertEqual(self.call('/support-tickets?user=x','POST',{},token='b'*43)[0],400)

    def test_body_limit_and_required_idempotency(self):
        self.assertEqual(self.call('/support-tickets','POST',b'x'*17000)[0],413)
        self.assertEqual(self.call('/support-tickets','POST',{'category':'other','text':'模拟：test'})[0],400)

    def test_origin_and_method_guards(self):
        self.assertEqual(self.call('/consumption-history',headers={'Origin':'https://untrusted.example'})[0],403)
        self.assertEqual(self.call('/consumption-history','POST',{})[0],405)
        self.assertEqual(self.call('/support-tickets','GET')[0],405)
        self.assertEqual(self.call('/consumption-history',headers={'Origin':'https://aistore.zhaopintong.com'})[0],200)

    def test_existing_routes_delegate_unchanged(self):
        for path in ['/balance','/quick-entry','/skill-jobs','/health','/membership-api/orders']:
            code,r=self.call(path);self.assertEqual(code,418);self.assertEqual(r['unchanged_parent'],'/platform-api/gemini'+path)
        self.assertEqual(self.call('/../temu/feedback')[0],418)

    def test_unavailable_database_returns_sanitized_503(self):
        self.support.financial_database=str(self.root/'nonexistent.sqlite3')
        code,r=self.call('/consumption-history')
        self.assertEqual(code,503);self.assertEqual(r,{'error':'SUPPORT_UNAVAILABLE'})
        self.assertFalse((self.root/'nonexistent.sqlite3').exists())

    def test_support_cannot_use_financial_database(self):
        with self.assertRaises(ValueError):Support(self.db,self.db)

    def test_ticket_quota_preserves_idempotent_replay(self):
        body={'category':'other','text':'模拟：quota'}
        for i in range(50):self.support.create('account-a',body,'synthetic-quota-%04d'%i)
        self.assertTrue(self.support.create('account-a',body,'synthetic-quota-0000')['replayed'])
        with self.assertRaises(Error) as error:self.support.create('account-a',body,'synthetic-over-quota')
        self.assertEqual(error.exception.status,429)

    def test_rate_limits_separate_reads_writes_and_accounts(self):
        r=Rate()
        for _ in range(5):r.allow('a',True)
        with self.assertRaises(Error):r.allow('a',True)
        r.allow('a',False);r.allow('b',True)


if __name__=='__main__':unittest.main()
