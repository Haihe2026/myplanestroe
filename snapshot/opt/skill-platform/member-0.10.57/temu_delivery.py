"""First-party asynchronous Temu delivery; no provider identifiers in public payloads."""
import base64
from contextlib import closing
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.parse
import uuid
import warnings

ORIGIN='https://myplanestore.com'
PREFIX='/platform-api/temu'
CONTRACT='temu-render-v1'
PRIVATE_ENGINE='temu-merchant-sunburst'
PRIVATE_MODEL='gpt-image-2.5-sunburst'
MAX_QUEUE=12
MAX_BODY=16*1024*1024
MESSAGES={400:'制作方案需要检查，未重新提交。',401:'请恢复原账户后继续。',402:'可用次数不足，请查看原账户企业入口。',
    403:'请确认原账户与本次制作授权。',409:'同一任务不能更换素材或需求。',413:'图片文件过大，请按说明调整。',
    422:'商品素材或制作方案需要调整。',429:'任务较多，请稍后查询原任务。',503:'服务暂未就绪，请保留原任务。'}


class Delivery:
    def __init__(self,store,server,shared,validator,path=None,autostart=True):
        self.store,self.server,self.shared,self.validator=store,server,shared,validator
        self.path=Path(path or os.environ.get('TEMU_DELIVERY_DB','/var/lib/skill-platform/temu-delivery-0.10.28.db'))
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.stop=threading.Event()
        self.wake=threading.Event()
        self.key=os.environ.get('IMAGE_TRIAL_HMAC_KEY','').encode()
        if len(self.key)<16:raise RuntimeError('First-party signing configuration unavailable')
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS delivery_jobs(
                id TEXT PRIMARY KEY,uid TEXT NOT NULL,idem TEXT NOT NULL,request_hash TEXT NOT NULL,
                state TEXT NOT NULL,payload TEXT,credential_id TEXT,source TEXT NOT NULL,channel TEXT NOT NULL,
                created INTEGER NOT NULL,updated INTEGER NOT NULL,started INTEGER,finished INTEGER,
                job_id TEXT,error_code INTEGER,image BLOB,preview BLOB,UNIQUE(uid,idem))''')
            if 'provider_route' not in {r[1] for r in c.execute('PRAGMA table_info(delivery_jobs)')}:
                c.execute("ALTER TABLE delivery_jobs ADD COLUMN provider_route TEXT NOT NULL DEFAULT 'legacy'")
                c.commit()
        self.path.chmod(0o600)
        self.reconcile()
        if autostart:
            self.threads=[threading.Thread(target=self.loop,name='temu-delivery-'+str(i),daemon=True) for i in range(2)]
            for thread in self.threads:thread.start()

    def connect(self):
        c=sqlite3.connect(self.path,timeout=10)
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA secure_delete=ON')
        return closing(c)

    def transaction(self,call):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            value=call(c)
            c.commit()
            return value

    def enqueue(self,uid,body,idem,credential_id=None,source='unknown',channel='unknown'):
        if not isinstance(idem,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{16,100}',idem):
            raise self.server.Problem(400,'任务标识无效')
        if not isinstance(body,dict) or body.get('contract')!=CONTRACT or set(body)-{'contract','countries','slot','facts','references','confirmed'}:
            raise self.server.Problem(400,'制作方案无效')
        source_body=dict(body);source_body.pop('contract')
        normalized,images=self.validator(source_body)
        # Hash the normalized content, including already verified reference digests.
        rh=hashlib.sha256(json.dumps([normalized,[hashlib.sha256(x).hexdigest() for x in images]],sort_keys=True).encode()).hexdigest()
        with self.connect() as c:
            prior=c.execute('SELECT * FROM delivery_jobs WHERE uid=? AND idem=?',(uid,idem)).fetchone()
        if prior:
            if prior['request_hash']!=rh:raise self.server.Problem(409,'原任务内容不同')
            return self.public(prior)
        quota=self.store.quota(uid,'temu')
        if quota.get('shared_uses',0)+quota.get('trial_remaining',0)<1:raise self.server.Problem(402,'次数不足')
        if not self.ready():raise self.server.Problem(503,'服务未就绪')
        now=int(time.time())
        def insert(c):
            prior=c.execute('SELECT * FROM delivery_jobs WHERE uid=? AND idem=?',(uid,idem)).fetchone()
            if prior:
                if prior['request_hash']!=rh:raise self.server.Problem(409,'原任务内容不同')
                return prior
            active=c.execute("SELECT count(*) FROM delivery_jobs WHERE state IN ('queued','running')").fetchone()[0]
            own=c.execute("SELECT count(*) FROM delivery_jobs WHERE uid=? AND state IN ('queued','running')",(uid,)).fetchone()[0]
            if active>=MAX_QUEUE or own>=2:raise self.server.Problem(429,'任务较多')
            rid=str(uuid.uuid4())
            from expert_service import select_route
            route=select_route(source,channel)
            c.execute('''INSERT INTO delivery_jobs(id,uid,idem,request_hash,state,payload,credential_id,source,channel,created,updated,provider_route)
                VALUES(?,?,?,?,'queued',?,?,?,?,?,?,?)''',(rid,uid,idem,rh,json.dumps(source_body),credential_id,source,channel,now,now,route))
            return c.execute('SELECT * FROM delivery_jobs WHERE id=?',(rid,)).fetchone()
        row=self.transaction(insert)
        self.wake.set()
        return self.public(row)

    def ready(self):
        from journey.gateway import REQUEST
        from expert_service import select_route,adapter
        request=REQUEST.get() or {}
        if select_route(request.get('source'),request.get('channel'))!='legacy':return adapter().ready
        import sunburst
        context=sunburst.CURRENT_ENGINE.set(PRIVATE_ENGINE)
        try:return bool(self.store.provider.edit_ready)
        finally:sunburst.CURRENT_ENGINE.reset(context)

    def find(self,uid,rid=None,idem=None):
        with self.connect() as c:
            row=c.execute('SELECT * FROM delivery_jobs WHERE uid=? AND '+('id=?' if rid else 'idem=?'),(uid,rid or idem)).fetchone()
        if not row:raise self.server.Problem(404,'原任务尚未查到，请勿重复生成。')
        return row

    def url(self,row,preview=False,expires=None):
        expires=expires or int(time.time())+3600
        kind='preview' if preview else 'image'
        message=f"temu-delivery:v1:{row['id']}:{row['uid']}:{row['job_id']}:{kind}:{expires}".encode()
        signature=hmac.new(self.key,message,hashlib.sha256).hexdigest()
        return f"{ORIGIN}{PREFIX}/media/{row['id']}/{kind}?expires={expires}&signature={signature}"

    def public(self,row):
        state=row['state']
        value=dict(render_id=row['id'],status='succeeded' if state=='succeeded' else 'failed' if state=='failed' else 'pending',
            phase=state,created_at=row['created'],updated_at=row['updated'],started_at=row['started'],finished_at=row['finished'],
            status_url=ORIGIN+PREFIX+'/render-jobs/'+row['id'],retry_after=3)
        if row['job_id']:value['id']=row['job_id']
        if state=='succeeded':
            value.update(image_url=self.url(row),preview_url=self.url(row,True),url_expires_in=3600,
                **{k:v for k,v in self.store.quota(row['uid'],'temu').items() if k in ('remaining_uses','shared_uses','legacy_uses','trial_total','trial_used','trial_pending','trial_remaining','balance_points')})
        if state=='failed':value.update(error_code=row['error_code'] or 503,notice=MESSAGES.get(row['error_code'],'任务未完成，请查看原账户状态。'))
        if state=='needs_review':value['notice']='原任务结果正在核对，不要重新生成或再次付款。'
        return value

    def media(self,rid,kind,expires,signature):
        if kind not in ('image','preview') or not re.fullmatch(r'[0-9a-f]{64}',signature or ''):
            raise self.server.Problem(403,'图片链接无效或过期。')
        try:expires=int(expires)
        except (TypeError,ValueError):raise self.server.Problem(403,'图片链接无效或过期。') from None
        if expires<int(time.time()) or expires>int(time.time())+3660:raise self.server.Problem(403,'图片链接无效或过期。')
        with self.connect() as c:row=c.execute("SELECT * FROM delivery_jobs WHERE id=? AND state='succeeded'",(rid,)).fetchone()
        if not row:raise self.server.Problem(404,'图片尚未可用。')
        expected=urllib.parse.parse_qs(urllib.parse.urlsplit(self.url(row,kind=='preview',expires)).query)['signature'][0]
        if not hmac.compare_digest(expected,signature):raise self.server.Problem(403,'图片链接无效或过期。')
        return (row['preview'],'image/jpeg') if kind=='preview' else (row['image'],'image/png')

    def clean_image(self,raw):
        from PIL import Image
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format!='PNG' or source.width*source.height>20_000_000:raise ValueError('Invalid result')
                source.load()
                mode='RGBA' if 'A' in source.getbands() else 'RGB'
                converted=source.convert(mode)
                clean=Image.frombytes(mode,converted.size,converted.tobytes())
        full=io.BytesIO();clean.save(full,format='PNG')
        if full.tell()>16*1024*1024:raise ValueError('Oversize result')
        clean.thumbnail((512,512),Image.Resampling.LANCZOS)
        white=Image.new('RGB',clean.size,'white')
        white.paste(clean,mask=clean.getchannel('A') if mode=='RGBA' else None)
        preview=io.BytesIO();white.save(preview,format='JPEG',quality=85,optimize=True)
        return full.getvalue(),preview.getvalue()

    def finish(self,row,jid):
        result=self.store.get_job(row['uid'],jid)
        if result['status']=='succeeded':
            full,preview=self.clean_image(result['image'])
            self.transaction(lambda c:c.execute("UPDATE delivery_jobs SET state='succeeded',payload=NULL,job_id=?,image=?,preview=?,finished=?,updated=? WHERE id=?",(jid,full,preview,int(time.time()),int(time.time()),row['id'])))
        elif result['status']=='failed':
            self.transaction(lambda c:c.execute("UPDATE delivery_jobs SET state='failed',payload=NULL,job_id=?,error_code=503,finished=?,updated=? WHERE id=?",(jid,int(time.time()),int(time.time()),row['id'])))
        else:
            self.transaction(lambda c:c.execute("UPDATE delivery_jobs SET state='needs_review',payload=NULL,job_id=?,updated=? WHERE id=?",(jid,int(time.time()),row['id'])))

    def reconcile(self,include_running=True):
        if getattr(self.store,'_journey_installed',False):
            from expert_service import adapter
            adapter().recover(self.store)
        # A restarted executing call is ambiguous. Never submit it a second time.
        with self.connect() as c:rows=c.execute("SELECT * FROM delivery_jobs WHERE state IN ('running','needs_review')" if include_running else "SELECT * FROM delivery_jobs WHERE state='needs_review'").fetchall()
        for row in rows:
            key=hashlib.sha256(('temu:'+row['idem']).encode()).hexdigest()
            with self.store.connect() as c:job=c.execute('SELECT id FROM jobs WHERE user_id=? AND idem=?',(row['uid'],key)).fetchone()
            try:
                if job:self.finish(row,job[0])
                else:self.transaction(lambda c:c.execute("UPDATE delivery_jobs SET state='needs_review',payload=NULL,updated=? WHERE id=?",(int(time.time()),row['id'])))
            except Exception:
                self.transaction(lambda c:c.execute("UPDATE delivery_jobs SET state='needs_review',payload=NULL,updated=? WHERE id=?",(int(time.time()),row['id'])))
        self.transaction(lambda c:c.execute("UPDATE delivery_jobs SET state='failed',payload=NULL,error_code=503,updated=? WHERE state='queued' AND created<?",(int(time.time()),int(time.time())-86400)))

    def process_one(self):
        if not self.server.EDIT_SLOTS.acquire(blocking=False):return False
        try:
            def claim(c):
                row=c.execute("SELECT * FROM delivery_jobs WHERE state='queued' ORDER BY created,id LIMIT 1").fetchone()
                if row:c.execute("UPDATE delivery_jobs SET state='running',payload=NULL,started=?,updated=? WHERE id=?",(int(time.time()),int(time.time()),row['id']))
                return row
            row=self.transaction(claim)
            if not row:return False
            try:
                if row['credential_id']:
                    current=self.store.skill_access.row(row['uid'])
                    if not current or current['revoked'] or current['id']!=row['credential_id']:raise self.server.Problem(401,'账户凭据已更新')
                body=json.loads(row['payload']);body['image_engine']=PRIVATE_ENGINE
                from journey.gateway import REQUEST
                context=REQUEST.set(dict(product='temu',uid=row['uid'],source=row['source'],channel=row['channel'],source_declared=True,
                                         provider_route=row['provider_route']))
                try:result=self.store.generate_product(row['uid'],'temu',body,row['idem'],self.validator)
                finally:REQUEST.reset(context)
                self.finish(row,result['id'])
            except self.server.Problem as error:
                key=hashlib.sha256(('temu:'+row['idem']).encode()).hexdigest()
                with self.store.connect() as c:known=c.execute('SELECT id FROM jobs WHERE user_id=? AND idem=?',(row['uid'],key)).fetchone()
                if known:self.finish(row,known[0])
                else:self.transaction(lambda c:c.execute("UPDATE delivery_jobs SET state='failed',payload=NULL,error_code=?,finished=?,updated=? WHERE id=?",(error.status if error.status in MESSAGES else 503,int(time.time()),int(time.time()),row['id'])))
            except Exception:
                self.transaction(lambda c:c.execute("UPDATE delivery_jobs SET state='needs_review',payload=NULL,updated=? WHERE id=?",(int(time.time()),row['id'])))
            return True
        finally:self.server.EDIT_SLOTS.release()

    def loop(self):
        last=time.monotonic()
        while not self.stop.is_set():
            try:
                if not getattr(self.store,'_journey_installed',False):
                    self.wake.wait(1);self.wake.clear();continue
                if time.monotonic()-last>30:self.reconcile(False);last=time.monotonic()
                if self.process_one():continue
            except Exception:
                print('temu_delivery_worker_attention')
            self.wake.wait(1);self.wake.clear()


def install(server,shared):
    old=shared.handler
    def handler(store,validator=None):
        parent=old(store,validator)
        delivery=Delivery(store,server,shared,validator)
        store.temu_delivery=delivery
        class Handler(parent):
            def run_request(self):
                parsed=urllib.parse.urlsplit(self.path)
                path=parsed.path
                if not (path==PREFIX+'/render-info' or path==PREFIX+'/render-jobs' or path.startswith(PREFIX+'/render-jobs/') or path.startswith(PREFIX+'/media/')):
                    return super().run_request()
                self.connection.settimeout(15)
                try:
                    if path==PREFIX+'/render-info' and self.command=='GET':
                        return self.send(200,dict(contract=CONTRACT,ready=delivery.ready(),signed_images=True,async_jobs=True))
                    if path.startswith(PREFIX+'/media/') and self.command=='GET':
                        parts=path.split('/')
                        if len(parts)!=6:raise server.Problem(404,'图片不存在')
                        query=urllib.parse.parse_qs(parsed.query)
                        raw,mime=delivery.media(parts[4],parts[5],query.get('expires',[''])[0],query.get('signature',[''])[0])
                        return self.send(200,raw,mime)
                    token=self.headers.get('Authorization','').removeprefix('Bearer ')
                    kid=None
                    if token.startswith('mpskill_'):uid,kid=store.skill_access.authenticate(token)
                    else:uid=store.user(token)
                    if path==PREFIX+'/render-jobs' and self.command=='POST':
                        length=int(self.headers.get('Content-Length','0'))
                        if not 0<length<=MAX_BODY or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'格式无效')
                        body=json.loads(self.rfile.read(length))
                        from journey.store import source,channel
                        result=delivery.enqueue(uid,body,self.headers.get('Idempotency-Key'),kid,
                            source(self.headers.get('X-Skill-Source')),channel(self.headers.get('X-Skill-Channel')))
                        return self.send(202 if result['status']=='pending' else 200,result)
                    if path.startswith(PREFIX+'/render-jobs/') and self.command=='GET':
                        suffix=path[len(PREFIX+'/render-jobs/'):]
                        if suffix.startswith('by-key/'):
                            row=delivery.find(uid,idem=suffix[7:])
                        else:row=delivery.find(uid,rid=suffix)
                        return self.send(200,delivery.public(row))
                    raise server.Problem(405,'请求方式无效')
                except server.Problem as error:
                    return self.send(error.status,dict(error=MESSAGES.get(error.status,'任务或图片暂未可用，请沿原任务查询。')))
                except (ValueError,TypeError,UnicodeError):return self.send(400,dict(error=MESSAGES[400]))
                except Exception:return self.send(503,dict(error=MESSAGES[503]))
            do_POST=run_request
            do_GET=run_request
        return Handler
    shared.handler=handler
