"""Generic phone identity binding over existing wallet. No quota or settlement writes."""
import hashlib,hmac,json,os,secrets,threading,time
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
LOCK=threading.RLock()

def install(server,shared):
 previous=shared.handler
 def handler(store,validator=None):
  parent=previous(store,validator)
  from album_accounts import PhoneKeys
  keys=PhoneKeys(store,server,os.environ.get('IMAGE_TRIAL_HMAC_KEY',''))
  master=keys.master
  def proof(uid,ph,key,expiry):
   return hmac.new(master,('phone-bind-v1|'+uid+'|'+ph+'|'+key+'|'+str(expiry)).encode(),hashlib.sha256).hexdigest()
  def bound(uid):
   with store.connect() as c:return c.execute('SELECT * FROM album_phone_keys WHERE user_id=?',(uid,)).fetchone()
  deliveries={}
  class Handler(parent):
   def run_request(self):
    path=urlsplit(self.path).path;parts=path.split('/')
    if len(parts)!=4 or parts[1]!='platform-api' or parts[2] not in ('gemini','temu') or parts[3] not in ('phone-status','phone-prepare','phone-bind','phone-key-delivery'):
     return super().run_request()
    try:
     self.connection.settimeout(15)
     route=parts[3]
     if route=='phone-key-delivery':
      if self.command!='POST':raise server.Problem(405,'请求方式无效')
      secret=self.headers.get('Authorization','').removeprefix('Bearer ')
      uid=store.user(secret)
      token=server.digest(secret)
      with LOCK:
       now=time.time()
       for k in list(deliveries):
        if deliveries[k]['expires']<now:del deliveries[k]
       d=deliveries.get(uid)
       if not d:return self.send(200,{'available':False,'phone_bound':bool(bound(uid))})
       return self.send(200,{'available':True,'key':d['key'],'expires_in':max(0,int(d['expires']-now)),'storage':'private_local_only'})
     cookie=SimpleCookie(self.headers.get('Cookie','')).get('platform_member')
     uid=store.membership.web_user(cookie.value if cookie else '')
     if route=='phone-status':
      if self.command!='GET':raise server.Problem(405,'请求方式无效')
      return self.send(200,{'phone_bound':bool(bound(uid))})
     if self.command!='POST':raise server.Problem(405,'请求方式无效')
     if self.headers.get('Origin')!='https://myplanestore.com' or self.headers.get('X-Membership-Request')!='1':raise server.Problem(403,'请从本站操作')
     size=int(self.headers.get('Content-Length','0'))
     if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式错误')
     body=json.loads(self.rfile.read(size))
     if not isinstance(body,dict) or body.get('accepted') is not True:raise server.Problem(400,'请同意手机号用于账户关联')
     ip=self.headers.get('X-Real-IP',self.client_address[0]) if self.client_address[0]=='127.0.0.1' else self.client_address[0]
     keys.limit('generic-ip:'+ip[:64]);ph,last4=keys.phone(body.get('phone'));keys.limit('generic-phone:'+ph)
     with LOCK:
      with store.connect() as c:
       own=c.execute('SELECT * FROM album_phone_keys WHERE user_id=?',(uid,)).fetchone()
       other=c.execute('SELECT * FROM album_phone_keys WHERE phone_hash=?',(ph,)).fetchone()
      if route=='phone-prepare':
       if own or other:raise server.Problem(409,'号码或原账户已绑定，请沿原凭证核对；不重置随机码、不合并余额')
       key=secrets.token_urlsafe(24)+last4;expiry=int(time.time())+600
       return self.send(200,{'key_once':key,'expires':expiry,'proof':proof(uid,ph,key,expiry),'phone_verified':False})
      key=body.get('key');expiry=body.get('expires');sig=body.get('proof')
      if not isinstance(key,str) or not 32<=len(key)<=128 or type(expiry)is not int or not time.time()<expiry<=time.time()+600 or not isinstance(sig,str) or not hmac.compare_digest(sig,proof(uid,ph,key,expiry)):
       raise server.Problem(401,'保存确认已过期，请重新准备；不会重置已绑定随机码')
      if own:
       if own['phone_hash']!=ph or not hmac.compare_digest(keys.hash_key(key,own['salt']),own['key_hash']):raise server.Problem(409,'原账户已绑定，不替换身份或余额')
      else:
       if other:raise server.Problem(409,'该号码已绑定其他账户，不自动合并余额')
       salt=secrets.token_bytes(16).hex()
       with store.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('INSERT INTO album_phone_keys VALUES(?,?,?,?,?,?)',(ph,uid,last4,salt,keys.hash_key(key,salt),int(time.time())))
      deliveries[uid]={'key':key,'expires':time.time()+600}
      return self.send(200,{'ok':True,'phone_bound':True,'skill_delivery_ready':True})
    except server.Problem as e:return self.send(e.status,{'error':e.message})
    except (ValueError,TypeError):return self.send(400,{'error':'参数无效'})
    except Exception:return self.send(503,{'error':'绑定暂不可用，请保留原账户及随机码，不重复注册'})
   do_GET=run_request
   do_POST=run_request
  return Handler
 shared.handler=handler
