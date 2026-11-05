"""Additive deployment; backups contain private production data and stay on server."""
from pathlib import Path
import sys,subprocess,json,base64,hashlib
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'0.10.20'))
from capture import SSH
names=['metered.py','listing_trial_gate.py','run_shared.py','services.json','metered_ops.py','listing-admin.js']
files={p.relative_to(R/'after').as_posix():base64.b64encode(p.read_bytes()).decode() for p in (R/'after').rglob('*') if p.is_file()}
expected={p.relative_to(R/'before').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'before').rglob('*') if p.is_file()}
v={'layer':{n:base64.b64encode((R/n).read_bytes()).decode() for n in names},'web':files,'expected_web':expected,'admin':base64.b64encode((R/'redesign_ops.py').read_bytes()).decode(),'expected_admin':hashlib.sha256((R.parent/'2026-11-05-aisplice-costs/redesign_ops.py').read_bytes()).hexdigest()}
code=r'''
from pathlib import Path
import subprocess,json,base64,hashlib,time,sqlite3,shutil,re,urllib.request,urllib.error
v=json.loads(PAYLOAD);root=Path('/opt/skill-platform/metered-page-20261105');old='/opt/skill-platform/provider-costs-20261105/run_shared.py';admin=Path('/opt/skill-platform/admin-redesign-20261103/redesign_ops.py')
assert Path(old).is_file(),'Current chain entry missing'
show=subprocess.check_output(['systemctl','show','skill-platform','-p','ExecStart','--value'],text=True);assert old in show,'Live chain changed'
assert not root.exists(),'Layer already exists; inspect deployment receipt before retry'
assert hashlib.sha256(admin.read_bytes()).hexdigest()==v['expected_admin'],'Admin source changed'
for p,h in v['expected_web'].items():assert hashlib.sha256(Path('/'+p).read_bytes()).hexdigest()==h,'Page changed: '+p
nginx={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['/etc/nginx/conf.d/image-assistant.conf','/etc/nginx/conf.d/aistore-myplanestore.conf']}
drop=Path('/etc/systemd/system/skill-platform.service.d')/('z'*221+'-metered.conf');assert len(drop.name)<=255 and all(p.name<drop.name for p in drop.parent.glob('*.conf'))
b=Path('/var/backups/myplanestore/metered-page-'+str(int(time.time())));b.mkdir(parents=True,mode=0o700)
source=sqlite3.connect('file:/var/lib/skill-platform/shared.db?mode=ro',uri=True);target=sqlite3.connect(b/'shared.db');source.backup(target);assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok';source.close();target.close();(b/'shared.db').chmod(0o600)
paths=[admin,*[Path('/'+p) for p in v['web']]]
manifest={str(p):p.exists() for p in paths}
for p in paths:
 if p.exists():q=b/str(p).lstrip('/');q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
(b/'manifest.json').write_text(json.dumps(manifest));(b/'drop-in.txt').write_text(str(drop))
def request(port,path):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as x:return x.status,x.read()
 except urllib.error.HTTPError as e:return e.code,e.read()
def health():
 for i in range(25):
  try:
   checks=[(8791,'/platform-api/listing/v1/pricing',200),(8791,'/platform-api/grok-video/health',200),(8791,'/platform-api/gemini/membership-api/plans',200),(8791,'/platform-api/temu/membership-api/plans',200),(8790,'/ops/',200),(8790,'/ops/api/listing/summary',401)]
   for port,path,status in checks:assert request(port,path)[0]==status,(port,path)
   return
  except Exception:
   if i==24:raise
   time.sleep(1)
def restore():
 # Restore all page/admin files before waiting for service readiness; a restart
 # delay cannot strand a new page pointing at rolled-back routes.
 try:drop.unlink(missing_ok=True)
 finally:
  for p,existed in manifest.items():
   path=Path(p)
   if existed:shutil.copy2(b/p.lstrip('/'),path)
   else:path.unlink(missing_ok=True)
 subprocess.run(['systemctl','daemon-reload'],check=True)
 for name in ['skill-platform','skill-monitor']:subprocess.run(['systemctl','restart',name],check=True)
 health()
try:
 root.mkdir(mode=0o755)
 for n,data in v['layer'].items():(root/n).write_bytes(base64.b64decode(data));(root/n).chmod(0o644)
 for p in root.glob('*.py'):compile(p.read_text(),str(p),'exec')
 admin.write_bytes(base64.b64decode(v['admin']))
 for p,data in v['web'].items():
  path=Path('/'+p);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(data));path.chmod(0o644)
 args=re.search(r'argv\[\]=(.*?) ;',show).group(1).replace(old,str(root/'run_shared.py'),1)
 drop.write_text('[Service]\nExecStart=\nExecStart='+args+'\n')
 subprocess.run(['systemctl','daemon-reload'],check=True)
 for name in ['skill-platform','skill-monitor']:subprocess.run(['systemctl','restart',name],check=True)
 health()
 assert request(8791,'/platform-api/listing/v1/me')[0]==401
 assert request(8791,'/platform-api/metered/v1/unregistered-service/pricing')[0]==404
 assert nginx=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in nginx},'Nginx unexpectedly changed'
 result={'backup':str(b),'entry':str(root/'run_shared.py'),'checks':'listing/grok/gemini/temu/ops healthy; anonymous account/admin rejected; unregistered skill 404','nginx_unchanged':True,'real_customer_credentials_used':False,'real_payments_or_generation_calls':0}
 (b/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
except Exception:
 restore();raise
'''.replace('PAYLOAD',repr(json.dumps(v)))
p=subprocess.run(SSH+['python3 -'],input=code,text=True,capture_output=True,encoding='utf-8',timeout=160)
print(p.stdout);print(p.stderr);p.check_returncode()
result=json.loads(p.stdout.strip().splitlines()[-1]);(R/'deployment-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
