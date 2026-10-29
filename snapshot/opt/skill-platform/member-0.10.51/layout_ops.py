from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
def extend(factory,path):
 def build(*args,**kwargs):
  parent=factory(*args,**kwargs)
  class Handler(parent):
   def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
    if status==200 and mime.startswith('text/html') and isinstance(result,bytes):result=result.replace(b'</head>',b'<script defer src="/ops/users-first.js?v=0.10.51"></script></head>',1)
    return super().send(status,result,mime,cookie=cookie)
   def do_GET(self):
    if urlsplit(self.path).path=='/ops/users-first.js':return self.send(200,(ROOT/'users-first.js').read_bytes(),'application/javascript; charset=utf-8')
    return super().do_GET()
  return Handler
 return build
