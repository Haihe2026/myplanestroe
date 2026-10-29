"""Extend only the approved price catalog; identity/reply verification stays original."""
from permanent_plans import TEMU_PLANS, LEGACY_TEMU_PLANS, SHARED_PLANS
CATALOG = {key: (p['price_fen'],p['images']) for key,p in {**LEGACY_TEMU_PLANS,**TEMU_PLANS}.items()}
NAMES = {key:p['name'] for key,p in {**LEGACY_TEMU_PLANS,**TEMU_PLANS}.items()}


def install(settlement,worker):
    from permanent_plans import PLANS
    settlement.PLANS.update({key: (p['price_fen'], p['images']) for key, p in PLANS.items()})
    worker.PLAN_NAMES.update({key: p['name'] for key, p in PLANS.items()})
    settlement.PLANS.update(CATALOG)
    worker.PLAN_NAMES.update(NAMES)
    settlement.PLANS.update({key: (p['price_fen'], p['images']) for key, p in SHARED_PLANS.items()})
    worker.PLAN_NAMES.update({key: p['name'] for key, p in SHARED_PLANS.items()})
    original=settlement.EmailSettlement.read_order
    def read_order(self,namespace,oid,db=None):
        result=original(self,namespace,oid,db)
        if result['plan'] in SHARED_PLANS and (namespace!='shared' or result['source_product'] not in ('gemini','temu','xhs')):
            raise ValueError('shared_plan_wrong_source')
        if result['plan'] in PLANS and (namespace!='shared' or result['source_product'] not in ('gemini','xhs')):
            raise ValueError('permanent_plan_wrong_source')
        if result['plan'] in CATALOG and (namespace!='shared' or result['source_product']!='temu'):
            raise ValueError('enterprise_plan_wrong_source')
        return result
    settlement.EmailSettlement.read_order=read_order
