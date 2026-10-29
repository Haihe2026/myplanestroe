"""Official WeChat SDK bridge plus documented SkillHub X402 body signing."""
import base64
import json
import os
import re
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

COMMON_REQUIRED = ('WX_CERT_SERIAL','WX_MERCHANT_KEY_FILE',
    'WX_PLATFORM_PUBLIC_KEY_ID','WX_PLATFORM_PUBLIC_KEY_FILE','WX_API_V3_KEY','WX_NOTIFY_URL',
    'WX_REFUND_NOTIFY_URL','SKILLHUB_DEVELOPER_ID','SKILLHUB_PUB_KEY_ID',
    'SKILLHUB_PRIVATE_KEY_FILE','SKILLHUB_PRODUCT_ID','SKILLHUB_SKILL_ID',
    'SKILLHUB_SKILL_VERSION','WECHAT_SDK_BINARY')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def preorder_body(code_url, private_key, developer_id, pub_key_id, product_id,
                  skill_id, skill_version, now=None, nonce=None):
    if not re.fullmatch(r'SP[A-Za-z0-9]{4,62}', product_id or ''):
        raise ValueError('Configure the platform product ID')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', skill_id or '') or not skill_version:
        raise ValueError('Configure skill identity')
    now = int(time.time()) if now is None else now
    nonce = secrets.token_hex(16) if nonce is None else nonce
    business = {'skill_info':{'skill_id':skill_id,'skill_version':skill_version},
        'pay_type':'SKILL_PAY','pay_mode':'AUTH_AND_PAY',
        'pay_items':[{'product_id':product_id,'pay_data':{'type':'code_url','value':code_url}}],
        'expires_at':str(now+900)}
    encoded = base64.b64encode(json.dumps(business,ensure_ascii=False,separators=(',',':')).encode()).decode()
    canonical = f'POST\n/palmpayminiapp/clawagentpay/preorder\n{now}\n{nonce}\n{encoded}\n'.encode()
    signature = private_key.sign(canonical,padding.PKCS1v15(),hashes.SHA256())
    return {'signature_type':'SKILLHUB-SHA256-RSA2048','developer_platform':'SKILLHUB',
        'developer_id':developer_id,'pub_key_id':pub_key_id,'nonce_str':nonce,'timestamp':str(now),
        'signature':base64.b64encode(signature).decode(),'payment_required':encoded}


class Payments:
    def __init__(self):
        self.mode = os.environ.get('WX_PAYMENT_MODE', 'direct')
        identities = {'direct': ('WX_MCH_ID', 'WX_APP_ID'),
                      'partner': ('WX_SP_MCH_ID', 'WX_SP_APP_ID', 'WX_SUB_MCH_ID')}
        required = COMMON_REQUIRED + identities.get(self.mode, ('WX_PAYMENT_MODE',))
        self.missing = [k for k in required if not os.environ.get(k)]
        self.ready = os.environ.get('SKILLPAY_ENABLED') == 'yes' and not self.missing
        if self.mode not in identities:
            self.ready = False
        self.sp_mch = os.environ.get('WX_SP_MCH_ID')
        self.mch = os.environ.get('WX_SUB_MCH_ID' if self.mode == 'partner' else 'WX_MCH_ID')
        self.app = os.environ.get('WX_SP_APP_ID' if self.mode == 'partner' else 'WX_APP_ID')
        self.key = None
        if self.ready:
            for field in ('WX_MERCHANT_KEY_FILE','WX_PLATFORM_PUBLIC_KEY_FILE','SKILLHUB_PRIVATE_KEY_FILE','WECHAT_SDK_BINARY'):
                if not Path(os.environ[field]).is_file(): self.ready=False
            if os.environ['WX_NOTIFY_URL'] != 'https://myplanestore.com/skillpay/gemini-tech/notify': self.ready=False
            if os.environ['WX_REFUND_NOTIFY_URL'] != 'https://myplanestore.com/skillpay/gemini-tech/refund-notify': self.ready=False
            if not re.fullmatch(r'sh-[A-Za-z0-9_-]+',os.environ['SKILLHUB_DEVELOPER_ID']): self.ready=False
            if not re.fullmatch(r'PUB_KEY_[0-9A-F]{32}',os.environ['SKILLHUB_PUB_KEY_ID']): self.ready=False
            if not re.fullmatch(r'SP[A-Za-z0-9]{4,62}',os.environ['SKILLHUB_PRODUCT_ID']): self.ready=False
            if self.ready:
                self.key=serialization.load_pem_private_key(Path(os.environ['SKILLHUB_PRIVATE_KEY_FILE']).read_bytes(),password=None)
                if not isinstance(self.key,rsa.RSAPrivateKey) or self.key.key_size != 2048: self.ready=False

    def sdk(self, op, order='', **extra):
        if not self.ready: raise RuntimeError('Payment configuration missing')
        result=subprocess.run([os.environ['WECHAT_SDK_BINARY']],input=json.dumps(dict(op=op,order=order,**extra)),
            text=True,capture_output=True,encoding='utf-8',timeout=45,check=True)
        return json.loads(result.stdout)

    def create(self, order, amount): return self.sdk('create',order,amount=amount)['code_url']
    def receipt(self, value, refund=False, callback=False):
        if self.mode != 'partner':
            return value
        if value.get('sub_mchid') != self.mch:
            raise ValueError('Sub-merchant mismatch')
        if (not refund or callback) and value.get('sp_mchid') != self.sp_mch:
            raise ValueError('Service-provider mismatch')
        if not refund and value.get('sp_appid') != self.app:
            raise ValueError('Service-provider application mismatch')
        normalized = dict(value, mchid=self.mch)
        if not refund:
            normalized['appid'] = self.app
        return normalized

    def query(self, order): return self.receipt(self.sdk('query',order))
    def refund(self, order, amount): return self.receipt(self.sdk('refund',order,amount=amount), refund=True)
    def refund_query(self, order): return self.receipt(self.sdk('refund-query',order), refund=True)
    def notify(self, headers, raw):
        return self.receipt(self.sdk('notify',headers={k:[v] for k,v in headers.items()},body=base64.b64encode(raw).decode()))
    def refund_notify(self, headers, raw):
        return self.receipt(self.sdk('refund-notify',headers={k:[v] for k,v in headers.items()},body=base64.b64encode(raw).decode()), refund=True, callback=True)
    def preorder(self, code_url):
        if not isinstance(code_url,str) or not code_url.startswith('weixin://wxpay/'): raise ValueError('Invalid native payment code')
        payload=preorder_body(code_url,self.key,os.environ['SKILLHUB_DEVELOPER_ID'],os.environ['SKILLHUB_PUB_KEY_ID'],
            os.environ['SKILLHUB_PRODUCT_ID'],os.environ['SKILLHUB_SKILL_ID'],os.environ['SKILLHUB_SKILL_VERSION'])
        req=urllib.request.Request('https://payapp.weixin.qq.com/palmpayminiapp/clawagentpay/preorder',
            data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as r:
            result=json.loads(r.read(1024*1024))
        code=result['payment_code']
        if not isinstance(code,str) or not code or len(code)>2048 or any(ord(x)<33 or ord(x)>126 for x in code): raise ValueError('Invalid payment code')
        return code
