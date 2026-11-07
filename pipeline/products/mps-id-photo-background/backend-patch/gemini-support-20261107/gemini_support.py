"""Account-scoped Gemini history and support. Existing financial state is read-only."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid
from urllib.parse import parse_qs, urlsplit

PREFIX = '/platform-api/gemini'
CATEGORIES = ('billing', 'image_quality', 'workflow', 'suggestion', 'other')
ORIGINS = ('https://myplanestore.com', 'https://aistore.zhaopintong.com')
TICKET_RE = re.compile(r'mpsg-[a-f0-9]{32}\Z')
KEY_RE = re.compile(r'[A-Za-z0-9_.:-]{16,100}\Z')


class Error(ValueError):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


@contextmanager
def readonly(database):
    path = Path(database).resolve()
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=3)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA query_only=ON')
        with connection:
            yield connection
    finally:
        connection.close()


class Support:
    def __init__(self, financial_database, support_database, response_hours=None, clock=time.time):
        self.financial_database = str(financial_database)
        self.database = Path(support_database).resolve()
        if self.database == Path(financial_database).resolve():
            raise ValueError('Support and financial databases must be separate')
        if response_hours is not None and (type(response_hours) is not int or not 1 <= response_hours <= 720):
            raise ValueError('Operator response commitment must be 1..720 hours, or unset')
        self.response_hours, self.clock = response_hours, clock

    def initialize(self):
        self.database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.database.exists():
            try:
                fd = os.open(self.database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
        with self.connect() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS gemini_support_tickets(
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, request_key TEXT NOT NULL,
                    body_hash TEXT NOT NULL, category TEXT NOT NULL, text TEXT NOT NULL,
                    job_id TEXT, status TEXT NOT NULL CHECK(status IN ('open','in_progress','resolved')),
                    reply TEXT, created INTEGER NOT NULL, updated INTEGER NOT NULL,
                    response_due_at INTEGER, UNIQUE(user_id,request_key));
                CREATE INDEX IF NOT EXISTS gemini_support_user_created
                    ON gemini_support_tickets(user_id,created);
                CREATE TABLE IF NOT EXISTS gemini_support_audit(
                    id INTEGER PRIMARY KEY, ticket_id TEXT NOT NULL, action TEXT NOT NULL,
                    actor TEXT NOT NULL, created INTEGER NOT NULL);
            ''')
        self.database.chmod(0o600)

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.database, timeout=3)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def owns_job(self, uid, jid):
        with readonly(self.financial_database) as c:
            return bool(c.execute('''SELECT 1 FROM jobs j JOIN job_products p ON p.job_id=j.id
                WHERE j.id=? AND j.user_id=? AND p.product='gemini' ''', (jid, uid)).fetchone())

    def history(self, uid, page=1, page_size=20):
        if (type(page) is not int or not 1 <= page <= 100000 or
                type(page_size) is not int or not 1 <= page_size <= 50):
            raise Error(400, 'INVALID_PAGE')
        with readonly(self.financial_database) as c:
            total = c.execute('''SELECT count(*) FROM jobs j JOIN job_products p ON p.job_id=j.id
                WHERE j.user_id=? AND p.product='gemini' ''', (uid,)).fetchone()[0]
            rows = c.execute('''SELECT j.id,j.status,j.created,
                (SELECT count(*) FROM ledger l WHERE l.job_id=j.id AND l.user_id=j.user_id) ledger_rows,
                (SELECT coalesce(sum(l.amount),0) FROM ledger l WHERE l.job_id=j.id AND l.user_id=j.user_id) net,
                (SELECT coalesce(sum(CASE WHEN l.amount>0 THEN l.amount ELSE 0 END),0)
                 FROM ledger l WHERE l.job_id=j.id AND l.user_id=j.user_id) refunded
                FROM jobs j JOIN job_products p ON p.job_id=j.id
                WHERE j.user_id=? AND p.product='gemini'
                ORDER BY j.created DESC,j.id DESC LIMIT ? OFFSET ?''',
                (uid, page_size, (page-1)*page_size)).fetchall()
        items = []
        for row in rows:
            known = bool(row['ledger_rows'])
            net = max(0, -row['net']) if known else None
            # A reservation is not a completed charge. Unknown states stay unknown.
            charged = net if row['status'] == 'succeeded' else (0 if known and net == 0 else None)
            reserved = net if row['status'] in ('pending','needs_review') else None
            items.append(dict(job_id=row['id'], occurred_at=row['created'], content='通用生图任务',
                              status=row['status'], charged_uses=charged, reserved_uses=reserved,
                              refunded_uses=row['refunded'] if known else None,
                              unit='image_use', ledger_available=known))
        return dict(items=items, total=total, page=page, page_size=page_size, product='gemini',
                    scope='current_shared_database_gemini_jobs',
                    content_scope='通用通道记录，现有数据不能保证单技能归因；不包含旧独立数据库历史')

    @staticmethod
    def public(row):
        return {k: row[k] for k in ('id','category','text','job_id','status','reply','created','updated','response_due_at')}

    def create(self, uid, body, request_key):
        if not isinstance(request_key, str) or not KEY_RE.fullmatch(request_key):
            raise Error(400, 'IDEMPOTENCY_KEY_REQUIRED')
        if not isinstance(body, dict) or set(body) - {'category','text','job_id'}:
            raise Error(400, 'INVALID_TICKET_FIELDS')
        category, text, jid = body.get('category'), body.get('text'), body.get('job_id')
        if (category not in CATEGORIES or not isinstance(text,str) or not 1 <= len(text) <= 2000
                or not text.strip() or any(ord(ch)<32 and ch not in '\n\t\r' for ch in text)):
            raise Error(400, 'INVALID_TICKET_CONTENT')
        if jid is not None:
            try:
                if not isinstance(jid,str) or str(uuid.UUID(jid)) != jid:
                    raise ValueError()
            except (ValueError,AttributeError,TypeError):
                raise Error(400, 'INVALID_JOB_ID') from None
            if not self.owns_job(uid,jid):
                raise Error(404, 'JOB_NOT_FOUND')
        digest = hashlib.sha256(json.dumps([category,text,jid],ensure_ascii=False).encode()).hexdigest()
        now = int(self.clock())
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT * FROM gemini_support_tickets WHERE user_id=? AND request_key=?',
                            (uid,request_key)).fetchone()
            if old:
                if old['body_hash'] != digest:
                    raise Error(409,'TICKET_REQUEST_CONFLICT')
                return dict(ticket=self.public(old), replayed=True)
            count = c.execute('SELECT count(*) FROM gemini_support_tickets WHERE user_id=? AND created>?',
                              (uid,now-86400)).fetchone()[0]
            if count >= 50:
                raise Error(429,'TICKET_DAILY_LIMIT')
            tid = 'mpsg-' + uuid.uuid4().hex
            due = now+self.response_hours*3600 if self.response_hours is not None else None
            c.execute('INSERT INTO gemini_support_tickets VALUES(?,?,?,?,?,?,?,\'open\',NULL,?,?,?)',
                      (tid,uid,request_key,digest,category,text,jid,now,now,due))
            c.execute('INSERT INTO gemini_support_audit(ticket_id,action,actor,created) VALUES(?,?,?,?)',
                      (tid,'created','account',now))
            row = c.execute('SELECT * FROM gemini_support_tickets WHERE id=?',(tid,)).fetchone()
        return dict(ticket=self.public(row),replayed=False)

    def ticket(self, uid, tid):
        if not isinstance(tid,str) or not TICKET_RE.fullmatch(tid):
            raise Error(404,'TICKET_NOT_FOUND')
        with self.connect() as c:
            row = c.execute('SELECT * FROM gemini_support_tickets WHERE id=? AND user_id=?',(tid,uid)).fetchone()
        if not row:
            raise Error(404,'TICKET_NOT_FOUND')
        return dict(ticket=self.public(row))

    def operator_reply(self, tid, status, reply, actor):
        """Local operator entry only. Never exposed through client routes."""
        if (not TICKET_RE.fullmatch(tid or '') or status not in ('in_progress','resolved')
                or not isinstance(reply,str) or not 1 <= len(reply.strip()) <= 4000
                or not isinstance(actor,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',actor)):
            raise Error(400,'INVALID_OPERATOR_REPLY')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            result = c.execute('UPDATE gemini_support_tickets SET status=?,reply=?,updated=? WHERE id=?',
                               (status,reply,int(self.clock()),tid))
            if result.rowcount != 1:
                raise Error(404,'TICKET_NOT_FOUND')
            c.execute('INSERT INTO gemini_support_audit(ticket_id,action,actor,created) VALUES(?,?,?,?)',
                      (tid,'operator_reply',actor,int(self.clock())))


class Rate:
    def __init__(self):self.lock=threading.Lock();self.rows={}
    def allow(self,uid,write=False):
        minute=int(time.time())//60;key=(uid,write)
        with self.lock:
            self.rows={k:v for k,v in self.rows.items() if v[0]==minute}
            old,count=self.rows.get(key,(minute,0))
            if count >= (5 if write else 60) or key not in self.rows and len(self.rows)>=4096:
                raise Error(429,'RATE_LIMITED')
            self.rows[key]=(minute,count+1)


def install(parent, store, server, support=None):
    if support is None:
        hours=os.environ.get('GEMINI_SUPPORT_RESPONSE_HOURS')
        support=Support(store.database,os.environ.get('GEMINI_SUPPORT_DB',
                        '/var/lib/skill-platform/gemini-support/tickets.sqlite3'),
                        int(hours) if hours else None)
        support.initialize()
    rate=Rate()
    class Handler(parent):
        def run_request(self):
            parsed=urlsplit(self.path)
            history=parsed.path==PREFIX+'/consumption-history'
            create=parsed.path==PREFIX+'/support-tickets'
            lookup=parsed.path.startswith(PREFIX+'/support-tickets/')
            if not (history or create or lookup):
                return super().run_request()
            try:
                self.connection.settimeout(5)
                if self.headers.get('Origin') not in (None,*ORIGINS):
                    raise Error(403,'ORIGIN_NOT_ALLOWED')
                expected='POST' if create else 'GET'
                if self.command!=expected:
                    raise Error(405,'METHOD_NOT_ALLOWED')
                # Account credentials only: do not expand the existing Skill/API-key scope.
                authorization=self.headers.get('Authorization','')
                if not re.fullmatch(r'Bearer [A-Za-z0-9_-]{43}',authorization):
                    raise Error(401,'ACCOUNT_AUTH_REQUIRED')
                uid=store.user(authorization[7:])
                if not uid:raise Error(401,'ACCOUNT_AUTH_REQUIRED')
                rate.allow(uid,write=create)
                if self.headers.get('Transfer-Encoding'):
                    raise Error(400,'TRANSFER_ENCODING_NOT_SUPPORTED')
                query=parse_qs(parsed.query,keep_blank_values=True,strict_parsing=True,max_num_fields=4)
                if history:
                    if set(query)-{'page','page_size'} or any(len(v)!=1 for v in query.values()):
                        raise Error(400,'INVALID_PAGE')
                    result=support.history(uid,int(query.get('page',['1'])[0]),int(query.get('page_size',['20'])[0]))
                elif create:
                    if query:raise Error(400,'INVALID_QUERY')
                    lengths=self.headers.get_all('Content-Length',[])
                    if len(lengths)!=1 or not lengths[0].isdigit() or not 0<int(lengths[0])<=16384:
                        raise Error(413,'INVALID_BODY_LENGTH')
                    if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                        raise Error(400,'INVALID_JSON')
                    body=json.loads(self.rfile.read(int(lengths[0])))
                    result=support.create(uid,body,self.headers.get('Idempotency-Key'))
                else:
                    if query:raise Error(400,'INVALID_QUERY')
                    result=support.ticket(uid,parsed.path[len(PREFIX+'/support-tickets/'):])
                self.send(200,result)
            except Error as error:
                self.close_connection=True
                self.send(error.status,dict(error=error.code))
            except server.Problem:
                self.close_connection=True
                # Existing store authentication semantics; no internal error body leaks.
                self.send(401,dict(error='ACCOUNT_AUTH_REQUIRED'))
            except (ValueError,UnicodeError,TypeError):
                self.close_connection=True
                self.send(400,dict(error='INVALID_REQUEST'))
            except Exception:
                self.close_connection=True
                self.send(503,dict(error='SUPPORT_UNAVAILABLE'))
        do_GET=run_request
        do_POST=run_request
        do_PUT=run_request
        do_DELETE=run_request
    Handler.gemini_support=support
    return Handler
