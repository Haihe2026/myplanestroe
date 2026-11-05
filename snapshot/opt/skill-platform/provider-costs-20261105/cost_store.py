"""Metadata-only cost estimates. No prompts, images, credentials, or customer text."""
from pathlib import Path
from contextlib import closing
from decimal import Decimal,InvalidOperation
import sqlite3,json,time,os,hashlib
ROOT=Path(__file__).resolve().parent
def catalog():return json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
class Costs:
 def __init__(self,path=None):self.path=Path(path or os.environ.get('PROVIDER_COSTS_DB','/var/lib/skill-monitor/provider-costs.sqlite3'))
 def connect(self):return sqlite3.connect(self.path,timeout=3)
 def initialize(self):
  self.path.parent.mkdir(parents=True,exist_ok=True)
  with closing(self.connect()) as c:
   c.executescript('CREATE TABLE IF NOT EXISTS cost_events(event_key TEXT PRIMARY KEY,model TEXT NOT NULL,status TEXT NOT NULL,quantity TEXT,input_tokens INTEGER,output_tokens INTEGER,estimated_usd TEXT,price_version TEXT,created INTEGER NOT NULL,updated INTEGER NOT NULL,params TEXT);CREATE TABLE IF NOT EXISTS provider_snapshots(id INTEGER PRIMARY KEY,captured INTEGER NOT NULL,currency TEXT NOT NULL,balance TEXT,available TEXT,key_used TEXT);');c.commit()
  self.path.chmod(0o600)
 def estimate(self,model,quantity=None,input_tokens=None,output_tokens=None,params=None):
  row=next((m for m in catalog()['models'] if m['model']==model),None)
  if not row:return None
  rate=row['tiers']['ordinary']
  # Parameter-specific video rates cannot be inferred from a public starting price.
  if row['unit']=='second':
   resolution=(params or {}).get('resolution')
   if model!='grok-imagine-1.5-video' or resolution not in ('480p','720p'):return None
   try:
    q=Decimal(str(quantity));return str(Decimal({'480p':'.0112','720p':'.021'}[resolution])*q) if q.is_finite() and q>0 else None
   except Exception:return None
  try:
   if row['unit']=='million_tokens':
    if any(type(v)is not int or v<0 for v in [input_tokens,output_tokens]):return None
    return str((Decimal(rate['input'])*input_tokens+Decimal(rate['output'])*output_tokens)/1000000)
   q=Decimal(str(quantity));return str(Decimal(rate['price'])*q) if q.is_finite() and q>0 else None
  except (InvalidOperation,TypeError):return None
 def record(self,key,model,status,quantity=None,input_tokens=None,output_tokens=None,params=None):
  if not isinstance(key,str) or not key or len(key)>256:return
  if not isinstance(model,str) or len(model)>128:return
  if status not in ('pending','succeeded','failed','unknown'):return
  params={k:v for k,v in (params or {}).items() if k in ('resolution','size','quality') and isinstance(v,str) and len(v)<=40}
  amount=self.estimate(model,quantity,input_tokens,output_tokens,params) if status in ('succeeded','pending') else None
  now=int(time.time());hashed=hashlib.sha256(key.encode()).hexdigest()
  with closing(self.connect()) as c:
   old=c.execute('SELECT status,estimated_usd FROM cost_events WHERE event_key=?',(hashed,)).fetchone()
   # Polls/retries never turn a settled success into pending/unknown or charge twice.
   if old and old[0] in ('succeeded','failed'):return
   if old and old[1] is not None and status=='succeeded':amount=old[1]
   c.execute('INSERT INTO cost_events VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(event_key) DO UPDATE SET model=excluded.model,status=excluded.status,quantity=excluded.quantity,input_tokens=excluded.input_tokens,output_tokens=excluded.output_tokens,estimated_usd=excluded.estimated_usd,updated=excluded.updated,params=excluded.params',(hashed,model,status,str(quantity) if quantity is not None else None,input_tokens,output_tokens,amount,catalog()['price_version'],now,now,json.dumps(params)));c.commit()
 def lookup(self,key):
  with closing(self.connect()) as c:
   c.row_factory=sqlite3.Row;r=c.execute('SELECT model,quantity,params FROM cost_events WHERE event_key=?',(hashlib.sha256(key.encode()).hexdigest(),)).fetchone()
  return dict(r) if r else None
 def snapshot(self,data):
  if data.get('currency')!='USD':raise ValueError('Unsupported currency')
  def num(v):
   if v is None:return None
   d=Decimal(str(v))
   if not d.is_finite():raise ValueError('Invalid amount')
   return str(d)
  with closing(self.connect()) as c:c.execute('INSERT INTO provider_snapshots(captured,currency,balance,available,key_used) VALUES(?,?,?,?,?)',(int(time.time()),'USD',num(data.get('balance')),num(data.get('available')),num(data.get('key',{}).get('used'))));c.commit()
 def report(self,days=30):
  if type(days)is not int or not 1<=days<=365:raise ValueError('Invalid days')
  since=int(time.time())-days*86400
  with closing(self.connect()) as c:
   c.row_factory=sqlite3.Row
   rows=[dict(r) for r in c.execute('SELECT * FROM cost_events WHERE created>=? ORDER BY created DESC LIMIT 500',(since,))]
   groups=[dict(r) for r in c.execute('SELECT model,status,count(*) calls FROM cost_events WHERE created>=? GROUP BY model,status',(since,))]
   amounts=[r[0] for r in c.execute("SELECT estimated_usd FROM cost_events WHERE created>=? AND status='succeeded' AND estimated_usd IS NOT NULL",(since,))]
   snapshot=c.execute('SELECT captured,currency,balance,available,key_used FROM provider_snapshots ORDER BY id DESC LIMIT 1').fetchone()
  total=sum((Decimal(x) for x in amounts),Decimal(0));fx=Decimal(catalog()['fx_usd_cny'])
  return dict(days=days,generated_at=int(time.time()),estimated_usd=str(total),estimated_cny=str(total*fx),fx_usd_cny=str(fx),groups=groups,items=rows,snapshot=dict(snapshot) if snapshot else None,scope='本网站接入成本账本后的观测；目录估算不等于供应商已结算费用。KEY累计消费包含此KEY所有来源，不能直接归属本网站。视频参数档位未核实或用量缺失时待核对。',price_version=catalog()['price_version'])
