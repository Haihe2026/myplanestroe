"""Bust stale admin bundles together; preserve existing response/auth behavior."""
import re
BUILD='0.10.55'
def rewrite(html):
 text=html.decode('utf8')
 text=re.sub(r"""((?:src|href)=["'])(/ops/[^"'?]+\.(?:js|css))(?:\?[^"']*)?(["'])""",lambda m:m[1]+m[2]+'?v='+BUILD+m[3],text)
 text=re.sub(r'(<small id="ops-build">)[^<]*(</small>)',lambda m:m[1]+'v'+BUILD+m[2],text)
 return text.encode('utf8')
def extend(factory):
 def build(*args,**kwargs):
  parent=factory(*args,**kwargs)
  class Handler(parent):
   def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
    if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=rewrite(result)
    return super().send(status,result,mime,cookie=cookie)
  return Handler
 return build
