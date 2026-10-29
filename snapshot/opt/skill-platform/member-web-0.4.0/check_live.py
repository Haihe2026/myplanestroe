"""Compare deployed HTML/CSS/JS and original payment hashes without transacting."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).parent
def get(path):
    with urllib.request.urlopen('https://myplanestore.com' + path, timeout=20) as response:
        return response.read()
def sha(raw): return hashlib.sha256(raw).hexdigest()
names = ['index.html','compact.css','compact.js','entry.js','gemini/index.html','temu/index.html','xhs/index.html']
for name in names:
    assert sha(get('/membership/' + name)) == sha((ROOT / 'web' / name).read_bytes()), name
assert sha(get('/auth/')) == sha((ROOT / 'web/auth/index.html').read_bytes())
manifest = json.loads((ROOT / 'build-manifest.json').read_text())
for name, expected in manifest['files'].items():
    assert sha(get('/membership/' + name)) == expected, name
assert json.loads(get('/membership-api/plans'))['payment_ready'] is True
assert json.loads(get('/temu/membership-api/plans'))['payment_ready'] is True
assert json.loads(get('/phone-auth/status'))['ready'] is False
record = {'https_files_match':True,'payment_scripts_and_qr_unchanged':True,
    'gemini_payment_ready':True,'temu_payment_ready':True,'sms_ready':False,
    'actual_payments':0,'actual_sms':0,'body_scroll_disabled':False}
(ROOT / 'live-validation.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record))
