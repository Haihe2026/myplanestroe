"""All executable image providers use one resource. Never read old image keys."""
from contextvars import ContextVar
import hashlib,http.client,json,os,threading,time
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from child_resource import Adapter as PriorAdapter,SIZES

ROOT=Path(__file__).resolve().parent
CONTEXT=ContextVar('new_only_reserved_task',default=None)
ROUTE='all-new-resource-v1'
NAMESPACES=('shared','legacy-gemini','legacy-temu','pack')
_adapters={};_lock=threading.RLock()

def enabled():
    try:return json.loads(Path(os.environ.get('NEW_ONLY_POLICY_FILE',ROOT/'new-only-policy.json')).read_text())['enabled'] is True
    except Exception:return False

class Adapter(PriorAdapter):
    def __init__(self,namespace,**kw):
        self.namespace=namespace
        if namespace not in NAMESPACES:raise ValueError('Unknown ledger namespace')
        kw.setdefault('root',Path(os.environ.get('NEW_ONLY_DATA_DIR','/var/lib/skill-platform/all-new-resource'))/namespace)
        super().__init__(**kw)
    def signed_input(self,i,expires):
        import hmac
        sig=hmac.new(self.signer,('new-only-input:v1:'+self.namespace+':'+i+':'+str(expires)).encode(),hashlib.sha256).hexdigest()
        return 'https://myplanestore.com/platform-api/image-resource/input/'+self.namespace+'/'+i+'?expires='+str(expires)+'&signature='+sig

def adapter(namespace):
    with _lock:
        if namespace not in _adapters:_adapters[namespace]=Adapter(namespace)
        return _adapters[namespace]

def deny_old_transport():
    # Unset the obsolete image-only variable without retrieving its value. Keep
    # the operator's files/backups intact; other text/vision credentials are untouched.
    try:del os.environ['IMAGE_PROVIDER_KEY']
    except KeyError:pass
    if getattr(http.client.HTTPConnection.putrequest,'_new_only',False):return
    previous=http.client.HTTPConnection.putrequest
    def putrequest(self,method,url,*a,**kw):
        host=str(self.host).lower().split(':')[0]
        p=urlsplit(url)
        host=p.hostname or host
        if host=='file.hfsyapi.cn' or p.path.startswith('/v1/images') and host!='www.aisplice.store':
            raise RuntimeError('Historical image transport disabled')
        return previous(self,method,url,*a,**kw)
    putrequest._new_only=True
    http.client.HTTPConnection.putrequest=putrequest

class Provider:
    def __init__(self,namespace):self.namespace=namespace
    @property
    def ready(self):return enabled() and adapter(self.namespace).ready
    @property
    def edit_ready(self):return self.ready
    @property
    def last_usage(self):return None
    def __call__(self,prompt,size):
        images=()
        try:
            import shared_platform
            images=shared_platform.TEMU_IMAGES.get()
        except (ImportError,AttributeError):pass
        # The isolated legacy Temu core passes references through its own context.
        if self.namespace=='legacy-temu':
            import server
            images=server.REFERENCES.get()
        return self.edit(prompt,size,images)
    def edit(self,prompt,size,images):
        ctx=CONTEXT.get()
        if not ctx or ctx['namespace']!=self.namespace:raise RuntimeError('Original reservation required')
        store=ctx['store']
        with store.connect() as c:row=c.execute('SELECT id FROM jobs WHERE user_id=? AND idem=?',(ctx['uid'],ctx['idem'])).fetchone()
        if not row:raise RuntimeError('Original reservation missing')
        try:
            import image_retention
            portrait=image_retention.REQUEST.get()
        except ImportError:portrait=None
        if portrait and portrait.get('portrait'):
            prompt=prompt.replace('Edit the supplied product photos. Preserve visible geometry, color, material, labels, quantity and accessories. Do not invent hidden surfaces or change the SKU. New text is added in post-production, not painted by the model.','Edit the supplied authorized portrait references. Preserve the depicted person identity and natural facial characteristics.')
        return adapter(self.namespace).execute(ctx['key'],ctx['uid'],row['id'],prompt,size,images)

def disable_old_constructor(module,namespace):
    """Before any original Store init: no old env/file credential is inspected."""
    if not hasattr(module,'Provider'):return
    cls=module.Provider
    def init(self,*a,**kw):self.ready=False;self.edit_ready=False;self.last_usage=None
    cls.__init__=init
    cls.ready=property(lambda self:Provider(namespace).ready,lambda self,value:None)
    cls.edit_ready=property(lambda self:Provider(namespace).ready,lambda self,value:None)
    cls.__call__=lambda self,prompt,size:Provider(namespace)(prompt,size)
    cls.generate=lambda self,prompt,size:Provider(namespace)(prompt,size)
    cls.edit=lambda self,prompt,size,images:Provider(namespace).edit(prompt,size,images)

