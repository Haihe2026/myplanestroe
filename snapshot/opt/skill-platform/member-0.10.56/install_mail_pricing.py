def install(settlement,worker):
 from permanent_plans import SHARED_PLANS,TEMU_PLANS
 catalog={**SHARED_PLANS,**TEMU_PLANS}
 settlement.PLANS.clear();settlement.PLANS.update({key:(p['price_fen'],p['images']) for key,p in catalog.items()})
 worker.PLAN_NAMES.clear();worker.PLAN_NAMES.update({key:p['name'] for key,p in catalog.items()})
