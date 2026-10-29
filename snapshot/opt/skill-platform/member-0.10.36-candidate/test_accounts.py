import os,sys,json,secrets,tempfile,sqlite3,signal,hashlib,subprocess,time
from pathlib import Path
from contextlib import closing
HERE=Path(__file__).parent
os.environ['MYPLANESTORE_SCHEMA_DIR']='/opt/skill-platform/member-0.10.32-r2/schema'
sys.path.insert(0,'/opt/skill-platform/member-0.10.32-r2');import test_account_link_base as t
work=Path(tempfile.mkdtemp(prefix='account36-'))
for name,value in {'TEMU_DELIVERY_DB':work/'temu.db','MPS_EPHEMERAL_IMAGE_KEYS':work/'keys','SUNBURST_KEY_FILE':work/'no-provider-key'}.items():os.environ[name]=str(value)
(work/'clock').write_text('0');os.environ['PHONE_TEST_CLOCK']=str(work/'clock')
t.ENTRY=HERE/'test_runner.py';t.SCHEMA=Path(os.environ['MYPLANESTORE_SCHEMA_DIR']);t.PORT=18936
proc,db=t.start(work);P='/platform-api/gemini';count=0
def check(v,label):
 global count
 if not v:raise AssertionError(label)
 count+=1
def clear_limits():
 with closing(sqlite3.connect(db)) as c,c:c.execute('DELETE FROM album_login_limits')
def entry(secret=None,product='gemini'):
 secret=secret or secrets.token_urlsafe(32);st,r=t.skill('POST','/platform-api/'+product+'/quick-entry',{'install_secret':secret});check(st==200 and r['status']=='registration' and '/'+product+'/register/' in r['url'],'generic old-compatible entry');return secret,t.entry_of(r)
def skill(path,secret,body=None,product='gemini'):
 import urllib.request,urllib.error
 data=json.dumps(body).encode() if body is not None else None
 req=urllib.request.Request('http://127.0.0.1:18936/platform-api/'+product+path,data=data,headers={'Authorization':'Bearer '+secret,**({'Content-Type':'application/json'} if data else {})})
 try:r=urllib.request.urlopen(req,timeout=15)
 except urllib.error.HTTPError as e:r=e
 return r.status,json.loads(r.read())
