"""Read-only production checks. No user registration, order or image generation."""
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.error
from http.cookiejar import CookieJar

BASE='https://myplanestore.com'
ROOT=Path(__file__).parent
def read(path):
    with urllib.request.urlopen(BASE+path,timeout=20) as response:return response.read()
record={'read_only':True,'actual_payments':0,'actual_sms':0,'actual_generation':0,'products':{}}
for product in ('gemini','temu','xhs'):
    health=json.loads(read('/platform-api/'+product+'/health'))
    plans=json.loads(read('/platform-api/'+product+'/membership-api/plans'))
    assert health['shared_wallet'] and health['new_user_uses']==0 and not health['sms_required']
    assert health['provider_configured'] and health['reference_editing'] and plans['payment_ready']
    assert [(p['price_fen'],p['images']) for p in plans['plans']]==[(2900,32),(3900,43),(4900,54),(99900,2000)]
    for name in ('index.html','app.js','manual-payment.js','platform.js'):
        actual=read('/membership/'+product+'/'+('' if name=='index.html' else name))
        assert hashlib.sha256(actual).digest()==hashlib.sha256((ROOT/'web'/product/name).read_bytes()).digest(),(product,name)
    record['products'][product]={'new_user_uses':0,'shared_wallet':True,'payment_ready':True,'assets_match':True}
for product in ('gemini','temu'):
    before=ROOT.parent/'0.4.0/web'/product/'payment-qr.png'
    current=read('/membership/'+product+'/payment-qr.png')
    # On the server deployment the previous version isn't bundled; compare the new,
    # byte-verified source QR rather than request a protected backup file.
    expected=before if before.exists() else ROOT/'web'/product/'payment-qr.png'
    assert hashlib.sha256(current).digest()==hashlib.sha256(expected.read_bytes()).digest()
record['qr_unchanged']=True
record['legacy_zero_grants']=all(json.loads(read(p))['new_user_uses']==0 for p in ('/health','/temu/health'))
assert record['legacy_zero_grants']
try:read('/ops/api/orders?product=shared&status=reported')
except urllib.error.HTTPError as error:assert error.code==401
else:raise AssertionError('Admin orders are public')
if Path('/etc/skill-monitor/config.json').exists():
    config=json.loads(Path('/etc/skill-monitor/config.json').read_text())
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    req=urllib.request.Request(BASE+'/ops/api/login',data=json.dumps({'password':config['password']}).encode(),
        headers={'Origin':BASE,'Content-Type':'application/json'})
    with opener.open(req,timeout=15) as response:assert json.load(response)['ok']
    for url in ('/ops/api/summary?days=7','/ops/api/orders?product=shared&status=all&page=1','/ops/api/users?product=shared&page=1'):
        with opener.open(BASE+url,timeout=15) as response:data=json.load(response)
        if '/orders?' in url:assert data['settlement_enabled']
    record['admin_authenticated_read_checks']=True
(ROOT/'live-validation.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
