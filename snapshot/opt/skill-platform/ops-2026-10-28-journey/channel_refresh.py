"""Fetch only official public counters. No account credentials or private WorkBuddy data."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from contextlib import contextmanager
import json,os,tempfile,threading,time,urllib.request,urllib.parse
TZ=timezone(timedelta(hours=8))
LOCK=threading.Lock()
OWNER='user_9dc847d2'
def stamp(item):return item.get('captured_at') or item.get('date') or ''
def merge(old,new):
 result=dict(old,**new)
 for key in ('history','workbuddy_history'):
  items=dict(old.get(key,{}) or {})
  for day,item in (new.get(key,{}) or {}).items():
   if day not in items or stamp(item)>=stamp(items[day]):items[day]=item
  result[key]=items
 for key in ('skillhub','workbuddy'):
  a,b=old.get(key) or {},new.get(key) or {}
  result[key]=a if stamp(a)>stamp(b) else b
 return result
@contextmanager
def file_lock(path):
 with (Path(path).parent/'.channel-stats.lock').open('a') as lock:
  try:import fcntl
  except ImportError:yield
  else:
   fcntl.flock(lock,fcntl.LOCK_EX)
   try:yield
   finally:fcntl.flock(lock,fcntl.LOCK_UN)
class Refresh:
 def __init__(self,path='/var/lib/skill-monitor/channel-stats.json',opener=None):self.path=Path(path);self.open=opener or urllib.request.urlopen
 def read(self):return json.loads(self.path.read_text(encoding='utf8'))
 def save(self,data):
  stat=self.path.stat();fd,temp=tempfile.mkstemp(prefix='.channels-',dir=self.path.parent)
  try:
   with os.fdopen(fd,'w',encoding='utf8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
   os.chmod(temp,stat.st_mode&0o777)
   if hasattr(os,'chown'):os.chown(temp,stat.st_uid,stat.st_gid)
   os.replace(temp,self.path)
  finally:
   if os.path.exists(temp):os.unlink(temp)
 def run(self):
  with LOCK,file_lock(self.path):
   old=self.read();now=datetime.now(TZ)
   skills={};started=time.monotonic()
   try:
    for page in range(1,21):
     remaining=22-(time.monotonic()-started)
     if remaining<=0:raise TimeoutError()
     url='https://api.skillhub.cn/api/skills?'+urllib.parse.urlencode(dict(keyword='jyai',page=page,pageSize=100))
     with self.open(url,timeout=min(10,remaining)) as response:
      raw=response.read(4*1024*1024+1)
      if len(raw)>4*1024*1024:raise ValueError('oversized')
      answer=json.loads(raw)
     if answer.get('code')!=0:raise ValueError('provider response')
     data=answer['data']
     for item in data['skills']:
      if item.get('ownerName')!=OWNER:continue
      slug,name,count=item['slug'],item['name'],item['downloads']
      if not isinstance(slug,str) or not 1<=len(slug)<=200 or not isinstance(name,str) or type(count)is not int or count<0 or slug in skills:raise ValueError('invalid counter')
      skills[slug]=dict(slug=slug,name=name,downloads=count)
     if page*100>=int(data['total']):break
    else:raise ValueError('incomplete pagination')
    if not skills:raise ValueError('empty author list')
    now=datetime.now(TZ);day=now.date().isoformat()
    snapshot=dict(date=day,captured_at=now.isoformat(),owner=OWNER,scope='该作者公开技能中，官方搜索关键词 jyai 命中的技能；尚未核对作者主页完整清单',coverage='partial',skill_count=len(skills),downloads=sum(x['downloads'] for x in skills.values()),skills=sorted(skills.values(),key=lambda x:x['slug']))
    fresh=self.read();out=merge(fresh,dict(skillhub=snapshot,history={day:snapshot},generated_at=now.isoformat()))
    out['skillhub_refresh']=dict(last_attempt_at=now.isoformat(),status='ok',last_success_at=now.isoformat())
    self.save(out);return dict(cached=False,channels=out)
   except Exception:
    # Preserve all original counters/timestamps; do not log supplier bodies or fake success.
    fresh=self.read();fresh['skillhub_refresh']=dict(last_attempt_at=datetime.now(TZ).isoformat(),status='failed',error='public_counter_fetch_failed')
    self.save(fresh);raise RuntimeError('SkillHub采集暂未成功，已保留上次数据，请稍后重试') from None
