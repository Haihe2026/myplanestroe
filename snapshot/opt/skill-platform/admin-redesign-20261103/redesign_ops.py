"""Static admin presentation layer only. Preserve all original authentication and routes."""
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent

def extend(factory,path):
    def build(*args,**kwargs):
        parent=factory(*args,**kwargs)
        class Handler(parent):
            def send(self,status,result,mime='application/json; charset=utf-8',cookie=None):
                if status==200 and mime.startswith('text/html') and isinstance(result,bytes):
                    result=result.replace(b'</head>',b'<link rel="stylesheet" href="/ops/admin-redesign.css?v=20261103"><script defer src="/ops/admin-redesign.js?v=20261103"></script></head>',1)
                return super().send(status,result,mime,cookie=cookie)
            def do_GET(self):
                name=urlsplit(self.path).path
                if name in ('/ops/admin-redesign.js','/ops/admin-redesign.css'):
                    p=ROOT/name.rsplit('/',1)[-1]
                    return self.send(200,p.read_bytes(),('text/css' if p.suffix=='.css' else 'application/javascript')+'; charset=utf-8')
                return super().do_GET()
        return Handler
    return build
