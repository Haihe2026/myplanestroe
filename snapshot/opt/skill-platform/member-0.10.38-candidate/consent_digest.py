"""Shared client/server digest of the exact generation payload; no file paths or image uploads here."""
import base64,hashlib,json

def task_digest(product,idem,body):
 if product not in ('gemini','temu') or not isinstance(idem,str) or not 16<=len(idem)<=100 or not isinstance(body,dict):raise ValueError('Invalid task identity')
 normalized=dict(body);normalized.pop('photo_consent',None)
 if 'references' in normalized:
  refs=normalized['references']
  if not isinstance(refs,list) or not 1<=len(refs)<=3:raise ValueError('Invalid reference list')
  converted=[]
  for ref in refs:
   if not isinstance(ref,dict) or set(ref)!={'mime','content'} or ref['mime'] not in ('image/png','image/jpeg') or not isinstance(ref['content'],str) or len(ref['content'])>7*1024*1024:raise ValueError('Invalid reference')
   raw=base64.b64decode(ref['content'],validate=True)
   converted.append({'mime':ref['mime'],'sha256':hashlib.sha256(raw).hexdigest()})
  normalized['references']=converted
 encoded=json.dumps({'gateway':product,'idempotency_key':idem,'request':normalized},sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
 return hashlib.sha256(encoded).hexdigest()
