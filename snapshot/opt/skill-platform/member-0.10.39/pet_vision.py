"""Supplier-neutral contract; no supplier implementation or prompt diagnosis here."""
from pathlib import Path
import os,re,stat,hashlib
class NotConfigured(Exception):pass
class Vision:
    def __init__(self,adapter=None,review=None):
        if adapter is None:
            import pet_vision_adapter
            if pet_vision_adapter.configured:adapter=pet_vision_adapter.analyze
        if review is None:
            import pet_triage
            if pet_triage.configured:review=pet_triage.review
        self.adapter,self.review=adapter,review;self._key=None
        p=Path(os.environ.get('PET_VISION_KEY_FILE','/etc/skill-platform/pet-vision.key'))
        if os.environ.get('PET_VISION_CONFIRMED','').lower() not in ('yes','true','1'):return
        try:
            s=p.stat()
            if os.name=='posix' and (stat.S_IMODE(s.st_mode)!=0o600 or s.st_uid!=os.geteuid()):return
            key=p.read_text(encoding='utf8').strip()
            if not re.fullmatch(r'[A-Za-z0-9_.-]{16,512}',key):return
            self._key=key
        except (OSError,UnicodeError):return
    @property
    def ready(self):return bool(self._key and self.adapter and self.review)
    def analyze(self,image,prompt):
        if not self.ready:raise NotConfigured('照片分析暂未开放')
        # adapter: bytes + prompt + private credential -> text, review: text -> safe text.
        # No default permissive reviewer: red-line policy must be installed and tested first.
        text=self.adapter(image,prompt,self._key)
        safe=self.review(text)
        if not isinstance(safe,str) or not safe.strip():raise ValueError('analysis_rejected')
        return safe+'\n照片无法替代检查；照片不能排除急症。'

def execute(billing,vision,uid,image,prompt):
    if not vision.ready:raise billing.Problem(503,'照片分析暂未开放')
    if not isinstance(image,bytes) or not 0<len(image)<=8*1024*1024 or not isinstance(prompt,str) or len(prompt)>4000:raise billing.Problem(400,'图片或提示词格式无效')
    # Same photo for the same user has one analysis task, irrespective of client retry key.
    digest=hashlib.sha256(image).hexdigest()
    job=billing.reserve_photo(uid,'photo_'+digest,digest)
    if job['state']!='reserved':return {'id':job['id'],'state':job['state'],'duplicate':True}
    # An atomic claim prevents concurrent HTTP retries from invoking the provider twice.
    with billing.store.connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS pet_photo_execution(job_id TEXT PRIMARY KEY)')
        owner=c.execute('INSERT OR IGNORE INTO pet_photo_execution VALUES(?)',(job['id'],)).rowcount
    if not owner:return {'id':job['id'],'state':'reserved','duplicate':True}
    try:text=vision.analyze(image,prompt)
    except Exception:
        # Confirmed failure/refusal/timeout releases the reservation, never image funds.
        billing.finish_photo(uid,job['id'],'failed')
        raise billing.Problem(503,'照片分析未完成，次数已释放')
    billing.finish_photo(uid,job['id'],'succeeded')
    return {'id':job['id'],'state':'succeeded','text':text}
