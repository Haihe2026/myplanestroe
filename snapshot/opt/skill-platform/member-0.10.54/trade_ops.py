"""Trade administration uses the existing 90-day ops sessions and Origin checks."""
import hashlib,json,os,time
from pathlib import Path
from urllib.parse import urlsplit
from trade_store import Trade,Error
from trade_provider import redact

def extend(factory,path):
    def build(*args,**kwargs):
        parent=factory(*args,**kwargs)
        from pet_ops import Database
        db=Database(path);trade=Trade(db)
        class Handler(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
                if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=result.replace(b'</head>',b'<script defer src="/ops/trade-admin.js?v=0.10.41"></script></head>',1)
                return super().send(status,result,mime,cookie=cookie)
            def do_GET(self):
                route=urlsplit(self.path).path
                if route=='/ops/trade-admin.js':return self.send(200,Path(__file__).with_name('trade-admin.js').read_bytes(),'application/javascript; charset=utf-8')
                if not route.startswith('/ops/api/trade-leads/'):return super().do_GET()
                if not self.authenticated():return self.send(401,{'error':'请登录后台'})
                if route.endswith('/summary'):
                    from datetime import datetime
                    from zoneinfo import ZoneInfo
                    month=datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m')
                    with db.connect() as c:
                        q=c.execute('SELECT * FROM trade_quota WHERE month=?',(month,)).fetchone()
                        orders=[dict(x) for x in c.execute('SELECT id,account_id,amount_fen,status,created,is_test FROM trade_orders ORDER BY created DESC LIMIT 100')]
                        daily=[dict(x) for x in c.execute("SELECT strftime('%Y-%m-%d',created_at,'unixepoch','+8 hours') day,sum(CASE WHEN action NOT IN ('recharge','promotion_bonus') THEN -amount_fen ELSE 0 END) revenue_fen FROM trade_ledger WHERE is_test=0 GROUP BY day ORDER BY day DESC LIMIT 90")]
                        calls=[dict(x) for x in c.execute("SELECT strftime('%Y-%m-%d',created_at,'unixepoch','+8 hours') day,sum(CASE WHEN cache_hit=0 THEN 1 ELSE 0 END) upstream_calls FROM trade_upstream WHERE provider='rockapis' GROUP BY day ORDER BY day DESC LIMIT 90")]
                        failures=c.execute("SELECT count(*) FROM trade_upstream WHERE mapping_failed=1 AND provider='rockapis'").fetchone()[0]
                        fixtures=[dict(x) for x in c.execute('SELECT id,endpoint,created,mapping_failed FROM trade_fixtures ORDER BY created DESC LIMIT 100')]
                    cost=float(os.environ.get('PROVIDER_COST_PER_CALL_USD','0.005'));rate=os.environ.get('PROVIDER_USD_CNY_RATE')
                    by_day={x['day']:x['upstream_calls'] for x in calls}
                    profit=[dict(day=x['day'],estimated_gross_profit_fen=round(x['revenue_fen']-by_day.get(x['day'],0)*cost*float(rate or '0')*100) if rate or cost==0 else None) for x in daily]
                    return self.send(200,dict(quota=dict(q) if q else None,monthly_limit=int(os.environ.get('PROVIDER_MONTHLY_QUOTA','50')),monthly_requests_limit=int(os.environ.get('PROVIDER_MONTHLY_REQUEST_QUOTA','75')),mapping_failures=failures,orders=orders,fixtures=fixtures,daily_revenue=daily,daily_upstream=calls,estimated_daily_profit=profit,cost_per_call_usd=cost,profit_currency_note='收入人民币/成本美元分别展示；有非零美元成本且未配置汇率时不虚构人民币毛利'))
                if '/fixtures/' in route:
                    fid=route.rsplit('/',1)[-1]
                    with db.connect() as c:r=c.execute('SELECT path FROM trade_fixtures WHERE id=?',(fid,)).fetchone()
                    if not r:return self.send(404,{'error':'样例不存在'})
                    return self.send(200,redact(json.loads(Path(r[0]).read_text(encoding='utf8'))))
                return self.send(404,{'error':'接口不存在'})
            def do_POST(self):
                route=urlsplit(self.path).path
                if route not in ('/ops/api/trade-leads/settle','/ops/api/trade-leads/revoke'):return super().do_POST()
                if not self.authenticated():return self.send(401,{'error':'请登录后台'})
                if self.headers.get('Origin')!='https://myplanestore.com':return self.send(403,{'error':'请从本站操作'})
                try:
                    trade.rate('settle:'+self.client_address[0],30)
                    n=int(self.headers.get('Content-Length','0'))
                    if not 0<n<=4096:raise Error(400,'INVALID_PARAMS','请求格式无效')
                    b=json.loads(self.rfile.read(n));actor='operator:'+hashlib.sha256(self.headers.get('Cookie','').encode()).hexdigest()[:16]
                    if route.endswith('/revoke'):
                        with db.connect() as c:c.execute('UPDATE trade_tokens SET revoked=1 WHERE account_id=?',(b.get('account_id'),))
                        return self.send(200,dict(revoked=True))
                    return self.send(200,trade.settle(b.get('order_id'),b.get('amount_fen'),b.get('transaction_id'),actor,b.get('verified')))
                except Error as e:return self.send(e.status,e.body())
                except (ValueError,TypeError):return self.send(400,{'error':'请求格式无效'})
                except Exception:return self.send(503,{'error':'操作未完成，请核对原订单，勿重复支付'})
        return Handler
    return build