def wrap_store(store,core,namespace,shared=False):
    if getattr(store,'_new_only_wrapped',False):return
    store._new_only_wrapped=True
    store.provider=Provider(namespace)
    # SharedStore.generate_product uses super().generate, so wrap the concrete
    # base class after the historic accounting/Journey installers have completed.
    base=core.Store
    if not getattr(base.generate,'_new_only',False):
        previous=base.generate
        locks=[threading.RLock() for _ in range(64)]
        def generate(actual,uid,body,idem,*a,**kw):
            ns=getattr(actual,'_new_only_namespace',namespace)
            key=hashlib.sha256(('new-only:v1:'+ns+':'+uid+':'+str(idem)).encode()).hexdigest()
            with locks[int(key[:8],16)%len(locks)]:
                with actual.connect() as c:old=c.execute('SELECT id FROM jobs WHERE user_id=? AND idem=?',(uid,idem)).fetchone()
                resource=adapter(ns)
                historical=old and not resource.row(key)
                if not historical and not enabled():raise core.Problem(503,'图片服务暂不可用，请保留原任务')
                if not isinstance(body,dict) or body.get('size','1024x1024') not in SIZES:
                    raise core.Problem(503,'该图片规格暂未开放，请保留原方案稍后继续；未扣次数')
                token=CONTEXT.set(dict(store=actual,uid=uid,idem=idem,key=key,namespace=ns))
                try:
                    result=previous(actual,uid,body,idem,*a,**kw)
                    current=resource.row(key)
                    if current and result.get('status')=='succeeded':resource.stage(key,'succeeded')
                    elif current and current['stage']=='failed' and result.get('status')=='pending':
                        actual.refund_confirmed_failure(result['id']);resource.stage(key,'settled_failed')
                        result=dict(result,status='failed',notice='本次制作未完成，次数已退回')
                    return result
                finally:CONTEXT.reset(token)
        generate._new_only=True;base.generate=generate
    store._new_only_namespace=namespace
    def loop():
        while True:
            time.sleep(5)
            try:adapter(namespace).recover(store)
            except Exception:pass
    threading.Thread(target=loop,name='new-only-recovery-'+namespace,daemon=True).start()

def health_writer(core,namespace):
    previous=core.handler
    def handler(store):
        parent=previous(store)
        class Handler(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None,download=None):
                path=urlsplit(self.path).path
                health_paths=('/platform-api/gemini/health','/platform-api/temu/health') if namespace=='shared' else ('/health','/temu/health','/quota-pack/gemini/health')
                if status==200 and path in health_paths and isinstance(result,dict):
                    ready=Provider(namespace).ready
                    engines={k:dict({field:value for field,value in v.items() if field!='model'},configured=ready) for k,v in result.get('image_engines',{}).items()}
                    # Child 1.2.0's required public contract remains stable.
                    if self.headers.get('X-Skill-Source')=='jyai-baby-growth-album':
                        engines['gemini-personal-sunburst']=dict(engines.get('gemini-personal-sunburst',{}),configured=ready,text_to_image=True,reference_editing=True,resolution='1K',contract='child-photo-resource-v1',sizes=list(SIZES),async_jobs=True)
                    result=dict(result,provider_configured=ready,reference_editing=ready,image_resource_contract=ROUTE)
                    if engines:result['image_engines']=engines
                if status in (200,202) and isinstance(result,dict) and self.command=='POST' and creation_path(path):
                    result={k:v for k,v in result.items() if k!='model'}
                    result['image_resource_contract']=ROUTE
                return super().send(status,result,mime,cookie,download)
        return Handler
    core.handler=handler

def shared_handler(parent,store,core):
    wrap_store(store,core,'shared',True)
    class Handler(parent):
        def run_request(self):
            p=urlsplit(self.path);prefix='/platform-api/image-resource/input/'
            if not enabled() and self.command=='POST' and creation_path(p.path):
                return self.send(503,dict(error='图片服务暂不可用，请保留原任务'))
            if not p.path.startswith(prefix):return super().run_request()
            try:
                if self.command!='GET':return self.send(405,dict(error='请求方式无效'))
                ns,i=p.path[len(prefix):].split('/');q=parse_qs(p.query,strict_parsing=True)
                if ns not in NAMESPACES or set(q)!={'expires','signature'} or any(len(v)!=1 for v in q.values()):raise ValueError()
                return self.send(200,adapter(ns).read_input(i,q['expires'][0],q['signature'][0]),'image/png')
            except Exception:return self.send(404,dict(error='素材链接无效或过期'))
        do_GET=run_request
        do_POST=run_request
    return Handler

def creation_path(path):return path.endswith(('/jobs','/skill-jobs','/render-jobs','/v1/images/generations'))

def guard_handler(parent,always=True):
    class Handler(parent):
        def run_request(self):
            path=urlsplit(self.path).path
            if (always or not enabled()) and self.command=='POST' and creation_path(path):
                return self.send(503,dict(error='图片服务暂不可用，请保留原任务'))
            return super().run_request()
        do_GET=run_request
        do_POST=run_request
    return Handler
