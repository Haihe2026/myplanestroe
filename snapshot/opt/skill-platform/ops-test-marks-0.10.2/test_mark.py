"""Admin test-order state transitions. Never grants quota or records payment."""
import hashlib
import json
import re
import sqlite3
import time
from contextlib import closing
from urllib.parse import urlsplit


class MarkError(Exception):
    def __init__(self,status,message):
        self.status,self.message=status,message


def mark(paths, body, actor):
    if not isinstance(body,dict) or body.get('product') not in paths:
        raise MarkError(400,'订单产品无效')
    ids=body.get('order_ids')
    if not isinstance(ids,list) or not 1<=len(ids)<=50 or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{32}',x) for x in ids) or len(set(ids))!=len(ids):
        raise MarkError(400,'请选择1至50笔不同的订单')
    reason=body.get('reason')
    if body.get('confirmed_test_only') is not True or not isinstance(reason,str) or not 2<=len(reason.strip())<=200:
        raise MarkError(400,'请确认仅处理测试订单，并填写2至200字的备注')
    product=body['product']
    # The caller holds the existing operator settlement lock. Reservations must
    # not be relabelled while a financial confirmation is unresolved.
    with closing(sqlite3.connect(paths['shared'],timeout=10)) as shared:
        for oid in ids:
            if shared.execute("SELECT 1 FROM settlement_receipts WHERE product=? AND order_id=? LIMIT 1",(product,oid)).fetchone():
                raise MarkError(409,'所选订单存在核款流水，请先核查，不能作测试标记')
    with closing(sqlite3.connect(paths[product],timeout=10)) as db:
        db.row_factory=sqlite3.Row
        with db:
            db.execute('BEGIN IMMEDIATE')
            rows=[]
            for oid in ids:
                row=db.execute('SELECT id,status,provider,paid_at,transaction_id FROM member_orders WHERE id=?',(oid,)).fetchone()
                if row is None:raise MarkError(404,'存在找不到的订单，本批次未更改')
                if row['status'] not in ('pending','reported','test_fulfilled') or row['paid_at'] is not None or row['transaction_id'] is not None:
                    raise MarkError(409,'存在已核款或状态异常的订单，本批次未更改')
                if db.execute('SELECT 1 FROM member_grants WHERE order_id=?',(oid,)).fetchone() or db.execute('SELECT 1 FROM ops_settlements WHERE order_id=?',(oid,)).fetchone():
                    raise MarkError(409,'存在额度或核款记录，本批次未更改')
                rows.append(row)
            db.execute('''CREATE TABLE IF NOT EXISTS ops_test_order_marks(
                order_id TEXT PRIMARY KEY,previous_status TEXT NOT NULL,
                actor TEXT NOT NULL,reason TEXT NOT NULL,marked_at INTEGER NOT NULL)''')
            changed=0
            for row in rows:
                if row['status']=='test_fulfilled':continue
                db.execute('INSERT INTO ops_test_order_marks VALUES(?,?,?,?,?)',(row['id'],row['status'],actor,reason.strip(),int(time.time())))
                db.execute("UPDATE member_orders SET status='test_fulfilled',provider='ops_test_marker' WHERE id=?",(row['id'],))
                changed+=1
            return {'ok':True,'marked':changed,'already_marked':len(ids)-changed,'quota_added':0,'payment_recorded':False}


def extend_handler(original):
    def factory(report,password,web,secure=True,settler=None):
        base=original(report,password,web,secure=secure,settler=settler)
        class Handler(base):
            def do_POST(self):
                if urlsplit(self.path).path!='/ops/api/test-orders/mark-fulfilled':
                    return super().do_POST()
                self.connection.settimeout(10)
                if self.headers.get('Origin')!=('https://myplanestore.com' if secure else 'http://127.0.0.1:18890'):
                    return self.send(403,{'error':'请从本站操作'})
                if not self.authenticated():return self.send(401,{'error':'请登录管理后台'})
                if settler is None:return self.send(503,{'error':'订单管理尚未启用'})
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=16384:raise MarkError(400,'请求大小无效')
                    body=json.loads(self.rfile.read(size))
                    actor='admin-session:'+hashlib.sha256(self.headers.get('Cookie','').encode()).hexdigest()[:16]
                    paths={key:adapter.path for key,adapter in settler.adapters.items()}
                    with settler.lock:result=mark(paths,body,actor)
                    return self.send(200,result)
                except MarkError as error:return self.send(error.status,{'error':error.message})
                except (ValueError,TypeError,UnicodeError):return self.send(400,{'error':'请求格式无效'})
                except Exception:return self.send(503,{'error':'测试标记未确认完成，请刷新订单核对后重试'})
        return Handler
    return factory


def test_orders(original):
    def orders(self,product,status,query,page):
        if status!='test_fulfilled':return original(self,product,status,query,page)
        if product not in self.products or type(page) is not int or not 1<=page<=100000 or not isinstance(query,str) or len(query)>64:raise ValueError('Invalid query')
        escaped=query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        pattern='%'+escaped+'%'
        with closing(sqlite3.connect(self.products[product],timeout=10)) as db:
            db.row_factory=sqlite3.Row
            where="status='test_fulfilled' AND (id LIKE ? ESCAPE '\\' OR user_id LIKE ? ESCAPE '\\')"
            total=db.execute('SELECT count(*) FROM member_orders WHERE '+where,(pattern,pattern)).fetchone()[0]
            rows=[dict(row,points=row['units']*1000) for row in db.execute('SELECT id,user_id,plan,amount_fen,units,status,created,paid_at,provider FROM member_orders WHERE '+where+' ORDER BY created DESC,id DESC LIMIT 50 OFFSET ?',(pattern,pattern,(page-1)*50))]
            counts={row['status']:dict(row) for row in db.execute('SELECT status,count(*) count,coalesce(sum(amount_fen),0) amount_fen FROM member_orders GROUP BY status')}
        return {'orders':rows,'total':total,'page':page,'counts':counts}
    return orders
