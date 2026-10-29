"""Server-only video adapter, fixed upstream and model. Never ship in channel ZIPs."""
import json,re,sqlite3,time,hashlib,threading,ipaddress,socket
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlsplit
from decimal import Decimal
from contextlib import contextmanager

MODEL='grok-imagine-1.5-video'
ORIGIN='https://www.aisplice.store'
SIZES=('16:9','9:16','1:1','3:2','2:3')
RATES={'480p':Decimal('0.0112'),'720p':Decimal('0.021')}
class Fault(Exception):pass
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None

def public_image(url,resolve=True):
 if not isinstance(url,str) or len(url)>4096:raise Fault('INVALID_REFERENCE')
 u=urlsplit(url)
 if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443) or u.fragment:raise Fault('INVALID_REFERENCE')
 if u.hostname.lower()=='localhost' or u.hostname.lower().endswith(('.local','.internal')):raise Fault('INVALID_REFERENCE')
 if resolve:
  try:addresses={i[4][0] for i in socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)}
  except OSError:raise Fault('INVALID_REFERENCE') from None
  if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses):raise Fault('INVALID_REFERENCE')
 return url

def validate(body,resolve=True):
 if not isinstance(body,dict) or set(body)-{'prompt','duration','resolution','size','images'}:raise Fault('INVALID_FIELDS')
 p=body.get('prompt');d=body.get('duration',6);r=body.get('resolution','480p');s=body.get('size','16:9');im=body.get('images',[])
 if not isinstance(p,str) or not p.strip() or len(p)>16000:raise Fault('INVALID_PROMPT')
 if type(d) is not int or not 6<=d<=15:raise Fault('INVALID_DURATION')
 if r not in RATES or s not in SIZES:raise Fault('INVALID_FORMAT')
 if not isinstance(im,list) or len(im)>7:raise Fault('INVALID_REFERENCE_COUNT')
 im=[public_image(x,resolve) for x in im]
 out=dict(model=MODEL,prompt=p,duration=d,resolution=r,size=s)
 if im:out['images']=im
 return out

def cost(body):return str(RATES[body.get('resolution','480p')]*body.get('duration',6))

class Provider:
 def __init__(self,key_file,requester=None):
  self.key_file=Path(key_file);self.requester=requester
 @property
 def ready(self):return self.key_file.is_file() and bool(re.fullmatch(r'sk-[A-Za-z0-9_-]{12,}',self.key_file.read_text().strip()))
 def request(self,method,path,body=None,idem=None,binary=False):
  if self.requester:return self.requester(method,path,body,idem,binary)
  if not self.ready:raise Fault('PROVIDER_NOT_CONFIGURED')
  if not re.fullmatch(r'/v1/videos(?:/[A-Za-z0-9_-]{1,180}(?:/content)?)?',path):raise Fault('INVALID_PATH')
  h={'Authorization':'Bearer '+self.key_file.read_text().strip(),'Content-Type':'application/json'}
  if idem:h['Idempotency-Key']=idem
  try:
   req=Request(ORIGIN+path,method=method,headers=h,data=json.dumps(body,separators=(',',':'),ensure_ascii=False).encode() if body is not None else None)
   with build_opener(NoRedirect()).open(req,timeout=30) as r:
    b=r.read((128*1024*1024 if binary else 1024*1024)+1)
    if len(b)>(128*1024*1024 if binary else 1024*1024):raise Fault('RESPONSE_TOO_LARGE')
    if binary:
     if len(b)<12 or b[4:8]!=b'ftyp':raise Fault('INVALID_VIDEO')
     return b
    o=json.loads(b)
    if not isinstance(o,dict):raise Fault('INVALID_RESPONSE')
    return o
  except Fault:raise
  except Exception:raise Fault('UPSTREAM_UNCERTAIN') from None

class Tasks:
 def __init__(self,root,provider):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True,mode=0o700);self.provider=provider;self.lock=threading.RLock()
  self.db=self.root/'tasks.db'
  with self.connect() as c:c.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, owner TEXT NOT NULL, idem TEXT NOT NULL, digest TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL, upstream_id TEXT, created INTEGER NOT NULL, UNIQUE(owner,idem))')
  self.db.chmod(0o600)
 @contextmanager
 def connect(self):
  c=sqlite3.connect(self.db,timeout=10);c.row_factory=sqlite3.Row
  try:
   with c:yield c
  finally:c.close()
 def get(self,owner,tid):
  with self.connect() as c:r=c.execute('SELECT * FROM tasks WHERE owner=? AND id=?',(owner,tid)).fetchone()
  if not r:raise Fault('TASK_NOT_FOUND')
  return dict(r)
 def submit(self,owner,idem,body,resolve=True):
  if not isinstance(owner,str) or not owner or not isinstance(idem,str) or not re.fullmatch('[A-Za-z0-9_-]{16,100}',idem):raise Fault('INVALID_IDENTITY')
  spec=validate(body,resolve);raw=json.dumps(spec,sort_keys=True,ensure_ascii=False,separators=(',',':'));digest=hashlib.sha256(raw.encode()).hexdigest()
  tid=hashlib.sha256((owner+':'+idem).encode()).hexdigest()[:32]
  with self.lock:
   with self.connect() as c:
    c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM tasks WHERE owner=? AND idem=?',(owner,idem)).fetchone()
    if old:
     if old['digest']!=digest:raise Fault('TASK_CONFLICT')
     return self.project(dict(old))
    c.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)',(tid,owner,idem,digest,raw,'submitting',None,int(time.time())))
   # Commit before sending: interrupted/ambiguous submissions are never silently replayed.
   try:
    result=self.provider.request('POST','/v1/videos',spec,'grok15-'+tid)
    uid=result.get('task_id')
    if not isinstance(uid,str) or not re.fullmatch('[A-Za-z0-9_-]{1,180}',uid):raise Fault('INVALID_RESPONSE')
    status='queued'
   except Exception:uid=None;status='needs_review'
   with self.connect() as c:c.execute('UPDATE tasks SET upstream_id=?,status=? WHERE id=?',(uid,status,tid))
   return self.project(self.get(owner,tid))
 def project(self,r):
  return dict(id=r['id'],status=r['status'],contract='grok-video-v1',download_ready=(r['status']=='completed'),notice='任务状态待核查，请保留原任务。' if r['status'] in ('needs_review','submitting','unknown') else '')
 def poll(self,owner,tid):
  r=self.get(owner,tid)
  if r['status'] in ('failed','completed') or not r['upstream_id']:return self.project(r)
  try:
   o=self.provider.request('GET','/v1/videos/'+r['upstream_id']);s=o.get('status')
   if s not in ('queued','in_progress','completed','failed','unknown'):s='unknown'
   with self.connect() as c:c.execute('UPDATE tasks SET status=? WHERE id=?',(s,tid))
   r['status']=s
  except Exception:pass
  return self.project(r)
 def download(self,owner,tid):
  r=self.get(owner,tid)
  if r['status']!='completed':raise Fault('VIDEO_NOT_READY')
  path=self.root/(tid+'.mp4')
  if not path.is_file():
   b=self.provider.request('GET','/v1/videos/'+r['upstream_id']+'/content',binary=True)
   if not isinstance(b,bytes) or len(b)<12 or b[4:8]!=b'ftyp':raise Fault('INVALID_VIDEO')
   temp=path.with_suffix('.tmp');temp.write_bytes(b);temp.chmod(0o600);temp.replace(path)
  return path.read_bytes()
