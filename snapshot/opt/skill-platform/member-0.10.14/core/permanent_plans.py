"""Versioned package identities preserve historical order units and terms."""

SHARED_PLANS = {

    'shared_permanent_29': {'name': 'Plus', 'price_fen': 2900, 'images': 150},

    'shared_permanent_39': {'name': 'Pro', 'price_fen': 3900, 'images': 200},

    'shared_permanent_49': {'name': 'Ultra', 'price_fen': 4900, 'images': 250},

    'shared_permanent_999': {'name': '终身会员', 'price_fen': 99900, 'images': 5000},

}

PLANS = {

    'gemini_permanent_29': {'name': 'Plus', 'price_fen': 2900, 'images': 150},

    'gemini_permanent_39': {'name': 'Pro', 'price_fen': 3900, 'images': 200},

    'gemini_permanent_49': {'name': 'Ultra', 'price_fen': 4900, 'images': 250},

    'gemini_permanent_999': {'name': '终身会员', 'price_fen': 99900, 'images': 5000},

}

TEMU_PLANS = {

    'temu_permanent_89': {'name': '企业入门', 'price_fen': 8900, 'images': 500},

    'temu_permanent_198': {'name': '企业成长', 'price_fen': 19800, 'images': 1000},

    'temu_permanent_365': {'name': '企业批量', 'price_fen': 36500, 'images': 2000},

}

LEGACY_TEMU_PLANS = {

    'temu_enterprise_89': {'name': '企业入门', 'price_fen': 8900, 'images': 100},

    'temu_enterprise_198': {'name': '企业成长', 'price_fen': 19800, 'images': 240},

    'temu_enterprise_365': {'name': '企业批量', 'price_fen': 36500, 'images': 500},

}





def permanent(plan):

    return plan == 'business' or plan in SHARED_PLANS or plan in PLANS or plan in TEMU_PLANS or plan in LEGACY_TEMU_PLANS





def snapshot_permanent(order):

    if permanent(order['plan']):

        return True

    return (order['plan'] in ('plus', 'pro', 'ultra')

            and order.get('namespace', 'shared') in ('shared', 'gemini', 'temu')

            and order.get('source_product', 'gemini') in ('gemini', 'temu', 'xhs'))





def order_permanent(connection, row):

    if permanent(row['plan']):

        return True

    if row['product'] not in ('gemini-image-assistant','temu-image-assistant'):

        return False

    source = None

    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='order_sources'").fetchone():

        source = connection.execute('SELECT product FROM order_sources WHERE order_id=?', (row['id'],)).fetchone()

    return snapshot_permanent(dict(row, source_product=source[0] if source else ('temu' if row['product']=='temu-image-assistant' else 'gemini')))

