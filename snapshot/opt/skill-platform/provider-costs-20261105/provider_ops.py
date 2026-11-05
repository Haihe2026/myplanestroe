from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from urllib.request import Request,build_opener,HTTPRedirectHandler
import json,time,sys
from cost_store import Costs,catalog
ROOT=Path(__file__).resolve().parent
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None
def registry():
 sys.path.insert(0,'/opt/skill-platform/member-0.10.52')
 from asset_registry import Registry
 return Registry()
def balance():
 asset=registry().resolve_for_service('aisplice-universal')
 req=Request('https://www.aisplice.store/v1/balance',headers={'Authorization':'Bearer '+asset['secret']})
 with build_opener(NoRedirect()).open(req,timeout=8) as r:data=json.loads(r.read(65536))
 Costs().snapshot(data)
 return {'synced':True,'captured_at':int(time.time())}
def catalog_rows(items):
 cfg=catalog();base=next((x for x in items if x['id']=='aisplice-universal'),{})
 for m in cfg['models']:
  if any(x.get('model')==m['model'] for x in items):continue
  rates=[]
  for t,label in [('ordinary','普通'),('plus','Plus'),('pro','Pro'),('max','Max')]:
   rate=m['tiers'][t]
   if m['unit']=='million_tokens':rates.extend([dict(label=label+' 输入',amount=rate['input'],unit='百万token'),dict(label=label+' 输出',amount=rate['output'],unit='百万token')])
   else:rates.append(dict(label=label,amount=rate['price'],unit=m['unit']))
  items.append(dict(id='catalog-'+m['model'].lower().replace('.','-'),name='AiSplice · '+m['name'],kind={'图片':'image','视频':'video','文本':'text','音频':'general','3D':'general'}[m['category']],model=m['model'],base_url='https://www.aisplice.store/v1',docs_url='https://www.aisplice.store/zh/docs',auth_type='通用资产引用',auth_header='',secret_hint=base.get('secret_hint','未配置'),secret_configured=base.get('secret_configured',False),enabled=False,cost_only=True,notes='价格目录，只读；共用资产 aisplice-universal。目录存在不代表业务已接入。分辨率/时长档位以官方模型详情为准。',cost=dict(currency='USD',rates=rates,basis='供应商公开目录 · '+cfg['captured_at'],notes='公开起价／普通与会员档位；非已结算支出。来源：'+cfg['source'])))
 return items
def wrap(parent):
 class Handler(parent):
  def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
   path=urlsplit(self.path).path
   if status==200 and isinstance(result,dict) and path=='/ops/api/upstream-assets':result={**result,'items':catalog_rows(list(result.get('items',[])))}
   if status==200 and isinstance(result,bytes) and mime.startswith('text/html'):result=result.replace(b'</head>',b'<script defer src="/ops/provider-finance.js?v=20261105"></script></head>',1)
   return super().send(status,result,mime,cookie=cookie)
  def do_GET(self):
   path=urlsplit(self.path).path
   if path=='/ops/provider-finance.js':return self.send(200,(ROOT/'provider-finance.js').read_bytes(),'application/javascript; charset=utf-8')
   if path=='/ops/api/provider-finance':
    if not self.authenticated():return self.send(401,{'error':'请登录管理后台'})
    try:
     days=int(parse_qs(urlsplit(self.path).query).get('days',['30'])[0]);return self.send(200,Costs().report(days))
    except Exception:return self.send(503,{'error':'成本统计暂时无法读取'})
   return super().do_GET()
  def do_POST(self):
   if urlsplit(self.path).path=='/ops/api/provider-finance/sync':
    if not self.authenticated():return self.send(401,{'error':'请登录管理后台'})
    if self.headers.get('Origin')!='https://myplanestore.com' or self.headers.get('X-Membership-Request')!='1':return self.send(403,{'error':'请从本站管理后台操作'})
    try:
     n=int(self.headers.get('Content-Length','0'))
     if not 0<n<=1024:return self.send(400,{'error':'参数无效'})
     self.rfile.read(n)
     # Cached for 60 seconds; repeated refresh does not amplify vendor traffic.
     current=Costs().report()['snapshot']
     if current and time.time()-current['captured']<60:return self.send(200,{'synced':True,'cached':True})
     return self.send(200,balance())
    except Exception:return self.send(503,{'error':'余额同步失败；未调用模型、未发起扣费'})
   return super().do_POST()
 return Handler
