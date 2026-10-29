"""Operator-confirmed one-time packs; registration never awards image credits."""
import hashlib
import json
import re
import time
import uuid

class QuotaPack:
    def __init__(self,store,problem):
        self.store,self.problem=store,problem
        with store.connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS pack_accounts(
                hash TEXT PRIMARY KEY,user_id TEXT NOT NULL UNIQUE,created INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS pack_confirmations(
                user_id TEXT PRIMARY KEY,order_id TEXT NOT NULL UNIQUE,grant_id TEXT NOT NULL UNIQUE,
                amount_fen INTEGER NOT NULL,units INTEGER NOT NULL,created INTEGER NOT NULL);''')

    def account(self,secret,accepted):
        if accepted is not True or not isinstance(secret,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',secret):
            raise self.problem(400,'请确认账户说明并保留原账户标识')
        hashed=hashlib.sha256(secret.encode()).hexdigest();now=int(time.time())
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT user_id FROM pack_accounts WHERE hash=?',(hashed,)).fetchone()
            uid=row['user_id'] if row else str(uuid.uuid4())
            if not row:
                c.execute('INSERT INTO users VALUES(?,0)',(uid,))
                c.execute('INSERT INTO pack_accounts VALUES(?,?,?)',(hashed,uid,now))
            c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',(hashed,uid,now+7*86400))
        return dict(self.info(uid),token=secret)

    def info(self,uid):
        with self.store.connect() as c:
            row=c.execute('SELECT 1 FROM pack_accounts WHERE user_id=?',(uid,)).fetchone()
            if not row: raise self.problem(404,'额度包账户不存在')
            grant=c.execute('SELECT 1 FROM pack_confirmations WHERE user_id=?',(uid,)).fetchone()
        return {'account_id':uid,'balance_points':self.store.balance(uid)*1000,
                'pack_confirmed':bool(grant),'fulfillment_mode':'operator_confirmed',
                'payment_verified_automatically':False}

    def confirm_purchase(self,uid,order_id,amount_fen,confirmed=False):
        if confirmed is not True or type(amount_fen) is not int or amount_fen!=1900:
            raise self.problem(400,'必须人工核对19元真实订单后确认')
        if not isinstance(order_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{6,100}',order_id):
            raise self.problem(400,'真实订单号格式无效')
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM pack_accounts WHERE user_id=?',(uid,)).fetchone():
                raise self.problem(404,'请先创建额度包账户')
            old=c.execute('SELECT * FROM pack_confirmations WHERE user_id=? OR order_id=?',(uid,order_id)).fetchone()
            if old:
                if old['user_id']==uid and old['order_id']==order_id: return {'awarded_points':0,'replayed':True}
                raise self.problem(409,'同一账户只发放一次，订单不能转给其他账户')
            grant='pack:'+uuid.uuid4().hex;now=int(time.time())
            c.execute('INSERT INTO pack_confirmations VALUES(?,?,?,?,40,?)',(uid,order_id,grant,1900,now))
            c.execute('INSERT INTO member_grants VALUES(?,?,40,NULL)',(grant,uid))
            c.execute('UPDATE users SET balance=balance+40 WHERE id=?',(uid,))
            c.execute('INSERT INTO paid_wallets VALUES(?,40) ON CONFLICT(user_id) DO UPDATE SET remaining=remaining+40',(uid,))
            c.execute("INSERT INTO ledger(user_id,job_id,amount,kind,created) VALUES(?,?,40,'pack_operator_confirmation',?)",(uid,grant,now))
        return {'awarded_points':40000,'replayed':False}

def pack_handler(parent,pack):
    prefix='/quota-pack/gemini'
    class Handler(parent):
        def run_request(self):
            if not self.path.startswith(prefix+'/'): return self.send(404,{'error':'接口不存在'})
            path=self.path[len(prefix):]
            try:
                if path=='/health' and self.command=='GET':
                    return self.send(200,{'version':'1.7.0','provider_configured':pack.store.provider.ready,
                        'reference_editing':getattr(pack.store.provider,'edit_ready',False),'point_scale':1000,
                        'fulfillment_mode':'operator_confirmed','automatic_payment_fulfillment':False})
                if path=='/account' and self.command=='POST':
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=4096: raise pack.problem(400,'账户请求大小无效')
                    body=json.loads(self.rfile.read(length))
                    if not isinstance(body,dict) or set(body)!={'install_secret','accepted'}: raise pack.problem(400,'账户请求字段无效')
                    return self.send(200,pack.account(body['install_secret'],body['accepted']))
                if path=='/info' and self.command=='GET':
                    uid=pack.store.user(self.headers.get('Authorization','').removeprefix('Bearer '))
                    return self.send(200,pack.info(uid))
                allowed=(self.command=='GET' and (path in ('/health','/balance') or path.startswith('/jobs/'))) or (self.command=='POST' and path=='/jobs')
                if not allowed: return self.send(404,{'error':'此服务不提供充值、赠分或独立付款接口'})
                original=self.path
                try:
                    self.path=path
                    return super().run_request()
                finally: self.path=original
            except pack.problem as e: return self.send(e.status,{'error':e.message})
            except (ValueError,TypeError,UnicodeError): return self.send(400,{'error':'请求格式错误'})
        do_GET=run_request
        do_POST=run_request
    return Handler
