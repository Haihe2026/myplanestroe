"""Fixed new provider for the real child Skill source; all other routes untouched."""
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import urlsplit,parse_qs
from child_resource import Adapter,SIZES

ROOT=Path(__file__).resolve().parent
SOURCE='jyai-baby-growth-album'
CHANNELS=('workbuddy_skill','workbuddy_expert','skillhub')
ENGINE='gemini-personal-sunburst'
CONTEXT=ContextVar('child_resource_request',default=None)
_adapter=None
_adapter_lock=threading.Lock()


def adapter():
    global _adapter
    with _adapter_lock:
        if _adapter is None:_adapter=Adapter()
        return _adapter


def policy():
    p=Path(os.environ.get('CHILD_RESOURCE_POLICY_FILE',ROOT/'child-policy.json'))
    return json.loads(p.read_text(encoding='utf8'))


def selected(product,ctx):
    return product=='gemini' and ctx.get('source')==SOURCE and ctx.get('channel') in CHANNELS


def install(server,shared,sunburst):
    from journey import store as journey_store
    journey_store.SOURCES=journey_store.SOURCES|{SOURCE}
    # Apply the capability projection immediately before the original HTTP writer.
    # Outer legacy sunburst.send() otherwise replaces the whole engines dictionary.
    original_http=server.handler
    def health_handler(store):
        parent=original_http(store)
        class Health(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None,download=None):
                if status==200 and urlsplit(self.path).path=='/platform-api/gemini/health' and isinstance(result,dict):
                    ctx={'source':self.headers.get('X-Skill-Source'),'channel':self.headers.get('X-Skill-Channel')}
                    if selected('gemini',ctx):
                        ready=policy().get('enabled') is True and adapter().ready
                        engines=dict(result.get('image_engines',{}))
                        engines[ENGINE]=dict(configured=ready,reference_editing=True,text_to_image=True,
                            sizes=list(SIZES),resolution='1K',async_jobs=True,contract='child-photo-resource-v1')
                        result=dict(result,image_engines=engines)
                return super().send(status,result,mime,cookie,download)
        return Health
    server.handler=health_handler
    original=sunburst.Provider
    class Scoped(original):
        # Wrapping rather than replacing the legacy object preserves every original
        # ready setter and any Temu-scoped wrapper installed later in the chain.
        def __init__(self,*a,**kw):self.legacy=original(*a,**kw)
        @property
        def ready(self):return adapter().ready if CONTEXT.get() else self.legacy.ready
        @property
        def last_usage(self):return None if CONTEXT.get() else self.legacy.last_usage
        def generate(self,prompt,size):
            ctx=CONTEXT.get()
            if not ctx:return self.legacy.generate(prompt,size)
            return execute(ctx,prompt,size,())
        def edit(self,prompt,size,images):
            ctx=CONTEXT.get()
            if not ctx:return self.legacy.edit(prompt,size,images)
            return execute(ctx,prompt,size,images)
    def execute(ctx,prompt,size,images):
        store=ctx['store']
        with store.connect() as c:
            row=c.execute('SELECT id FROM jobs WHERE user_id=? AND idem=?',(ctx['uid'],ctx['ledger_key'])).fetchone()
        if not row:raise ValueError('Original reservation missing')
        return adapter().execute(ctx['key'],ctx['uid'],row['id'],prompt,size,images)
    sunburst.Provider=Scoped
    previous_install=sunburst.install
    def scoped_install(*a,**kw):
        already=getattr(shared,'_sunburst_installed',False)
        previous_install(*a,**kw)
        if already:return
        previous=shared.SharedStore.generate_product
        # Striped locks serialize route selection with reservation and prevent a
        # concurrent duplicate from racing the old-task/no-route decision.
        locks=[threading.RLock() for _ in range(64)]
        def generate(store,uid,product,body,idem,validator=None):
            from journey.gateway import REQUEST
            ctx=REQUEST.get() or {}
            if not selected(product,ctx):return previous(store,uid,product,body,idem,validator)
            if not isinstance(idem,str) or not 16<=len(idem)<=100:raise server.Problem(400,'任务标识无效')
            ledger_key=hashlib.sha256((product+':'+idem).encode()).hexdigest()
            key=hashlib.sha256(('child-resource:v1:'+uid+':'+ledger_key).encode()).hexdigest()
            lock=locks[int(key[:8],16)%len(locks)]
            with lock:
                resource=adapter()
                task=resource.row(key)
                with store.connect() as c:
                    old=c.execute('SELECT id,status FROM jobs WHERE user_id=? AND idem=?',(uid,ledger_key)).fetchone()
                # Existing pre-layer tasks must retain their original request hash,
                # model and query identity. They are never sent to the new provider.
                if old and not task:return previous(store,uid,product,body,idem,validator)
                if not isinstance(body,dict) or body.get('image_engine')!=ENGINE:
                    raise server.Problem(400,'本技能图片方案需要更新，未提交新任务')
                if body.get('size','1024x1024') not in SIZES:
                    raise server.Problem(400,'图片尺寸不支持，未提交新任务')
                if not task and (policy().get('enabled') is not True or not resource.ready):
                    raise server.Problem(503,'图片服务暂不可用，方案已保留，请稍后继续')
                token=CONTEXT.set(dict(store=store,uid=uid,key=key,ledger_key=ledger_key))
                try:
                    result=previous(store,uid,product,body,idem,validator)
                    # The compatibility engine name stays stable; do not advertise
                    # the old Sunburst model as the model that actually executed.
                    result={k:v for k,v in result.items() if k!='model'}
                    result['contract']='child-photo-resource-v1'
                    current=resource.row(key)
                    if current and result.get('status')=='succeeded':resource.stage(key,'succeeded')
                    elif current and current['stage']=='failed' and result.get('status')=='pending':
                        # Only a definite upstream rejection can use the established
                        # failure-release mechanism. Unknown results stay pending.
                        store.refund_confirmed_failure(result['id'])
                        resource.stage(key,'settled_failed')
                        result=dict(result,status='failed',notice='本次制作未完成，次数已退回，请查看原任务')
                    return result
                finally:CONTEXT.reset(token)
        shared.SharedStore.generate_product=generate
    sunburst.install=scoped_install


