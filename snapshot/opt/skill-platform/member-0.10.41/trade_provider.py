"""Network boundary: fixed RockApis host, persistent budgets, separate mock caches.
No real provider is ever called by a test. Header names must distinguish credits
from requests; a missing credit header locks further requests rather than guessing.
"""
import hashlib,json,os,re,time,uuid,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from trade_store import Error
from trade_config import COUNTRIES
from trade_mapping import jobs,profile,people,rows,val,text,MappingError

HOST='linkedin-api8.p.rapidapi.com'
ENDPOINTS={'/search-locations','/search-jobs','/get-company-details','/search-people'}

def redact(obj):
    if isinstance(obj,dict):
        return {k:('[REDACTED]' if re.search(r'key|token|secret|authoriz|cookie|email|phone|mobile|telephone',str(k),re.I) else redact(v)) for k,v in obj.items()}
    if isinstance(obj,list):return [redact(x) for x in obj]
    if isinstance(obj,str):
        obj=re.sub(r'[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]',obj)
        obj=re.sub(r'(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)', '[PHONE]',obj)
        key=os.environ.get('RAPIDAPI_KEY')
        return obj.replace(key,'[KEY]') if key else obj
    return obj

class MockProvider:
    """Synthetic data only. Has no transport and cannot touch the real provider."""
    def __init__(self,store,uid=None,ref=None):self.store,self.uid,self.ref=store,uid,ref
    def log(self,endpoint,key,data):
        now=int(time.time())
        with self.store.connect() as c:
            hit=c.execute('SELECT 1 FROM trade_cache WHERE provider=\'mock\' AND key=? AND expires>?',(key,now)).fetchone()
            c.execute("INSERT OR REPLACE INTO trade_cache VALUES('mock',?,?,?)",(key,json.dumps(data),now+86400))
            c.execute("INSERT INTO trade_upstream(provider,endpoint,cache_hit,http_status,latency_ms,account_id,ref_id,created_at,is_test) VALUES('mock',?,?,200,0,?,?,?,1)",(endpoint,int(bool(hit)),self.uid,self.ref,now))
        return data
    def search_jobs(self,keyword,country,page):
        data=[] if keyword=='zzz' else [dict(company_id='synthetic-northwind',name='Synthetic Northwind Trade',linkedin_url='https://www.linkedin.com/company/synthetic-northwind',location=country,jobs=[dict(title='Sourcing Buyer',url='',posted_at='2026-10-25',buyer_role=True)])]
        return self.log('/search-jobs','jobs:'+keyword+country+str(page),data)
    def company_profile(self,cid):
        data=None if cid=='ghost' else dict(company_id=cid,name='Synthetic Northwind Trade',website='',industry='Synthetic goods',size='51-200',headquarters='Synthetic City',type='Private',description='合成测试公司，不是真实客户',similar=[],public_contacts=dict(emails=[],phones=[],contact_page='',site_status='unreachable'))
        return self.log('/get-company-details','company:'+cid,data)
    def company_employees(self,cid,limit):
        data=[] if cid=='empty' else [dict(name='Synthetic Buyer '+str(i),title='Purchasing Manager',linkedin_url='https://www.linkedin.com/in/synthetic-'+str(i),location='Synthetic City') for i in range(min(2,limit))]
        return self.log('/search-people','people:'+cid+str(limit),data)

