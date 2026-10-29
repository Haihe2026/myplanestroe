"""Generic phone identity and per-install encrypted credential delivery; original ledgers untouched."""
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlsplit,parse_qs
import hashlib,hmac,json,os,re,secrets,time,threading
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import phone_binding
LOCK=phone_binding.LOCK
PRODUCTS=('gemini','temu')
BASE='https://myplanestore.com'
def install(server,shared,parent_handler=None):
 previous=shared.handler if parent_handler is None else lambda store,validator=None:parent_handler
 def handler(store,validator=None):
  parent=previous(store,validator)
  from album_accounts import PhoneKeys
  keys=PhoneKeys(store,server,os.environ.get('IMAGE_TRIAL_HMAC_KEY',''))
  cipher=AESGCM(hmac.new(keys.master,b'mps-phone-target-delivery-v1',hashlib.sha256).digest())
  entries=store.registration_entries;original_prepare=entries.prepare;completed={}
  with store.connect() as c:c.execute('CREATE TABLE IF NOT EXISTS album_key_delivery_targets(user_id TEXT NOT NULL,identity_hash TEXT NOT NULL,delivery_id TEXT UNIQUE NOT NULL,nonce BLOB,ciphertext BLOB,key_digest TEXT NOT NULL,created INTEGER NOT NULL,expires INTEGER NOT NULL,acknowledged INTEGER,PRIMARY KEY(user_id,identity_hash))')
  def cleanup_deliveries():
   while True:
    try:
     with store.connect() as c:
      for table in ('album_key_deliveries','album_key_delivery_targets'):
       c.execute('UPDATE '+table+' SET nonce=NULL,ciphertext=NULL WHERE expires<=? AND ciphertext IS NOT NULL',(int(time.time()),))
    except Exception:pass # Never log credential contents; request paths also enforce expiry.
    time.sleep(30)
  threading.Thread(target=cleanup_deliveries,name='phone-key-expiry',daemon=True).start()
  def account(ph=None,uid=None):
   with store.connect() as c:return c.execute('SELECT * FROM album_phone_keys WHERE '+('phone_hash=?' if ph else 'user_id=?'),(ph or uid,)).fetchone()
  def entry(product,secret,ip):
   if product not in PRODUCTS or not isinstance(secret,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',secret):raise server.Problem(400,'请从原账户入口重新打开')
   keys.limit('universal-entry:'+ip)
   with entries.lock:
    now=time.time();entries.pending={k:v for k,v in entries.pending.items() if v['expires']>now}
    if len(entries.pending)>=2048 or sum(v['ip']==ip for v in entries.pending.values())>=12:raise server.Problem(429,'入口请求较多，请稍后继续')
    ticket=secrets.token_urlsafe(32);entries.pending[server.digest(ticket)]={'secret':secret,'ip':ip,'product':product,'expires':now+300}
   return {'status':'registration','url':BASE+'/membership/'+product+'/register/#entry='+ticket,'expires_in':300,'phone_binding_required':True}
  def prepare(product,secret,ip):
   try:uid=store.user(secret)
   except server.Problem as e:
    if e.status!=401:raise
    return entry(product,secret,ip)
   if account(uid=uid):return original_prepare(product,secret,ip)
   return entry(product,secret,ip)
  entries.prepare=prepare
  def row_for(product,ticket):
   if not isinstance(ticket,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',ticket):raise server.Problem(401,'请重新打开账户入口')
   digest=server.digest(ticket);now=time.time()
   for k in list(completed):
    if completed[k]['expires']<=now:del completed[k]
   row=entries.pending.get(digest) or completed.get(digest)
   if not row or row['expires']<=now or row['product']!=product:raise server.Problem(401,'账户入口已过期，请重新打开')
   return row
  def signature(ticket,ph,key,expiry):return hmac.new(keys.master,('universal-phone-v1|'+ticket+'|'+ph+'|'+key+'|'+str(expiry)).encode(),hashlib.sha256).hexdigest()
  def outbox(uid,secret):
   identity=server.digest(secret)
   with store.connect() as c:
    c.execute('UPDATE album_key_delivery_targets SET nonce=NULL,ciphertext=NULL WHERE expires<=? AND ciphertext IS NOT NULL',(int(time.time()),))
    return c.execute('SELECT * FROM album_key_delivery_targets WHERE user_id=? AND identity_hash=?',(uid,identity)).fetchone()
  def queue(uid,secret,key,renew=False):
   old=outbox(uid,secret)
   if old and not renew:return old
   nonce=secrets.token_bytes(12);identity=server.digest(secret);now=int(time.time());payload=cipher.encrypt(nonce,key.encode(),(uid+'|'+identity).encode())
   with store.connect() as c:c.execute('INSERT OR REPLACE INTO album_key_delivery_targets VALUES(?,?,?,?,?,?,?,?,NULL)',(uid,identity,secrets.token_urlsafe(24),nonce,payload,hashlib.sha256(key.encode()).hexdigest(),now,now+86400))
   return outbox(uid,secret)
  def session(product,row,ticket):
   if server.digest(ticket) in entries.pending:return entries.confirm(product,ticket,True)
   uid=store.user(row['secret']);handoff=store.membership.handoff(uid);token=parse_qs(urlsplit(handoff['url']).fragment)['ticket'][0]
   return store.membership.redeem(token)
  class Handler(parent):
   def run_request(self):
    path=urlsplit(self.path).path;parts=path.split('/')
    routes=('phone-login-entry','phone-entry-prepare','phone-entry-register','phone-entry-login','phone-key-delivery','phone-key-ack')
    if len(parts)!=4 or parts[1]!='platform-api' or parts[2] not in PRODUCTS or parts[3] not in routes:return super().run_request()
    product,route=parts[2:]
    try:
     self.connection.settimeout(15)
     if self.command!='POST':raise server.Problem(405,'请使用POST')
     if route in ('phone-key-delivery','phone-key-ack'):
      secret=self.headers.get('Authorization','').removeprefix('Bearer ');uid=store.user(secret);d=outbox(uid,secret)
      if d is None:return super().run_request() # Preserve 0.10.34 existing-account delivery contract.
      if route=='phone-key-delivery':
       if d['ciphertext'] is None:return self.send(200,{'available':False,'phone_bound':bool(account(uid=uid)),'state':'acknowledged' if d['acknowledged'] else 'expired','requires_saved_copy':True})
       key=cipher.decrypt(d['nonce'],d['ciphertext'],(uid+'|'+server.digest(secret)).encode()).decode()
       return self.send(200,{'available':True,'key':key,'delivery_id':d['delivery_id'],'expires_at':d['expires'],'expires_in':max(0,d['expires']-int(time.time())),'ack_required':True,'contract_version':'phone-key-delivery/1','delivery_scope':'current_install_identity','storage':'private_local_only'})
     else:
      if self.headers.get('Origin')!=BASE or self.headers.get('X-Membership-Request')!='1':raise server.Problem(403,'请从本站操作')
     size=int(self.headers.get('Content-Length','0'))
     if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise server.Problem(400,'请求格式错误')
     body=json.loads(self.rfile.read(size))
     if not isinstance(body,dict):raise server.Problem(400,'请求格式错误')
     if route=='phone-key-ack':
      if body.get('delivery_id')!=d['delivery_id'] or not isinstance(body.get('key_sha256'),str) or not hmac.compare_digest(body['key_sha256'],d['key_digest']):raise server.Problem(409,'领取确认不匹配')
      with store.connect() as c:
       changed=c.execute('UPDATE album_key_delivery_targets SET nonce=NULL,ciphertext=NULL,acknowledged=coalesce(acknowledged,?) WHERE user_id=? AND identity_hash=? AND delivery_id=?',(int(time.time()),uid,server.digest(secret),body['delivery_id']))
       if changed.rowcount!=1:raise server.Problem(409,'领取记录已更新，请重新核对，不删除新的交付')
      return self.send(200,{'ok':True,'acknowledged':True,'delivery_id':d['delivery_id']})
     ip=self.headers.get('X-Real-IP',self.client_address[0]) if self.client_address[0]=='127.0.0.1' else self.client_address[0]
     if route=='phone-login-entry':return self.send(200,entry(product,secrets.token_urlsafe(32),ip[:64]))
     if body.get('accepted') is not True:raise server.Problem(400,'请同意手机号用于账户关联及登录')
     keys.limit('generic-phone-ip:'+ip[:64]);ph,last4=keys.phone(body.get('phone'));keys.limit('generic-phone:'+ph)
     ticket=body.get('entry')
     with LOCK,entries.lock:
      row=row_for(product,ticket);existing=account(ph=ph)
      try:current=store.user(row['secret'])
      except server.Problem as e:
       if e.status!=401:raise
       with store.connect() as c:
        claim=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(server.digest(row['secret']),)).fetchone()
        current=claim['user_id'] if claim else None
      if route=='phone-entry-prepare':
       if existing or (current and account(uid=current)):raise server.Problem(409,'号码或原账户已绑定，请使用原手机号和KEY登录；不重置或合并余额')
       key=secrets.token_urlsafe(24)+last4;expiry=min(int(row['expires']),int(time.time())+300)
       return self.send(200,{'key_once':key,'expires':expiry,'proof':signature(ticket,ph,key,expiry),'phone_verified':False})
      key=body.get('key')
      if not isinstance(key,str) or not 1<=len(key)<=128:raise server.Problem(401,'手机号或KEY不匹配')
      if route=='phone-entry-login':
       salt=existing['salt'] if existing else '00'*16;actual=keys.hash_key(key,salt)
       if not existing or not hmac.compare_digest(actual,existing['key_hash']):raise server.Problem(401,'手机号或KEY不匹配')
       uid=existing['user_id']
       if current and current!=uid:raise server.Problem(409,'当前对话已有另一个账户，请保留原凭证并核对；不覆盖身份或合并余额')
       with store.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        for gateway in store.legacy:
         old=store.old_identity(gateway,row['secret'])
         if old:
          linked=c.execute('SELECT user_id FROM legacy_links WHERE product=? AND legacy_uid=?',(gateway,old)).fetchone()
          if linked and linked[0]!=uid:raise server.Problem(409,'原凭证已有其他账户，不合并余额')
        c.execute('INSERT OR IGNORE INTO trial_claims VALUES(?,?,?)',(server.digest(row['secret']),uid,int(time.time())))
       store.register_product(product,row['secret'],row['ip'],True)
      else:
       expiry=body.get('expires');sig=body.get('proof')
       if type(expiry)is not int or not time.time()<expiry<=time.time()+300 or not isinstance(sig,str) or not hmac.compare_digest(sig,signature(ticket,ph,key,expiry)):raise server.Problem(401,'保存确认已过期，请重新准备；不重置既有KEY')
       if existing:
        if not current or existing['user_id']!=current or not hmac.compare_digest(keys.hash_key(key,existing['salt']),existing['key_hash']):raise server.Problem(409,'号码已绑定，请使用原KEY登录')
       else:
        if current and account(uid=current):raise server.Problem(409,'原账户已有号码，不替换KEY')
        store.register_product(product,row['secret'],row['ip'],True);uid=store.user(row['secret'])
        salt=secrets.token_bytes(16).hex()
        with store.connect() as c:c.execute('INSERT INTO album_phone_keys VALUES(?,?,?,?,?,?)',(ph,uid,last4,salt,keys.hash_key(key,salt),int(time.time())))
      uid=store.user(row['secret'])
      repeated=server.digest(ticket) in completed
      queued=queue(uid,row['secret'],key,renew=route=='phone-entry-login' and not repeated)
      cookie=session(product,row,ticket)
      completed[server.digest(ticket)]=dict(row,expires=min(row['expires'],time.time()+300))
      return self.send(200,{'ok':True,'phone_bound':True,'linked_existing':route=='phone-entry-login','skill_delivery_ready':queued['ciphertext'] is not None,'delivery_id':queued['delivery_id'],'delivery_expires_at':queued['expires']},cookie='platform_member='+cookie+'; HttpOnly; Secure; SameSite=Strict; Path=/platform-api/; Max-Age=1800')
    except server.Problem as e:return self.send(e.status,{'error':e.message})
    except (ValueError,TypeError):return self.send(400,{'error':'参数无效，请核对后重试'})
    except Exception:return self.send(503,{'error':'账户操作暂不可用，请保留原凭证，不重复创建账户'})
   do_POST=run_request
   do_GET=run_request
  return Handler
 if parent_handler is None:shared.handler=handler
 return handler
