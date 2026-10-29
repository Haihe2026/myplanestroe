"""Preserve the original legacy service; recognize its migrated permanent grants."""
import api_access
import runpy
import sys

# The local module changes only the NULL-expiry eligibility predicate.
sys.path.insert(0,'/opt/skill-platform/member-0.5.0/service')
runpy.run_path('/opt/skill-platform/member-0.5.0/service/run_legacy.py',run_name='__main__')
