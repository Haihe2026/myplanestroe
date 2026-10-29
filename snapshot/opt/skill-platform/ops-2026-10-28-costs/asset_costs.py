"""Presentation-only cost catalogue. Never resolve, copy or rotate supplier keys."""
from pathlib import Path
from decimal import Decimal
import json,urllib.request
ROOT=Path(__file__).resolve().parent
def costs():return json.loads((ROOT/'cost-catalog.json').read_text(encoding='utf8'))
def video_ready():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8791/platform-api/grok-video/health',timeout=1.5) as r:raw=r.read(16385)
        if len(raw)>16384:return None
        d=json.loads(raw);return d.get('customer_generation_enabled') if type(d.get('customer_generation_enabled'))is bool else None
    except Exception:return None
def public_cost(catalog,aid):
    value=catalog.get(aid)
    if not value:return None
    out=dict(value,rates=[dict(r) for r in value['rates']])
    if aid=='grok-imagine-1.5-video':
        out['examples']=[dict(label=r['label'],duration_seconds=6,amount=str(Decimal(r['amount'])*6)) for r in out['rates']]
    return out
def install(cls):
    if getattr(cls,'_cost_display_installed',False):return
    original_public=cls.public;original_listing=cls.listing
    def public(self,row):
        item=original_public(self,row);item['cost']=public_cost(costs(),item['id']);return item
    def listing(self):
        result=original_listing(self);catalog=costs();aid='grok-imagine-1.5-video'
        # This is explicitly a cost-only row, not a newly registered credential.
        # Existing save/archive/resolve operations continue to use real registry rows.
        if not any(i['id']==aid for i in result['items']):
            ready=video_ready()
            result=dict(result,items=[*result['items'],dict(id=aid,name='Grok Imagine 1.5 视频服务',kind='video',model=aid,base_url='https://www.aisplice.store',docs_url='https://www.aisplice.store/docs',auth_type='原视频服务管理',auth_header='',secret_hint='由原视频服务管理',secret_configured=False,enabled=ready is True,status_unknown=ready is None,cost_only=True,notes='现有视频服务的成本展示；不在本行编辑KEY、启停或归档。',cost=public_cost(catalog,aid))])
        return result
    cls.public=public;cls.listing=listing;cls._cost_display_installed=True
