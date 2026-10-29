"""Explicit per-task browser checkbox consent; not an additional gate for legacy requests."""
from contextlib import contextmanager
from contextvars import ContextVar
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
import base64,hashlib,hmac,json,os,re,secrets,time,threading
from consent_digest import task_digest
VERSION='photo-consent-2026-10-23-v1'
BASE='https://myplanestore.com'
TTL=900
ACTIVE=ContextVar('photo_consent_task',default=None)

def wrap(parent,store,server):
 original_connect=store.connect
 with original_connect() as c:
  c.execute('CREATE TABLE IF NOT EXISTS photo_task_consents(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,product TEXT NOT NULL,idem TEXT NOT NULL,task_digest TEXT NOT NULL,policy_version TEXT NOT NULL,ticket_hash TEXT UNIQUE NOT NULL,created INTEGER NOT NULL,expires INTEGER NOT NULL,state TEXT NOT NULL,approved_nonce TEXT,approved_at INTEGER,job_id TEXT,UNIQUE(user_id,product,idem))')
 master=os.environ.get('IMAGE_TRIAL_HMAC_KEY','').encode()
 if len(master)<32:raise RuntimeError('Consent signing key unavailable')
 def owner(token):
  return store.skill_access.authenticate(token)[0] if token.startswith('mpskill_') else store.user(token)
 def receipt(row):
  data='|'.join(str(row[k] or '') for k in ('id','user_id','product','idem','task_digest','policy_version','approved_nonce'))
  return hmac.new(master,('photo-consent-receipt-v1|'+data).encode(),hashlib.sha256).hexdigest()
 def link_ticket(cid,uid,product,digest,nonce):
  value='|'.join((cid,uid,product,digest,nonce))
  return base64.urlsafe_b64encode(hmac.new(master,('photo-link-v1|'+value).encode(),hashlib.sha256).digest()).decode().rstrip('=')
 def public(row,private=False):
  state=row['state']
  if state in ('pending','approved') and row['expires']<=time.time():state='expired'
  result={'id':row['id'],'state':state,'task_digest':row['task_digest'],'policy_version':row['policy_version'],'expires_at':row['expires'],'expires_in':max(0,row['expires']-int(time.time())),'job_id':row['job_id']}
  if private and state in ('approved','used'):result['receipt']=receipt(row)
  return result
 class Connection:
  def __init__(self,c):self.c=c
  def __getattr__(self,k):return getattr(self.c,k)
  def execute(self,sql,args=()):
   ctx=ACTIVE.get()
   if ctx and re.sub(r'\s+','',sql).lower().startswith('insertintojobsvalues('):
    row=self.c.execute('SELECT * FROM photo_task_consents WHERE id=?',(ctx['id'],)).fetchone()
    if not row or row['user_id']!=args[1] or row['state']!='approved' or row['expires']<=time.time():raise server.Problem(409,'本次照片授权已过期或取消，请重新确认')
    result=self.c.execute(sql,args)
    self.c.execute("UPDATE photo_task_consents SET state='used',job_id=? WHERE id=?",(args[0],row['id']))
    return result
   return self.c.execute(sql,args)
 @contextmanager
 def connect():
  with original_connect() as c:yield Connection(c)
 store.connect=connect
 generate=store.generate_product
 def guarded_generate(uid,product,body,idem,validator=None):
  authorization=body.get('photo_consent') if isinstance(body,dict) else None
  if authorization is None:return generate(uid,product,body,idem,validator)
  if not isinstance(authorization,dict) or set(authorization)!={'id','receipt'} or not isinstance(authorization['id'],str) or not re.fullmatch('[a-f0-9]{32}',authorization['id']) or not isinstance(authorization['receipt'],str) or not re.fullmatch('[a-f0-9]{64}',authorization['receipt']):raise server.Problem(400,'照片授权凭据无效')
  clean=dict(body);clean.pop('photo_consent');digest=task_digest(product,idem,clean)
  with original_connect() as c:row=c.execute('SELECT * FROM photo_task_consents WHERE id=? AND user_id=? AND product=?',(authorization['id'],uid,product)).fetchone()
  if not row or row['idem']!=idem or row['task_digest']!=digest or row['policy_version']!=VERSION or row['state'] not in ('approved','used') or not hmac.compare_digest(authorization['receipt'],receipt(row)) or (row['state']=='approved' and row['expires']<=time.time()):raise server.Problem(409,'授权与本次任务、素材或账户不匹配，请重新确认')
  token=ACTIVE.set({'id':row['id']})
  try:
   result=generate(uid,product,clean,idem,validator)
   with original_connect() as c:used=c.execute('SELECT job_id FROM photo_task_consents WHERE id=?',(row['id'],)).fetchone()
   if used['job_id']!=result.get('id'):raise server.Problem(409,'授权任务状态需要核对，请查询原任务')
   return result
  finally:ACTIVE.reset(token)
 store.generate_product=guarded_generate
 class Handler(parent):
  def run_request(self):
   path=urlsplit(self.path).path;parts=path.split('/')
   if len(parts)<4 or parts[1]!='platform-api' or parts[2] not in ('gemini','temu'):return super().run_request()
   product=parts[2];route='/'.join(parts[3:])
   if route not in ('photo-consents','photo-consent-view','photo-consent-decision','photo-consent-policy') and not re.fullmatch('photo-consents/[a-f0-9]{32}',route):return super().run_request()
   try:
    self.connection.settimeout(15)
    if route=='photo-consent-policy' and self.command=='GET':return self.send(200,{'policy_version':VERSION,'ttl_seconds':TTL,'page':BASE+'/membership/photo-consent/','account_consent_substitutes':False,'legacy_reference_consent_unchanged':True})
    if route.startswith('photo-consents/'):
     if self.command!='GET':raise server.Problem(405,'请使用GET查询')
     uid=owner(self.headers.get('Authorization','').removeprefix('Bearer '))
     with original_connect() as c:row=c.execute('SELECT * FROM photo_task_consents WHERE id=? AND user_id=? AND product=?',(route.split('/')[1],uid,product)).fetchone()
     if not row:raise server.Problem(404,'未找到本人的任务授权')
     return self.send(200,public(row,True))
    if self.command!='POST':raise server.Problem(405,'请使用POST')
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式错误')
    body=json.loads(self.rfile.read(size))
    if not isinstance(body,dict):raise server.Problem(400,'请求格式错误')
    if route=='photo-consents':
     uid=owner(self.headers.get('Authorization','').removeprefix('Bearer '))
     if set(body)-{'task_digest','idempotency_key','policy_version','restart'} or not isinstance(body.get('task_digest'),str) or not re.fullmatch('[a-f0-9]{64}',body['task_digest']) or not isinstance(body.get('idempotency_key'),str) or not re.fullmatch('[A-Za-z0-9_-]{16,100}',body['idempotency_key']) or body.get('policy_version')!=VERSION:raise server.Problem(400,'任务摘要或政策版本无效，请勿提交照片、路径或需求正文')
     with original_connect() as c:
      c.execute('BEGIN IMMEDIATE');now=int(time.time())
      old=c.execute('SELECT * FROM photo_task_consents WHERE user_id=? AND product=? AND idem=?',(uid,product,body['idempotency_key'])).fetchone()
      if old and old['task_digest']!=body['task_digest']:raise server.Problem(409,'同一任务标识不能更换照片或需求')
      if old and old['state']=='used':return self.send(200,public(old,True))
      if old and old['policy_version']!=VERSION and body.get('restart') is not True:raise server.Problem(409,'处理说明已更新，请明确重新打开本次授权')
      if old and old['policy_version']==VERSION and public(old)['state']=='approved':return self.send(200,public(old,True))
      if old and public(old)['state'] in ('declined','expired') and body.get('restart') is not True:return self.send(200,public(old))
      if old and old['policy_version']==VERSION and public(old)['state']=='pending':
       ticket=link_ticket(old['id'],uid,product,old['task_digest'],old['approved_nonce'])
       return self.send(200,dict(public(old),url=BASE+'/membership/photo-consent/#consent='+ticket+'&product='+product))
      if c.execute('SELECT count(*) FROM photo_task_consents WHERE user_id=? AND created>?',(uid,now-60)).fetchone()[0]>=30:raise server.Problem(429,'授权请求较多，请稍后再试')
      cid=old['id'] if old else secrets.token_hex(16);nonce=secrets.token_hex(16)
      ticket=link_ticket(cid,uid,product,body['task_digest'],nonce)
      if old:c.execute("UPDATE photo_task_consents SET ticket_hash=?,created=?,expires=?,state='pending',approved_nonce=?,approved_at=NULL,policy_version=? WHERE id=?",(server.digest(ticket),now,now+TTL,nonce,VERSION,cid))
      else:c.execute('INSERT INTO photo_task_consents VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)',(cid,uid,product,body['idempotency_key'],body['task_digest'],VERSION,server.digest(ticket),now,now+TTL,'pending',nonce))
      row=c.execute('SELECT * FROM photo_task_consents WHERE id=?',(cid,)).fetchone()
     return self.send(200,dict(public(row),url=BASE+'/membership/photo-consent/#consent='+ticket+'&product='+product))
    if self.headers.get('Origin')!=BASE or self.headers.get('X-Membership-Request')!='1':raise server.Problem(403,'请从本站操作')
    if set(body)-{'ticket','accepted','policy_version'} or not isinstance(body.get('ticket'),str) or not re.fullmatch('[A-Za-z0-9_-]{43}',body['ticket']):raise server.Problem(400,'授权链接无效')
    cookie=SimpleCookie(self.headers.get('Cookie','')).get('platform_member')
    try:uid=store.membership.web_user(cookie.value if cookie else '')
    except server.Problem:uid=None
    with original_connect() as c:
     c.execute('BEGIN IMMEDIATE')
     row=c.execute('SELECT * FROM photo_task_consents WHERE ticket_hash=? AND product=?',(server.digest(body['ticket']),product)).fetchone()
     if not row:raise server.Problem(404,'链接无效，请从原对话重新打开')
     if row['expires']<=time.time():raise server.Problem(410,'链接已过期，请回原对话重新打开')
     value=public(row)
     if route=='photo-consent-view':return self.send(200,dict(value,account_verified=uid==row['user_id'],policy_current=row['policy_version']==VERSION))
     if uid!=row['user_id']:raise server.Problem(403,'请先登录提交本任务的本人创作账户')
     if body.get('policy_version')!=VERSION or row['policy_version']!=VERSION:raise server.Problem(409,'处理说明已更新，请重新打开授权页')
     if type(body.get('accepted'))is not bool:raise server.Problem(400,'请明确选择同意或拒绝')
     if value['state']=='expired':raise server.Problem(410,'链接已过期，请回原对话重新打开')
     if row['state']!='pending':
      if row['state']=='approved' and body['accepted'] is True:return self.send(200,dict(value,account_verified=True))
      raise server.Problem(409,'本次选择已记录，请返回原对话')
     c.execute('UPDATE photo_task_consents SET state=?,approved_nonce=?,approved_at=? WHERE id=?',('approved' if body['accepted'] else 'declined',secrets.token_hex(16) if body['accepted'] else None,int(time.time()) if body['accepted'] else None,row['id']))
     row=c.execute('SELECT * FROM photo_task_consents WHERE id=?',(row['id'],)).fetchone()
    return self.send(200,dict(public(row),account_verified=True))
   except server.Problem as e:return self.send(e.status,{'error':e.message})
   except (ValueError,TypeError):return self.send(400,{'error':'参数无效，请重新打开本次授权'})
   except Exception:return self.send(503,{'error':'授权暂不可用，请保留原任务稍后再试'})
  do_GET=run_request
  do_POST=run_request
 return Handler
