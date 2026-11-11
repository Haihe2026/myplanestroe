# Sanitized reading mirror: adapter names/configuration differ from production; target URL omitted.
"""Server-only prepaid adapter. Responses are mapped to first-party contracts.

Costs are integer micro USD; reservations survive processes/restarts. The operator
must reconcile any unknown outcome before clearing the persistent stop flag.
No transport retries or unconfigured real fallback are performed here.
"""
import hashlib
import json
import os
import re
import time
import uuid
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

from trade_config import COUNTRIES
from trade_mapping import BUYER, MappingError, date, profile, slug
from trade_store import Error

PROVIDER = 'data_v1'
BASE = os.environ.get('TRADE_DATA_API_BASE', '')
COSTS = {'/linkedin/account-search': 100000, '/linkedin/company-search': 4000,
         '/linkedin/job-search': 1000, '/linkedin/company': 4000,
         '/linkedin/lead-search': 100000}
UNAVAILABLE = '客户检索服务暂未就绪，已停止本次检索。本次未扣费，请联系维护方确认后再继续。'
BUSY = '当前查询较多，请稍后继续。本次未扣费。'
SCHEMA = '''
CREATE TABLE IF NOT EXISTS trade_data_budget(
 provider TEXT PRIMARY KEY, spent_micro INTEGER NOT NULL DEFAULT 0,
 reserved_micro INTEGER NOT NULL DEFAULT 0, blocked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS trade_data_calls(
 id TEXT PRIMARY KEY, provider TEXT NOT NULL, cache_key TEXT NOT NULL,
 endpoint TEXT NOT NULL, day TEXT NOT NULL, cost_micro INTEGER NOT NULL,
 created INTEGER NOT NULL, finished INTEGER, http_status INTEGER,
 outcome TEXT NOT NULL DEFAULT 'pending');
CREATE INDEX IF NOT EXISTS trade_data_day ON trade_data_calls(provider,day);
'''


def safe_text(value, maximum=500):
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ''
    value = str(value)
    key = os.environ.get('TRADE_DATA_API_KEY', '')
    if key:
        value = value.replace(key, '[已隐藏]')
    value = re.sub(r'(?i)(?:https?://)?(?:[\w.-]*\.)?(?:data_api\.io|previous_api\.com)\S*|data_api|previous_vendor|previous_host', '[已隐藏]', value)
    return re.sub(r'[\x00-\x1f\x7f]', ' ', value).strip()[:maximum]


def linkedin_url(value, kind):
    value = safe_text(value, 500)
    try:
        u = urlsplit(value)
        if u.scheme not in ('https', 'http') or u.hostname not in ('linkedin.com', 'www.linkedin.com') or u.username or u.password or u.port not in (None, 80, 443):
            return ''
        if kind == 'company':
            cid = slug(value)
            return 'https://www.linkedin.com/company/' + cid if cid else ''
        if kind == 'person' and re.fullmatch(r'/in/[A-Za-z0-9%_.-]+/?', u.path):
            return 'https://www.linkedin.com' + u.path.rstrip('/')
        if kind == 'job' and re.fullmatch(r'/jobs/view/[A-Za-z0-9_-]+/?', u.path):
            return 'https://www.linkedin.com' + u.path.rstrip('/')
    except (ValueError, TypeError):
        pass
    return ''


