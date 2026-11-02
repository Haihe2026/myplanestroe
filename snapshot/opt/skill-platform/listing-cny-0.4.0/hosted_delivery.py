"""Host-generated text contract: structural validation, not a factual/model attestation.

The host supplies actual finished text. The server checks immutable scope, all
targets and platform field completeness, then core persists all artifacts in the
same transaction as settlement. Client success flags cannot authorize billing.
This cannot prevent a readable Skill being copied or a host skipping the API.
"""
from listing_store import Error,canonical,sha

FIELDS={
 'amazon':('title','bullets','description','keywords','checks'),
 'temu':('title','description','keywords','checks'),
 'tiktok-shop':('title','description','keywords','checks'),
 'shopify':('title','description','seo_title','meta_description','url_handle','checks'),
 'shopee':('title','description','attributes','variants','checks'),
 'etsy':('title','description','tags','attributes','checks'),
 'ebay':('title','description','item_specifics','condition','checks'),
 'independent-site':('title','description','checks')}

class HostedDelivery:
 ready=True
 def recover_verified(self,task,evidence,scope):
  if not isinstance(evidence,dict) or set(evidence)!={'scope_hash','deliveries'} or evidence['scope_hash']!=sha(canonical(scope)):
   raise Error(409,'SCOPE_EVIDENCE_MISMATCH')
  rows=evidence['deliveries']
  if not isinstance(rows,list) or len(rows)!=len(scope['targets']):raise Error(409,'INCOMPLETE_BUNDLE')
  expected={canonical(t) for t in scope['targets']};seen=set()
  for row in rows:
   if not isinstance(row,dict) or set(row)!={'target','content'} or canonical(row['target']) not in expected or canonical(row['target']) in seen:
    raise Error(409,'INCOMPLETE_BUNDLE')
   seen.add(canonical(row['target']));content=row['content']
   if not isinstance(content,dict) or set(content)-set(FIELDS[row['target']['platform']]):raise Error(400,'INVALID_DELIVERY_FIELDS')
   for name in FIELDS[row['target']['platform']]:
    v=content.get(name)
    if isinstance(v,str):valid=1<=len(v.strip())<=20000
    elif isinstance(v,list):valid=1<=len(v)<=100 and all(isinstance(x,str) and 1<=len(x.strip())<=2000 for x in v)
    elif isinstance(v,dict):valid=1<=len(v)<=100 and all(isinstance(k,str) and isinstance(x,str) and 1<=len(k)<=100 and 1<=len(x)<=2000 for k,x in v.items())
    else:valid=False
    if not valid:raise Error(409,'INCOMPLETE_PLATFORM_FIELDS')
  return dict(artifact_id='listing-'+task+'-'+sha(canonical(evidence))[:16],scope_hash=evidence['scope_hash'],deliveries=rows)
