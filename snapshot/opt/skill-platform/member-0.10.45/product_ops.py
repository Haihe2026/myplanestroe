"""Read-only observed product directory. Missing attribution is never a zero."""
from pathlib import Path
from contextlib import closing
from urllib.parse import urlsplit,parse_qs
import sqlite3,json,time
ROOT=Path(__file__).resolve().parent
class Products:
 def __init__(self,db,channels='/var/lib/skill-monitor/channel-stats.json'):self.db,self.channels=db,Path(channels)
 def listing(self,days=7):
  if days not in (1,2,7,14,30,90):raise ValueError('invalid days')
  now=int(time.time());since=now-days*86400;rows=[];issues=[]
  try:data=json.loads(self.channels.read_text(encoding='utf8'))
  except (OSError,ValueError):data={};issues.append('渠道采集文件暂不可用')
  sh=data.get('skillhub') or {};wb=data.get('workbuddy') or {}
  for s in sh.get('skills',[]):
   rows.append(dict(id='skillhub:'+s['slug'],name=s['name'],channel='SkillHub',slug=s['slug'],downloads=s.get('downloads'),installs=None,captured_at=sh.get('captured_at') or sh.get('date'),attribution='尚未接入逐技能业务统计'))
  # Assets without stable platform IDs remain separate, even when names match.
  for i,a in enumerate(wb.get('assets',[])):
   rows.append(dict(id='workbuddy:'+str(i),name=a['name'],channel='WorkBuddy',slug=None,downloads=None,installs=a.get('installs'),captured_at=wb.get('captured_at') or wb.get('date'),attribution='近30天安装量；同名资产分别展示',page=a.get('page'),row=a.get('row')))
  services=[]
  with closing(sqlite3.connect(Path(self.db).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as c:
   c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
   def q(sql,args=()):return c.execute(sql,args).fetchone()[0]
   for key,name in [('pet','宠物养护'),('trade-leads','外贸获客')]:
    try:
     if key=='pet':
      users=q('SELECT count(*) FROM pet_accounts');new=q('SELECT count(*) FROM pet_accounts WHERE created>=?',(since,))
      counts=dict(c.execute('SELECT state,count(*) FROM pet_photo_jobs WHERE created>=? GROUP BY state',(since,)))
      amount=q("SELECT coalesce(sum(amount_fen),0) FROM pet_orders WHERE status='paid' AND paid_at>=?",(since,))
      detail='照片分析任务；档案总数 '+str(q('SELECT count(*) FROM pet_profiles'))+'；不统计宿主模型问询'
     else:
      users=q('SELECT count(*) FROM trade_wallets WHERE is_test=0');new=None
      counts={};amount=q("SELECT coalesce(sum(amount_fen),0) FROM trade_orders WHERE status='paid' AND is_test=0 AND paid_at>=?",(since,))
      detail='已排除标记测试的账户和订单；搜索请求按独立口径展示'
     services.append(dict(product=key,name=name,users=users,new_users=new,jobs=counts,paid_fen=amount,note=detail))
    except sqlite3.Error:services.append(dict(product=key,name=name,unavailable=True,note='数据表暂不可用'))
  return dict(products=rows,services=services,generated_at=now,days=days,issues=issues,scope=sh.get('scope','部分公开观测清单'),coverage=sh.get('coverage','partial'),workbuddy_scope=wb.get('scope',''),source_generated_at=data.get('generated_at'))
def extend(factory,path):
 def build(*args,**kwargs):
  parent=factory(*args,**kwargs);directory=Products(path)
  class Handler(parent):
   def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
    if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=result.replace(b'</head>',b'<script defer src="/ops/product-directory.js?v=0.10.45"></script></head>',1)
    return super().send(status,result,mime,cookie=cookie)
   def do_GET(self):
    u=urlsplit(self.path)
    if u.path=='/ops/product-directory.js':return self.send(200,(ROOT/'product-directory.js').read_bytes(),'application/javascript; charset=utf-8')
    if u.path!='/ops/api/product-directory':return super().do_GET()
    if not self.authenticated():return self.send(401,{'error':'ops_login_required'})
    try:return self.send(200,directory.listing(int(parse_qs(u.query).get('days',['7'])[0])))
    except (ValueError,TypeError):return self.send(400,{'error':'invalid_days'})
    except (sqlite3.Error,OSError):return self.send(503,{'error':'product_data_unavailable'})
  return Handler
 return build