def clean_tree(value):
    if isinstance(value, dict):
        return {k: clean_tree(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_tree(v) for v in value]
    return safe_text(value, 1000) if isinstance(value, str) else value


def elements(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('elements'), list):
        raise MappingError('missing elements')
    return raw['elements']


class DataProvider:
    def __init__(self, store, uid=None, ref=None, transport=None, clock=time.time):
        self.store, self.uid, self.ref, self.clock = store, uid, ref, clock
        self.injected_transport = transport is not None
        self.transport = transport or self.http
        with store.connect() as c:
            c.executescript(SCHEMA)
            c.execute('INSERT OR IGNORE INTO trade_data_budget(provider) VALUES(?)', (PROVIDER,))

    def day(self):
        return datetime.fromtimestamp(self.clock(), ZoneInfo('Asia/Shanghai')).date().isoformat()

    def limits(self):
        total = int(os.environ.get('TRADE_DATA_TOTAL_BUDGET_MICRO_USD', '20000000'))
        margin = int(os.environ.get('TRADE_DATA_SAFETY_MARGIN_MICRO_USD', '1000000'))
        daily = int(os.environ.get('TRADE_DATA_DAILY_BUDGET_MICRO_USD', '5000000'))
        concurrency = int(os.environ.get('TRADE_DATA_MAX_CONCURRENT', '2'))
        if not 0 <= margin < total or daily <= 0 or not 1 <= concurrency <= 5:
            raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
        return total-margin, daily, concurrency

    def available(self, c):
        row = c.execute('SELECT * FROM trade_data_budget WHERE provider=?', (PROVIDER,)).fetchone()
        if row['blocked']:
            raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
        return row

    def cache_key(self, endpoint, params):
        return hashlib.sha256(json.dumps([endpoint, params], sort_keys=True).encode()).hexdigest()

    def cached(self, endpoint, key):
        with self.store.connect() as c:
            self.available(c)
            row = c.execute('SELECT payload FROM trade_cache WHERE provider=? AND key=? AND expires>?',
                            (PROVIDER, key, int(self.clock()))).fetchone()
            if row:
                c.execute('INSERT INTO trade_upstream(provider,endpoint,cache_hit,http_status,latency_ms,account_id,ref_id,created_at) VALUES(?,?,1,200,0,?,?,?)',
                          (PROVIDER, endpoint, self.uid, self.ref, int(self.clock())))
                return True, json.loads(row[0])
        return False, None

    def reserve(self, endpoint, key):
        cap, daily, concurrency = self.limits()
        cost = COSTS[endpoint]
        stale = False
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self.available(c)
            # Pending calls never expire into free credit. A crash or abandoned
            # request has an unknown billable outcome and requires reconciliation.
            stale = bool(c.execute("SELECT 1 FROM trade_data_calls WHERE provider=? AND outcome='pending' AND created<? LIMIT 1",
                                   (PROVIDER, int(self.clock())-120)).fetchone())
            if stale:
                c.execute('UPDATE trade_data_budget SET blocked=1 WHERE provider=?', (PROVIDER,))
            else:
                pending = c.execute("SELECT count(*) FROM trade_data_calls WHERE provider=? AND outcome='pending'", (PROVIDER,)).fetchone()[0]
                duplicate = c.execute("SELECT 1 FROM trade_data_calls WHERE provider=? AND cache_key=? AND outcome='pending'", (PROVIDER, key)).fetchone()
                if duplicate or pending >= concurrency:
                    raise Error(503, 'SERVICE_BUSY', BUSY)
                used_today = c.execute('SELECT coalesce(sum(cost_micro),0) FROM trade_data_calls WHERE provider=? AND day=?', (PROVIDER, self.day())).fetchone()[0]
                if row['spent_micro']+row['reserved_micro']+cost > cap or used_today+cost > daily:
                    raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
                ticket = uuid.uuid4().hex
                c.execute('UPDATE trade_data_budget SET reserved_micro=reserved_micro+? WHERE provider=?', (cost, PROVIDER))
                c.execute('INSERT INTO trade_data_calls(id,provider,cache_key,endpoint,day,cost_micro,created) VALUES(?,?,?,?,?,?,?)',
                          (ticket, PROVIDER, key, endpoint, self.day(), cost, int(self.clock())))
        if stale:
            raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
        return ticket

    def finish(self, ticket, status, ms, outcome, result=None, ttl=0, stop=False, failed_mapping=False):
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            call = c.execute("SELECT * FROM trade_data_calls WHERE id=? AND outcome='pending'", (ticket,)).fetchone()
            if not call:
                raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
            # Conservatively count every started request, including a timeout or
            # failed response. No undocumented provider refunds are assumed.
            c.execute('UPDATE trade_data_budget SET reserved_micro=reserved_micro-?,spent_micro=spent_micro+?,blocked=max(blocked,?) WHERE provider=?',
                      (call['cost_micro'], call['cost_micro'], int(stop), PROVIDER))
            c.execute('UPDATE trade_data_calls SET outcome=?,http_status=?,finished=? WHERE id=?',
                      (outcome, status, int(self.clock()), ticket))
            c.execute('INSERT INTO trade_upstream(provider,endpoint,cache_hit,http_status,latency_ms,account_id,ref_id,created_at,mapping_failed) VALUES(?,?,0,?,?,?,?,?,?)',
                      (PROVIDER, call['endpoint'], status, ms, self.uid, self.ref, int(self.clock()), int(failed_mapping)))
            if outcome == 'ok':
                c.execute('INSERT OR REPLACE INTO trade_cache VALUES(?,?,?,?)',
                          (PROVIDER, call['cache_key'], json.dumps(result, ensure_ascii=False), int(self.clock())+ttl))

    def http(self, endpoint, params):
        if endpoint not in COSTS:
            raise Error(400, 'INVALID_PARAMS', '查询方式无效')
        key = os.environ.get('TRADE_DATA_API_KEY', '')
        if not key:
            raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
        request = urllib.request.Request(BASE+endpoint+'?'+urlencode(params), headers={
            'X-API-Key': key, 'Accept': 'application/json', 'User-Agent': 'MyPlaneStore/2.0.11'})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        timeout = min(60, max(5, int(os.environ.get('TRADE_DATA_HTTP_TIMEOUT_SECONDS', '40'))))
        def decode(response):
            raw = response.read(2*1024*1024+1)
            if len(raw) > 2*1024*1024:
                raise ValueError('response too large')
            return json.loads(raw)
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
                return response.status, dict(response.headers), decode(response)
        except urllib.error.HTTPError as error:
            try:
                payload = decode(error)
            except (ValueError, UnicodeError):
                payload = {}
            return error.code, dict(error.headers), payload

    def fixture(self, endpoint, payload, failed=False):
        # Server-only records; never return raw envelopes or diagnostic fields.
        def redact(value):
            if isinstance(value, dict):
                return {k: ('[REDACTED]' if re.search(r'key|token|secret|authoriz|cookie|email|phone|mobile|firstName|lastName', k, re.I) else redact(v)) for k, v in value.items()}
            if isinstance(value, list):
                return [redact(v) for v in value]
            if isinstance(value, str):
                value = safe_text(value, 3000)
                value = re.sub(r'[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', value)
                value = re.sub(r'(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)', '[PHONE]', value)
                return re.sub(r'/in/[^/?"\s]+', '/in/[REDACTED]', value)
            return value
        with self.store.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            label = PROVIDER+':'+endpoint
            count = c.execute('SELECT count(*) FROM trade_fixtures WHERE endpoint=?', (label,)).fetchone()[0]
            if count >= (6 if failed else 3):
                return
            root = Path(os.environ.get('TRADE_FIXTURE_DIR', '/var/lib/skill-platform/trade-fixtures'))
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            fid = uuid.uuid4().hex
            path = root/(fid+'.json')
            fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='utf8') as out:
                json.dump(redact(payload), out, ensure_ascii=False)
            c.execute('INSERT INTO trade_fixtures VALUES(?,?,?,?,?)', (fid, label, str(path), int(self.clock()), int(failed)))

    def call(self, endpoint, params, ttl, mapper):
        if endpoint not in COSTS:
            raise Error(400, 'INVALID_PARAMS', '查询方式无效')
        if not self.injected_transport and (os.environ.get('LINKEDIN_PROVIDER') != 'data_api' or not os.environ.get('TRADE_DATA_API_KEY')):
            raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
        key = self.cache_key(endpoint, params)
        hit, result = self.cached(endpoint, key)
        if hit:
            return result
        ticket = self.reserve(endpoint, key)
        start = time.monotonic()
        def finish(status, outcome, **kwargs):
            return self.finish(ticket, status, int((time.monotonic()-start)*1000), outcome, **kwargs)
        try:
            status, headers, payload = self.transport(endpoint, params)
        except BaseException:
            finish(0, 'unknown', stop=True)
            raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE) from None
        business_error = (not isinstance(payload, dict) or payload.get('success') is False or
                          bool(payload.get('error')) or payload.get('status') not in (None, 200, '200', 'success', 'ok'))
        if status != 200 or business_error:
            finish(status, 'business_error' if status == 200 else 'http_error', stop=True)
            try:
                self.fixture(endpoint, payload, True)
            except Exception:
                pass
            raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
        try:
            result = clean_tree(mapper(payload))
        except (MappingError, ValueError, TypeError, KeyError, AttributeError):
            finish(status, 'mapping_error', stop=True, failed_mapping=True)
            try:
                self.fixture(endpoint, payload, True)
            except Exception:
                pass
            raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE) from None
        finish(status, 'ok', result=result, ttl=ttl)
        try:
            self.fixture(endpoint, payload)
        except Exception:
            pass
        return result

    def map_companies(self, raw):
        result = []
        seen = set()
        for company in elements(raw):
            if not isinstance(company, dict):
                raise MappingError('invalid company')
            url = linkedin_url(company.get('linkedinUrl', ''), 'company')
            cid = slug(url or company.get('universalName') or company.get('id'))
            name = safe_text(company.get('name'), 200)
            if not cid or not name:
                raise MappingError('missing company identity')
            if cid in seen:
                continue
            seen.add(cid)
            location = company.get('location') or {}
            result.append(dict(company_id=cid, name=name, linkedin_url=url or 'https://www.linkedin.com/company/'+cid,
                               location=safe_text(location.get('linkedinText')) if isinstance(location, dict) else safe_text(location),
                               description=safe_text(company.get('description') or company.get('summary'), 500),
                               industry=safe_text(company.get('industry') or company.get('industries'), 200), jobs=[]))
        return result

    def map_jobs(self, raw, keyword):
        result = {}
        for job in elements(raw):
            if not isinstance(job, dict) or not isinstance(job.get('company'), dict):
                raise MappingError('invalid job')
            company = job['company']
            url = linkedin_url(company.get('linkedinUrl', ''), 'company')
            cid = slug(url or company.get('universalName'))
            name, title = safe_text(company.get('name'), 200), safe_text(job.get('title'), 200)
            if not cid or not name or not title:
                raise MappingError('missing job identity')
            location = job.get('location') or {}
            item = result.setdefault(cid, dict(company_id=cid, name=name, linkedin_url=url,
                location=safe_text(location.get('linkedinText')) if isinstance(location, dict) else safe_text(location), jobs=[]))
            jid = safe_text(job.get('id'), 40)
            jurl = linkedin_url(job.get('url', ''), 'job')
            if not jurl and re.fullmatch(r'\d+', jid):
                jurl = 'https://www.linkedin.com/jobs/view/'+jid
            item['jobs'].append(dict(title=title, url=jurl, posted_at=date(job.get('postedDate')), buyer_role=bool(BUYER.search(title))))
        return list(result.values())

    def search_jobs(self, keyword, country, page):
        if country not in COUNTRIES or type(page) is not int or page != 1:
            raise Error(400, 'INVALID_PARAMS', '查询地区或页码无效')
        mode = os.environ.get('TRADE_DATA_SEARCH_MODE', 'accounts')
        ttl = int(os.environ.get('CACHE_TTL_JOBS_HOURS', '72'))*3600
        if mode == 'accounts':
            return self.call('/linkedin/account-search', dict(search=keyword, headquarterLocations=COUNTRIES[country], page=1), ttl, self.map_companies)
        if mode == 'names':
            return self.call('/linkedin/company-search', dict(search=keyword, location=COUNTRIES[country], page=1), ttl, self.map_companies)
        if mode == 'jobs':
            return self.call('/linkedin/job-search', dict(search=keyword, location=COUNTRIES[country], postedLimit='month', sortBy='relevance', page=1), ttl, lambda raw: self.map_jobs(raw, keyword))
        raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)

    def company_profile(self, cid):
        if not slug(cid):
            raise Error(400, 'INVALID_PARAMS', '公司标识无效')
        def mapper(raw):
            obj = raw.get('element')
            if not isinstance(obj, dict):
                raise MappingError('missing company element')
            identities = {field: slug(obj.get(field)) for field in ('id', 'universalName', 'linkedinUrl')}
            if any(obj.get(field) not in (None, '') and not value for field, value in identities.items()):
                raise MappingError('invalid company identity')
            oid, universal, url_id = (identities[field] for field in ('id', 'universalName', 'linkedinUrl'))
            if oid and url_id.isdigit() and oid != url_id:
                raise MappingError('conflicting company numeric identities')
            if oid and universal.isdigit() and oid != universal:
                raise MappingError('conflicting company numeric universal name')
            if universal and url_id and not url_id.isdigit() and universal.casefold() != url_id.casefold():
                raise MappingError('conflicting company universal identities')
            if cid.isdigit():
                if (oid and oid != cid) or (url_id.isdigit() and url_id != cid):
                    raise MappingError('company differs from requested identity')
            elif (universal and universal.casefold() != cid.casefold()) or (url_id and not url_id.isdigit() and url_id.casefold() != cid.casefold()):
                raise MappingError('company differs from requested identity')
            if cid.casefold() not in {value.casefold() for value in identities.values() if value}:
                raise MappingError('requested company identity unproven')
            normalized = dict(obj)
            locations = obj.get('locations') or []
            hq = next((v for v in locations if isinstance(v, dict) and v.get('headquarter') is True), None)
            if hq:
                normalized['headquarters'] = dict(city=hq.get('city'), state=hq.get('geographicArea'), country=hq.get('country'))
            normalized['similar'] = obj.get('similarOrganizations') or []
            result = profile(normalized, cid)
            if result is None:
                return None
            # Preserve requested identity; numeric/universal aliases remain local.
            result['company_id'] = cid
            result['_company_aliases'] = sorted({value for value in
                (slug(cid), slug(obj.get('id')), slug(obj.get('universalName')), slug(obj.get('linkedinUrl'))) if value})
            return result
        data = self.call('/linkedin/company', dict(query='https://www.linkedin.com/company/'+cid),
                         int(os.environ.get('CACHE_TTL_COMPANY_DAYS', '30'))*86400, mapper)
        if data is not None:
            data = dict(data)
            data.pop('_company_aliases', None)
            from trade_site import contacts
            cachekey = 'site:'+cid
            with self.store.connect() as c:
                cached = c.execute("SELECT payload FROM trade_cache WHERE provider='website' AND key=? AND expires>?", (cachekey, int(self.clock()))).fetchone()
            public = json.loads(cached[0]) if cached else contacts(data['website'])
            if not cached:
                with self.store.connect() as c:
                    c.execute("INSERT OR REPLACE INTO trade_cache VALUES('website',?,?,?)", (cachekey, json.dumps(clean_tree(public)), int(self.clock())+86400*30))
            data = dict(data, public_contacts=clean_tree(public))
        return data

    def company_employees(self, cid, limit):
        if not slug(cid) or type(limit) is not int or not 1 <= limit <= 10:
            raise Error(400, 'INVALID_PARAMS', '公司或人数无效')
        # Only a fetched profile may establish numeric/universal URL aliases.
        # A matching display name must never override a conflicting company ID.
        profilekey = self.cache_key('/linkedin/company', dict(query='https://www.linkedin.com/company/'+cid))
        with self.store.connect() as c:
            row = c.execute('SELECT payload FROM trade_cache WHERE provider=? AND key=? AND expires>?', (PROVIDER, profilekey, int(self.clock()))).fetchone()
        cached_profile = (json.loads(row[0]) or {}) if row else {}
        aliases = {cid.casefold()}
        aliases.update(slug(value).casefold() for value in cached_profile.get('_company_aliases', []) if slug(value))
        def current_company_matches(position):
            supplied = [position.get(field) for field in ('companyId', 'companyLinkedinUrl') if position.get(field) not in (None, '')]
            identities = [slug(value).casefold() for value in supplied]
            # Every supplied ID/URL must be well-formed and known. Missing
            # identifiers and same-name companies remain unverified.
            return bool(identities) and all(value and value in aliases for value in identities)
        def mapper(raw):
            result, seen = [], set()
            for person in elements(raw):
                if not isinstance(person, dict):
                    raise MappingError('invalid person')
                positions = person.get('currentPositions') or []
                if not isinstance(positions, list):
                    raise MappingError('invalid positions')
                matching = [pos for pos in positions if isinstance(pos, dict) and BUYER.search(safe_text(pos.get('title'))) and current_company_matches(pos)]
                if not matching:
                    continue
                person_name = (safe_text(person.get('firstName'))+' '+safe_text(person.get('lastName'))).strip()
                url = linkedin_url(person.get('linkedinUrl', ''), 'person')
                if not person_name or person_name.casefold() == 'linkedin member' or not url or url in seen:
                    continue
                seen.add(url)
                location = person.get('location') or {}
                result.append(dict(name=person_name, title=safe_text(matching[0].get('title'), 200), linkedin_url=url,
                                   location=safe_text(location.get('linkedinText')) if isinstance(location, dict) else safe_text(location)))
            return result
        data = self.call('/linkedin/lead-search', dict(currentCompanies='https://www.linkedin.com/company/'+cid,
                         currentJobTitles='Buyer,Purchasing Manager,Procurement Manager,Sourcing Manager,Category Manager', page=1),
                         int(os.environ.get('CACHE_TTL_PEOPLE_DAYS', '30'))*86400, mapper)
        return data[:limit]


def real_provider(store, uid=None, ref=None):
    # The retired provider remains available for offline regression evidence only.
    # An unknown environment value cannot silently activate another real vendor.
    if os.environ.get('LINKEDIN_PROVIDER') != 'data_api':
        raise Error(503, 'SERVICE_UNAVAILABLE', UNAVAILABLE)
    return DataProvider(store, uid, ref)
