"""Tolerant candidate mapping; actual RockApis samples are still pending.
Missing optional fields are empty; missing identities raise MappingError (never bill).
"""
import datetime,re
from urllib.parse import urlsplit,unquote

BUYER = re.compile(r'buyer|purchas|procure|sourcing|category manager|merchandis|supply chain|import|采购', re.I)

class MappingError(Exception): pass

def val(obj, *keys, default=''):
    if not isinstance(obj, dict): return default
    for k in keys:
        v = obj.get(k)
        if v is not None and v != '': return v
    return default

def text(v):
    if isinstance(v, (str,int,float)): return str(v)
    if isinstance(v, dict):return str(val(v,'name','text','label','city','country'))
    if isinstance(v, list): return ', '.join(filter(None, (text(x) for x in v)))
    return ''

def rows(raw, *keys):
    if isinstance(raw, list):return raw
    if not isinstance(raw, dict):raise MappingError('invalid envelope')
    for k in (*keys,'items','results','data'):
        if k in raw and isinstance(raw[k], (list,dict)):return rows(raw[k],*keys)
    if raw.get('total') == 0 or raw.get('totalResults') == 0:return []
    raise MappingError('missing result list')

def slug(value):
    if not isinstance(value, (str,int)):return ''
    s=str(value).strip()
    if s.startswith(('http://','https://')):
        u=urlsplit(s)
        if u.hostname not in ('linkedin.com','www.linkedin.com') or not u.path.startswith('/company/'):return ''
        s=unquote(u.path.split('/company/',1)[1].split('/')[0])
    return s if re.fullmatch(r'[A-Za-z0-9_.-]{1,120}',s) else ''

def date(value):
    try:
        if isinstance(value,(int,float)):
            return datetime.datetime.fromtimestamp(value/(1000 if value>10**11 else 1),datetime.timezone.utc).date().isoformat()
        return datetime.date.fromisoformat(str(value)[:10]).isoformat()
    except (ValueError,OverflowError,OSError):return ''

def jobs(raw, keyword):
    result={}
    for j in rows(raw,'jobs'):
        if not isinstance(j,dict):raise MappingError('invalid job')
        c=val(j,'company',default={})
        name=text(val(c,'name','companyName') or val(j,'companyName','company_name'))
        url=text(val(c,'url','linkedinUrl','linkedin_url') or val(j,'companyUrl','companyLinkedinUrl'))
        cid=slug(val(c,'username','universalName') or val(j,'companyUsername') or url or val(c,'id') or val(j,'companyId'))
        if not name or not cid:raise MappingError('missing company identity')
        title=text(val(j,'title','jobTitle'));buyer=bool(BUYER.search(title))
        if not buyer and keyword.casefold() not in (title+' '+name).casefold():continue
        entry=result.setdefault(cid,dict(company_id=cid,name=name,linkedin_url=url or 'https://www.linkedin.com/company/'+cid,
                                         location=text(val(j,'location','formattedLocation')),jobs=[]))
        jid=text(val(j,'id','jobId'))
        entry['jobs'].append(dict(title=title,url=text(val(j,'url','jobUrl','job_url')) or ('https://www.linkedin.com/jobs/view/'+jid if jid else ''),
                                 posted_at=date(val(j,'postedAt','posted_at','postedDate','listedAt')),buyer_role=buyer))
    return list(result.values())

def profile(raw, requested):
    o=raw
    for _ in range(3):
        if isinstance(o,dict) and isinstance(o.get('data'),dict):o=o['data']
        else:break
    if isinstance(o,dict) and isinstance(o.get('company'),dict):o=o['company']
    if not isinstance(o,dict):raise MappingError('invalid company')
    if o.get('found') is False:return None
    name=text(val(o,'name','companyName'));cid=slug(val(o,'username','universalName') or requested or val(o,'id'))
    if not name or not cid:raise MappingError('missing company identity')
    raw_size=val(o,'companySize','size','employeeCountRange');size=text(raw_size)
    if isinstance(raw_size,dict):
        lo=val(raw_size,'start','min');hi=val(raw_size,'end','max')
        if lo!='' and hi!='':size=str(lo)+'-'+str(hi)
    if not size:
        count=val(o,'employeeCount','staffCount',default=0)
        if isinstance(count,int) and count>0:
            size=next((label for maximum,label in [(10,'1-10'),(50,'11-50'),(200,'51-200'),(500,'201-500'),(1000,'501-1000'),(5000,'1001-5000'),(10000,'5001-10000')] if count<=maximum),'10001+')
    industry=val(o,'industry','industries');industry=industry[0] if isinstance(industry,list) and industry else industry
    hq=val(o,'headquarters','headquarter','location')
    if isinstance(hq,dict):hq=', '.join(filter(None,(text(val(hq,k)) for k in ('city','state','country'))))
    similar=val(o,'similar','similarCompanies','peopleAlsoViewed',default=[])
    return dict(company_id=cid,name=name,website=text(val(o,'website','websiteUrl')),industry=text(industry),size=size,
                headquarters=text(hq),type=text(val(o,'type','companyType')),description=text(val(o,'description','about'))[:300],
                similar=[dict(name=text(val(x,'name')),linkedin_url=text(val(x,'url','linkedinUrl'))) for x in similar[:5] if isinstance(x,dict)] if isinstance(similar,list) else [])

def people(raw,cid,company_name,limit):
    result=[];seen=set()
    for p in rows(raw,'people'):
        title=text(val(p,'title','headline','jobTitle'))
        current=val(p,'currentCompany','company',default={})
        current_id=slug(val(current,'username','universalName','id','url') if isinstance(current,dict) else '')
        current_name=text(current)
        # Fail closed on unproven current employment (headline alone is insufficient).
        if not (current_id==cid or (company_name and current_name.casefold()==company_name.casefold())):continue
        name=text(val(p,'name','fullName')) or (text(val(p,'firstName'))+' '+text(val(p,'lastName'))).strip();url=text(val(p,'linkedin_url','linkedinUrl','profileURL','url'))
        if not name or not url or not BUYER.search(title) or url in seen:continue
        seen.add(url);result.append(dict(name=name,title=title,linkedin_url=url,location=text(val(p,'location'))))
    return result[:limit]
