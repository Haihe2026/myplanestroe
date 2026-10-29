import os,sys,json,tempfile,secrets,sqlite3,signal,time,hashlib,urllib.request,urllib.error
from pathlib import Path
from contextlib import closing
from urllib.parse import urlsplit,parse_qs
HERE=Path(__file__).parent
os.environ['MYPLANESTORE_SCHEMA_DIR']='/opt/skill-platform/member-0.10.32-r2/schema'
sys.path.insert(0,'/opt/skill-platform/member-0.10.32-r2');import test_account_link_base as t
from consent_digest import task_digest
work=Path(tempfile.mkdtemp(prefix='consents38-'))
for k,v in {'TEMU_DELIVERY_DB':work/'temu.db','MPS_EPHEMERAL_IMAGE_KEYS':work/'keys','SUNBURST_KEY_FILE':work/'no-key','FIXTURE_CALLS':work/'calls'}.items():os.environ[k]=str(v)
t.ENTRY=HERE/'fixture_runner.py';t.SCHEMA=Path(os.environ['MYPLANESTORE_SCHEMA_DIR']);t.PORT=18938
proc,db=t.start(work);P='/platform-api/gemini';count=0
owner=secrets.token_urlsafe(32);other=secrets.token_urlsafe(32)
def check(v,label):
 global count
 if not v:raise AssertionError(label)
 count+=1
def req(method,path,body=None,secret=None,idem=None,product='gemini'):
 data=json.dumps(body).encode() if body is not None else None
 headers={'Authorization':'Bearer '+(secret or owner)}
 if body is not None:headers['Content-Type']='application/json'
 if idem:headers['Idempotency-Key']=idem
 q=urllib.request.Request('http://127.0.0.1:18938/platform-api/'+product+path,data=data,headers=headers,method=method)
 try:r=urllib.request.urlopen(q,timeout=15)
 except urllib.error.HTTPError as e:r=e
 raw=r.read();return r.status,json.loads(raw) if r.headers.get('Content-Type','').startswith('application/json') else raw
V='photo-consent-2026-10-23-v1'
body={'prompt':'Create an illustration','confirmed':True,'role':'general','platform':'general','slot':'poster','size':'1024x1024','image_engine':'gemini-personal-sunburst','gemini_trial_intent':'paid','image_retention':{'policy':'gateway-delivery-delete/1'}}
def create(idem='consent-task-fixture-0001',payload=None,**extra):
 payload=payload or body;data={'task_digest':task_digest('gemini',idem,payload),'idempotency_key':idem,'policy_version':V,**extra};return req('POST','/photo-consents',data)
def token(row):return parse_qs(urlsplit(row['url']).fragment)['consent'][0]
def browser(secret):
 b=t.Browser();st,link=req('POST','/membership-link',{},secret=secret);check(st==200,'membership link');ticket=parse_qs(urlsplit(link['url']).fragment)['ticket'][0];check(b.call('POST',P+'/membership-api/redeem',{'ticket':ticket})[0]==200,'browser session');return b