def wrap_handler(parent,store,server):
    """Called after retention/consent/Journey have installed their store wrappers."""
    if not getattr(store,'_child_recovery_started',False):
        store._child_recovery_started=True
        def loop():
            while True:
                time.sleep(5)
                try:adapter().recover(store)
                except Exception:pass
        threading.Thread(target=loop,name='child-photo-recovery',daemon=True).start()
    class Handler(parent):
        def run_request(self):
            p=urlsplit(self.path)
            ctx={'source':self.headers.get('X-Skill-Source'),'channel':self.headers.get('X-Skill-Channel')}
            if (self.command=='POST' and p.path in ('/platform-api/gemini/jobs','/platform-api/gemini/skill-jobs')
                    and selected('gemini',ctx) and self.headers.get('Origin') not in (None,'https://myplanestore.com')):
                return self.send(403,dict(error='请从本站或原技能操作'))
            prefix='/platform-api/gemini/child-resource-input/'
            if not p.path.startswith(prefix):return super().run_request()
            if self.command!='GET':return self.send(405,dict(error='请求方式无效'))
            try:
                q=parse_qs(p.query,strict_parsing=True)
                if set(q)!={'expires','signature'} or any(len(v)!=1 for v in q.values()):raise ValueError()
                raw=adapter().read_input(p.path[len(prefix):],q['expires'][0],q['signature'][0])
                return self.send(200,raw,'image/png')
            except Exception:return self.send(404,dict(error='素材链接无效或已过期'))
        do_GET=run_request
        do_POST=run_request
    return Handler
