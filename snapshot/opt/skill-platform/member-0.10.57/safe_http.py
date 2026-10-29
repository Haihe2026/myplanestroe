"""Server-only HTTPS with public DNS pinning, TLS validation and no redirects."""
import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit


class RemoteProblem(Exception):
    def __init__(self,status):self.status=status


class Pinned(http.client.HTTPSConnection):
    def __init__(self,host,ip,timeout):
        super().__init__(host,timeout=timeout,context=ssl.create_default_context())
        self.ip=ip

    def connect(self):
        sock=socket.create_connection((self.ip,443),self.timeout)
        try:self.sock=self._context.wrap_socket(sock,server_hostname=self.host)
        except Exception:sock.close();raise


def validate_url(url,api=False):
    p=urlsplit(url)
    if (p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443)
            or p.fragment or len(url)>8192):raise ValueError('Unsupported remote URL')
    if api and (p.netloc!='www.aisplice.store' or not p.path.startswith('/v1/')):
        raise ValueError('Unsupported API origin')
    return p


def request(url,method='GET',body=None,key=None,idem=None,limit=2_000_000,timeout=20):
    p=validate_url(url,api=key is not None)
    addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
    ips=list(dict.fromkeys(r[4][0] for r in addresses))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError('Non-public remote address')
    ip=next((ip for ip in ips if ':' not in ip),ips[0])
    headers={'Accept':'application/json' if key else 'image/*','User-Agent':'MyPlaneStore-Image/1.0'}
    data=json.dumps(body,separators=(',',':')).encode() if body is not None else None
    if data is not None:headers['Content-Type']='application/json'
    if key:headers['Authorization']='Bearer '+key
    if idem:headers['Idempotency-Key']=idem
    conn=Pinned(p.hostname,ip,timeout)
    try:
        conn.request(method,p.path+('?' + p.query if p.query else ''),body=data,headers=headers)
        r=conn.getresponse()
        if r.status<200 or r.status>=300:raise RemoteProblem(r.status)
        length=r.getheader('Content-Length')
        if length and int(length)>limit:raise ValueError('Remote payload too large')
        raw=r.read(limit+1)
        if len(raw)>limit:raise ValueError('Remote payload too large')
        return raw
    finally:conn.close()
