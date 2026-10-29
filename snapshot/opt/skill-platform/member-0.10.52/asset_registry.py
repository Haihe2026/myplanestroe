"""Server-side encrypted upstream registry. No public credential retrieval or HTTP proxy."""
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import urlsplit
import sqlite3,secrets,json,time,re,os,ipaddress,sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"vendor"))
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
class Invalid(ValueError):pass
def url(value,optional=False):
 if optional and value=='':return ''
 if not isinstance(value,str) or len(value)>1024:raise Invalid('请填写HTTPS地址')
 u=urlsplit(value)
 if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.port not in (None,443):raise Invalid('地址须为HTTPS，不能包含密钥、查询参数或非443端口')
 host=u.hostname.lower()
 if host=='localhost' or host.endswith(('.localhost','.local','.internal')):raise Invalid('请填写公网服务地址')
 try:
  if not ipaddress.ip_address(host).is_global:raise Invalid('不接受内网地址')
 except ValueError as e:
  if isinstance(e,Invalid):raise
  if not re.fullmatch(r'(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}',host) or '..' in host:raise Invalid('公网域名格式无效')
 return value.rstrip('/')
class Registry:
 def __init__(self,path='/var/lib/skill-monitor/upstream-assets.sqlite3',key_file='/etc/skill-platform/upstream-assets.key'):
  self.path,self.key_file=Path(path),Path(key_file)
  if os.name!='nt' and self.key_file.stat().st_mode&0o077:raise RuntimeError('Registry key permissions invalid')
  key=self.key_file.read_bytes()
  if len(key)!=32:raise RuntimeError('Registry master key invalid')
  self.cipher=AESGCM(key)
 @contextmanager
 def connect(self):
  c=sqlite3.connect(self.path,timeout=5);c.row_factory=sqlite3.Row
  try:
   self.path.chmod(0o600)
   with c:yield c
  finally:c.close()
 def initialize(self):
  with self.connect() as c:c.executescript("CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,metadata TEXT NOT NULL,nonce BLOB,secret BLOB,last4 TEXT,enabled INTEGER NOT NULL,archived INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL,created INTEGER NOT NULL,updated INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS asset_audit(id INTEGER PRIMARY KEY,asset_id TEXT NOT NULL,action TEXT NOT NULL,actor TEXT NOT NULL,created INTEGER NOT NULL);")
 def public(self,r):
  return dict(json.loads(r['metadata']),id=r['id'],secret_configured=r['secret'] is not None,secret_hint='••••'+r['last4'] if r['secret'] is not None else '未配置',enabled=bool(r['enabled']),archived=bool(r['archived']),revision=r['revision'],created=r['created'],updated=r['updated'],integration_status='待业务适配')
 def listing(self):
  with self.connect() as c:
   items=[self.public(r) for r in c.execute('SELECT * FROM assets WHERE archived=0 ORDER BY updated DESC,id')]
   audit=[dict(r) for r in c.execute('SELECT asset_id,action,created FROM asset_audit ORDER BY id DESC LIMIT 50')]
  return dict(items=items,audit=audit)
 def save(self,b,actor):
  if not isinstance(b,dict) or set(b)-{'id','name','kind','base_url','docs_url','auth_type','auth_header','model','notes','secret','enabled','revision'}:raise Invalid('资产字段无效')
  aid=b.get('id','')
  if not isinstance(aid,str) or not re.fullmatch('[a-z][a-z0-9_-]{2,63}',aid):raise Invalid('资产标识需3–64位小写字母、数字、短横线或下划线')
  meta={}
  for k,limit in [('name',100),('model',128),('notes',500)]:
   v=b.get(k,'')
   if not isinstance(v,str) or len(v)>limit or any(ord(x)<32 and x not in '\n\t' for x in v):raise Invalid('名称、模型或备注格式无效')
   meta[k]=v.strip()
  if not meta['name']:raise Invalid('请填写资产名称')
  meta['kind']=b.get('kind','general');meta['auth_type']=b.get('auth_type','bearer');meta['auth_header']=b.get('auth_header','')
  if meta['kind'] not in ('image','vision','text','data','general') or meta['auth_type'] not in ('bearer','header','none'):raise Invalid('资产类型或认证方式无效')
  if meta['auth_type']=='header':
   h=meta['auth_header']
   if not isinstance(h,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9-]{0,63}',h) or h.lower() in ('host','cookie','set-cookie','authorization','content-length','origin','connection','transfer-encoding','proxy-authorization'):raise Invalid('自定义认证头无效，请使用X-API-Key等认证头')
  else:meta['auth_header']='Authorization' if meta['auth_type']=='bearer' else ''
  meta['base_url']=url(b.get('base_url'));meta['docs_url']=url(b.get('docs_url',''),True)
  secret=b.get('secret','')
  if not isinstance(secret,str) or (secret and not re.fullmatch(r'[!-~]{8,8192}',secret)):raise Invalid('KEY应为8–8192位可见字符，不含空格或换行')
  if secret and any(secret in str(v) for v in meta.values()):raise Invalid('请将密钥仅填写在KEY栏，不要放进地址、名称或备注')
  enabled=b.get('enabled',False)
  if type(enabled)is not bool:raise Invalid('启用状态无效')
  now=int(time.time())
  with self.connect() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM assets WHERE id=?',(aid,)).fetchone()
   if old and (old['archived'] or b.get('revision')!=old['revision']):raise Invalid('记录已更新或已归档，请刷新后重试')
   if not old and b.get('revision') not in (None,0):raise Invalid('记录不存在，请刷新')
   if meta['auth_type']=='none':nonce=encrypted=None;last4=''
   elif secret:
    nonce=secrets.token_bytes(12);encrypted=self.cipher.encrypt(nonce,secret.encode(),aid.encode());last4=secret[-4:]
   elif old and old['secret'] is not None:nonce,encrypted,last4=old['nonce'],old['secret'],old['last4']
   else:raise Invalid('请填写KEY；更新时留空可保留原KEY')
   revision=old['revision']+1 if old else 1;created=old['created'] if old else now
   c.execute('INSERT OR REPLACE INTO assets VALUES(?,?,?,?,?,?,0,?,?,?)',(aid,json.dumps(meta,ensure_ascii=False),nonce,encrypted,last4,int(enabled),revision,created,now))
   action='rotate_key' if old and secret else 'update' if old else 'create'
   c.execute('INSERT INTO asset_audit(asset_id,action,actor,created) VALUES(?,?,?,?)',(aid,action,actor,now))
   return self.public(c.execute('SELECT * FROM assets WHERE id=?',(aid,)).fetchone())
 def archive(self,aid,revision,actor):
  with self.connect() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM assets WHERE id=?',(aid,)).fetchone()
   if not r or r['archived'] or r['revision']!=revision:raise Invalid('记录已更新，请刷新')
   c.execute('UPDATE assets SET archived=1,enabled=0,revision=revision+1,updated=? WHERE id=?',(int(time.time()),aid));c.execute('INSERT INTO asset_audit(asset_id,action,actor,created) VALUES(?,?,?,?)',(aid,'archive',actor,int(time.time())))
  return dict(archived=True)
 def resolve_for_service(self,aid):
  """Internal only: adapters import this method; never send the result to clients/logs.
  Adapters must pin public DNS/IPs and enforce budgets/timeouts/idempotency before calls.
  This registry intentionally makes zero network requests and offers no arbitrary proxy.
  """
  with self.connect() as c:r=c.execute('SELECT * FROM assets WHERE id=? AND enabled=1 AND archived=0',(aid,)).fetchone()
  if not r:raise Invalid('资产未启用或不存在')
  meta=json.loads(r['metadata']);secret=self.cipher.decrypt(r['nonce'],r['secret'],aid.encode()).decode() if r['secret'] is not None else None
  return dict(meta,id=aid,secret=secret)
