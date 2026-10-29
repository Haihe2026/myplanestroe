"""First-dialogue metadata only; no message text, IP, credential, or fingerprint persisted."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
import sqlite3,time,uuid,re,json,hmac,hashlib,base64,os
class Invalid(ValueError):pass
class Conflict(Invalid):pass
CHANNELS=('workbuddy_skill','workbuddy_expert','skillhub')
FIELDS={'event_id','installation_id','skill_id','skill_name','skill_version','channel','client_occurred_at','is_test'}
def identity(value):
 try:return isinstance(value,str) and str(uuid.UUID(value))==value
 except (ValueError,AttributeError):return False
class Dialogues:
 def __init__(self,path=None,key_file=None,clock=time.time):
  self.path=Path(path or os.environ.get('FIRST_DIALOGUES_DB','/var/lib/skill-monitor/first-dialogues.sqlite3'));self.clock=clock;p=Path(key_file or os.environ.get('FIRST_DIALOGUES_KEY_FILE','/etc/skill-platform/first-dialogues.key'))
  if os.name!='nt' and p.stat().st_mode&0o077:raise RuntimeError('Invalid metadata key permissions')
  self.key=p.read_bytes()
  if len(self.key)!=32:raise RuntimeError('Invalid metadata key')
 def digest(self,value):return hmac.new(self.key,value.encode(),hashlib.sha256).hexdigest()
 @contextmanager
 def connect(self,readonly=False):
  c=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=3) if readonly else sqlite3.connect(self.path,timeout=3)
  c.row_factory=sqlite3.Row
  try:
   if readonly:c.execute('PRAGMA query_only=ON')
   else:self.path.chmod(0o600)
   with c:yield c
  finally:c.close()
 def initialize(self):
  with self.connect() as c:c.executescript("CREATE TABLE IF NOT EXISTS first_dialogues(event_id TEXT PRIMARY KEY,installation_hash TEXT NOT NULL,skill_id TEXT NOT NULL,skill_name TEXT NOT NULL,skill_version TEXT NOT NULL,channel TEXT NOT NULL,received_at INTEGER NOT NULL,client_occurred_at INTEGER,is_test INTEGER NOT NULL,user_id TEXT,linked_at INTEGER,UNIQUE(installation_hash,skill_id,channel));CREATE INDEX IF NOT EXISTS first_dialogues_time ON first_dialogues(received_at);CREATE INDEX IF NOT EXISTS first_dialogues_user ON first_dialogues(user_id,received_at);")
 def receipt(self,row):return base64.urlsafe_b64encode(hmac.new(self.key,('receipt:'+row['event_id']+':'+row['installation_hash']).encode(),hashlib.sha256).digest()).decode().rstrip('=')
 def record(self,b):
  if not isinstance(b,dict) or set(b)-FIELDS:raise Invalid('仅接受首次对话元数据，禁止提交聊天正文或凭证')
  if not identity(b.get('event_id')) or not identity(b.get('installation_id')):raise Invalid('请提供独立随机UUID作为事件和安装标识')
  sid=b.get('skill_id');channel=b.get('channel')
  if not isinstance(sid,str) or not re.fullmatch('[a-z0-9][a-z0-9_-]{1,99}',sid) or channel not in CHANNELS:raise Invalid('技能标识或渠道无效')
  name=b.get('skill_name',sid);version=b.get('skill_version','')
  if not isinstance(name,str) or not 1<=len(name)<=100 or not isinstance(version,str) or len(version)>40 or any(ord(x)<32 for x in name+version):raise Invalid('技能名称或版本无效')
  test=b.get('is_test',False)
  if type(test)is not bool:raise Invalid('测试标记无效')
  claimed=None;value=b.get('client_occurred_at')
  if value is not None:
   try:
    stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    if not stamp.tzinfo:raise ValueError()
    claimed=int(stamp.timestamp())
    if not 1577836800<=claimed<=int(self.clock())+86400:raise ValueError()
   except (ValueError,TypeError,AttributeError,OverflowError):raise Invalid('客户端时间需为带时区的ISO时间')
  install=self.digest('installation:'+b['installation_id']);now=int(self.clock())
  with self.connect() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM first_dialogues WHERE installation_hash=? AND skill_id=? AND channel=?',(install,sid,channel)).fetchone()
   if old:row=old;duplicate=True
   else:
    if c.execute('SELECT 1 FROM first_dialogues WHERE event_id=?',(b['event_id'],)).fetchone():raise Conflict('事件标识已用于其他安装或技能')
    c.execute('INSERT INTO first_dialogues VALUES(?,?,?,?,?,?,?,?,?,NULL,NULL)',(b['event_id'],install,sid,name,version,channel,now,claimed,int(test)))
    row=c.execute('SELECT * FROM first_dialogues WHERE event_id=?',(b['event_id'],)).fetchone();duplicate=False
   return dict(event_id=row['event_id'],received_at=row['received_at'],receipt=self.receipt(row),duplicate=duplicate,evidence='skill_reported_first_dialogue')
 def link(self,event_id,receipt,uid):
  if not identity(event_id) or not isinstance(receipt,str) or len(receipt)!=43:raise Invalid('事件回执无效')
  with self.connect() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM first_dialogues WHERE event_id=?',(event_id,)).fetchone()
   if not row or not hmac.compare_digest(self.receipt(row),receipt):raise Invalid('事件回执无效')
   if row['user_id'] and row['user_id']!=uid:raise Conflict('事件已关联其他账户')
   if not row['user_id']:c.execute('UPDATE first_dialogues SET user_id=?,linked_at=? WHERE event_id=?',(uid,int(self.clock()),event_id))
  return dict(linked=True,event_id=event_id)
 def public(self,row):return {k:row[k] for k in ['event_id','skill_id','skill_name','skill_version','channel','received_at','client_occurred_at','is_test','user_id','linked_at']}
 def listing(self,days=30,page=1,skill='',channel='',state='',include_test=False):
  if days not in (1,7,30,90) or type(page)is not int or not 1<=page<=100000 or len(skill)>100 or channel not in ('',*CHANNELS) or state not in ('','linked','anonymous'):raise Invalid('筛选条件无效')
  where=['received_at>=?'];args=[int(self.clock())-days*86400]
  if not include_test:where.append('is_test=0')
  for key,value in [('skill_id',skill),('channel',channel)]:
   if value:where.append(key+'=?');args.append(value)
  if state:where.append('user_id IS '+('NOT NULL' if state=='linked' else 'NULL'))
  sql=' AND '.join(where)
  with self.connect(True) as c:
   total=c.execute('SELECT count(*) FROM first_dialogues WHERE '+sql,args).fetchone()[0]
   rows=c.execute('SELECT * FROM first_dialogues WHERE '+sql+' ORDER BY received_at DESC,event_id LIMIT 50 OFFSET ?',args+[(page-1)*50]).fetchall()
   groups=[dict(x) for x in c.execute('SELECT skill_id,channel,count(*) events,sum(user_id IS NOT NULL) linked,min(received_at) first_at,max(received_at) latest_at FROM first_dialogues WHERE '+sql+' GROUP BY skill_id,channel ORDER BY latest_at DESC LIMIT 500',args)]
  return dict(items=[self.public(x) for x in rows],total=total,page=page,page_size=50,groups=groups,generated_at=int(self.clock()),scope='Skill上报的首次对话；按随机安装标识×技能×渠道去重，不等于独立人数或平台已验证消息。',test_excluded=not include_test)
 def for_user(self,uid):
  with self.connect(True) as c:return [self.public(x) for x in c.execute('SELECT * FROM first_dialogues WHERE is_test=0 AND user_id=? ORDER BY received_at,event_id LIMIT 100',(uid,))]

 def first_for_users(self,uids):
  if not uids:return {}
  with self.connect(True) as c:
   rows=c.execute('SELECT * FROM (SELECT *,row_number() OVER(PARTITION BY user_id ORDER BY received_at,event_id) position FROM first_dialogues WHERE is_test=0 AND user_id IN ('+','.join('?' for _ in uids)+')) WHERE position=1',uids).fetchall()
   return {row['user_id']:self.public(row) for row in rows}
