"""A billing unit is one SKU and its entire confirmed platform bundle, never a platform."""
import re
from listing_store import Error


def normalize(scope, config):
    if not isinstance(scope, dict) or set(scope) != {'sku','targets'}:
        raise Error(400,'BUNDLE_SCOPE_REQUIRED')
    sku,targets=scope['sku'],scope['targets']
    if not isinstance(sku,str) or not 1<=len(sku.strip())<=100 or not isinstance(targets,list) or not 1<=len(targets)<=100:
        raise Error(400,'INVALID_BUNDLE')
    enabled={p['id'] for p in config['platforms'] if p['status']=='available' and p['publicly_available'] is True}
    result={}
    for t in targets:
        if not isinstance(t,dict) or set(t)-{'platform','country','site'} or not {'platform','country'}<=set(t):
            raise Error(400,'INVALID_TARGET')
        platform,country=t['platform'],t['country']
        if not isinstance(platform,str) or platform not in enabled:raise Error(503,'PLATFORM_NOT_OPEN')
        if not isinstance(country,str) or not re.fullmatch('[A-Z]{2}',country):raise Error(400,'INVALID_COUNTRY')
        if platform=='shopee' and country=='US':raise Error(400,'UNSUPPORTED_SITE')
        target=dict(platform=platform,country=country)
        if platform in ('shopify','independent-site'):
            site=t.get('site','')
            if not isinstance(site,str) or not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,251})\.[a-zA-Z]{2,63}',site):
                raise Error(400,'SITE_HOST_REQUIRED')
            target['site']=site.lower()
            # The same website is one delivery target, irrespective of duplicate
            # Shopify/independent-site labels. Prefer the more specific adapter.
            key=('website',site.lower(),country)
            if key in result and result[key]['platform']=='shopify':continue
        else:
            if 'site' in t:raise Error(400,'UNEXPECTED_SITE')
            key=(platform,country)
        result[key]=target
    return dict(sku=sku.strip(),targets=sorted(result.values(),key=lambda x:(x['platform'],x['country'],x.get('site',''))))
