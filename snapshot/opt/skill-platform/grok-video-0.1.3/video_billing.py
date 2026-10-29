"""Shared paid wallet, separate video tasks; one successful 6–15s clip = one use."""
import hashlib,json,re,time,uuid,threading,os
from pathlib import Path
from grok_provider import validate,Fault
LOCKS=[threading.RLock() for _ in range(64)]

class Billing:
 def __init__(self,store,provider,root):
  self.store=store;self.provider=provider;self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  with store.connect() as c:
   c.execute('''CREATE TABLE IF NOT EXISTS grok_video_jobs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,idem TEXT NOT NULL,digest TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL,upstream_id TEXT,created INTEGER NOT NULL,held INTEGER NOT NULL DEFAULT 1,settled INTEGER NOT NULL DEFAULT 0,UNIQUE(user_id,idem))''')
 def get(self,uid,tid):
  with self.store.connect() as c:r=c.execute('SELECT * FROM grok_video_jobs WHERE user_id=? AND id=?',(uid,tid)).fetchone()
  if not r:raise Fault('TASK_NOT_FOUND')
  return dict(r)
 def quota(self,uid):
  with self.store.connect() as c:
   c.execute('BEGIN IMMEDIATE');self.store.membership.expire(c,uid)
   w=c.execute('SELECT remaining FROM paid_wallets WHERE user_id=?',(uid,)).fetchone()
   held=c.execute('SELECT count(*) FROM grok_video_jobs WHERE user_id=? AND held=1 AND settled=0',(uid,)).fetchone()[0]
   return dict(shared_uses=max(0,w['remaining']) if w else 0,video_pending_uses=held,video_cost_uses=1,video_trial_uses=0)
 def public(self,r):
  return dict(id=r['id'],status=r['status'],contract='grok-video-v1',download_ready=r['status']=='completed',cost_uses=1,held_uses=1 if r['held'] and not r['settled'] else 0,charged_uses=1 if r['status']=='completed' and r['settled'] else 0,refunded_uses=1 if r['status']=='failed' and r['settled'] and not r['held'] else 0)
 def submit(self,uid,idem,body,resolve=True):
  if not isinstance(idem,str) or not re.fullmatch('[A-Za-z0-9_-]{16,100}',idem):raise Fault('INVALID_IDENTITY')
  if not isinstance(body,dict) or body.get('confirmed') is not True:raise Fault('CONFIRM_REQUIRED')
  if body.get('images') and body.get('reference_consent') is not True:raise Fault('REFERENCE_CONSENT_REQUIRED')
  data={k:v for k,v in body.items() if k not in ('confirmed','reference_consent')};spec=validate(data,resolve)
  raw=json.dumps(spec,ensure_ascii=False,sort_keys=True,separators=(',',':'));digest=hashlib.sha256(raw.encode()).hexdigest()
  lock=LOCKS[int(hashlib.sha256((uid+idem).encode()).hexdigest()[:8],16)%len(LOCKS)]
  with lock:
   with self.store.connect() as c:
    c.execute('BEGIN IMMEDIATE')
    old=c.execute('SELECT * FROM grok_video_jobs WHERE user_id=? AND idem=?',(uid,idem)).fetchone()
    if old:
     if old['digest']!=digest:raise Fault('TASK_CONFLICT')
     return self.public(dict(old))
    if not self.provider.ready:raise Fault('PROVIDER_UNAVAILABLE')
    if hasattr(self.provider,'can_afford') and not self.provider.can_afford(spec):raise Fault('PROVIDER_BALANCE_INSUFFICIENT')
    self.store.membership.expire(c,uid)
    w=c.execute('SELECT remaining FROM paid_wallets WHERE user_id=?',(uid,)).fetchone();u=c.execute('SELECT balance FROM users WHERE id=?',(uid,)).fetchone()
    if not w or not u or min(w['remaining'],u['balance'])<1:raise Fault('INSUFFICIENT_SHARED_USES')
    tid=uuid.uuid4().hex;now=int(time.time())
    c.execute('INSERT INTO grok_video_jobs VALUES(?,?,?,?,?,?,NULL,?,1,0)',(tid,uid,idem,digest,raw,'submitting',now))
    c.execute('UPDATE users SET balance=balance-1 WHERE id=?',(uid,));c.execute('UPDATE paid_wallets SET remaining=remaining-1 WHERE user_id=?',(uid,))
    self.store.membership.reserve_grant(c,uid,tid)
    c.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,-1,'grok_video_reserve',?)",(uid,tid,now))
   try:
    result=self.provider.request('POST','/v1/videos',spec,'grok15-paid-'+tid);up=result.get('task_id')
    if not isinstance(up,str) or not re.fullmatch('[A-Za-z0-9_-]{1,180}',up):raise Fault('INVALID_RESPONSE')
    with self.store.connect() as c:c.execute("UPDATE grok_video_jobs SET upstream_id=?,status='queued' WHERE id=?",(up,tid))
   except Fault as e:
    if str(e)=='PROVIDER_BALANCE_INSUFFICIENT':self.settle_failed(uid,tid)
    else:
     with self.store.connect() as c:c.execute("UPDATE grok_video_jobs SET status='needs_review' WHERE id=?",(tid,))
   except Exception:
    with self.store.connect() as c:c.execute("UPDATE grok_video_jobs SET status='needs_review' WHERE id=?",(tid,))
   return self.public(self.get(uid,tid))
 def settle_failed(self,uid,tid):
  with self.store.connect() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM grok_video_jobs WHERE id=? AND user_id=?',(tid,uid)).fetchone()
   if not r or r['settled']:return
   self.store.membership.expire(c,uid)
   returned=self.store.membership.refund_grant(c,tid)
   if returned:
    c.execute('UPDATE users SET balance=balance+1 WHERE id=?',(uid,));c.execute('UPDATE paid_wallets SET remaining=remaining+1 WHERE user_id=?',(uid,))
   c.execute("UPDATE grok_video_jobs SET status='failed',held=?,settled=1 WHERE id=?",(0 if returned else 1,tid))
   c.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,?,'grok_video_failure_release',?)",(uid,tid,1 if returned else 0,int(time.time())))
 def poll(self,uid,tid):
  r=self.get(uid,tid)
  if r['settled'] or not r['upstream_id']:return self.public(r)
  try:o=self.provider.request('GET','/v1/videos/'+r['upstream_id'])
  except Exception:return self.public(r)
  s=o.get('status')
  if s=='failed':self.settle_failed(uid,tid)
  elif s=='completed':
   # A stored, valid MP4 is required before finalizing the single-use charge.
   try:
    raw=self.provider.request('GET','/v1/videos/'+r['upstream_id']+'/content',binary=True)
    if not isinstance(raw,bytes) or len(raw)<12 or raw[4:8]!=b'ftyp':raise Fault('INVALID_VIDEO')
    p=self.root/(tid+'.mp4');tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_bytes(raw);tmp.chmod(0o600);tmp.replace(p)
    with self.store.connect() as c:
     c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT settled FROM grok_video_jobs WHERE id=?',(tid,)).fetchone()
     if not old['settled']:
      c.execute("UPDATE grok_video_jobs SET status='completed',settled=1 WHERE id=?",(tid,));c.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,0,'grok_video_success',?)",(uid,tid,int(time.time())))
   except Exception:
    with self.store.connect() as c:c.execute("UPDATE grok_video_jobs SET status='needs_review' WHERE id=? AND settled=0",(tid,))
  else:
   s=s if s in ('queued','in_progress','unknown') else 'unknown'
   with self.store.connect() as c:c.execute('UPDATE grok_video_jobs SET status=? WHERE id=? AND settled=0',(s,tid))
  return self.public(self.get(uid,tid))
 def download(self,uid,tid):
  r=self.get(uid,tid)
  if r['status']!='completed' or not r['settled']:raise Fault('VIDEO_NOT_READY')
  p=self.root/(tid+'.mp4')
  if not p.is_file():raise Fault('VIDEO_UNAVAILABLE')
  return p.read_bytes()
