"""First-party product registry. Existing pet/image prices are never overridden."""
import os

SKILLS = {
    'trade-leads': {
        'skill_id': 'trade-leads', 'display_name': '外贸获客',
        'description': '按产品和目标国家找海外采购商，整理公司档案、官网公开联系方式和采购联系人',
        'wallet_type': 'cny', 'scope': 'trade-leads', 'tiers': [2900, 4900, 9900],
        'price_list': {'search': 100, 'company': 150, 'contact': 50}, 'daily_free_trial': 1,
    },
    # A dispatch/metadata entry only: pet-config.json and PetBilling remain authoritative.
    'pet': {'skill_id': 'pet', 'display_name': '宠物养护', 'description': '宠物养护独立订阅',
            'wallet_type': 'pet_entitlement', 'tiers_source': 'member-0.10.39/pet-config.json',
            'page': '/membership/pet/', 'billing_adapter': 'existing_pet'},
}

def config():
    base = SKILLS['trade-leads']
    result=dict(base, price_list={k: int(os.environ.get('TRADE_PRICE_'+k.upper()+'_FEN', v))
                                 for k, v in base['price_list'].items()},
                daily_free_trial=int(os.environ.get('TRADE_DAILY_FREE_TRIAL', '1')))
    if any(v<=0 for v in result['price_list'].values()) or result['daily_free_trial']<0:raise ValueError('Invalid trade billing configuration')
    return result

def ids(name):
    return {x.strip() for x in os.environ.get(name, '').split(',') if x.strip()}

def mock_identity(uid, device):
    return uid in ids('SMOKE_TEST_ACCOUNT_IDS') or device in ids('SMOKE_TEST_DEVICE_IDS')

COUNTRIES = dict(x.split(':', 1) for x in '''US:United States|GB:United Kingdom|CA:Canada|AU:Australia|NZ:New Zealand|DE:Germany|FR:France|IT:Italy|ES:Spain|PT:Portugal|NL:Netherlands|BE:Belgium|LU:Luxembourg|IE:Ireland|CH:Switzerland|AT:Austria|SE:Sweden|NO:Norway|DK:Denmark|FI:Finland|PL:Poland|CZ:Czech Republic|SK:Slovakia|HU:Hungary|RO:Romania|BG:Bulgaria|GR:Greece|HR:Croatia|SI:Slovenia|EE:Estonia|LV:Latvia|LT:Lithuania|IS:Iceland|MT:Malta|CY:Cyprus|TR:Turkey|AE:United Arab Emirates|SA:Saudi Arabia|QA:Qatar|KW:Kuwait|BH:Bahrain|OM:Oman|IL:Israel|EG:Egypt|ZA:South Africa|NG:Nigeria|KE:Kenya|MA:Morocco|IN:India|PK:Pakistan|BD:Bangladesh|SG:Singapore|MY:Malaysia|TH:Thailand|VN:Vietnam|ID:Indonesia|PH:Philippines|JP:Japan|KR:South Korea|CN:China|MX:Mexico|BR:Brazil|AR:Argentina|CL:Chile|CO:Colombia|PE:Peru|UY:Uruguay|CR:Costa Rica|PA:Panama'''.split('|'))
