"""Extend only unexpired paid Gemini grants, preserving every balance and order."""
from permanent_plans import order_permanent


def migrate(connection, cutoff):
    rows=connection.execute('''SELECT o.*,g.expires FROM member_orders o
        JOIN member_grants g ON g.order_id=o.id
        WHERE o.status='paid' AND o.product='gemini-image-assistant'
        AND g.expires IS NOT NULL AND g.expires>?''',(cutoff,)).fetchall()
    changed=[]
    for row in rows:
        if order_permanent(connection,row):
            connection.execute('UPDATE member_grants SET expires=NULL WHERE order_id=?',(row['id'],))
            changed.append({'order_id':row['id'],'expires':row['expires']})
    return changed