try:
 for s in [owner,other]:check(t.skill('POST',P+'/register',{'install_secret':s,'accepted':True})[0]==200,'registered synthetic identity')
 b=browser(owner);foreign_owner=browser(other)
 st,c=create();check(st==200 and c['state']=='pending' and c['expires_in']<=900,'create without photos')
 check(create()[1]['url']==c['url'],'stable pending URL retry')
 cid=c['id'];ticket=token(c)
 check(req('GET','/photo-consents/'+cid,secret=other)[0]==404,'owner query isolation')
 check(req('GET','/photo-consents/'+cid)[1]['state']=='pending','pending query')
 anon=t.Browser();check(anon.call('POST',P+'/photo-consent-view',{'ticket':ticket})[1]['account_verified'] is False,'no browser session recoverable')
 choose={'ticket':ticket,'accepted':True,'policy_version':V}
 check(anon.call('POST',P+'/photo-consent-decision',choose)[0]==403,'ticket alone cannot approve')
 check(foreign_owner.call('POST',P+'/photo-consent-decision',choose)[0]==403,'wrong browser account cannot approve')
 foreign=t.Browser(origin='https://invalid.example');foreign.jar=b.jar.copy();check(foreign.call('POST',P+'/photo-consent-decision',choose)[0]==403,'CSRF origin')
 check(b.call('POST',P+'/photo-consent-decision',dict(choose,policy_version='wrong'))[0]==409,'policy binding')
 check(b.call('POST',P+'/photo-consent-decision',{'ticket':ticket,'policy_version':V})[0]==400,'no default consent')
 fake=dict(body,photo_consent={'id':cid,'receipt':'0'*64});check(req('POST','/jobs',fake,idem='consent-task-fixture-0001')[0]==409,'cannot execute before approval')
 check(b.call('POST',P+'/photo-consent-view',{'ticket':ticket})[1]['account_verified'],'same UID browser')
 check(b.call('POST',P+'/photo-consent-decision',choose)[0]==200,'checkbox approval')
 check(b.call('POST',P+'/photo-consent-decision',choose)[0]==200,'decision retry')
 st,approved=req('GET','/photo-consents/'+cid);check(st==200 and approved['state']=='approved' and len(approved['receipt'])==64,'private receipt')
 payload=dict(body,photo_consent={'id':cid,'receipt':approved['receipt']})
 check(req('POST','/jobs',dict(payload,prompt='changed'),idem='consent-task-fixture-0001')[0]==409,'changed task blocked')
 check(req('POST','/jobs',payload,idem='consent-task-fixture-other')[0]==409,'different idem blocked')
 check(req('POST','/jobs',payload,secret=other,idem='consent-task-fixture-0001')[0]==409,'different account blocked')
 check(req('POST','/jobs',payload,product='temu',idem='consent-task-fixture-0001')[0]==409,'different gateway blocked')
 check(req('POST','/jobs',payload,idem='consent-task-fixture-0001')[0]==402,'existing zero balance check')
 check(req('GET','/photo-consents/'+cid)[1]['state']=='approved','402 does not consume')
 with closing(sqlite3.connect(db)) as con,con:
  uid=con.execute('SELECT user_id FROM trial_claims WHERE hash=?',(hashlib.sha256(owner.encode()).hexdigest(),)).fetchone()[0]
  con.execute('UPDATE users SET balance=2 WHERE id=?',(uid,))
  con.execute('INSERT INTO skill_credentials(user_id,id,nonce,created) VALUES(?,?,?,?)',(uid,secrets.token_hex(16),secrets.token_hex(32),int(time.time())))
 st,key=req('POST','/skill-key',{});check(st==200 and 'key' in key,'paid fixture key');private=key['key'];check(req('POST','/skill-key/bound',{'key':private})[1]['bound'],'paid bound')
 st,job=req('POST','/skill-jobs',payload,secret=private,idem='consent-task-fixture-0001');check(st==200 and job['status']=='succeeded','consent with paid private key generation')
 used=req('GET','/photo-consents/'+cid)[1];check(used['state']=='used' and used['job_id']==job['id'],'atomic consume on original job')
 st,replay=req('POST','/skill-jobs',payload,secret=private,idem='consent-task-fixture-0001');check(st==200 and replay.get('replayed') and replay['id']==job['id'],'same task replay')
 check(len((work/'calls').read_text().splitlines())==1,'provider once')
 st,image=req('GET','/jobs/'+job['id']+'/image');check(st==200 and image.startswith(b'\x89PNG'),'original download')
 check(req('POST','/jobs/'+job['id']+'/delivery-confirm',{'confirmed':True,'image_sha256':hashlib.sha256(image).hexdigest()})[0]==200,'existing delivery cleanup unchanged')
 # Rejection is explicit and does not silently reopen.
 st,d=create('consent-task-fixture-decline');dt=token(d)
 check(b.call('POST',P+'/photo-consent-decision',{'ticket':dt,'accepted':False,'policy_version':V})[1]['state']=='declined','reject')
 check(create('consent-task-fixture-decline')[1]['state']=='declined','no automatic re-open')
 st,restarted=create('consent-task-fixture-decline',restart=True);check(st==200 and token(restarted)!=dt,'explicit restart rotates ticket')
 check(b.call('POST',P+'/photo-consent-view',{'ticket':dt})[0]==404,'old token invalid')
 # Expiry also invalidates browser links and old receipts after an explicit restart.
 st,e=create('consent-task-fixture-expiry');et=token(e);check(b.call('POST',P+'/photo-consent-decision',{'ticket':et,'accepted':True,'policy_version':V})[0]==200,'expiry preparation')
 previous_receipt=req('GET','/photo-consents/'+e['id'])[1]['receipt']
 with closing(sqlite3.connect(db)) as con,con:con.execute('UPDATE photo_task_consents SET expires=1 WHERE id=?',(e['id'],))
 check(req('GET','/photo-consents/'+e['id'])[1]['state']=='expired','receipt expiry')
 check(b.call('POST',P+'/photo-consent-view',{'ticket':et})[0]==410,'browser expiry')
 st,new=create('consent-task-fixture-expiry',restart=True);check(b.call('POST',P+'/photo-consent-decision',{'ticket':token(new),'accepted':True,'policy_version':V})[0]==200,'re-approve explicitly')
 check(req('GET','/photo-consents/'+e['id'])[1]['receipt']!=previous_receipt,'old receipt not reused')
 with closing(sqlite3.connect(db)) as con,con:
  check(con.execute('SELECT count(*) FROM jobs').fetchone()[0]==1,'only one image task')
  check(con.execute('SELECT balance FROM users WHERE id=?',(uid,)).fetchone()[0]==1,'billing unchanged, once')
  check('references' not in ' '.join(x[1] for x in con.execute('PRAGMA table_info(photo_task_consents)')),'no image column in authorization store')
 check(req('POST','/photo-consents',{'task_digest':'0'*64,'idempotency_key':'consent-task-fixture-invalid','policy_version':'wrong'})[0]==400,'create policy mismatch')
 # Real reference decoder, exact raw-byte digest and concurrent free path.
 import base64
 reference=dict(body,references=[{'mime':'image/png','content':base64.b64encode(image).decode()}],reference_consent=True,reference_purpose='portrait')
 st,rc=create('consent-reference-fixture-01',reference);check(st==200,'reference digest creation only')
 check(b.call('POST',P+'/photo-consent-decision',{'ticket':token(rc),'accepted':True,'policy_version':V})[0]==200,'reference approval')
 rr=req('GET','/photo-consents/'+rc['id'])[1]['receipt'];refpayload=dict(reference,photo_consent={'id':rc['id'],'receipt':rr})
 changed=dict(refpayload,references=[{'mime':'image/png','content':base64.b64encode(image+b'changed').decode()}]);check(req('POST','/jobs',changed,idem='consent-reference-fixture-01')[0]==409,'reference-byte change blocked')
 check(req('POST','/jobs',refpayload,idem='consent-reference-fixture-01')[1]['status']=='succeeded','authorized reference fixture edit')
 free=dict(reference,gemini_trial_intent='free');st,fc=create('consent-reference-free-fixture',free);check(st==200,'free consent')
 from concurrent.futures import ThreadPoolExecutor
 def decision(_):
  ab=t.Browser();ab.jar=b.jar.copy();return ab.call('POST',P+'/photo-consent-decision',{'ticket':token(fc),'accepted':True,'policy_version':V})[0]
 with ThreadPoolExecutor(max_workers=2) as pool:check(list(pool.map(decision,range(2)))==[200,200],'concurrent browser confirmation')
 fr=req('GET','/photo-consents/'+fc['id'])[1]['receipt'];fp=dict(free,photo_consent={'id':fc['id'],'receipt':fr})
 with ThreadPoolExecutor(max_workers=2) as pool:answers=list(pool.map(lambda _:req('POST','/jobs',fp,idem='consent-reference-free-fixture'),range(2)))
 check(all(x[0]==200 for x in answers) and answers[0][1]['id']==answers[1][1]['id'],'concurrent free receipt consumes once')
 check(req('GET','/balance')[1]['shared_uses']==0 and req('GET','/balance')[1]['gemini_trial']['used']==1,'free photo does not debit paid wallet')
 check(len((work/'calls').read_text().splitlines())==3,'only three fixture generations')
 # Durable pending URL and used receipt survive a complete service restart.
 st,durable=create('consent-durable-fixture');check(st==200,'durable link')
 env=dict(x.split('=',1) for x in Path('/proc/'+str(proc.pid)+'/environ').read_bytes().decode().strip(chr(0)).split(chr(0)));command=[x.decode() for x in Path('/proc/'+str(proc.pid)+'/cmdline').read_bytes().split(bytes([0])) if x]
 os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
 import subprocess
 proc=subprocess.Popen(command,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 for _ in range(80):
  try:urllib.request.urlopen('http://127.0.0.1:18938'+P+'/health',timeout=1);break
  except Exception:time.sleep(.1)
 check(create('consent-durable-fixture')[1]['url']==durable['url'],'durable URL identical')
 check(req('GET','/photo-consents/'+cid)[1]['receipt']==used['receipt'],'durable original-task receipt')
 # Version migration requires a fresh explicit choice; old signatures stay invalid.
 with closing(sqlite3.connect(db)) as con,con:con.execute("UPDATE photo_task_consents SET policy_version='older-policy' WHERE id=?",(e['id'],))
 check(create('consent-task-fixture-expiry')[0]==409,'policy change requires explicit restart')
 st,updated=create('consent-task-fixture-expiry',restart=True);check(st==200 and updated['policy_version']==V and updated['state']=='pending','policy restart migrated')
 check(b.call('POST',P+'/photo-consent-decision',{'ticket':token(updated),'accepted':True,'policy_version':V})[0]==200,'policy re-confirmed')
 check(req('POST','/jobs',dict(body,photo_consent={'id':[],'receipt':'0'*64}),idem='consent-task-fixture-bad')[0]==400,'malformed receipt safe failure')
 with closing(sqlite3.connect(db)) as con,con:con.execute('UPDATE photo_task_consents SET expires=1 WHERE id=?',(cid,))
 check(b.call('POST',P+'/photo-consent-view',{'ticket':ticket})[0]==410,'used browser ticket still expires')
 check(req('GET','/photo-consents/'+cid)[1]['state']=='used','owner retains historical original task state')
 st,oldjob=req('POST','/skill-jobs',payload,secret=private,idem='consent-task-fixture-0001');check(st==200 and oldjob.get('replayed') and oldjob['id']==job['id'],'used receipt only replays original deleted task after expiry')
 check(len((work/'calls').read_text().splitlines())==3,'expiry replay never generates again')
 print(json.dumps({'passed':count,'production':False,'scope':'isolated real service chain + valid PNG fixture, no real photos/provider/payment'}))
finally:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
