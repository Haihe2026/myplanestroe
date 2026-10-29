def install():
 import membership,permanent_plans
 # The user confirmed there are no old orders: expose only the new price catalog.
 membership.PLANS.clear()
 membership.PLANS.update(permanent_plans.SHARED_PLANS)
