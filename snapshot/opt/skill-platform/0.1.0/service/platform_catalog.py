"""Product registry and verified-purchase gift delivery."""
from pathlib import Path
import hashlib

PRODUCTS = [
    {'id':'gemini-image-assistant','name':'Gemini生图助手','tag':'办公 / 内容创作',
     'description':'24个岗位预设。说需求，生成工作配图、封面与活动视觉。',
     'icon':'icon.png','membership_ready':True,'quota_policy':'独立生图额度',
     'status':'会员入口已接入'},
    {'id':'temu-image-assistant','name':'Temu生图skill','tag':'电商 / 商品上架',
     'description':'从产品照片出发，规划主图、SKU图和详情图。',
     'icon':'temu.png','membership_ready':False,'quota_policy':'独立账户与生图额度',
     'status':'技能可用，会员接入中'},
]
GIFT_FILE = Path(__file__).resolve().parent.parent/'gifts/scam-check-360.zip'

class PlatformCatalog:
    def __init__(self, store, problem):
        self.store, self.problem = store, problem
        with store.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS member_gifts(user_id TEXT NOT NULL,gift_id TEXT NOT NULL,
                      campaign TEXT NOT NULL,granted INTEGER NOT NULL,PRIMARY KEY(user_id,gift_id))''')
            # Verified historical paid orders qualify, never browser claims or unpaid orders.
            c.execute("""INSERT OR IGNORE INTO member_gifts SELECT user_id,'scam-check-360','member-welcome',min(paid_at)
                         FROM member_orders WHERE status='paid' AND paid_at IS NOT NULL GROUP BY user_id""")

    def catalog(self):
        return {'brand':'MyPlaneStore','products':PRODUCTS,'shared_payment_portal':True,
                'shared_quota':False,'campaign':{'id':'member-welcome','gift':'360防骗免费版',
                'status':'支付开放后生效','scope':'购买任意已开放会员套餐，附赠免费版安装包'}}

    def gifts(self, uid):
        with self.store.connect() as c:
            row=c.execute("SELECT granted FROM member_gifts WHERE user_id=? AND gift_id='scam-check-360'", (uid,)).fetchone()
            paid=c.execute("SELECT 1 FROM member_orders WHERE user_id=? AND status='paid' LIMIT 1",(uid,)).fetchone()
        available=bool(row and paid and GIFT_FILE.is_file())
        return {'items':[{'id':'scam-check-360','name':'360防骗免费版','version':'0.1.0',
               'available':available,'download_url':'/membership-api/gifts/360/download' if available else None,
               'description':'360度全方位核验可疑话术、转账风险和止损留证步骤。不是设备防盗或实时拦截。'}]}

    def download(self, uid):
        if not self.gifts(uid)['items'][0]['available']:
            raise self.problem(403, '会员支付确认后才能领取赠品；当前收款尚未开放')
        return GIFT_FILE.read_bytes()
