import os,sys,json,tempfile,secrets,sqlite3,signal,urllib.request,urllib.error,hashlib,base64,struct,zlib,time,subprocess
from pathlib import Path
HERE=Path(__file__).parent
os.environ['MYPLANESTORE_SCHEMA_DIR']='/opt/skill-platform/member-0.10.32-r2/schema'
sys.path.insert(0,'/opt/skill-platform/member-0.10.32-r2');import test_account_link_base as t
t.ENTRY=HERE/'fixture_runner.py';t.SCHEMA=Path(os.environ['MYPLANESTORE_SCHEMA_DIR']);t.PORT=18935
work=Path(tempfile.mkdtemp(prefix='retention35-'));os.environ['MPS_EPHEMERAL_IMAGE_KEYS']=str(work/'keys');os.environ['FIXTURE_CALLS']=str(work/'calls');os.environ['SUNBURST_KEY_FILE']=str(work/'no-provider-key');os.environ['TEMU_DELIVERY_DB']=str(work/'temu-delivery.db')
proc,db=t.start(work);count=0;P='/platform-api/gemini'
launch_env=dict(x.split('=',1) for x in Path('/proc/'+str(proc.pid)+'/environ').read_bytes().decode().strip(chr(0)).split(chr(0)));command=[x.decode() for x in Path('/proc/'+str(proc.pid)+'/cmdline').read_bytes().split(bytes([0])) if x]
def check(v,label):
 global count
 if not v:raise AssertionError(label)
 count+=1
