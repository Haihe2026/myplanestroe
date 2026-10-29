"""Versioned package identities preserve historical order units and terms."""
PLANS = {
    'gemini_permanent_29': {'name': 'Plus', 'price_fen': 2900, 'images': 60},
    'gemini_permanent_39': {'name': 'Pro', 'price_fen': 3900, 'images': 80},
    'gemini_permanent_49': {'name': 'Ultra', 'price_fen': 4900, 'images': 100},
    'gemini_permanent_999': {'name': '终身会员', 'price_fen': 99900, 'images': 2000},
}


def permanent(plan):
    return plan == 'business' or plan in PLANS


def snapshot_permanent(order):
    if permanent(order['plan']):
        return True
    return (order['plan'] in ('plus', 'pro', 'ultra')
            and order.get('namespace', 'shared') in ('shared', 'gemini')
            and order.get('source_product', 'gemini') in ('gemini', 'xhs'))


def order_permanent(connection, row):
    if permanent(row['plan']):
        return True
    if row['product'] != 'gemini-image-assistant':
        return False
    source = None
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='order_sources'").fetchone():
        source = connection.execute('SELECT product FROM order_sources WHERE order_id=?', (row['id'],)).fetchone()
    return snapshot_permanent(dict(row, source_product=source[0] if source else 'gemini'))
