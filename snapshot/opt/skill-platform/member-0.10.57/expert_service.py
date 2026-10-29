"""Private route policy: only the declared Temu WorkBuddy expert delivery queue."""
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path
import urllib.parse
from resource_adapter import Adapter,ROUTE

ROOT=Path(__file__).resolve().parent
CONTEXT=ContextVar('expert_resource_context',default=None)
ADAPTER=None


def adapter():
    global ADAPTER
    if ADAPTER is None:ADAPTER=Adapter()
    return ADAPTER


def select_route(source,channel):
    try:enabled=json.loads((ROOT/'policy.json').read_text())['enabled'] is True
    except Exception:enabled=False
    return ROUTE if enabled and source=='temu-image-master' and channel=='workbuddy_expert' else 'legacy'


def is_new():
    ctx=CONTEXT.get()
    return bool(ctx and ctx['route']==ROUTE)


def install(server,shared,sunburst):
    original=sunburst.Provider
    class Scoped:
        def __init__(self,*a,**k):self.legacy=original(*a,**k)
        @property
        def ready(self):return adapter().ready if is_new() else self.legacy.ready
        @property
        def last_usage(self):return None if is_new() else self.legacy.last_usage
        def generate(self,*a,**k):
            if is_new():raise ValueError('Product reference required')
            return self.legacy.generate(*a,**k)
        def edit(self,prompt,size,images):
            if not is_new():return self.legacy.edit(prompt,size,images)
            ctx=CONTEXT.get();store=ctx['store'];key=ctx['ledger_key']
            with store.connect() as c:row=c.execute('SELECT id FROM jobs WHERE user_id=? AND idem=?',(ctx['uid'],key)).fetchone()
            if not row:raise ValueError('Missing original reservation')
            return adapter().edit(ctx['adapter_key'],ctx['uid'],row[0],prompt,size,images)
    sunburst.Provider=Scoped
    install_previous=sunburst.install
    def scoped_install(*args,**kwargs):
        installed_before=getattr(shared,'_sunburst_installed',False)
        install_previous(*args,**kwargs)
        if installed_before:return
        previous_generate=shared.SharedStore.generate_product
        def generate(store,uid,product,body,idem,validator=None):
            from journey.gateway import REQUEST
            request=REQUEST.get() or {}
            # Only the server-persisted delivery route may activate this provider.
            route=request.get('provider_route','legacy')
            if product!='temu' or request.get('source')!='temu-image-master' or request.get('channel')!='workbuddy_expert':route='legacy'
            ledger_key=hashlib.sha256(('temu:'+str(idem)).encode()).hexdigest()
            key=hashlib.sha256(('expert:v1:'+uid+':'+ledger_key).encode()).hexdigest()
            token=CONTEXT.set(dict(route=route,store=store,uid=uid,ledger_key=ledger_key,adapter_key=key))
            try:return previous_generate(store,uid,product,body,idem,validator)
            finally:CONTEXT.reset(token)
        shared.SharedStore.generate_product=generate
        previous_handler=shared.handler
        def handler(store,validator=None):
            parent=previous_handler(store,validator)
            class Handler(parent):
                def run_request(self):
                    p=urllib.parse.urlsplit(self.path)
                    prefix='/platform-api/temu/expert-input/'
                    if not p.path.startswith(prefix):return super().run_request()
                    if self.command!='GET':return self.send(405,dict(error='请求方式无效。'))
                    try:
                        q=urllib.parse.parse_qs(p.query,strict_parsing=True)
                        if set(q)!={'expires','signature'} or any(len(v)!=1 for v in q.values()):raise ValueError('Invalid input')
                        raw=adapter().read_input(p.path[len(prefix):],q['expires'][0],q['signature'][0])
                        return self.send(200,raw,'image/png')
                    except Exception:return self.send(404,dict(error='素材链接无效或已过期。'))
                do_GET=run_request
                do_POST=run_request
            return Handler
        shared.handler=handler
    sunburst.install=scoped_install
