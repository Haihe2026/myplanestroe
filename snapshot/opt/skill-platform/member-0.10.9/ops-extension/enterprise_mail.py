"""Extend only the approved price catalog; identity/reply verification stays original."""
CATALOG = {'temu_enterprise_89': (8900,100), 'temu_enterprise_198': (19800,240), 'temu_enterprise_365': (36500,500)}
NAMES = {'temu_enterprise_89':'企业入门', 'temu_enterprise_198':'企业成长', 'temu_enterprise_365':'企业批量'}


def install(settlement,worker):
    from permanent_plans import PLANS
    settlement.PLANS.update({key: (p['price_fen'], p['images']) for key, p in PLANS.items()})
    worker.PLAN_NAMES.update({key: p['name'] for key, p in PLANS.items()})
    settlement.PLANS.update(CATALOG)
    worker.PLAN_NAMES.update(NAMES)
    original=settlement.EmailSettlement.read_order
    def read_order(self,namespace,oid,db=None):
        result=original(self,namespace,oid,db)
        if result['plan'] in PLANS and (namespace!='shared' or result['source_product'] not in ('gemini','xhs')):
            raise ValueError('permanent_plan_wrong_source')
        if result['plan'] in CATALOG and (namespace!='shared' or result['source_product']!='temu'):
            raise ValueError('enterprise_plan_wrong_source')
        return result
    settlement.EmailSettlement.read_order=read_order