try:
 secret,e=entry();b=t.Browser();phone='13800000000'
 payload={'entry':e,'phone':phone,'accepted':True}
 check(b.call('POST',P+'/phone-entry-prepare',dict(payload,accepted=False))[0]==400,'phone consent separate')
 st,draft=b.call('POST',P+'/phone-entry-prepare',payload);check(st==200 and len(draft['key_once'])==36 and draft['key_once'].endswith('3456'),'server random KEY')
 with closing(sqlite3.connect(db)) as c,c:check(c.execute('SELECT count(*) FROM users').fetchone()[0]==0,'no user until saved and confirmed')
 confirm=dict(payload,key=draft['key_once'],proof=draft['proof'],expires=draft['expires'])
 st,response=b.call('POST',P+'/phone-entry-register',confirm);check(st==200,'register')
 st,data=skill('/register',secret,{'install_secret':secret,'accepted':True});check(st==200 and data['created'] is False,'existing skill registration contract')
 st,acct=b.call('GET',P+'/membership-api/account');check(st==200,'account cookie')
 label=acct['account_label'];key=draft['key_once']
 with closing(sqlite3.connect(db)) as c,c:
  uid=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(hashlib.sha256(secret.encode()).hexdigest(),)).fetchone()[0]
  c.execute('UPDATE users SET balance=7 WHERE id=?',(uid,))
  c.execute("INSERT INTO member_orders(id,user_id,plan,amount_fen,units,status,created,product) VALUES('synthetic-order',?,'shared_permanent_49',4900,100,'pending',?,'gemini-image-assistant')",(uid,int(time.time())))
 st,delivery=skill('/phone-key-delivery',secret,{});check(st==200 and delivery['key']==key and delivery['delivery_scope']=='current_install_identity','scoped private delivery')
 check(skill('/phone-key-delivery',secret,{})[1]['delivery_id']==delivery['delivery_id'],'same delivery retry')
 check(skill('/phone-key-ack',secret,{'delivery_id':delivery['delivery_id'],'key_sha256':'0'*64})[0]==409,'wrong ACK')
 ack={'delivery_id':delivery['delivery_id'],'key_sha256':hashlib.sha256(key.encode()).hexdigest()}
 check(skill('/phone-key-ack',secret,ack)[0]==200,'ACK')
 check(skill('/phone-key-ack',secret,ack)[0]==200,'ACK idempotent')
 check(b.call('POST',P+'/phone-entry-register',confirm)[0]==200,'lost response retry')
 check(skill('/phone-key-delivery',secret,{})[1]['available'] is False,'retry does not renew ACKed delivery')
 clear_limits();fresh,e2=entry();b2=t.Browser();login={'entry':e2,'phone':phone,'key':key,'accepted':True}
 check(b2.call('POST',P+'/phone-entry-prepare',login)[0]==409,'same phone no duplicate registration')
 check(b2.call('POST',P+'/phone-entry-login',dict(login,key='wrong'))[0]==401,'wrong KEY')
 check(b2.call('POST',P+'/phone-entry-login',login)[0]==200,'new conversation restores UID')
 st,a=b2.call('GET',P+'/membership-api/account');check(a['account_label']==label and a['shared_uses']==7,'old balance restored')
 check(skill('/register',fresh,{'install_secret':fresh,'accepted':True})[1]['created'] is False,'new conversation no grant')
 new=skill('/phone-key-delivery',fresh,{})[1];check(new['available'] and new['key']==key and new['delivery_id']!=delivery['delivery_id'],'separate install delivery after old ACK')
 check(skill('/phone-key-ack',fresh,ack)[0]==409,'other install ACK rejected')
 check(skill('/phone-key-delivery',fresh,{})[1]['available'],'wrong ACK preserves new payload')
 clear_limits();temu,e3=entry(product='temu');b3=t.Browser();tl=dict(login,entry=e3)
 check(b3.call('POST','/platform-api/temu/phone-entry-login',tl)[0]==200,'Temu restores same UID')
 check(skill('/balance',temu,product='temu')[1]['shared_uses']==7,'shared balance not moved')
 with closing(sqlite3.connect(db)) as c,c:before=c.execute('SELECT count(*) FROM gemini_personal_trials').fetchone()[0];trial=c.execute('SELECT count(*) FROM temu_enterprise_trials').fetchone()[0]
 clear_limits();temu2,e4=entry(product='temu');b4=t.Browser();check(b4.call('POST','/platform-api/temu/phone-entry-login',dict(login,entry=e4))[0]==200,'Temu second device')
 with closing(sqlite3.connect(db)) as c,c:check(c.execute('SELECT count(*) FROM gemini_personal_trials').fetchone()[0]==before and c.execute('SELECT count(*) FROM temu_enterprise_trials').fetchone()[0]==trial,'no duplicate trial grant')
 clear_limits();standalone=t.Browser();st,l=standalone.call('POST',P+'/phone-login-entry',{});check(st==200,'website standalone entry');check(standalone.call('POST',P+'/phone-entry-login',dict(login,entry=t.entry_of(l)))[0]==200,'standalone website login')
 check(standalone.call('GET',P+'/membership-api/account')[1]['account_label']==label,'standalone original UID')
 other=secrets.token_urlsafe(32);check(t.skill('POST',P+'/register',{'install_secret':other,'accepted':True})[0]==200,'other used identity')
 clear_limits();_,ce=entry(other);check(t.Browser().call('POST',P+'/phone-entry-login',dict(login,entry=ce))[0]==409,'other UID no overwrite')
 with closing(sqlite3.connect(db)) as c,c:c.execute('UPDATE sessions SET expires=1 WHERE hash=?',(hashlib.sha256(other.encode()).hexdigest(),))
 clear_limits();_,ce=entry(other);check(t.Browser().call('POST',P+'/phone-entry-login',dict(login,entry=ce))[0]==409,'expired session still protects original identity')
 foreign=t.Browser(origin='https://invalid.example');check(foreign.call('POST',P+'/phone-login-entry',{})[0]==403,'foreign origin denied')
 with closing(sqlite3.connect(db)) as c,c:
  check(c.execute('SELECT count(*) FROM album_phone_keys').fetchone()[0]==1,'one phone binding')
  check(c.execute('SELECT count(*) FROM users').fetchone()[0]==2,'only owner plus explicitly created other user')
  check(c.execute('SELECT user_id FROM member_orders WHERE id=?',('synthetic-order',)).fetchone()[0]==uid,'order ownership unchanged')
  raw=Path(db).read_bytes();check(key.encode() not in raw and phone.encode() not in raw,'no plaintext credentials in DB')
 # Encrypted per-install delivery survives service restart.
 launch_env=dict(x.split('=',1) for x in Path('/proc/'+str(proc.pid)+'/environ').read_bytes().decode().strip(chr(0)).split(chr(0)));command=[x.decode() for x in Path('/proc/'+str(proc.pid)+'/cmdline').read_bytes().split(bytes([0])) if x]
 os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10);proc=subprocess.Popen(command,env=launch_env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 for _ in range(80):
  try:
   import urllib.request;urllib.request.urlopen('http://127.0.0.1:18936'+P+'/health',timeout=1);break
  except Exception:time.sleep(.1)
 restored=skill('/phone-key-delivery',fresh,{})[1];check(restored.get('key')==key and restored['delivery_id']==new['delivery_id'],'restart preserves scoped delivery')
 with closing(sqlite3.connect(db)) as c,c:c.execute('UPDATE album_key_delivery_targets SET expires=1 WHERE identity_hash=?',(hashlib.sha256(fresh.encode()).hexdigest(),))
 check(skill('/phone-key-delivery',fresh,{})[1]['state']=='expired','expired target inaccessible')
 with closing(sqlite3.connect(db)) as c,c:check(c.execute('SELECT ciphertext FROM album_key_delivery_targets WHERE identity_hash=?',(hashlib.sha256(fresh.encode()).hexdigest(),)).fetchone()[0] is None,'expired ciphertext purged')
 clear_limits();unused,expired=entry();(work/'clock').write_text('301')
 check(t.Browser().call('POST',P+'/phone-entry-login',dict(login,entry=expired))[0]==401,'expired entry denied');(work/'clock').write_text('0')
 # Existing album-created KEY remains valid and is not renamed/reset.
 clear_limits();legacy=secrets.token_urlsafe(32);st,le=t.skill('POST',P+'/album-entry',{'install_secret':legacy});check(st==200,'legacy album entry preserved')
 oldbrowser=t.Browser();st,old=oldbrowser.call('POST',P+'/album-register',{'entry':t.entry_of(le),'phone':'13800000000','accepted':True});check(st==200 and len(old['key_once'])==20,'legacy KEY preserved')
 clear_limits();ls,le=entry();newbrowser=t.Browser();check(newbrowser.call('POST',P+'/phone-entry-login',{'entry':le,'phone':'13800000000','key':old['key_once'],'accepted':True})[0]==200,'legacy KEY restores through generic login')
 check(skill('/phone-key-delivery',ls,{})[1]['key']==old['key_once'],'legacy KEY delivered without rotation')
 # Two confirmations of one saved KEY create one user and one delivery.
 clear_limits();cs,ce=entry();cb=t.Browser();base={'entry':ce,'phone':'13800000000','accepted':True};st,cd=cb.call('POST',P+'/phone-entry-prepare',base);check(st==200,'concurrent preparation')
 complete=dict(base,key=cd['key_once'],proof=cd['proof'],expires=cd['expires'])
 from concurrent.futures import ThreadPoolExecutor
 with ThreadPoolExecutor(max_workers=2) as pool:answers=list(pool.map(lambda _:t.Browser().call('POST',P+'/phone-entry-register',complete),range(2)))
 check(all(x[0]==200 for x in answers) and answers[0][1]['delivery_id']==answers[1][1]['delivery_id'],'concurrent confirmation and response retry')
 with closing(sqlite3.connect(db)) as c,c:check(c.execute('SELECT count(*) FROM users').fetchone()[0]==4,'no duplicate wallet after concurrent or cross-device flows')
 clear_limits();bs,be=entry();wrong={'entry':be,'phone':phone,'key':'wrong','accepted':True};browser=t.Browser();statuses=[browser.call('POST',P+'/phone-entry-login',wrong)[0] for _ in range(11)]
 check(statuses[0]==401 and statuses[-1]==429,'wrong KEY persisted rate limit')
 # Binding an already used, expired-session account must retain its original wallet.
 clear_limits()
 with closing(sqlite3.connect(db)) as c,c:
  original_other=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(hashlib.sha256(other.encode()).hexdigest(),)).fetchone()[0]
  c.execute('UPDATE users SET balance=3 WHERE id=?',(original_other,))
 _,oe=entry(other);ob=t.Browser();op={'entry':oe,'phone':'13800000000','accepted':True};st,od=ob.call('POST',P+'/phone-entry-prepare',op);check(st==200,'existing account binding prepare')
 check(ob.call('POST',P+'/phone-entry-register',dict(op,key=od['key_once'],proof=od['proof'],expires=od['expires']))[0]==200,'existing account supplemental binding')
 check(skill('/balance',other)[1]['shared_uses']==3,'existing balance retained')
 with closing(sqlite3.connect(db)) as c,c:check(c.execute('SELECT count(*) FROM users').fetchone()[0]==4,'supplemental binding creates no user')
 # Verify unattended credential expiry, without triggering a delivery read.
 with closing(sqlite3.connect(db)) as c,c:c.execute('UPDATE album_key_delivery_targets SET expires=1 WHERE identity_hash=?',(hashlib.sha256(temu2.encode()).hexdigest(),))
 deadline=time.monotonic()+35;purged=False
 while time.monotonic()<deadline:
  with closing(sqlite3.connect(db)) as c,c:purged=c.execute('SELECT ciphertext FROM album_key_delivery_targets WHERE identity_hash=?',(hashlib.sha256(temu2.encode()).hexdigest(),)).fetchone()[0] is None
  if purged:break
  time.sleep(.25)
 check(purged,'automatic encrypted delivery expiry')
 print(json.dumps({'passed':count,'production':False,'scope':'isolated real service chain, synthetic accounts/orders, no provider/payment'}))
finally:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
