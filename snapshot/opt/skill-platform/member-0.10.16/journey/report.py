"""Read-only business projection. Completion time is never inferred from job creation."""
from pathlib import Path
import time

from .store import database, identifier, SOURCES

LIMIT = 20000

def table(c, name):
    return bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())

class Report:
    def __init__(self, journey, shared, legacy=None):
        self.journey, self.shared, self.legacy = journey, shared, legacy or {}

    def metadata(self):
        with database(self.journey.path, True) as c:
            return dict(c.execute('SELECT key,value FROM journey_meta'))

    def tests(self):
        with database(self.journey.path, True) as c:
            return {r['user_id']: dict(r) for r in c.execute('SELECT user_id,evidence,marked_at FROM journey_test_accounts')}

    @staticmethod
    def marked_orders(c):
        if not table(c, 'ops_test_order_marks'):
            return set()
        return {r[0] for r in c.execute('SELECT order_id FROM ops_test_order_marks')}

    def objects(self, kind, uid=None):
        with database(self.journey.path, True) as c:
            where = 'kind=?' + (' AND user_id=?' if uid else '')
            return {r['id']: dict(r) for r in c.execute('SELECT * FROM journey_objects WHERE ' + where,
                                                       (kind, uid) if uid else (kind,))}

    def events(self, uid=None, since=0, limit=LIMIT):
        with database(self.journey.path, True) as c:
            where = 'created>=?' + (' AND user_id=?' if uid else '')
            rows = [dict(r) for r in c.execute('''SELECT event,created,user_id,invitation_id,source,channel,
                product,object_id FROM journey_events WHERE ''' + where + ' ORDER BY created DESC,id DESC LIMIT ?',
                (since, uid, limit + 1) if uid else (since, limit + 1))]
        return rows[:limit], len(rows) > limit

    def quota(self, c, uid, now):
        row = c.execute('SELECT balance FROM users WHERE id=?', (uid,)).fetchone()
        expired = c.execute('SELECT coalesce(sum(remaining),0) FROM member_grants WHERE user_id=? AND expires IS NOT NULL AND expires<=?', (uid, now)).fetchone()[0]
        shared = max(0, row[0] - expired)
        legacy, missing = {}, []
        for product in ('gemini', 'temu'):
            link = c.execute('SELECT legacy_uid FROM legacy_links WHERE product=? AND user_id=?', (product, uid)).fetchone()
            if not link:
                legacy[product] = 0
                continue
            try:
                with database(self.legacy[product], True) as old:
                    balance = old.execute('SELECT balance FROM users WHERE id=?', (link[0],)).fetchone()
                    expired_old = old.execute('SELECT coalesce(sum(remaining),0) FROM member_grants WHERE user_id=? AND expires IS NOT NULL AND expires<=?', (link[0], now)).fetchone()[0]
                    legacy[product] = max(0, balance[0] - expired_old) if balance else None
                    if balance is None:
                        missing.append(product + '_legacy_identity_missing')
            except Exception:
                legacy[product] = None
                missing.append(product + '_legacy_unavailable')
        enrolled = c.execute('SELECT allowance FROM temu_enterprise_trials WHERE user_id=?', (uid,)).fetchone()
        reserved = c.execute("SELECT count(*) FROM temu_trial_jobs t JOIN jobs j ON t.job_id=j.id WHERE t.user_id=? AND j.status IN ('pending','succeeded')", (uid,)).fetchone()[0]
        # Legacy allowance is fixed at 3 by the old schema; the later per-account
        # policy is authoritative for new one-use enrollments. Read only: never grant.
        policy = None
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='temu_trial_policy'").fetchone():
            policy = c.execute('SELECT trial_total FROM temu_trial_policy WHERE user_id=?', (uid,)).fetchone()
        allowance = policy[0] if policy else (enrolled[0] if enrolled else 0)
        trial = max(0, allowance - reserved) if enrolled else 0
        return dict(shared=shared, legacy=legacy, temu_trial=trial,
                    available={p: shared + legacy[p] + (trial if p == 'temu' else 0) if legacy[p] is not None else None
                               for p in ('gemini', 'temu')}, missing=missing, observed_at=now)

    def user(self, uid):
        if not identifier(uid):
            raise ValueError('Invalid anonymous ID')
        events, events_truncated = self.events(uid, limit=200)
        orders_meta, jobs_meta = self.objects('order', uid), self.objects('job', uid)
        with database(self.shared, True) as c:
            if not c.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
                raise LookupError('Unknown account')
            quota = self.quota(c, uid, int(time.time()))
            key = c.execute('SELECT id,revoked,bound_at FROM skill_credentials WHERE user_id=?', (uid,)).fetchone()
            test_orders = self.marked_orders(c)
            orders = [dict(r) for r in c.execute('SELECT id,created,paid_at,status,units,amount_fen FROM member_orders WHERE user_id=? ORDER BY created DESC,id DESC LIMIT 101', (uid,))]
            products = dict(c.execute('SELECT s.order_id,s.product FROM order_sources s JOIN member_orders o ON o.id=s.order_id WHERE o.user_id=?', (uid,)))
            jobs = [dict(r) for r in c.execute('SELECT j.id,j.created,j.status,p.product FROM jobs j LEFT JOIN job_products p ON p.job_id=j.id WHERE j.user_id=? ORDER BY j.created DESC,j.id DESC LIMIT 101', (uid,))]
            historical_successes = c.execute("SELECT count(*) FROM jobs WHERE user_id=? AND status='succeeded'", (uid,)).fetchone()[0]
            ledger = [dict(r, database='shared') for r in c.execute('SELECT id,job_id,created,kind,amount FROM ledger WHERE user_id=? ORDER BY created DESC,id DESC LIMIT 101', (uid,))]
            links = dict(c.execute('SELECT product,legacy_uid FROM legacy_links WHERE user_id=?', (uid,)))
        with database(self.journey.path, True) as c:
            account = c.execute('SELECT * FROM journey_accounts WHERE user_id=?', (uid,)).fetchone()
            first_success_observed = c.execute("SELECT min(created) FROM journey_events WHERE user_id=? AND event='image_succeeded'", (uid,)).fetchone()[0]
        legacy_records = {}
        for product, legacy_uid in links.items():
            if product not in ('gemini', 'temu'):
                continue
            try:
                with database(self.legacy[product], True) as old:
                    old_jobs = [dict(r, database='legacy_' + product, source='unknown',
                        product=product, completed_at=None, success_observed_at=None) for r in old.execute(
                        'SELECT id,created,status FROM jobs WHERE user_id=? ORDER BY created DESC,id DESC LIMIT 101', (legacy_uid,))]
                    old_ledger = [dict(r, database='legacy_' + product) for r in old.execute(
                        'SELECT id,job_id,created,kind,amount FROM ledger WHERE user_id=? ORDER BY created DESC,id DESC LIMIT 101', (legacy_uid,))]
                    counts = dict(old.execute('SELECT status,count(*) FROM jobs WHERE user_id=? GROUP BY status', (legacy_uid,)))
                legacy_records[product] = dict(available=True, jobs=old_jobs[:100], ledger=old_ledger[:100],
                    job_counts=counts, truncated=dict(jobs=len(old_jobs)>100, ledger=len(old_ledger)>100),
                    coverage='linked_legacy_read_only_no_skill_source_no_completion_time')
            except Exception:
                legacy_records[product] = dict(available=False, coverage='linked_legacy_unavailable')
        success_observations = {e['object_id']: e['created'] for e in events if e['event'] == 'image_succeeded'}
        for order in orders:
            meta = orders_meta.get(order['id'], {})
            order.update(source=meta.get('source', 'unknown'), channel=meta.get('channel', 'unknown'),
                         gateway_product=products.get(order['id'], 'unknown'),
                         test_order=order['id'] in test_orders,
                         paid_authoritative=order['status'] == 'paid' and order['paid_at'] is not None,
                         reported_at=next((e['created'] for e in events if e['event'] == 'payment_reported' and e['object_id'] == order['id']), None))
        for job in jobs:
            meta = jobs_meta.get(job['id'], {})
            job.update(source=meta.get('source', 'unknown'), channel=meta.get('channel', 'unknown'),
                       completed_at=None, success_observed_at=success_observations.get(job['id']))
            job['database'] = 'shared'
        return dict(id=uid, first_observed_source=account['source'] if account else 'unknown',
                    source_evidence=account['evidence'] if account else 'not_collected',
                    first_observed_at=account['first_seen'] if account else None,
                    last_active=account['last_seen'] if account else None,
                    quota=quota, key=dict(state='not_issued' if not key else 'revoked' if key['revoked'] else 'issued',
                        mask='****' + key['id'][-4:] if key else None, bound=bool(key and key['bound_at'])),
                    test_account=self.tests().get(uid), orders=orders[:100], jobs=jobs[:100], events=events,
                    ledger=ledger[:100], legacy=legacy_records, first_success_observed_at=first_success_observed,
                    historical_succeeded_jobs=historical_successes,
                    collection=self.metadata(), coverage='partial_observed_journey',
                    truncated=dict(events=events_truncated, orders=len(orders) > 100, jobs=len(jobs) > 100,
                                   ledger=len(ledger) > 100))

    def users(self, page=1, query=''):
        if not 1 <= page <= 100000 or len(query) > 64:
            raise ValueError('Invalid page/query')
        pattern = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        with database(self.shared, True) as c:
            total = c.execute("SELECT count(*) FROM users WHERE id LIKE ? ESCAPE '\\'", (pattern,)).fetchone()[0]
            ids = [r[0] for r in c.execute("SELECT id FROM users WHERE id LIKE ? ESCAPE '\\' ORDER BY id LIMIT 30 OFFSET ?", (pattern, (page - 1) * 30))]
        rows = []
        for uid in ids:
            detail = self.user(uid)
            rows.append({k: detail[k] for k in ('id', 'first_observed_source', 'source_evidence', 'last_active', 'quota', 'key', 'test_account')})
        return dict(users=rows, page=page, total=total, page_size=30)

    def summary(self, days=7, exclude_unknown=False, exclude_test_accounts=True, exclude_test_orders=True):
        if days not in (1, 2, 7, 30, 90):
            raise ValueError('Invalid window')
        since = int(time.time()) - days * 86400
        events, truncated = self.events(since=since)
        tests = self.tests() if exclude_test_accounts else {}
        metadata = self.objects('order')
        with database(self.shared, True) as c:
            marks = self.marked_orders(c) if exclude_test_orders else set()
            gateway_products = dict(c.execute('SELECT order_id,product FROM order_sources'))
            orders = [dict(r) for r in c.execute('''SELECT id,user_id,created,paid_at,status FROM member_orders
                        WHERE created>=? OR paid_at>=? ORDER BY created DESC,id DESC LIMIT ?''', (since, since, LIMIT + 1))]
        truncated = truncated or len(orders) > LIMIT
        groups = {}
        exclusions = dict(test_account_events=0, test_order_events=0, unknown_events=0,
                          test_orders=0, test_account_orders=0, unknown_orders=0)
        def group(src, ch, product):
            key = (src, ch, product)
            if key not in groups:
                groups[key] = dict(source=src, channel=ch, gateway_product=product,
                                   stages={}, orders_created=0, orders_paid=0)
            return groups[key]
        stage_sets = {}
        for e in events:
            if e['user_id'] in tests:
                exclusions['test_account_events'] += 1
                continue
            if e['object_id'] in marks:
                exclusions['test_order_events'] += 1
                continue
            if exclude_unknown and e['source'] == 'unknown':
                exclusions['unknown_events'] += 1
                continue
            if e['event'] == 'activity':
                continue
            g = group(e['source'], e['channel'], e['product'])
            key = (e['source'], e['channel'], e['product'], e['event'])
            # Invitations, pages and order reports are not silently relabelled as unique people.
            unit = e['invitation_id'] if e['event'] in ('invitation_created', 'registration_page_entered') else e['object_id'] if e['event'] in ('order_created', 'payment_reported') else e['user_id']
            if unit:
                stage_sets.setdefault(key, set()).add(unit)
                g['stages'][e['event']] = len(stage_sets[key])
        for order in orders[:LIMIT]:
            if order['id'] in marks:
                exclusions['test_orders'] += 1
                continue
            if order['user_id'] in tests:
                exclusions['test_account_orders'] += 1
                continue
            meta = metadata.get(order['id'], {})
            src = meta.get('source', 'unknown')
            if exclude_unknown and src == 'unknown':
                exclusions['unknown_orders'] += 1
                continue
            g = group(src, meta.get('channel', 'unknown'), gateway_products.get(order['id'], meta.get('product', 'unknown')))
            if order['created'] >= since:
                g['orders_created'] += 1
            if order['status'] == 'paid' and order['paid_at'] is not None and order['paid_at'] >= since:
                g['orders_paid'] += 1
        return dict(groups=list(groups.values()), since=since, days=days, generated_at=int(time.time()),
                    collection=self.metadata(), exclusions=exclusions, truncated=truncated, limit=LIMIT,
                    scope='period_stage_counts_not_cohort_conversion',
                    stage_units=dict(invitation_created='invitations', registration_page_entered='invitations',
                        recharge_page_entered='accounts', account_linked='accounts', payment_reported='orders',
                        image_succeeded='accounts_with_new_success_observations_in_period', return_visit='accounts'),
                    filters=dict(exclude_unknown=exclude_unknown, exclude_test_accounts=exclude_test_accounts,
                                 exclude_test_orders=exclude_test_orders))
