"""New route; original account, payment, image and WeChat systems remain untouched."""
import json,re,os,time
from pathlib import Path
from urllib.parse import urlsplit
from grok_provider import Provider,Tasks,Fault
PREFIX='/platform-api/grok-video'
KEY='/etc/skill-platform/grok-video-upstream.key'
DATA='/var/lib/skill-platform/grok-video'

def wrap(parent,store,product):
 tasks=Tasks(DATA,Provider(KEY))
 class Handler(parent):
  def log_message(self,*a):
   if urlsplit(self.path).path.startswith(PREFIX+'/'):return
   return super().log_message(*a)
  def run_request(self):
   p=urlsplit(self.path).path
   if not p.startswith(PREFIX+'/'):return super().run_request()
   if product not in ('gemini','shared'):return self.send(404,{'error':'not_found'})
   if self.headers.get('Origin') not in (None,'https://myplanestore.com'):return self.send(403,{'error':'origin_not_allowed'})
   if self.command=='GET' and p==PREFIX+'/health':
    return self.send(200,dict(status='ok',version='0.1.0',contract='grok-video-v1',provider_configured=tasks.provider.ready,customer_generation_enabled=False,registration='wechat_configured_untested',retail_pricing='pending_confirmation',max_images=7,duration_min=6,duration_max=15,resolutions=['480p','720p']))
   # No false QR code, invented OAuth or fallback to phone. Never create orders
   # or consume image credits for this uncommissioned video product.
   if self.command=='POST' and p==PREFIX+'/entry':
    return self.send(503,dict(status='service_pending',code='VIDEO_PRICING_PENDING',message='视频创作方案已保留，本品服务尚未开放，请稍后继续。'))
   h=self.headers.get('Authorization','')
   if not re.fullmatch('Bearer [A-Za-z0-9_-]{43}',h):return self.send(401,{'error':'account_auth_required'})
   try:owner=store.user(h[7:])
   except Exception:return self.send(401,{'error':'account_auth_required'})
   if not owner:return self.send(401,{'error':'account_auth_required'})
   if self.command=='POST' and p==PREFIX+'/jobs':
    return self.send(503,dict(code='VIDEO_NOT_COMMISSIONED',message='视频服务尚未开放，本次未提交制作。'))
   m=re.fullmatch(re.escape(PREFIX)+r'/jobs/([a-f0-9]{32})(/content)?',p)
   if self.command=='GET' and m:
    try:
     if m[2]:return self.send(200,tasks.download(owner,m[1]),'video/mp4',download='grok-video.mp4')
     return self.send(200,tasks.poll(owner,m[1]))
    except Fault:return self.send(404,dict(error='原任务暂不可用，请核对同一账户。'))
   return self.send(404,dict(error='not_found'))
  do_GET=run_request
  do_POST=run_request
 return Handler