class RockApis:
    def __init__(self,store,uid=None,ref=None,transport=None,clock=time.time):
        self.store,self.uid,self.ref,self.clock=store,uid,ref,clock
        self.injected_transport=transport is not None
        self.transport=transport or self.http
        self.month=datetime.fromtimestamp(clock(),ZoneInfo('Asia/Shanghai')).strftime('%Y-%m')
    def http(self,endpoint,params):
        key=os.environ.get('RAPIDAPI_KEY','')
        if not key:raise Error(503,'UPSTREAM_ERROR','服务暂未配置')
        req=urllib.request.Request('https://'+HOST+endpoint+'?'+urlencode(params),headers={'x-rapidapi-key':key,'x-rapidapi-host':HOST,'User-Agent':'MyPlaneStore/0.10.41'})
        # Never follow a redirect with a credential-bearing request.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*a,**k):return None
        def decode(raw):
            try:return json.loads(raw)
            except (ValueError,UnicodeError):return {'unparsed_text':raw.decode('utf8','replace')}
        try:
            with urllib.request.build_opener(NoRedirect()).open(req,timeout=25) as r:
                raw=r.read(1024*1024+1)
                if len(raw)>1024*1024:raise Error(502,'UPSTREAM_ERROR','上游响应过大')
                return r.status,dict(r.headers),decode(raw)
        except urllib.error.HTTPError as e:
            try:payload=decode(e.read(1024*1024))
            except Exception:payload={'error':'non-json upstream error'}
            return e.code,dict(e.headers),payload
    def reserve(self):
        maximum=int(os.environ.get('PROVIDER_MONTHLY_QUOTA','50'))
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');c.execute('INSERT OR IGNORE INTO trade_quota(month) VALUES(?)',(self.month,))
            q=c.execute('SELECT * FROM trade_quota WHERE month=?',(self.month,)).fetchone()
            remaining=min(maximum-q['local_used'],q['remote_remaining'] if q['remote_remaining'] is not None else maximum)
            request_limit=int(os.environ.get('PROVIDER_MONTHLY_REQUEST_QUOTA','75'))
            requests_left=min(request_limit-q['requests'],q['remote_requests'] if q['remote_requests'] is not None else request_limit)
            if q['blocked'] or remaining<5 or requests_left<=0:raise Error(503,'UPSTREAM_ERROR','服务繁忙，请稍后再试')
            if q['lease_until']>self.clock():raise Error(503,'UPSTREAM_ERROR','服务繁忙，请稍后再试')
            # Serialize all real outgoing calls across processes. Unknown/crashed outcomes
            # retain their reservation and close the quota, never automatically retry.
            c.execute('UPDATE trade_quota SET local_used=local_used+1,requests=requests+1,lease_until=?,blocked=1 WHERE month=?',(int(self.clock())+90,self.month))
    def finish(self,endpoint,status,headers,ms):
        h={k.lower():v for k,v in headers.items()}
        credit_names=[x.strip().lower() for x in os.environ.get('PROVIDER_CREDIT_REMAINING_HEADERS','x-ratelimit-credits-remaining,x-ratelimit-credit-remaining').split(',')]
        def number(keys):
            values=[]
            for k in keys:
                try:
                    n=int(h[k])
                    if n>=0:values.append(n)
                except (ValueError,KeyError,TypeError):pass
            return min(values) if values else None
        # requests-remaining is NOT a synonym for credits-remaining on this plan.
        credits=number(credit_names);requests=number(['x-ratelimit-requests-remaining'])
        maximum=int(os.environ.get('PROVIDER_MONTHLY_QUOTA','50'))
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE');q=c.execute('SELECT * FROM trade_quota WHERE month=?',(self.month,)).fetchone()
            remote=min(credits,q['remote_remaining']) if credits is not None and q['remote_remaining'] is not None else credits
            used=max(q['local_used'],maximum-remote) if remote is not None else q['local_used']
            alert=used>=maximum*.8
            c.execute('UPDATE trade_quota SET local_used=?,remote_remaining=?,remote_requests=?,blocked=?,lease_until=0,alerted=max(alerted,?) WHERE month=?',(used,remote,requests,int(credits is None or status in (401,403,429)),int(alert),self.month))
            c.execute("INSERT INTO trade_upstream(provider,endpoint,cache_hit,http_status,latency_ms,account_id,ref_id,created_at,credits_remaining) VALUES('rockapis',?,0,?,?,?,?,?,?)",(endpoint,status,ms,self.uid,self.ref,int(self.clock()),credits))
            if alert and not q['alerted']:print('WARNING trade-leads provider monthly credit usage reached 80%',flush=True)
    def fixture(self,endpoint,payload,failed=False):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            count=c.execute('SELECT count(*) FROM trade_fixtures WHERE endpoint=? AND mapping_failed=0',(endpoint,)).fetchone()[0]
            if not failed and count>=3:return
            root=Path(os.environ.get('TRADE_FIXTURE_DIR','/var/lib/skill-platform/trade-fixtures'));root.mkdir(parents=True,exist_ok=True,mode=0o700)
            fid=uuid.uuid4().hex;path=root/(fid+'.json')
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w',encoding='utf8') as out:json.dump(redact(payload),out,ensure_ascii=False)
            c.execute('INSERT INTO trade_fixtures VALUES(?,?,?,?,?)',(fid,endpoint,str(path),int(self.clock()),int(failed)))
            if failed:c.execute('UPDATE trade_upstream SET mapping_failed=1 WHERE id=(SELECT max(id) FROM trade_upstream WHERE provider=\'rockapis\' AND endpoint=? AND ref_id IS ?)',(endpoint,self.ref))
    def call(self,endpoint,params,ttl,mapper):
        if endpoint not in ENDPOINTS:raise Error(400,'INVALID_PARAMS','接口未开放')
        key=hashlib.sha256(json.dumps([endpoint,params],sort_keys=True).encode()).hexdigest();now=int(self.clock())
        with self.store.connect() as c:r=c.execute("SELECT payload FROM trade_cache WHERE provider='rockapis' AND key=? AND expires>?",(key,now)).fetchone()
        if r:
            with self.store.connect() as c:c.execute("INSERT INTO trade_upstream(provider,endpoint,cache_hit,http_status,latency_ms,account_id,ref_id,created_at) VALUES('rockapis',?,1,200,0,?,?,?)",(endpoint,self.uid,self.ref,now))
            return json.loads(r[0])
        if not self.injected_transport and (os.environ.get('LINKEDIN_PROVIDER','rockapis')!='rockapis' or not os.environ.get('RAPIDAPI_KEY')):
            raise Error(503,'UPSTREAM_ERROR','服务暂未配置，本次未扣费')
        self.reserve();start=time.monotonic()
        try:status,headers,payload=self.transport(endpoint,params)
        except Exception:
            self.finish(endpoint,0,{},int((time.monotonic()-start)*1000))
            raise Error(502,'UPSTREAM_ERROR','数据服务暂不可用，本次未扣费') from None
        self.finish(endpoint,status,headers,int((time.monotonic()-start)*1000));self.fixture(endpoint,payload)
        if status==404 and endpoint=='/get-company-details':return None
        if status!=200:raise Error(502,'UPSTREAM_ERROR','数据服务暂不可用，本次未扣费')
        try:result=mapper(payload)
        except (MappingError,ValueError,TypeError,KeyError,AttributeError):
            self.fixture(endpoint,payload,True);raise Error(502,'UPSTREAM_ERROR','数据字段待核对，本次未扣费') from None
        with self.store.connect() as c:c.execute("INSERT OR REPLACE INTO trade_cache VALUES('rockapis',?,?,?)",(key,json.dumps(result,ensure_ascii=False),now+ttl))
        return result
    def location(self,country):
        def mapper(raw):
            matches=[r for r in rows(raw,'locations') if text(val(r,'name','text','title')).casefold()==COUNTRIES[country].casefold()]
            if not matches:raise MappingError('country match missing')
            loc=text(val(matches[0],'id','locationId'))
            if not loc:raise MappingError('country id missing')
            return loc
        return self.call('/search-locations',{'keyword':COUNTRIES[country]},100*365*86400,mapper)
    def search_jobs(self,keyword,country,page):
        return self.call('/search-jobs',dict(keywords=keyword,locationId=self.location(country),datePosted='pastMonth',sort='mostRelevant',start=(page-1)*25),int(os.environ.get('CACHE_TTL_JOBS_HOURS','72'))*3600,lambda raw:jobs(raw,keyword))
    def company_profile(self,cid):
        try:data=self.call('/get-company-details',{'username':cid},int(os.environ.get('CACHE_TTL_COMPANY_DAYS','30'))*86400,lambda raw:profile(raw,cid))
        except Error as error:
            # An unconfigured skeleton NEVER causes a paid secondary call. Quota
            # exhaustion (503) must not be bypassed with another provider either.
            with self.store.connect() as c:
                r=c.execute("SELECT count(*),coalesce(sum(CASE WHEN http_status!=200 OR mapping_failed=1 THEN 1 ELSE 0 END),0) FROM trade_upstream WHERE provider='rockapis' AND endpoint='/get-company-details' AND cache_hit=0 AND created_at>?",(int(self.clock())-300,)).fetchone()
            fallback=BrightDataProvider()
            if error.status==502 and r[0]>=2 and r[1]/r[0]>.5 and fallback.ready:data=fallback.company_profile('https://www.linkedin.com/company/'+cid)
            else:raise
        if data is not None:
            from trade_site import contacts
            # Public-site acquisition is separately cached, never a RapidAPI call.
            ck='site:'+cid
            with self.store.connect() as c:cached=c.execute("SELECT payload FROM trade_cache WHERE provider='website' AND key=? AND expires>?",(ck,int(self.clock()))).fetchone()
            public=json.loads(cached[0]) if cached else contacts(data['website'])
            if not cached:
                with self.store.connect() as c:c.execute("INSERT OR REPLACE INTO trade_cache VALUES('website',?,?,?)",(ck,json.dumps(public),int(self.clock())+86400*30))
            data=dict(data,public_contacts=public)
        return data
    def company_employees(self,cid,limit):
        # Name already delivered by search/company may be present in cached profile;
        # never spend an extra API call solely to obtain it.
        profile_key=hashlib.sha256(json.dumps(['/get-company-details',{'username':cid}],sort_keys=True).encode()).hexdigest()
        with self.store.connect() as c:cached=c.execute("SELECT payload FROM trade_cache WHERE provider='rockapis' AND key=? AND expires>?",(profile_key,int(self.clock()))).fetchone()
        name=(json.loads(cached[0]) or {}).get('name','') if cached else ''
        def mapper(raw):return people(raw,cid,name,10)
        data=self.call('/search-people',dict(company=cid,keywordTitle='buyer OR purchasing OR procurement OR sourcing'),int(os.environ.get('CACHE_TTL_PEOPLE_DAYS','30'))*86400,mapper)
        # BASIC always one pass. A future explicit second pass is available only
        # with the paid-plan budget, not by toggling a flag on the free plan.
        if len(data)<limit and os.environ.get('CONTACTS_SECOND_PASS')=='true' and int(os.environ.get('PROVIDER_MONTHLY_QUOTA','50'))>50:
            second=self.call('/search-people',dict(company=cid,keywordTitle='purchasing'),int(os.environ.get('CACHE_TTL_PEOPLE_DAYS','30'))*86400,mapper)
            seen={x['linkedin_url'] for x in data};data+= [x for x in second if x['linkedin_url'] not in seen]
        return data[:limit]

class BrightDataProvider:
    """Reserved interface only. No token read or network until vendor acceptance.
    Automatic fallback cannot safely be enabled on an unimplemented paid adapter.
    """
    ready=False
    def company_profile(self,company):raise Error(503,'UPSTREAM_ERROR','备用供应商未配置')
