"""Account invitations work independently of video availability; no account creation."""
import json,secrets,time,re,ipaddress
from urllib.parse import urlsplit
PREFIX='/platform-api/grok-video'

def wrap(parent,store,server):
 class EntryHandler(parent):
  def send(self,status,result,*a,**kw):
   if status==200 and urlsplit(self.path).path==PREFIX+'/health' and isinstance(result,dict):
    result=dict(result,version='0.1.2',registration='wechat_ready',account_entry_enabled=True)
   return super().send(status,result,*a,**kw)
  def run_request(self):
   path=urlsplit(self.path).path
   if path!=PREFIX+'/entry':return super().run_request()
   if self.command!='POST':return self.send(405,dict(error='method_not_allowed'))
   if self.headers.get('Origin') not in (None,'https://myplanestore.com'):return self.send(403,dict(error='origin_not_allowed'))
   try:
    self.connection.settimeout(5)
    n=int(self.headers.get('Content-Length','0'))
    if not 0<n<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(400,dict(error='invalid_request'))
    body=json.loads(self.rfile.read(n))
    if not isinstance(body,dict) or set(body)!={'install_secret'} or not isinstance(body['install_secret'],str) or not re.fullmatch('[A-Za-z0-9_-]{43}',body['install_secret']):return self.send(400,dict(error='invalid_identity'))
    # Use the already deployed WeChat entry contract and shared account identity.
    # Never query video quota, create an account/order or send a provider task here.
    ip=self.client_address[0]
    if ip in ('127.0.0.1','::1'):
     try:ip=str(ipaddress.ip_address(self.headers.get('X-Real-IP',ip)))
     except ValueError:return self.send(400,dict(error='invalid_request'))
    entries=store.registration_entries;now=time.time()
    with entries.lock:
     entries.pending={k:v for k,v in entries.pending.items() if v['expires']>now}
     if len(entries.pending)>=2048 or sum(v['ip']==ip for v in entries.pending.values())>=12:return self.send(429,dict(error='entry_rate_limited'))
     ticket=secrets.token_urlsafe(32)
     entries.pending[server.digest(ticket)]=dict(product='gemini',secret=body['install_secret'],ip=ip,expires=now+300)
    return self.send(200,dict(status='registration',url='https://myplanestore.com/membership/gemini/register/#entry='+ticket,expires_in=300,message='请使用微信扫码关联账户，完成后回原对话发送“继续”。'))
   except Exception:return self.send(503,dict(error='账户入口暂不可用，请保留方案稍后重试。'))
  do_GET=run_request
  do_POST=run_request
 return EntryHandler
