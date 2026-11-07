from contextlib import closing
from contextvars import ContextVar
from datetime import datetime
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
import uuid

from funnel_gateway import PREFIX, install
from funnel_ops import extend
from machine_funnel import Conflict, DAY, Funnel, Invalid, Limited, TZ, migrate

SKILL = 'mps-id-photo-background'
IP = '192.0.2.80'
DAY_START = int(datetime(2026, 11, 7, tzinfo=TZ).timestamp())
KEY = bytes(range(32))


def event(**changes):
    return dict({'event_id':str(uuid.uuid4()),'installation_id':str(uuid.uuid4()),
                 'machine_id':str(uuid.uuid4()),'skill_id':SKILL,'channel':'workbuddy_skill'},
                **changes)


class Store:
    def user(self, token):
        return {'a'*43:'fixture-a','b'*43:'fixture-b'}.get(token)


class Parent(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def authenticated(self):
        return self.headers.get('X-Test-Ops') == 'allowed'

    def send(self, status, result, mime='application/json'):
        body = json.dumps(result).encode() if isinstance(result, dict) else result
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def run_request(self):
        size = int(self.headers.get('Content-Length',0))
        raw = self.rfile.read(size)
        self.send(200,{'parent':True,'body':json.loads(raw) if raw else None})

    do_GET = do_POST = run_request


class FunnelTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.db = self.root/'private'/'funnel.db'
        self.business = self.root/'business.db'
        self.clock = DAY_START + 60
        migrate(self.db)
        self.funnel = Funnel(self.db,KEY,clock=lambda:self.clock,daily_limit=8)

    def call(self, handler, method, path, body=None, headers=None):
        with ThreadingHTTPServer(('127.0.0.1',0),handler) as server:
            thread = threading.Thread(target=server.serve_forever,args=(.01,),daemon=True)
            thread.start()
            connection = http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            try:
                body = json.dumps(body).encode() if isinstance(body,dict) else body
                connection.request(method,path,body,{'Content-Type':'application/json',**(headers or {})})
                response=connection.getresponse()
                return response.status,dict(response.getheaders()),response.read()
            finally:
                connection.close()
                server.shutdown()
                thread.join()

    def gateway(self, rate=lambda *_:True):
        return install(Parent,Store(),self.funnel,rate)

    def make_business(self):
        with closing(sqlite3.connect(self.business)) as db, db:
            db.executescript('''
                CREATE TABLE ledger(id INTEGER PRIMARY KEY,user_id TEXT,job_id TEXT,created INTEGER,kind TEXT,amount INTEGER);
                CREATE TABLE member_orders(id TEXT,user_id TEXT,paid_at INTEGER,provider TEXT,status TEXT);
            ''')
            db.executemany('INSERT INTO ledger VALUES(?,?,?,?,?,?)',[
                (1,'fixture-a',None,self.clock-30,'account_created',0),
                (2,'fixture-a','order-1',self.clock+10,'manual_verified_topup',10),
                (3,'fixture-a','external',self.clock+20,'paid_topup',5),
                (4,'fixture-a',None,self.clock+30,'trial_grant',15),
            ])
            db.execute('INSERT INTO member_orders VALUES(?,?,?,?,?)',
                       ('order-1','fixture-a',self.clock+10,'manual_qr','paid'))

    def test_migration_idempotent_and_private(self):
        before=self.db.read_bytes()
        migrate(self.db)
        self.assertEqual(self.db.read_bytes(),before)
        if os.name!='nt':
            self.assertEqual(self.db.stat().st_mode & 0o777,0o600)
            self.assertEqual(self.db.parent.stat().st_mode & 0o777,0o700)

    def test_migration_refuses_unrelated_business_db(self):
        self.make_business()
        self.business.chmod(0o600)
        before=self.business.read_bytes()
        with self.assertRaises(Invalid):
            migrate(self.business)
        self.assertEqual(self.business.read_bytes(),before)

    def test_event_deduplication_and_identity_conflict(self):
        item=event()
        original=self.funnel.record(item,IP)
        replay=self.funnel.record(dict(item,event_id=str(uuid.uuid4())),IP)
        self.assertEqual(replay['event_id'],original['event_id'])
        self.assertEqual(replay['receipt'],original['receipt'])
        self.assertTrue(replay['duplicate'])
        with self.assertRaises(Conflict):
            self.funnel.record(dict(item,machine_id=str(uuid.uuid4())),IP)

    def test_metadata_validation(self):
        for bad in (event(skill_id='unlisted'),event(machine_id='raw-machine'),
                    event(channel=[]),event(email='private'),event(client_occurred_at='2026-11-07T09:00:00')):
            with self.subTest(body=bad), self.assertRaises(Invalid):
                self.funnel.record(bad,IP)

    def test_daily_limit_resets_at_beijing_midnight(self):
        self.funnel.daily_limit=1
        self.funnel.record(event(),IP)
        with self.assertRaises(Limited):
            self.funnel.record(event(),IP)
        self.clock=DAY_START+DAY
        self.assertFalse(self.funnel.record(event(),IP)['duplicate'])

    def test_raw_machine_installation_and_ip_absent(self):
        item=event()
        self.funnel.record(item,IP)
        raw=self.db.read_bytes()
        for value in (item['machine_id'],item['installation_id'],IP):
            self.assertNotIn(value.encode(),raw)

    def test_link_conflict_and_idempotency(self):
        result=self.funnel.record(event(),IP)
        args=result['event_id'],result['receipt']
        with self.assertRaises(Invalid):
            self.funnel.link(args[0],'a'*43,'fixture-a')
        self.assertEqual(self.funnel.link(*args,'fixture-a'),self.funnel.link(*args,'fixture-a'))
        with self.assertRaises(Conflict):
            self.funnel.link(*args,'fixture-b')

    def test_funnel_projection_and_no_financial_writes(self):
        self.make_business()
        before=self.business.read_bytes()
        item=event()
        receipt=self.funnel.record(item,IP)
        self.funnel.record(event(machine_id=item['machine_id']),IP)
        self.funnel.record(event(is_test=True),IP)
        self.funnel.link(receipt['event_id'],receipt['receipt'],'fixture-a')
        for visit in ('a'*32,'b'*32):
            self.funnel.page(visit,'registration',SKILL,'workbuddy_skill',IP)
        self.funnel.page('c'*32,'recharge',SKILL,'workbuddy_skill',IP,'fixture-a')
        report=self.funnel.report('2026-11-07','2026-11-07',self.business,SKILL)
        self.assertEqual(report['steps'],{'L0':1,'L1':1,'L2':1,'L3':1,'L4':1})
        self.assertEqual(report['metrics']['recharges'],{'manual_qr':1,'paid_topup':1})
        self.assertEqual(report['metrics']['anonymous_page_views'],2)
        self.assertEqual(self.business.read_bytes(),before)

    def test_missing_projection_is_unknown_and_does_not_create_file(self):
        result=self.funnel.report('2026-11-07','2026-11-07',self.business)
        self.assertIsNone(result['steps']['L4'])
        self.assertTrue(result['data_gaps'])
        self.assertFalse(self.business.exists())

    def test_retention_does_not_recreate_old_installation(self):
        item=event()
        self.funnel.record(item,IP)
        self.clock+=181*DAY
        self.funnel.purge()
        result=self.funnel.record(item,IP)
        self.assertTrue(result['duplicate'])
        self.assertTrue(result['detail_expired'])
        self.assertIsNone(result['receipt'])

    def test_http_legacy_and_native_contracts(self):
        handler=self.gateway()
        old=event()
        old.pop('machine_id')
        status,_,raw=self.call(handler,'POST',PREFIX+'/first-dialogue',old)
        self.assertEqual((status,json.loads(raw)),(200,{'parent':True,'body':old}))
        status,headers,raw=self.call(handler,'POST',PREFIX+'/first-dialogue',event())
        self.assertEqual((status,raw),(204,b''))
        self.assertEqual(len(headers['X-First-Dialogue-Receipt']),43)
        self.assertEqual(self.call(handler,'GET',PREFIX+'/capabilities')[0],200)

    def test_legacy_link_is_delegated_when_sidecar_unavailable(self):
        self.funnel.path=self.root/'unavailable.db'
        body={'event_id':str(uuid.uuid4()),'product':'temu','receipt':'legacy'}
        status,_,raw=self.call(self.gateway(),'POST',PREFIX+'/first-dialogue/link',body)
        self.assertEqual((status,json.loads(raw)),(200,{'parent':True,'body':body}))

    def test_http_native_link_uses_original_account_resolver(self):
        result=self.funnel.record(event(),IP)
        body={k:result[k] for k in ('event_id','receipt')}
        body['product']='gemini'
        handler=self.gateway()
        path=PREFIX+'/first-dialogue/link'
        self.assertEqual(self.call(handler,'POST',path,body)[0],401)
        self.assertEqual(self.call(handler,'POST',path,body,{'Authorization':'Bearer '+'a'*43})[0],200)
        self.assertEqual(self.call(handler,'POST',path,body,{'Authorization':'Bearer '+'b'*43})[0],409)

    def test_http_rejects_origin_and_source_mismatch(self):
        handler=self.gateway()
        path=PREFIX+'/first-dialogue'
        self.assertEqual(self.call(handler,'POST',path,event(),{'Origin':'https://invalid.example'})[0],403)
        self.assertEqual(self.call(handler,'POST',path,event(),{'X-Skill-Source':'other-skill'})[0],400)
        self.assertEqual(self.call(self.gateway(lambda *_:False),'POST',path,event())[0],429)

    def test_journey_observes_only_authorized_page_success(self):
        request_context=ContextVar('fixture_request')

        class JourneyParent(Parent):
            def run_request(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if body.get('allowed') is not True:
                    return self.send(401,{'error':'fixture_denied'})
                token=request_context.set({'product':'gemini','uid':'fixture-a'})
                try:
                    return self.send(200,{'ok':True})
                finally:
                    request_context.reset(token)

        module=SimpleNamespace(REQUEST=request_context,dimensions=lambda _journey,_ctx:(SKILL,'workbuddy_skill'))
        handler=install(JourneyParent,Store(),self.funnel,lambda *_:True,module,object())
        path='/platform-api/gemini/membership-api/journey-page'
        payload={'page':'recharge','view_id':'d'*32}
        self.assertEqual(self.call(handler,'POST',path,payload)[0],401)
        with self.funnel.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM mf_pages').fetchone()[0],0)
        payload['allowed']=True
        self.assertEqual(self.call(handler,'POST',path,payload)[0],200)
        self.assertEqual(self.call(handler,'POST',path,payload)[0],200)
        with self.funnel.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM mf_pages').fetchone()[0],1)

    def test_ops_existing_auth_and_unknown_detail(self):
        handler=extend(lambda:Parent,self.funnel,self.business)()
        self.assertEqual(self.call(handler,'GET','/ops/machine-funnel')[0],401)
        headers={'X-Test-Ops':'allowed'}
        status,_,raw=self.call(handler,'GET','/ops/machine-funnel',headers=headers)
        self.assertEqual(status,200)
        self.assertIn(b'/ops/api/machine-funnel',raw)
        route='/ops/api/machine-funnel?start=2026-11-07&end=2026-11-07&step=L4'
        status,_,raw=self.call(handler,'GET',route,headers=headers)
        self.assertEqual(status,200)
        self.assertFalse(json.loads(raw)['available'])
        self.assertIsNone(json.loads(raw)['total'])

    def test_cli_read_only_projection(self):
        self.make_business()
        key=self.root/'funnel.key'
        key.write_bytes(KEY)
        key.chmod(0o600)
        before=self.business.read_bytes()
        out=subprocess.check_output([sys.executable,str(Path(__file__).with_name('report.py')),
                                     '--db',str(self.db),'--key-file',str(key),'--shared-db',str(self.business),
                                     '--start','2026-11-07','--end','2026-11-07'],encoding='utf-8')
        self.assertEqual(json.loads(out)['steps']['L0'],0)
        self.assertEqual(self.business.read_bytes(),before)