def req(method,path,body=None,secret=None,idem=None):
 headers={'Authorization':'Bearer '+(secret or owner)}
 if idem:headers['Idempotency-Key']=idem
 if body is not None:headers['Content-Type']='application/json'
 q=urllib.request.Request('http://127.0.0.1:18935'+P+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
 try:r=urllib.request.urlopen(q,timeout=15)
 except urllib.error.HTTPError as e:r=e
 raw=r.read()
 return r.status,json.loads(raw) if r.headers.get('Content-Type','').startswith('application/json') else raw
try:
 owner=secrets.token_urlsafe(32);other=secrets.token_urlsafe(32)
 for s in [owner,other]:check(t.skill('POST',P+'/register',{'install_secret':s,'accepted':True})[0]==200,'register')
 with sqlite3.connect(db) as c:c.execute('UPDATE users SET balance=10')
 body={'prompt':'Create a synthetic illustration','confirmed':True,'role':'general','platform':'general','slot':'poster','size':'1024x1024','image_engine':'gemini-personal-sunburst','gemini_trial_intent':'paid','image_retention':{'policy':'gateway-delivery-delete/1'}}
 st,r=req('POST','/jobs',body,idem='synthetic-retention-case01');check(st==200 and r['status']=='succeeded','generation');jid=r['id']
 st,image=req('GET','/jobs/'+jid+'/image');check(st==200 and image.startswith(b'\x89PNG'),'download real PNG fixture')
 with sqlite3.connect(db) as c:stored=c.execute('SELECT image FROM jobs WHERE id=?',(jid,)).fetchone()[0];check(stored.startswith(b'MPS-EPHEMERAL-1:') and stored!=image,'encrypted before SQL store')
 backup=work/'backup.db';a=sqlite3.connect(db);b=sqlite3.connect(backup);a.backup(b);a.close();b.close();check(image not in backup.read_bytes(),'backup excludes plaintext result')
 check(req('POST','/jobs/'+jid+'/delivery-confirm',{'confirmed':True,'image_sha256':'0'*64})[0]==409,'wrong delivery hash')
 check(req('POST','/jobs/'+jid+'/delete-image',{'confirmed':True},secret=other)[0]==404,'owner isolation')
 # A service restart retains key under runtime directory; no duplicate provider request.
 os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10);proc=subprocess.Popen(command,env=launch_env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 for _ in range(80):
  try:urllib.request.urlopen('http://127.0.0.1:18935'+P+'/health',timeout=1);break
  except Exception:time.sleep(.1)
 check(req('GET','/jobs/'+jid+'/image')[1]==image,'service restart resumes download')
 confirm={'confirmed':True,'image_sha256':hashlib.sha256(image).hexdigest()}
 check(req('POST','/jobs/'+jid+'/delivery-confirm',confirm)[0]==200,'delivery deletion')
 check(req('POST','/jobs/'+jid+'/delivery-confirm',confirm)[0]==200,'deletion retry')
 check(not (work/'keys'/(jid+'.key')).exists(),'key destroyed')
 check(req('GET','/jobs/'+jid+'/image')[0]==410,'deleted download blocked')
 check(req('GET','/jobs/by-key/synthetic-retention-case01')[1]['image_retention']['state']=='deleted','by-key tombstone')
 st,r=req('POST','/jobs',body,idem='synthetic-retention-case01');check(st==200 and r.get('replayed') and r['image_retention']['state']=='deleted','deleted replay no regeneration')
 check(len((work/'calls').read_text().splitlines())==1,'provider called once')
 st,r=req('POST','/jobs',body,idem='synthetic-retention-case02');jid2=r['id'];check(st==200,'second task')
 with sqlite3.connect(db) as c:c.execute('UPDATE ephemeral_image_jobs SET expires=? WHERE job_id=?',(int(time.time())-1,jid2))
 check(req('GET','/jobs/'+jid2+'/image')[0]==410,'expired download blocked')
 check(not (work/'keys'/(jid2+'.key')).exists(),'expired key removed')
 st,r=req('POST','/jobs',body,idem='synthetic-retention-case03');jid3=r['id'];check(req('POST','/jobs/'+jid3+'/delete-image',{'confirmed':True})[0]==200,'owner requested deletion')
 legacy=dict(body);legacy.pop('image_retention');st,r=req('POST','/jobs',legacy,idem='synthetic-retention-legacy');legacyid=r['id'];check(st==200,'legacy task')
 check(req('POST','/jobs/'+legacyid+'/delete-image',{'confirmed':True})[0]==404,'no enrollment of historical policy')
 check(req('GET','/jobs/'+legacyid+'/image')[0]==200,'legacy result untouched')
 check(req('POST','/jobs',body,idem='synthetic-retention-legacy')[0]==409,'cannot attach policy to old task')
 # Actual reference decoder and portrait provider routing, using fixture PNG, no human photos.
 portrait=dict(body,reference_purpose='portrait',references=[{'mime':'image/png','content':base64.b64encode(image).decode()}],reference_consent=True)
 st,r=req('POST','/jobs',portrait,idem='synthetic-retention-portrait');check(st==200 and r['status']=='succeeded','reference edit fixture')
 check((work/'calls').read_text().splitlines()[-1]=='portrait','product instruction removed only for explicit portrait')
 bad=dict(portrait,reference_consent=False);check(req('POST','/jobs',bad,idem='synthetic-retention-no-consent')[0]==400,'reference consent enforced')
 with sqlite3.connect(db) as c:
  check(c.execute('SELECT image FROM jobs WHERE id=?',(jid,)).fetchone()[0] is None,'active ciphertext removed')
  check(c.execute('SELECT count(*) FROM jobs').fetchone()[0]==5,'no duplicated jobs')
  check(c.execute('SELECT min(balance) FROM users').fetchone()[0]==5,'original billing once per accepted task')
 from concurrent.futures import ThreadPoolExecutor
 with ThreadPoolExecutor(max_workers=2) as pool:
  receipts=list(pool.map(lambda _:req('POST','/jobs/'+jid+'/delivery-confirm',confirm)[0],range(2)))
 check(receipts==[200,200],'concurrent delivery confirmations idempotent')
 # Automatic cleanup must work without a user downloading the expired result.
 st,r=req('POST','/jobs',body,idem='synthetic-retention-background');jid4=r['id'];check(st==200,'automatic cleanup task')
 with sqlite3.connect(db) as c:c.execute('UPDATE ephemeral_image_jobs SET expires=? WHERE job_id=?',(int(time.time())-1,jid4))
 deadline=time.monotonic()+35
 while time.monotonic()<deadline:
  with sqlite3.connect(db) as c:state=c.execute('SELECT state FROM ephemeral_image_jobs WHERE job_id=?',(jid4,)).fetchone()[0]
  if state=='deleted':break
  time.sleep(.25)
 check(state=='deleted' and not (work/'keys'/(jid4+'.key')).exists(),'background TTL removes key and image')
 pending=dict(body,prompt='force-pending-fixture')
 st,pr=req('POST','/jobs',pending,idem='synthetic-retention-pending');check(st==200 and pr['status']=='pending','provider timeout stays pending')
 check(req('POST','/jobs/'+pr['id']+'/delete-image',{'confirmed':True})[0]==200,'pending owner deletion')
 st,replay=req('POST','/jobs',pending,idem='synthetic-retention-pending');check(st==200 and replay['status']=='pending' and replay['image_retention']['state']=='deleted','pending never resubmitted')
 concurrent=dict(body,prompt='concurrent-fixture')
 with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda _:req('POST','/jobs',concurrent,idem='synthetic-retention-concurrent'),range(2)))
 check(all(x[0]==200 for x in rs) and rs[0][1]['id']==rs[1][1]['id'],'concurrent generation one task')
 with sqlite3.connect(db) as c:check(c.execute('SELECT count(*) FROM jobs').fetchone()[0]==8 and c.execute('SELECT min(balance) FROM users').fetchone()[0]==2,'concurrent and timeout charged once')
 with sqlite3.connect(db) as c:
  uid=c.execute('SELECT user_id FROM trial_claims WHERE hash=?',(hashlib.sha256(owner.encode()).hexdigest(),)).fetchone()[0]
  c.execute('INSERT INTO skill_credentials(user_id,id,nonce,created) VALUES(?,?,?,?)',(uid,secrets.token_hex(16),secrets.token_hex(32),int(time.time())))
 st,k=req('POST','/skill-key',{});check(st==200 and k['state']=='ready','paid private key retrieval fixture')
 private=k['key'];check(req('POST','/skill-key/bound',{'key':private})[1]['bound'],'paid key bound')
 st,r=req('POST','/skill-jobs',body,secret=private,idem='synthetic-retention-paid-key');paidid=r.get('id');check(st==200 and r.get('status')=='succeeded','paid /skill-jobs generation')
 st,paidimage=req('GET','/jobs/'+paidid+'/image',secret=private);check(st==200 and paidimage==image,'paid key download permitted')
 check(req('POST','/jobs/'+paidid+'/delivery-confirm',{'confirmed':True,'image_sha256':hashlib.sha256(paidimage).hexdigest()},secret=private)[0]==200,'paid key delivery confirmation')
 check(req('GET','/jobs/'+paidid+'/image')[0]==410,'owner sees paid deleted result')
 fresh=secrets.token_urlsafe(32);check(t.skill('POST',P+'/register',{'install_secret':fresh,'accepted':True})[0]==200,'fresh free user')
 free=dict(body,gemini_trial_intent='free');st,r=req('POST','/jobs',free,secret=fresh,idem='synthetic-retention-free-job');check(st==200 and r.get('status')=='succeeded','actual free path')
 st,q=req('GET','/balance',secret=fresh);check(st==200 and q['shared_uses']==0 and q['gemini_trial']['used']==1,'free trial does not debit paid wallet')
 check(req('POST','/jobs/'+r['id']+'/delivery-confirm',{'confirmed':True,'image_sha256':hashlib.sha256(image).hexdigest()},secret=fresh)[0]==200,'free result deletion')
 print(json.dumps({'passed':count,'production':False,'scope':'real service chain with valid PNG provider fixture; no real child images/provider/payments','synthetic_workdir':str(work)}))
finally:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
