"""Expose paid video over the existing shared wallet without changing plan prices."""
import json,re,threading,time
from urllib.parse import urlsplit
from pathlib import Path
from grok_provider import Fault,validate
from paid_provider import Provider
from video_billing import Billing
PREFIX='/platform-api/grok-video'
KEY='/etc/skill-platform/grok-video-upstream.key'
ROOT='/var/lib/skill-platform/grok-video/paid-results'

def wrap(parent,store,server):
 engine=Billing(store,Provider(KEY),ROOT)
 if not getattr(store,'grok_paid_worker_started',False):
  store.grok_paid_worker_started=True
  def worker():
   while True:
    time.sleep(5)
    try:
     with store.connect() as c:rows=c.execute("SELECT user_id,id FROM grok_video_jobs WHERE settled=0 AND upstream_id IS NOT NULL ORDER BY created LIMIT 16").fetchall()
     for r in rows:
      try:engine.poll(r['user_id'],r['id'])
      except Exception:pass
    except Exception:pass
  threading.Thread(target=worker,name='grok-video-settlement',daemon=True).start()
 class PaidHandler(parent):
  def run_request(self):
   path=urlsplit(self.path).path
   if path==PREFIX+'/health' and self.command=='GET':
    return self.send(200,dict(status='ok',version='0.1.2',billing_version='0.1.3',contract='grok-video-v1',account_entry_enabled=True,registration='wechat_ready',customer_generation_enabled=engine.provider.ready,retail_pricing='shared_per_success',video_cost_uses=1,video_trial_uses=0,duration_min=6,duration_max=15,resolutions=['480p','720p'],max_images=7))
   if not path.startswith(PREFIX+'/') or path in (PREFIX+'/health',PREFIX+'/entry'):return super().run_request()
   if self.headers.get('Origin') not in (None,'https://myplanestore.com'):return self.send(403,dict(error='origin_not_allowed'))
   routes=(PREFIX+'/balance',PREFIX+'/quote',PREFIX+'/membership-link',PREFIX+'/jobs')
   match=re.fullmatch(re.escape(PREFIX)+r'/jobs/([a-f0-9]{32})(/content)?',path)
   if path not in routes and not match:return super().run_request()
   token=self.headers.get('Authorization','')
   if not re.fullmatch('Bearer [A-Za-z0-9_-]{43}',token):return self.send(401,dict(error='account_auth_required'))
   try:uid=store.user(token[7:])
   except Exception:return self.send(401,dict(error='account_auth_required'))
   if not uid:return self.send(401,dict(error='account_auth_required'))
   try:
    self.connection.settimeout(10)
    body={}
    if self.command=='POST':
     n=int(self.headers.get('Content-Length','0'))
     if not 0<n<=65536 or self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(400,dict(error='invalid_request'))
     body=json.loads(self.rfile.read(n))
     if not isinstance(body,dict):return self.send(400,dict(error='invalid_request'))
    if self.command=='GET' and path==PREFIX+'/balance':return self.send(200,engine.quota(uid))
    if self.command=='POST' and path==PREFIX+'/quote':
     spec=validate(body);q=engine.quota(uid)
     return self.send(200,dict(status='quoted',duration=spec['duration'],resolution=spec['resolution'],size=spec['size'],cost_uses=1,affordable=q['shared_uses']>=1,service_available=engine.provider.ready and engine.provider.can_afford(spec),**q))
    if self.command=='POST' and path==PREFIX+'/membership-link':return self.send(200,dict(store.membership.handoff(uid),status='checkout',message='请在通用充值中心选择套餐；核款到账后回原对话继续。'))
    if self.command=='POST' and path==PREFIX+'/jobs':
     out=engine.submit(uid,self.headers.get('Idempotency-Key'),body);return self.send(200,dict(out,**engine.quota(uid)))
    if self.command=='GET' and match:
     if match[2]:return self.send(200,engine.download(uid,match[1]),'video/mp4',download='grok-video.mp4')
     out=engine.poll(uid,match[1]);return self.send(200,dict(out,**engine.quota(uid)))
    return self.send(405,dict(error='method_not_allowed'))
   except Fault as e:
    code=str(e);status=402 if code=='INSUFFICIENT_SHARED_USES' else 503 if code.startswith('PROVIDER_') else 404 if code=='TASK_NOT_FOUND' else 409 if code=='TASK_CONFLICT' else 400
    messages={'INSUFFICIENT_SHARED_USES':'通用次数不足，请充值到账后继续原方案。','TASK_CONFLICT':'原任务内容已冻结，请勿更换内容重复提交。','TASK_NOT_FOUND':'原任务暂不可用，请核对同一账户。','CONFIRM_REQUIRED':'请先确认本次制作与1次通用次数消耗。','REFERENCE_CONSENT_REQUIRED':'参考图发送前需确认素材处理授权。'}
    return self.send(status,dict(status='insufficient_uses' if status==402 else 'error',code=code if code in messages else 'VIDEO_REQUEST_INVALID',message=messages.get(code,'视频参数或状态需要核对，请保留原方案。')))
   except Exception:return self.send(503,dict(status='needs_review',message='视频状态待核查，请保留原任务，不要重新提交。'))
  do_GET=run_request
  do_POST=run_request
 return PaidHandler
