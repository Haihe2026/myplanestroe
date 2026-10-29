"""Private, resumable single-image task adapter, scoped by the service installer."""
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
import uuid
from PIL import Image
from safe_http import request,RemoteProblem

API='https://www.aisplice.store/v1'
MODEL='gpt-image-2.5-ext'
MEDIA='https://myplanestore.com/platform-api/temu/expert-input/'
ROUTE='expert-resource-20261027'


class AwaitingResult(Exception):pass


class Adapter:
    def __init__(self,root='/var/lib/skill-platform/temu-expert-resource',resolve=None,http=request):
        self.root=Path(root);self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.db=self.root/'tasks.sqlite3';self.keyfile=self.root/'input-signing.key'
        if not self.keyfile.exists():
            try:
                fd=os.open(self.keyfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'wb') as f:f.write(secrets.token_bytes(32))
            except FileExistsError:pass
        self.signer=self.keyfile.read_bytes()
        assert len(self.signer)==32
        self.resolve=resolve or self.registry
        self.http=http
        with self.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS tasks(
                k TEXT PRIMARY KEY,uid TEXT NOT NULL,job_id TEXT NOT NULL,body_hash TEXT NOT NULL,
                stage TEXT NOT NULL,remote_id TEXT,created INTEGER NOT NULL,updated INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS inputs(id TEXT PRIMARY KEY,k TEXT NOT NULL,image BLOB NOT NULL,expires INTEGER NOT NULL);
                ''')
        self.db.chmod(0o600)

    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.db,timeout=10);c.row_factory=sqlite3.Row
        try:
            c.execute('PRAGMA secure_delete=ON')
            with c:yield c
        finally:c.close()

    @staticmethod
    def registry():
        import sys
        sys.path.insert(0,'/opt/skill-platform/member-0.10.52')
        from asset_registry import Registry
        value=Registry().resolve_for_service('aisplice')
        if (value['base_url'].rstrip('/')!='https://www.aisplice.store' or value['auth_type']!='bearer'
                or not value.get('secret') or value.get('kind')!='image'):
            raise ValueError('Resource configuration unavailable')
        return value['secret']

    @property
    def ready(self):
        try:return bool(self.resolve())
        except Exception:return False

    def signed_input(self,i,expires):
        sig=hmac.new(self.signer,('input:v1:'+i+':'+str(expires)).encode(),hashlib.sha256).hexdigest()
        return MEDIA+i+'?expires='+str(expires)+'&signature='+sig

    def read_input(self,i,expires,sig):
        if not re.fullmatch('[a-f0-9]{32}',i):raise ValueError('Invalid input')
        expires=int(expires)
        if not int(time.time())<=expires<=int(time.time())+3660:raise ValueError('Expired input')
        expected=self.signed_input(i,expires).rsplit('=',1)[1]
        if not hmac.compare_digest(expected,sig):raise ValueError('Invalid signature')
        with self.connect() as c:r=c.execute('SELECT image,expires FROM inputs WHERE id=?',(i,)).fetchone()
        if not r or r['expires']!=expires:raise ValueError('Missing input')
        return r['image']

    def row(self,k):
        with self.connect() as c:return c.execute('SELECT * FROM tasks WHERE k=?',(k,)).fetchone()

    def stage(self,k,stage,remote_id=None):
        with self.connect() as c:
            c.execute('UPDATE tasks SET stage=?,remote_id=coalesce(?,remote_id),updated=? WHERE k=?',
                      (stage,remote_id,int(time.time()),k))
            if stage in ('succeeded','failed','settled_failed'):c.execute('DELETE FROM inputs WHERE k=?',(k,))

    def begin(self,k,uid,jid,prompt,size,images):
        if size not in ('1024x1024','1536x1024','1024x1536') or not 1<=len(images)<=3:
            raise ValueError('Unsupported image request')
        for raw in images:
            if not isinstance(raw,bytes) or not raw.startswith(b'\x89PNG\r\n\x1a\n') or len(raw)>8*1024*1024:
                raise ValueError('Invalid sanitized image')
        ratio={'1024x1024':'1:1','1536x1024':'3:2','1024x1536':'2:3'}[size]
        # The old execution marker is an internal compatibility field, not a visual instruction.
        prompt=re.sub(r'\[Execution model: [^\]\n]+\]\n','',prompt)
        bh=hashlib.sha256(json.dumps([prompt,size,[hashlib.sha256(x).hexdigest() for x in images]]).encode()).hexdigest()
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM tasks WHERE k=?',(k,)).fetchone()
            if old:
                if old['body_hash']!=bh or old['uid']!=uid or old['job_id']!=jid:raise ValueError('Original task conflict')
                return old
            now=int(time.time());expires=now+3600
            urls=[]
            for raw in images:
                i=uuid.uuid4().hex
                c.execute('INSERT INTO inputs VALUES(?,?,?,?)',(i,k,raw,expires));urls.append(self.signed_input(i,expires))
            c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,NULL,?,?)',(k,uid,jid,bh,'submitting',now,now))
        body=dict(model=MODEL,prompt=prompt,size=ratio,resolution='1K',quality='auto',n=1,images=urls)
        try:
            data=json.loads(self.http(API+'/images/tasks',method='POST',body=body,key=self.resolve(),idem=k,timeout=30))
            remote=data.get('task_id') or data.get('id')
            if not isinstance(remote,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,200}',remote):raise ValueError('Missing task identity')
            self.stage(k,'pending',remote)
        except RemoteProblem as error:
            self.stage(k,'failed' if error.status in (400,401,402,403,404,413,422) else 'needs_review')
            raise AwaitingResult() from None
        except Exception:
            # Submission may have succeeded; do not post again or fall back to another provider.
            self.stage(k,'needs_review')
            raise AwaitingResult() from None
        return self.row(k)

    @staticmethod
    def clean(raw):
        if len(raw)>24*1024*1024:raise ValueError('Oversize image')
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ('PNG','JPEG','WEBP') or im.width*im.height>20_000_000 or min(im.size)<128:
                raise ValueError('Invalid image')
            im.load();im=im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
            clean=Image.frombytes(im.mode,im.size,im.tobytes())
        out=io.BytesIO();clean.save(out,format='PNG')
        if out.tell()>16*1024*1024:raise ValueError('Oversize PNG')
        return out.getvalue()

    def poll(self,k):
        row=self.row(k)
        if not row or not row['remote_id']:raise AwaitingResult()
        remote=row['remote_id'];key=self.resolve()
        data=json.loads(self.http(API+'/images/tasks/'+remote,key=key,timeout=15))
        status=str(data.get('status','')).lower()
        if status in ('failed','failure','cancelled','canceled'):
            self.stage(k,'failed');return None
        if status not in ('completed','succeeded','success'):raise AwaitingResult()
        content=json.loads(self.http(API+'/images/tasks/'+remote+'/content',key=key,timeout=15))
        rows=content.get('data')
        if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict):raise ValueError('Invalid result count')
        url=rows[0].get('url')
        if not isinstance(url,str):raise ValueError('Missing image URL')
        raw=self.clean(self.http(url,limit=24*1024*1024,timeout=30))
        return raw

    def edit(self,k,uid,jid,prompt,size,images,wait=90):
        self.begin(k,uid,jid,prompt,size,images)
        deadline=time.monotonic()+wait
        while True:
            try:
                raw=self.poll(k)
                if raw is not None:return raw
                raise AwaitingResult()
            except AwaitingResult:
                if self.row(k)['stage']=='failed' or time.monotonic()>=deadline:raise
                time.sleep(3)

    def recover(self,store):
        with self.connect() as c:
            rows=c.execute("SELECT * FROM tasks WHERE stage IN ('pending','failed') ORDER BY updated LIMIT 4").fetchall()
            c.execute('DELETE FROM inputs WHERE expires<?',(int(time.time()),))
        for row in rows:
            try:
                with store.connect() as c:job=c.execute('SELECT user_id,status FROM jobs WHERE id=?',(row['job_id'],)).fetchone()
                if not job or job['user_id']!=row['uid']:continue
                if job['status']!='pending':
                    self.stage(row['k'],'settled_failed' if job['status']=='failed' else job['status']);continue
                raw=None if row['stage']=='failed' else self.poll(row['k'])
                if raw is None:
                    store.refund_confirmed_failure(row['job_id'])
                    self.stage(row['k'],'settled_failed')
                else:
                    with store.connect() as c:
                        c.execute("UPDATE jobs SET status='succeeded',image=? WHERE id=? AND user_id=? AND status='pending'",(raw,row['job_id'],row['uid']))
                    self.stage(row['k'],'succeeded')
            except Exception:continue
