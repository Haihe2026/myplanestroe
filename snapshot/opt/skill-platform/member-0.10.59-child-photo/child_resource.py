"""Child-scoped implementation of the documented async image contract.

Provider keys remain inside the server resolver, including readiness checks.
Synthetic tests inject both the key resolver and HTTP transport. Reference blobs are
encrypted locally and expire; supplier deletion is deliberately NOT asserted.
"""
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from resource_adapter import Adapter as ExistingAdapter, AwaitingResult, API, MODEL
from safe_http import RemoteProblem

MEDIA = 'https://myplanestore.com/platform-api/gemini/child-resource-input/'
SIZES = {'1024x1024': '1:1', '1536x1024': '3:2', '1024x1536': '2:3'}


class Adapter(ExistingAdapter):
    def __init__(self, root=None, resolve=None, http=None):
        options = dict(root=root or os.environ.get('CHILD_RESOURCE_DIR', '/var/lib/skill-platform/child-photo-resource'))
        if resolve is not None: options['resolve'] = resolve
        if http is not None: options['http'] = http
        super().__init__(**options)
        self.locks = [threading.RLock() for _ in range(64)]

    def lock(self, k):
        return self.locks[int(hashlib.sha256(k.encode()).hexdigest()[:8], 16) % len(self.locks)]

    def signed_input(self, i, expires):
        signature = hmac.new(self.signer, ('child-input:v1:'+i+':'+str(expires)).encode(), hashlib.sha256).hexdigest()
        return MEDIA+i+'?expires='+str(expires)+'&signature='+signature

    def read_input(self, i, expires, sig):
        encrypted = super().read_input(i, expires, sig)
        return AESGCM(self.signer).decrypt(encrypted[:12], encrypted[12:], i.encode())

    def begin(self, k, uid, jid, prompt, size, images):
        if size not in SIZES or not 0 <= len(images) <= 3:
            raise ValueError('Unsupported image request')
        for raw in images:
            if not isinstance(raw, bytes) or not raw.startswith(b'\x89PNG\r\n\x1a\n') or len(raw) > 8*1024*1024:
                raise ValueError('Invalid sanitized image')
        prompt = re.sub(r'\[Execution model: [^\]\n]+\]\n', '', prompt)
        body_hash = hashlib.sha256(json.dumps([prompt,size,[hashlib.sha256(x).hexdigest() for x in images]]).encode()).hexdigest()
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old = c.execute('SELECT * FROM tasks WHERE k=?', (k,)).fetchone()
            if old:
                if old['body_hash'] != body_hash or old['uid'] != uid or old['job_id'] != jid:
                    raise ValueError('Original task conflict')
                return old
            now = int(time.time()); expires = now+3600; urls = []
            for raw in images:
                i = uuid.uuid4().hex; nonce = os.urandom(12)
                encrypted = nonce+AESGCM(self.signer).encrypt(nonce, raw, i.encode())
                c.execute('INSERT INTO inputs VALUES(?,?,?,?)', (i,k,encrypted,expires))
                urls.append(self.signed_input(i, expires))
            c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,NULL,?,?)', (k,uid,jid,body_hash,'submitting',now,now))
        body = dict(model=MODEL,prompt=prompt,size=SIZES[size],resolution='1K',quality='auto',n=1)
        if urls: body['images'] = urls
        try:
            data = json.loads(self.http(API+'/images/tasks',method='POST',body=body,key=self.resolve(),idem=k,timeout=30))
            remote = data.get('task_id') or data.get('id')
            if not isinstance(remote,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,200}',remote):
                raise ValueError('Missing task identity')
            self.stage(k,'pending',remote)
        except RemoteProblem as error:
            # Definite request rejection can be released through the existing ledger.
            self.stage(k,'failed' if error.status in (400,401,402,403,404,413,422) else 'needs_review')
            raise AwaitingResult() from None
        except Exception:
            # A POST timeout is ambiguous. NEVER retry POST or use another provider.
            self.stage(k,'needs_review')
            raise AwaitingResult() from None
        return self.row(k)

    def execute(self,k,uid,jid,prompt,size,images):
        with self.lock(k):
            self.begin(k,uid,jid,prompt,size,images)
            if self.row(k)['stage'] in ('failed','settled_failed','needs_review','submitting'):
                raise AwaitingResult()
            raw = self.poll(k)
            if raw is None: raise AwaitingResult()
            return raw

    def recover(self,store):
        with self.connect() as c:
            rows = c.execute("SELECT * FROM tasks WHERE stage IN ('pending','failed') AND updated<=? ORDER BY updated LIMIT 4", (int(time.time())-3,)).fetchall()
            c.execute('DELETE FROM inputs WHERE expires<?', (int(time.time()),))
        for row in rows:
            lock = self.lock(row['k'])
            if not lock.acquire(blocking=False): continue
            try:
                with store.connect() as c:
                    job = c.execute('SELECT user_id,status FROM jobs WHERE id=?', (row['job_id'],)).fetchone()
                if not job or job['user_id'] != row['uid']: continue
                if job['status'] != 'pending':
                    self.stage(row['k'],'settled_failed' if job['status']=='failed' else job['status']); continue
                # Rotate the bounded polling batch fairly; a slow first task must
                # not permanently starve later pending tasks.
                self.stage(row['k'],row['stage'])
                raw = None if row['stage']=='failed' else self.poll(row['k'])
                if raw is None:
                    store.refund_confirmed_failure(row['job_id'])
                    self.stage(row['k'],'settled_failed')
                else:
                    # Exact original statement shape is intentional: retention 0.10.35
                    # wraps it to encrypt the result with the per-job runtime key.
                    with store.connect() as c:
                        current = c.execute('SELECT user_id,status FROM jobs WHERE id=?', (row['job_id'],)).fetchone()
                        if current and current['user_id']==row['uid'] and current['status']=='pending':
                            c.execute("UPDATE jobs SET status='succeeded',image=? WHERE id=? AND status='pending'", (raw,row['job_id']))
                    self.stage(row['k'],'succeeded')
            except Exception:
                # Do not log payloads, supplier errors, keys or media URLs.
                pass
            finally: lock.release()
