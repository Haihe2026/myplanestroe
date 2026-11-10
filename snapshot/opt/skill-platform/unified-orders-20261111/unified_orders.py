"""Read existing order namespaces in one snapshot without modifying billing data."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
NAMES = {
    'gemini': '通用生图', 'temu': 'Temu商家生图', 'pet': '宠物养护',
    'trade-leads': '外贸获客', 'listing-optimizer': '跨境多平台Listing优化师',
    'temu-image-master': 'Temu商家生图',
    'gemini-image-assistant': '通用生图',
    'jyai-gemini-image-assistant': 'ChatGPT全能生图王Pro',
}


class Orders:
    def __init__(self, shared, products, journey=None, services=None):
        self.shared = Path(shared)
        self.products = {k: Path(v) for k, v in products.items() if k in ('gemini', 'temu')}
        self.journey = Path(journey or os.environ.get(
            'SKILL_JOURNEY_DB', '/var/lib/skill-monitor/journey-0.10.16.db'))
        self.services = services or '/opt/skill-platform/metered-page-20261105/services.json'

    @staticmethod
    def tables(connection, schema):
        return {row[0] for row in connection.execute(
            f"SELECT name FROM {schema}.sqlite_master WHERE type='table'")}

    @staticmethod
    def attach(connection, path, alias):
        connection.execute(f'ATTACH DATABASE ? AS {alias}',
                           (path.resolve().as_uri() + '?mode=ro',))

    def queries(self, connection):
        tables = self.tables(connection, 'main')
        source = "'unknown'"
        if self.journey.is_file():
            self.attach(connection, self.journey, 'journey')
            if 'journey_objects' in self.tables(connection, 'journey'):
                source = "coalesce((SELECT j.source FROM journey.journey_objects j WHERE j.kind='order' AND j.id=o.id AND j.user_id=o.user_id), 'unknown')"
        product = "coalesce((SELECT s.product FROM main.order_sources s WHERE s.order_id=o.id),'unknown')" if 'order_sources' in tables else "'unknown'"
        queries = [f"""SELECT 'shared' namespace, o.id, o.user_id, o.plan,
            o.amount_fen, o.units, o.status, o.created, o.paid_at,
            {source} source_skill, {product} source_product, '' snapshot,
            NULL credit_fen, '' service_id FROM main.member_orders o"""]
        seen = {self.shared.resolve()}
        for namespace, path in self.products.items():
            if path.resolve() in seen:
                continue
            seen.add(path.resolve())
            alias = 'legacy_' + namespace
            self.attach(connection, path, alias)
            queries.append(f"""SELECT '{namespace}', id, user_id, plan,
                amount_fen, units, status, created, paid_at, 'unknown',
                '{namespace}', '', NULL, '' FROM {alias}.member_orders""")
        if 'pet_orders' in tables:
            queries.append("""SELECT 'pet', id, user_id, plan, amount_fen,
                NULL, status, created, paid_at, 'pet', 'pet', snapshot,
                NULL, '' FROM main.pet_orders""")
        if 'trade_orders' in tables:
            credit = 'o.amount_fen'
            if 'trade_order_promotions' in tables:
                credit += '+coalesce((SELECT p.bonus_fen FROM main.trade_order_promotions p WHERE p.order_id=o.id),0)'
            queries.append(f"""SELECT 'trade-leads', o.id, o.account_id, '', o.amount_fen,
                NULL, o.status, o.created, o.paid_at, o.skill_id, 'trade-leads', '',
                {credit}, '' FROM main.trade_orders o""")
        if 'listing_orders' in tables:
            queries.append(self.listing_query('listing_orders', 'listing', ''))
        configs = json.loads(Path(self.services).read_text(encoding='utf8'))['services']
        prefixes = {
            'metered_' + hashlib.sha256(sid.encode()).hexdigest()[:12] + '_orders': sid
            for sid, cfg in configs.items() if cfg.get('bridge') != 'listing'
        }
        for table in sorted(tables):
            if not re.fullmatch(r'metered_[a-f0-9]{12}_orders', table):
                continue
            sid = prefixes.get(table, '')
            namespace = 'metered-' + table[8:20]
            queries.append(self.listing_query(table, namespace, sid))
        return queries, configs

    @staticmethod
    def listing_query(table, namespace, sid):
        # Identifiers are fixed literals or schema names checked above, never request input.
        return f"""SELECT '{namespace}', id, account_id, tier_id, pay_fen,
            NULL, status, created, paid_at, source, '{sid or 'listing-optimizer'}',
            '', credit_fen, '{sid}' FROM main.{table}"""

    def listing(self, status='all', query='', page=1):
        if status not in ('all', 'pending', 'reported', 'paid', 'test_fulfilled'):
            raise ValueError('订单状态无效')
        if not isinstance(query, str) or len(query) > 100 or not 1 <= page <= 100000:
            raise ValueError('订单查询条件无效')
        uri = self.shared.resolve().as_uri() + '?mode=ro'
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA query_only=ON')
            queries, configs = self.queries(connection)
            connection.execute('BEGIN')
            union = ' UNION ALL '.join(queries)
            prefix = 'WITH orders AS (' + union + ') '
            counts = {r['status']: dict(r) for r in connection.execute(prefix +
                'SELECT status,count(*) count,coalesce(sum(amount_fen),0) amount_fen FROM orders GROUP BY status')}
            conditions = ['1=1']
            values = []
            if status != 'all':
                conditions.append('status=?')
                values.append(status)
            if query:
                conditions.append("(id LIKE ? ESCAPE '\\' OR user_id LIKE ? ESCAPE '\\' OR source_skill LIKE ? ESCAPE '\\' OR source_product LIKE ? ESCAPE '\\')")
                value = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
                values.extend([value] * 4)
            where = ' WHERE ' + ' AND '.join(conditions)
            total = connection.execute(prefix + 'SELECT count(*) FROM orders' + where, values).fetchone()[0]
            rows = [dict(row) for row in connection.execute(prefix + 'SELECT * FROM orders' + where +
                ' ORDER BY created DESC,namespace,id DESC LIMIT 50 OFFSET ?', values + [(page - 1) * 50])]
            for row in rows:
                sid = row['source_skill']
                row['source_name'] = configs.get(sid, {}).get('name') or NAMES.get(sid) or (sid if sid != 'unknown' else NAMES.get(row['source_product'], '历史生图') + ' · 来源未记录')
                row['row_key'] = row['namespace'] + '/' + row['id']
                row['journey_product'] = row['namespace'] if row['namespace'] in ('gemini', 'temu') else 'shared'
                row['can_mark_test'] = row['namespace'] in ('shared', 'gemini', 'temu')
                row['can_settle'] = row['namespace'] in ('shared', 'gemini', 'temu') or row['status'] == 'reported'
                row['entitlement'] = None
                if row['namespace'] == 'pet':
                    snapshot = json.loads(row.pop('snapshot'))
                    row['plan_name'] = snapshot['name']
                    row['entitlement'] = str(snapshot['duration_days']) + '天养护权益'
                else:
                    row.pop('snapshot')
                if row['namespace'].startswith('metered-') and not row['service_id']:
                    row['can_settle'] = False
        return dict(orders=rows, total=total, page=page, counts=counts,
                    generated_at=int(time.time()), settlement_enabled=True)


def extend(factory, path):
    def build(*args, **kwargs):
        parent = factory(*args, **kwargs)
        report = args[0] if args else kwargs['report']
        reader = Orders(path, report.products)

        class Handler(parent):
            def send(self, status, result, mime='application/json; charset=utf-8', cookie=None):
                if status == 200 and mime.startswith('text/html') and isinstance(result, bytes):
                    result = re.sub(rb'/ops/app\.js\?v=[^"\s]+', b'/ops/all-orders-20261111.js?v=1', result)
                    result = re.sub(rb'<select id="order-product".*?</select>', b'<input id="order-product" type="hidden" value="all">', result, count=1)
                    result = result.replace('<option value="all">全部状态</option>'.encode(), '<option value="all" selected>全部状态</option>'.encode(), 1)
                    result = result.replace('会员订单'.encode(), '全部产品订单'.encode())
                    result = result.replace('套餐 / 次数'.encode(), '来源 Skill</th><th>套餐 / 权益'.encode())
                return super().send(status, result, mime, cookie=cookie)

            def do_GET(self):
                parsed = urlsplit(self.path)
                if parsed.path == '/ops/all-orders-20261111.js':
                    return self.send(200, (ROOT / 'app.js').read_bytes(), 'application/javascript; charset=utf-8')
                if parsed.path != '/ops/api/all-orders':
                    return super().do_GET()
                if not self.authenticated():
                    return self.send(401, {'error': '请登录管理后台'})
                try:
                    query = parse_qs(parsed.query)
                    result = reader.listing(query.get('status', ['all'])[0],
                                            query.get('q', [''])[0], int(query.get('page', ['1'])[0]))
                    return self.send(200, result)
                except ValueError:
                    return self.send(400, {'error': '订单查询条件无效'})
                except (OSError, sqlite3.Error, KeyError, TypeError):
                    return self.send(503, {'error': '订单读取未完成，请稍后刷新'})

        return Handler
    return build
