"""Opt-in synchronous Gemini image lifetime; no historical image or ledger migration."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import hashlib,json,os,re,secrets,threading,time
from urllib.parse import urlsplit
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
REQUEST=ContextVar('ephemeral_image_request',default=None)
MAGIC=b'MPS-EPHEMERAL-1:'
POLICY='gateway-delivery-delete/1'
TTL=3600
class Retention:
 def __init__(self,store,server,autostart=True):
  self.store,self.server=store,server
  self.original_connect=store.connect
  self.lock=threading.RLock()
  self.root=Path(os.environ.get('MPS_EPHEMERAL_IMAGE_KEYS','/run/myplanestore-image-keys'))
  if not self.root.is_absolute() or self.root.is_symlink():raise RuntimeError('Unsafe image key directory')
  self.root.mkdir(mode=0o700,parents=True,exist_ok=True);self.root.chmod(0o700)
  with self.original_connect() as c:
   c.execute('CREATE TABLE IF NOT EXISTS ephemeral_image_jobs(job_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,product TEXT NOT NULL,policy TEXT NOT NULL,created INTEGER NOT NULL,expires INTEGER NOT NULL,image_sha256 TEXT,state TEXT NOT NULL,deleted_at INTEGER,reason TEXT)')
  original_get=store.get_job
  @contextmanager
  def connect():
   with self.original_connect() as c:yield Connection(c,self)
  store.connect=connect
  def get(uid,jid):
   with self.lock:
    self.expire_one(jid)
    result=original_get(uid,jid)
    row=self.row(jid,uid)
    if not row:return result
    result.update(self.public(row))
    if row['state']=='deleted':result['image']=None;return result
    image=result.get('image')
    if image:
     key=self.keypath(jid)
     if not key.exists():
      self.erase(uid,jid,'key_unavailable');result['image']=None;result.update(self.public(self.row(jid,uid)));return result
     if not image.startswith(MAGIC):raise self.server.Problem(503,'图片保护状态需要核对，请保留原任务')
     nonce=image[len(MAGIC):len(MAGIC)+12]
     result['image']=AESGCM(key.read_bytes()).decrypt(nonce,image[len(MAGIC)+12:],jid.encode())
    return result
  store.get_job=get
  old_edit=store.provider.edit
  def edit(prompt,size,images):
   ctx=REQUEST.get()
   if ctx and ctx.get('portrait'):
    prompt=prompt.replace('Edit the supplied product photos. Preserve visible geometry, color, material, labels, quantity and accessories. Do not invent hidden surfaces or change the SKU. New text is added in post-production, not painted by the model.','Edit the supplied authorized portrait references for the confirmed portrait task. Preserve the depicted person identity and natural facial characteristics. Do not invent unrelated people or imply commercial product/SKU constraints.')
   return old_edit(prompt,size,images)
  store.provider.edit=edit
  previous=store.generate_product
  def generate(uid,product,body,idem,validator=None):
   opt=body.get('image_retention') if isinstance(body,dict) else None
   if opt is None:return previous(uid,product,body,idem,validator)
   if product!='gemini' or opt!={'policy':POLICY}:raise server.Problem(400,'图片删除策略无效；未提交新任务')
   if not isinstance(idem,str) or not 16<=len(idem)<=100:raise server.Problem(400,'任务标识无效')
   identity=hashlib.sha256((product+':'+idem).encode()).hexdigest()
   with self.original_connect() as c:
    old=c.execute('SELECT id FROM jobs WHERE user_id=? AND idem=?',(uid,identity)).fetchone()
   if old and not self.row(old['id'],uid):raise server.Problem(409,'旧任务不能改变留存策略，不重建任务')
   clean=dict(body);clean.pop('image_retention')
   portrait=clean.pop('reference_purpose',None)
   if portrait not in (None,'portrait') or (portrait and clean.get('slot') in ('main','sku')):raise server.Problem(400,'参考图用途与任务不匹配')
   if portrait:clean['prompt']='[Reference purpose: portrait]\n'+str(clean.get('prompt',''))
   token=REQUEST.set({'uid':uid,'product':product,'portrait':bool(portrait)})
   try:
    result=previous(uid,product,clean,idem,validator)
    row=self.row(result.get('id'),uid)
    if not row:raise server.Problem(409,'该任务不支持改变留存策略，不重复提交')
    return dict(result,**self.public(row))
   finally:REQUEST.reset(token)
  store.generate_product=generate
  self.sweep()
  if autostart:threading.Thread(target=self.loop,name='private-image-expiry',daemon=True).start()
 def keypath(self,jid):
  if not isinstance(jid,str) or not re.fullmatch(r'[a-f0-9-]{36}',jid):raise self.server.Problem(400,'任务编号无效')
  return self.root/(jid+'.key')
 def row(self,jid,uid=None):
  with self.original_connect() as c:
   return c.execute('SELECT * FROM ephemeral_image_jobs WHERE job_id=?'+(' AND user_id=?' if uid else ''),(jid,uid) if uid else (jid,)).fetchone()
 def public(self,row):
  return {'image_retention':{'policy':POLICY,'state':row['state'],'expires_at':row['expires'],'deleted_at':row['deleted_at'],'reason':row['reason'],'image_sha256':row['image_sha256'],'scope':'gateway_opt_in_result_only','supplier_deletion_verified':False}}
 def encrypt(self,c,image,jid):
  with self.lock:
   row=c.execute('SELECT * FROM ephemeral_image_jobs WHERE job_id=?',(jid,)).fetchone()
   if not row:return image
   if row['state']=='deleted' or row['expires']<=time.time():return None
   path=self.keypath(jid);key=secrets.token_bytes(32)
   flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW
   fd=os.open(path,flags,0o600)
   with os.fdopen(fd,'wb') as f:f.write(key);f.flush();os.fsync(f.fileno())
   self.syncdir()
   nonce=secrets.token_bytes(12)
   encoded=MAGIC+nonce+AESGCM(key).encrypt(nonce,image,jid.encode())
   c.execute('UPDATE ephemeral_image_jobs SET image_sha256=? WHERE job_id=?',(hashlib.sha256(image).hexdigest(),jid))
   return encoded
 def syncdir(self):
  fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
 def erase(self,uid,jid,reason,expected=None):
  with self.lock:
   with self.original_connect() as c:
    c.execute('BEGIN IMMEDIATE')
    row=c.execute('SELECT * FROM ephemeral_image_jobs WHERE job_id=? AND user_id=?',(jid,uid)).fetchone()
    if not row:raise self.server.Problem(404,'未找到本人启用该策略的任务')
    if expected is not None and (not row['image_sha256'] or not secrets.compare_digest(expected,row['image_sha256'])):raise self.server.Problem(409,'交付图片校验不匹配，未删除')
    self.keypath(jid).unlink(missing_ok=True);self.syncdir()
    c.execute("UPDATE ephemeral_image_jobs SET state='deleted',deleted_at=coalesce(deleted_at,?),reason=coalesce(reason,?) WHERE job_id=?",(int(time.time()),reason,jid))
    c.execute('UPDATE jobs SET image=NULL WHERE id=?',(jid,))
   return dict(ok=True,**self.public(self.row(jid,uid)),upstream_deletion_confirmed=False,original_job_preserved=True)
 def expire_one(self,jid):
  row=self.row(jid)
  if row and row['state']=='active' and row['expires']<=time.time():self.erase(row['user_id'],jid,'unclaimed_expiry')
 def sweep(self):
  with self.original_connect() as c:rows=c.execute("SELECT job_id FROM ephemeral_image_jobs WHERE state='active' AND expires<=?",(int(time.time()),)).fetchall()
  for row in rows:self.expire_one(row['job_id'])
  # Keys without a committed active row (crash/rollback) are removed after a grace period.
  for path in self.root.glob('*.key'):
   if path.stat().st_mtime<time.time()-TTL and not self.row(path.stem):path.unlink(missing_ok=True)
 def loop(self):
  while True:
   time.sleep(30)
   try:self.sweep()
   except Exception:pass # read/delete requests still enforce deadlines; never log images or credentials
class Connection:
 def __init__(self,c,retention):self.c,self.retention=c,retention
 def __getattr__(self,name):return getattr(self.c,name)
 def execute(self,sql,params=()):
  normalized=re.sub(r'\s+','',sql).lower()
  if normalized.startswith('insertintojobsvalues(') and REQUEST.get():
   result=self.c.execute(sql,params);ctx=REQUEST.get();jid,uid=params[:2]
   if uid!=ctx['uid']:raise RuntimeError('Task identity mismatch')
   self.c.execute('INSERT INTO ephemeral_image_jobs VALUES(?,?,?,?,?,?,NULL,?,NULL,NULL)',(jid,uid,ctx['product'],POLICY,int(time.time()),int(time.time())+TTL,'active'))
   return result
  if normalized.startswith("updatejobssetstatus='succeeded',image=?whereid=?"):
   image,jid=params;params=(self.retention.encrypt(self.c,image,jid),jid)
  return self.c.execute(sql,params)
def install(server,shared):
 previous=shared.handler
 def handler(store,validator=None):
  parent=previous(store,validator)
  retention=Retention(store,server)
  def image_owner(token,allow_api=False):
   if token.startswith('mpskill_'):return store.skill_access.authenticate(token)[0]
   if allow_api and token.startswith('mpimg_'):return store.api_access.authenticate(token)[0]
   return store.user(token)
  class Handler(parent):
   def run_request(self):
    path=urlsplit(self.path).path
    if path=='/platform-api/gemini/image-retention-policy' and self.command=='GET':
     return self.send(200,{'enabled':True,'contract':POLICY,'opt_in':{'image_retention':{'policy':POLICY}},'unclaimed_ttl_seconds':TTL,'cleanup_interval_seconds':30,'supplier_deletion_verified':False,'reference_consent_unchanged':True,'scope':'new_explicit_gemini_jobs_only','key_storage':'volatile_runtime_files_survive_service_restart_not_host_reboot'})
    image_match=re.fullmatch(r'/platform-api/gemini/jobs/([a-f0-9-]{36})/image',path)
    if image_match and self.command=='GET':
     try:
      uid=image_owner(self.headers.get('Authorization','').removeprefix('Bearer '),True)
      row=retention.row(image_match[1],uid)
      if row:
       retention.expire_one(image_match[1]);row=retention.row(image_match[1],uid)
       if row['state']=='deleted':return self.send(410,dict(error='图片已删除或过期，请勿重新生成原任务',**retention.public(row)))
     except server.Problem as e:return self.send(e.status,{'error':e.message})
    m=re.fullmatch(r'/platform-api/gemini/jobs/([a-f0-9-]{36})/(delivery-confirm|delete-image)',path)
    if not m:return super().run_request()
    try:
     if self.command!='POST':raise server.Problem(405,'请求方式无效')
     uid=image_owner(self.headers.get('Authorization','').removeprefix('Bearer '))
     size=int(self.headers.get('Content-Length','0'))
     if not 0<size<=2048 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式错误')
     body=json.loads(self.rfile.read(size))
     if not isinstance(body,dict) or body.get('confirmed') is not True:raise server.Problem(400,'请确认原任务操作')
     expected=body.get('image_sha256') if m[2]=='delivery-confirm' else None
     if m[2]=='delivery-confirm' and (not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{64}',expected)):raise server.Problem(400,'请先校验已保存图片')
     return self.send(200,retention.erase(uid,m[1],'client_delivery_confirmed' if m[2]=='delivery-confirm' else 'owner_requested',expected))
    except server.Problem as e:return self.send(e.status,{'error':e.message})
    except (ValueError,TypeError):return self.send(400,{'error':'参数无效'})
    except Exception:return self.send(503,{'error':'删除状态需要核对，请查询原任务，不重复生成'})
   def send(self,status,result,mime='application/json; charset=utf-8',cookie=None,download=None):
    if status==200 and isinstance(result,dict) and urlsplit(self.path).path.startswith('/platform-api/gemini/jobs/') and result.get('id'):
     retention.expire_one(result['id'])
     row=retention.row(result['id'])
     if row:result=dict(result,**retention.public(row))
    return super().send(status,result,mime,cookie,download)
   do_GET=run_request
   do_POST=run_request
  return Handler
 shared.handler=handler
