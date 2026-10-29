"""Production activation probe, no upstream generation or payment."""
import hashlib
import json
import secrets
import sqlite3
import time
import urllib.request

secret = secrets.token_urlsafe(32)
def account():
    req = urllib.request.Request('http://127.0.0.1:8787/skill-pay/account',
        data=json.dumps({'install_secret': secret, 'accepted': True}).encode(),
        headers={'Content-Type': 'application/json', 'X-Real-IP': '192.0.2.250'})
    with urllib.request.urlopen(req, timeout=15) as r: return json.load(r)
def balance():
    req = urllib.request.Request('http://127.0.0.1:8787/balance', headers={'Authorization': 'Bearer '+secret})
    with urllib.request.urlopen(req, timeout=15) as r: return json.load(r)['balance_points']
first = account()
again = account()
assert first['balance_points'] == 150000 and first['awarded_points'] == 150000
assert again['awarded_points'] == 0 and first['expires_at'] == again['expires_at']
assert balance() == 150000
assert first['payment_verified'] is False
# Only expire this synthetic probe's grant. Existing user balances are untouched.
with sqlite3.connect('/var/lib/image-assistant/pilot.db') as c:
    uid = c.execute('SELECT user_id FROM sessions WHERE hash=?', (hashlib.sha256(secret.encode()).hexdigest(),)).fetchone()[0]
    grant = c.execute('SELECT grant_id FROM annual_activations WHERE user_id=?', (uid,)).fetchone()[0]
    c.execute('UPDATE member_grants SET expires=? WHERE order_id=?', (int(time.time())-1, grant))
    c.execute('UPDATE annual_activations SET expires=? WHERE user_id=?', (int(time.time())-1, uid))
assert balance() == 0
assert account()['awarded_points'] == 0
print(json.dumps({'activation_points': 150000, 'duplicate_points': 0,
    'expiry_seconds': 365*86400, 'synthetic_expiry_balance': 0,
    'payment_tested': False, 'upstream_generation': False,
    'test_grant_expired': True, 'activation_api_tested': True}))
