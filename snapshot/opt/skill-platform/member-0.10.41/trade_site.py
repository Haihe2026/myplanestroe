"""Bounded public-site contacts. Pin public IPs on each hop; no proxy/credential use."""
import http.client,ipaddress,re,socket,ssl,time,threading,queue
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin
from urllib.robotparser import RobotFileParser

UA='MyPlaneStorePublicContacts/1.0 (+https://myplanestore.com)'

class Page(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.href=None;self.label=''
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href','');self.label=''
    def handle_data(self,data):
        if self.href is not None:self.label+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.href is not None:self.links.append((self.href,self.label));self.href=None

def fetch(url,deadline):
    page_deadline=min(deadline,time.monotonic()+8)
    for hop in range(4):
        u=urlsplit(url)
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.port not in (None,80,443):raise ValueError('unsafe url')
        results=queue.Queue(1)
        def resolve():
            try:results.put(socket.getaddrinfo(u.hostname,u.port or (443 if u.scheme=='https' else 80),type=socket.SOCK_STREAM))
            except Exception:results.put([])
        threading.Thread(target=resolve,daemon=True).start()
        addresses={r[4][0] for r in results.get(timeout=max(.01,page_deadline-time.monotonic()))}
        if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses):raise ValueError('private target')
        timeout=page_deadline-time.monotonic()
        if timeout<=0:raise TimeoutError()
        conn=http.client.HTTPConnection(u.hostname,port=u.port or (443 if u.scheme=='https' else 80),timeout=timeout)
        conn.sock=socket.create_connection((next(iter(addresses)),conn.port),timeout=timeout)
        if u.scheme=='https':conn.sock=ssl.create_default_context().wrap_socket(conn.sock,server_hostname=u.hostname)
        try:
            conn.request('GET',u.path+('?' +u.query if u.query else '') or '/',headers={'User-Agent':UA,'Accept':'text/html,text/plain','Connection':'close'})
            r=conn.getresponse()
            if r.status in (301,302,303,307,308):url=urljoin(url,r.getheader('Location',''));continue
            if r.status!=200:raise ValueError('site unavailable')
            if r.getheader('Content-Type','').split(';')[0] not in ('text/html','text/plain'):raise ValueError('not text')
            data=bytearray()
            while len(data)<=512000:
                remaining=page_deadline-time.monotonic()
                if remaining<=0:raise TimeoutError()
                if conn.sock:conn.sock.settimeout(remaining)
                chunk=r.read1(min(16384,512001-len(data)))
                if not chunk:break
                data.extend(chunk)
            if len(data)>512000:raise ValueError('page too large')
            return url,data.decode('utf8','replace')
        finally:conn.close()
    raise ValueError('redirects')

def contacts(website):
    out=dict(emails=[],phones=[],contact_page='',site_status='unreachable')
    if not website:return out
    deadline=time.monotonic()+20
    try:
        u=urlsplit(website);origin=u.scheme+'://'+u.netloc
        # Robots retrieval failing is a refusal to crawl, not permission.
        robot_url,rules=fetch(origin+'/robots.txt',deadline)
        if urlsplit(robot_url).hostname!=u.hostname:raise ValueError('robots changed host')
        robot=RobotFileParser();robot.parse(rules.splitlines())
        pending=[website];seen=set();emails={};phones={}
        while pending and len(seen)<4 and time.monotonic()<deadline:
            url=pending.pop(0)
            if url in seen or not robot.can_fetch(UA,url):continue
            seen.add(url);actual,html=fetch(url,deadline)
            if urlsplit(actual).hostname!=u.hostname:continue
            page=Page();page.feed(html)
            for email in re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',html):
                if not re.search(r'example\.|sentry|wixpress|\.(png|jpg|jpeg|svg|gif|webp)$',email,re.I):emails[email.lower()]=actual
            for href,label in page.links:
                if href.startswith('tel:'):phones[href[4:].strip()]=actual
                target=urljoin(actual,href)
                if urlsplit(target).hostname==u.hostname and re.search(r'contact|about|impressum|kontakt|contacto|联系',href+' '+label,re.I):
                    if not out['contact_page']:out['contact_page']=target
                    if target not in seen:pending.append(target)
            for phone in re.findall(r'\+[1-9][\d ()-]{7,20}\d',html):phones[phone]=actual
        ordered=sorted(emails,key=lambda e:(not e.endswith('@'+u.hostname.removeprefix('www.')),e))
        out.update(emails=[dict(value=e,source_url=emails[e]) for e in ordered[:5]],phones=[dict(value=p,source_url=s) for p,s in list(phones.items())[:3]],site_status='ok' if seen else 'robots_denied')
    except Exception:pass
    return out
