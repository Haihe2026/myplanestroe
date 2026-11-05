"""Reuse the vetted Listing transaction engine with isolated, configured namespaces."""
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,re,uuid,importlib.util
from listing_store import Listing,Error,canonical,sha
ROOT=Path(__file__).resolve().parent
def services():return json.loads((ROOT/'services.json').read_text(encoding='utf-8'))['services']
def bound(store,uid):
 with store.connect() as c:return c.execute('SELECT 1 FROM wechat_identities WHERE user_id=?',(uid,)).fetchone() is not None
TABLES=['accounts','orders','quotes','tasks','ledger','artifacts','bonus_accounts','order_bonus','bonus_ledger','idem']
class Connection:
 def __init__(self,c,sid):self.c=c;self.prefix='metered_'+hashlib.sha256(sid.encode()).hexdigest()[:12]+'_';self.sid=sid
 def sql(self,s):
  for suffix in sorted(TABLES,key=len,reverse=True):s=re.sub(r'\blisting_'+suffix+r'\b',self.prefix+suffix,s)
  return s.replace("'listing-optimizer'","'metered:"+self.sid+"'")
 def execute(self,s,args=()):return self.c.execute(self.sql(s),args)
 def executescript(self,s):return self.c.executescript(self.sql(s))
 def __getattr__(self,name):return getattr(self.c,name)
class Store:
 def __init__(self,store,sid):self.original=store;self.sid=sid
 def __getattr__(self,name):return getattr(self.original,name)
 @contextmanager
 def connect(self):
  with self.original.connect() as c:yield Connection(c,self.sid)
class Delivery:
 ready=True
 def __init__(self,fields):self.fields=fields
 def recover_verified(self,task,evidence,scope):
  if not isinstance(evidence,dict) or set(evidence)!={'scope_hash','deliveries'} or evidence['scope_hash']!=sha(canonical(scope)):raise Error(409,'SCOPE_EVIDENCE_MISMATCH')
  rows=evidence['deliveries']
  if not isinstance(rows,list) or len(rows)!=1:raise Error(409,'INCOMPLETE_DELIVERY')
  r=rows[0]
  if not isinstance(r,dict) or set(r)!={'target','content'} or r['target']!=scope['targets'][0]:raise Error(409,'INCOMPLETE_DELIVERY')
  content=r['content']
  if not isinstance(content,dict) or set(content)!=set(self.fields) or any(not isinstance(v,str) or not 1<=len(v.strip())<=20000 for v in content.values()):raise Error(409,'INCOMPLETE_DELIVERY')
  return dict(artifact_id='metered-'+task+'-'+sha(canonical(evidence))[:16],scope_hash=evidence['scope_hash'],deliveries=rows)
class Service(Listing):
 def __init__(self,store,sid,cfg,**kwargs):
  self.sid=sid;self.service=cfg
  price=cfg.get('unit_price_fen',30)
  if type(price)is not int or price!=30:raise ValueError('Owner confirmed price is 30 fen per service')
  fields=cfg.get('result_fields',['result'])
  if not isinstance(fields,list) or not fields or any(not re.fullmatch('[a-z][a-z0-9_]{0,39}',x) for x in fields):raise ValueError('Invalid result schema')
  tiers=cfg.get('tiers',[dict(id='metered-39',pay_fen=3900,credit_fen=3900,label='灵活体验'),dict(id='metered-99',pay_fen=9900,credit_fen=9900,label='持续使用'),dict(id='metered-190',pay_fen=19000,credit_fen=19000,label='长期使用')])
  config=dict(product_id=sid,display_name=cfg['name'],currency='CNY',price_version=cfg.get('price_version','metered-v1'),unit_price_fen=price,charging_enabled=cfg.get('enabled') is True,delivery_adapter_confirmed=True,trial_policy={'total_successes':1},tiers=tiers,terms=dict(confirmed=True,unit_scope=cfg['unit_scope'],trial_scope=cfg['unit_scope'],included_revisions=0,balance_validity='no_expiry',refund_policy='statutory_rights_preserved',public_summary=['扫码关联微信账户后，每个服务首次可体验1次。','余额长期有效，按成功交付结算。']))
  super().__init__(Store(store,sid),config=config,verifier=Delivery(fields),**kwargs)
 def enroll(self,uid,key,accepted):
  if not bound(self.store.original,uid):raise Error(403,'WECHAT_REQUIRED')
  return super().enroll(uid,key,accepted)
 def quote(self,uid,key,scope):
  self.require_ready()
  if not bound(self.store.original,uid):raise Error(403,'WECHAT_REQUIRED')
  if not isinstance(scope,dict) or set(scope)!={'request_id'} or not isinstance(scope['request_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{16,100}',scope['request_id']):raise Error(400,'INVALID_SCOPE')
  scope={'request_id':scope['request_id'],'targets':[{'service':self.sid}]}
  def go(c):
   a=self.account(c,uid)
   if a['trial_state']=='held':raise Error(409,'TRIAL_IN_PROGRESS')
   funding='trial' if a['trial_state']=='available' else 'paid';qid=uuid.uuid4().hex
   c.execute('INSERT INTO listing_quotes VALUES(?,?,?,?,?,?,?)',(qid,uid,canonical(scope),self.config['price_version'],self.config['unit_price_fen'],funding,self.now()+600))
   return dict(id=qid,units=1,trial_units=int(funding=='trial'),paid_units=int(funding=='paid'),bonus_units=0,reserve_fen=0 if funding=='trial' else self.config['unit_price_fen'],expires=self.now()+600,scope=scope,scope_hash=sha(canonical(scope)),price_version=self.config['price_version'])
  return self.mutate(uid,key,'quote',scope,go)
def install(parent,store,server):
 import listing_gateway
 # Extend the actual route factory once per explicitly configured service.
 for sid,cfg in services().items():
  if cfg.get('bridge')=='listing':continue
  if not re.fullmatch('[a-z][a-z0-9_-]{2,63}',sid):raise ValueError('Invalid service id')
  api=Service(store,sid,cfg)
  spec=importlib.util.spec_from_file_location('metered_gateway_'+sid.replace('-','_'),listing_gateway.__file__);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  mod.PREFIX='/platform-api/metered/v1/'+sid
  mod.Listing=lambda *a,_api=api,**kw:_api
  original_public=mod.public
  def public(instance,_old=original_public):
   result=_old(instance);result.pop('platform_fields',None)
   return {**result,'description':instance.service.get('description',''),'unit_scope':instance.service['unit_scope'],'result_fields':instance.service.get('result_fields',['result']),'requires_wechat':True}
  mod.public=public
  handler=mod.wrap(parent,Store(store,sid),server)
  # Carry the Skill's original ephemeral credential entry into the common page.
  # Opening a second anonymous entry would link the browser but strand the Skill.
  def page_handler(base,service_id,prefix):
   from urllib.parse import urlsplit,urlunsplit
   class PageHandler(base):
    def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
     if status==200 and urlsplit(self.path).path==prefix+'/entry' and isinstance(result,dict) and 'url' in result:
      u=urlsplit(result['url'])
      result={**result,'url':urlunsplit((u.scheme,u.netloc,'/membership/listing/','skill='+service_id,u.fragment))}
     return super().send(status,result,mime,cookie=cookie)
   return PageHandler
  parent=page_handler(handler,sid,mod.PREFIX)
 return parent
