import sys,os,tempfile,secrets,sqlite3,signal,json,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,'/opt/skill-platform/member-0.10.32-r2')
os.environ['MYPLANESTORE_SCHEMA_DIR']='/opt/skill-platform/member-0.10.32-r2/schema'
import test_account_link_base as t
t.ENTRY=Path(__file__).parent/'run_shared.py';t.SCHEMA=Path('/opt/skill-platform/member-0.10.32-r2/schema');t.PORT=18933
P='/platform-api/gemini';work=Path(tempfile.mkdtemp(prefix='phone33-'));proc,db=t.start(work);count=0
def check(value):
 global count
 assert value
 count+=1
def user():
 s=secrets.token_urlsafe(32);_,e=t.skill('POST',P+'/album-entry',{'install_secret':s});b=t.Browser();_,r=b.call('POST',P+'/album-register',{'entry':t.entry_of(e),'phone':'199'+str(secrets.randbelow(10**8)).zfill(8),'accepted':True});return s,b
try:
 # Create original unbound account through unchanged registration and redeem its own ticket.
 s=secrets.token_urlsafe(32);st,r=t.skill('POST',P+'/register',{'install_secret':s,'accepted':True});check(st==200)
 import urllib.parse
 def auth(path):
  req=urllib.request.Request('http://127.0.0.1:18933'+P+path,data=b'{}',headers={'Authorization':'Bearer '+s,'Content-Type':'application/json'},method='POST')
  return json.load(urllib.request.urlopen(req))
 link=auth('/membership-link');ticket=urllib.parse.parse_qs(urllib.parse.urlsplit(link['url']).fragment)['ticket'][0]
 b=t.Browser();st,_=b.call('POST',P+'/membership-api/redeem',{'ticket':ticket});check(st==200)
 st,before=b.call('GET',P+'/membership-api/account');check(st==200)
 st,status=b.call('GET',P+'/phone-status');check(st==200 and not status['phone_bound'])
 payload={'phone':'13800000000','accepted':True}
 st,p=b.call('POST',P+'/phone-prepare',payload);check(st==200 and p['key_once'].endswith('2345'))
 with sqlite3.connect(db) as c:check(c.execute('SELECT count(*) FROM album_phone_keys').fetchone()[0]==0)
 confirm=dict(payload,key=p['key_once'],proof=p['proof'],expires=p['expires'])
 st,_=b.call('POST',P+'/phone-bind',dict(confirm,key='x'*36));check(st==401)
 st,_=b.call('POST',P+'/phone-bind',confirm);check(st==200)
 st,_=b.call('POST',P+'/phone-bind',confirm);check(st==200) # lost response retry
 st,after=b.call('GET',P+'/membership-api/account');check(before==after)
 st,status=b.call('GET',P+'/phone-status');check(status['phone_bound'])
 st,_=b.call('POST',P+'/phone-prepare',payload);check(st==409)
 check(auth('/phone-key-delivery')['key']==p['key_once'])
 with sqlite3.connect(db) as c:
  check(c.execute('SELECT count(*) FROM users').fetchone()[0]==1)
  check(c.execute('SELECT count(*) FROM album_phone_keys').fetchone()[0]==1)
  raw=Path(db).read_bytes();check(p['key_once'].encode() not in raw and payload['phone'].encode() not in raw)
 check(b.call('POST',P+'/phone-bind',dict(confirm,expires=1))[0]==401)
 foreign=t.Browser(origin='https://invalid.example');foreign.jar=b.jar.copy();check(foreign.call('POST',P+'/phone-prepare',payload)[0]==403)
 # Another browser cannot see the original account or obtain its KEY.
 anonymous=t.Browser();check(anonymous.call('GET',P+'/phone-status')[0]==401)
 secret2=secrets.token_urlsafe(32);st,_=t.skill('POST',P+'/register',{'install_secret':secret2,'accepted':True});check(st==200)
 saved=s;s=secret2;link=auth('/membership-link');ticket=urllib.parse.parse_qs(urllib.parse.urlsplit(link['url']).fragment)['ticket'][0]
 second=t.Browser();check(second.call('POST',P+'/membership-api/redeem',{'ticket':ticket})[0]==200)
 check(second.call('POST',P+'/phone-prepare',payload)[0]==409)
 check(second.call('POST',P+'/phone-bind',confirm)[0]==401)
 check(auth('/phone-key-delivery')['available'] is False);s=saved
 # Same account sees binding across product views without changing wallet.
 check(b.call('GET','/platform-api/temu/phone-status')[1]['phone_bound'])
 print(json.dumps({'passed':count,'production':False,'scope':'isolated real service chain; no image, payment or customer data'}))
finally:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
