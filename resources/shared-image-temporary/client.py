"""Stdlib client for the existing paid shared image gateway; no provider keys."""
import json,re,uuid,urllib.request,urllib.error
from urllib.parse import urlsplit,urlunsplit,quote
ORIGIN='https://aistore.zhaopintong.com'
FIRST_PARTY=('https://aistore.zhaopintong.com','https://myplanestore.com')
class GatewayError(RuntimeError):
 def __init__(self,status):self.status=status;super().__init__('Gateway request incomplete (HTTP '+str(status)+'); preserve the original task')
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def temporary_link(url):
 """Only normalize server-issued browser links; never invent a ticket or redirect POST."""
 u=urlsplit(url)
 if u.scheme+'://'+u.netloc not in FIRST_PARTY or u.username or u.password or u.path not in ('/membership/','/membership/gemini/','/membership/gemini/register/','/auth/wechat/'):
  raise ValueError('Untrusted account page')
 return urlunsplit(('https','aistore.zhaopintong.com',u.path,u.query,u.fragment))

def text_job(prompt,idem,confirmed=False,size='1024x1024'):
 """Paid text branch only. Caller persists idem and obtains actual confirmation first."""
 if confirmed is not True:raise ValueError('User confirmation required')
 if not isinstance(prompt,str) or not 1<=len(prompt.strip())<=6000:raise ValueError('Prompt length invalid')
 if size not in ('1024x1024','1536x1024','1024x1536'):raise ValueError('Unsupported image size')
 if not isinstance(idem,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{16,100}',idem):raise ValueError('Stable original task key required')
 return dict(prompt=prompt,role='general',platform='general',slot='poster',size=size,confirmed=True,image_engine='gemini-personal-sunburst',gemini_trial_intent='paid',image_retention={'policy':'gateway-delivery-delete/1'})

class Client:
 def __init__(self,source,channel,account_secret=None,skill_key=None,device='unknown',origin=ORIGIN,allow_local_test=False):
  if not isinstance(source,str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{1,99}',source):raise ValueError('Stable Skill identifier required')
  if channel not in ('skillhub','workbuddy_skill','workbuddy_expert') or device not in ('desktop','mobile','cloud','unknown'):raise ValueError('Use actual channel/device')
  u=urlsplit(origin)
  local=allow_local_test and u.scheme=='http' and u.hostname=='127.0.0.1' and not u.username and not u.password and u.path in ('','/') and not u.query and not u.fragment
  if origin!=ORIGIN and not local:raise ValueError('Use the temporary gateway; local HTTP is test-only')
  if account_secret is not None and not re.fullmatch(r'[A-Za-z0-9_-]{43}',account_secret):raise ValueError('Invalid account credential format')
  if skill_key is not None:self.check_key(skill_key)
  self.origin=origin.rstrip('/');self.source=source;self.channel=channel;self.device=device;self.account_secret=account_secret;self.skill_key=skill_key;self.opener=urllib.request.build_opener(NoRedirect())
 @staticmethod
 def check_key(key):
  if not isinstance(key,str) or not re.fullmatch(r'mpskill_[0-9a-f]{32}_[A-Za-z0-9_-]{43}',key):raise ValueError('Invalid Skill credential format')
 def _call(self,path,body=None,auth='account',idem=None,binary=False):
  h={'X-Skill-Source':self.source,'X-Skill-Channel':self.channel,'X-Skill-Device':self.device}
  token=self.account_secret if auth=='account' else self.skill_key if auth=='skill' else None
  if auth!='none':
   if not token:raise ValueError('Restore the original runtime account/Skill credential first')
   h['Authorization']='Bearer '+token
  if body is not None:h['Content-Type']='application/json'
  if idem is not None:
   if not isinstance(idem,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{16,100}',idem):raise ValueError('Stable task key required')
   h['Idempotency-Key']=idem
  req=urllib.request.Request(self.origin+'/platform-api/gemini'+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
  limit=16*1024*1024 if binary else 2*1024*1024
  try:
   with self.opener.open(req,timeout=90 if body is not None and path=='/skill-jobs' else 15) as r:raw=r.read(limit+1)
  except urllib.error.HTTPError as e:raise GatewayError(e.code) from None
  except (urllib.error.URLError,TimeoutError,OSError):raise GatewayError(0) from None
  if len(raw)>limit:raise GatewayError(0)
  if binary:
   if not raw.startswith(b'\x89PNG\r\n\x1a\n'):raise GatewayError(0)
   return raw
  try:result=json.loads(raw)
  except (ValueError,UnicodeError):raise GatewayError(0) from None
  if not isinstance(result,dict):raise GatewayError(0)
  return result
 def health(self):return self._call('/health',auth='none')
 def plans(self):return self._call('/membership-api/plans',auth='none')
 def balance(self):return self._call('/balance')
 def quick_entry(self):
  if not self.account_secret:raise ValueError('Persist one original installation identity before opening entry')
  d=self._call('/quick-entry',{'install_secret':self.account_secret},auth='none')
  if 'url' in d:d={**d,'url':temporary_link(d['url'])}
  return d
 def entry_status(self):
  if not self.account_secret:raise ValueError('Original account identity required')
  return self._call('/quick-entry/status',{'install_secret':self.account_secret},auth='none')
 def membership_link(self):
  d=self._call('/membership-link',{})
  return {**d,'url':temporary_link(d['url'])}
 def bind_skill_key(self,save_private):
  """Caller supplies secure runtime storage, excluded from the package and repository."""
  if not callable(save_private):raise ValueError('Private persistence callback required')
  d=self._call('/skill-key',{})
  if d.get('state')!='ready' or not d.get('key'):raise ValueError('Account has no available paid Skill credential; inspect balance/payment state')
  self.check_key(d['key']);save_private(d['key']);self.skill_key=d['key']
  return self._call('/skill-key/bound',{'key':self.skill_key})
 def submit(self,body,idem):
  if not isinstance(body,dict) or body.get('confirmed') is not True:raise ValueError('Confirmed gateway task required')
  return self._call('/skill-jobs',body,auth='skill',idem=idem)
 def by_key(self,idem):
  if not isinstance(idem,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{16,100}',idem):raise ValueError('Original task key required')
  return self._call('/jobs/by-key/'+quote(idem,safe=''),auth='skill' if self.skill_key else 'account')
 @staticmethod
 def job_id(jid):
  try:
   if str(uuid.UUID(jid))!=jid:raise ValueError()
  except (ValueError,TypeError,AttributeError):raise ValueError('Original job UUID required') from None
  return jid
 def job(self,jid):return self._call('/jobs/'+self.job_id(jid),auth='skill' if self.skill_key else 'account')
 def image(self,jid):return self._call('/jobs/'+self.job_id(jid)+'/image',auth='skill' if self.skill_key else 'account',binary=True)

if __name__=='__main__':
 # Read-only public capability check. No credential arguments or automatic generation.
 print(json.dumps(Client('repository-image-client','skillhub',device='cloud').health(),ensure_ascii=False))
