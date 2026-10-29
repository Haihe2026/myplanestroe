"""Existing admin authentication remains authoritative for pet manual settlement."""
import json,sqlite3,time,hashlib,threading
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import urlsplit
from pet_billing import PetBilling
class Problem(Exception):
    def __init__(self,status,message):self.status,self.message=status,message
class Database:
    def __init__(self,path):self.path=path
    @contextmanager
    def connect(self):
        c=sqlite3.connect(Path(self.path).resolve().as_uri()+'?mode=rw',uri=True,timeout=20);c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()
def extend(factory,path):
    def build(*args,**kwargs):
        parent=factory(*args,**kwargs);db=Database(path);billing=PetBilling(db,Problem)
        attempts={};lock=threading.Lock()
        class Handler(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
                if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=result.replace(b'</head>',b'<script defer src="/ops/pet-orders.js?v=0.10.39"></script></head>',1)
                return super().send(status,result,mime,cookie=cookie)
            def do_GET(self):
                route=urlsplit(self.path).path
                if route=='/ops/pet-orders.js':return self.send(200,Path(__file__).with_name('pet-orders.js').read_bytes(),'application/javascript; charset=utf-8')
                if route!='/ops/api/pet-orders':return super().do_GET()
                if not self.authenticated():return self.send(401,{'error':'请登录后台'})
                with db.connect() as c:items=[dict(r) for r in c.execute('SELECT id,user_id,plan,amount_fen,status,created,paid_at FROM pet_orders ORDER BY created DESC LIMIT 200')]
                return self.send(200,{'orders':items})
            def do_POST(self):
                if urlsplit(self.path).path!='/ops/api/pet-settle':return super().do_POST()
                if not self.authenticated():return self.send(401,{'error':'请登录后台'})
                if self.headers.get('Origin')!='https://myplanestore.com':return self.send(403,{'error':'请从本站操作'})
                try:
                    with lock:
                        now=time.time();key=self.client_address[0];attempts[key]=[t for t in attempts.get(key,[]) if t>now-60]
                        if len(attempts[key])>=30:raise Problem(429,'核款操作过于频繁')
                        attempts[key].append(now)
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise Problem(400,'请求格式错误')
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict):raise Problem(400,'JSON对象必填')
                    actor='operator:'+hashlib.sha256(self.headers.get('Cookie','').encode()).hexdigest()[:16]
                    return self.send(200,billing.settle(body.get('order_id'),body.get('amount_fen'),body.get('transaction_id'),actor,body.get('verified')))
                except Problem as e:return self.send(e.status,{'error':e.message})
                except (ValueError,TypeError):return self.send(400,{'error':'请求格式错误'})
                except Exception:return self.send(503,{'error':'核款未完成，请使用原流水核查，勿重复付款'})
        return Handler
    return build
