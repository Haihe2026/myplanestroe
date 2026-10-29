"""Compact product pages; retain existing payment scripts and dialog markup."""
import json
from pathlib import Path
import re
import shutil
import hashlib

ROOT = Path(__file__).parent
out = ROOT / 'web'
out.mkdir(exist_ok=True)
evidence = json.loads((ROOT / 'ratings-evidence.json').read_text(encoding='utf-8'))
gemini = evidence['gemini']
assert gemini['found'] and all(gemini['evaluation']['securityReports'][k]['status'] == 'benign' for k in ('keen','sanbu'))
assert gemini['evaluation']['skill_fields']['stats']['comments'] == 0

def header(active):
    names = {'gemini':'Gemini生图助手','temu':'Temu图片大师','xhs':'XHS选题大师'}
    nav = ''.join(f'<a href="/membership/{key}/"'+(' aria-current="page"' if key==active else '')+'>'+name+'</a>' for key,name in names.items())
    ai = ''.join(f'<span><img src="/membership/{file}.svg" alt="" width="20" height="20">{name}</span>' for file,name in [('qwen','千问'),('doubao','豆包'),('deepseek','DeepSeek'),('kimi','Kimi')])
    return f'''<header class="compact-header"><div class="header-line"><a class="compact-brand" href="/membership/"><img src="/membership/platform-mark.svg" alt="" width="28" height="28"><b>MyPlaneStore</b></a><div class="model-brands" aria-label="AI平台">{ai}</div><div class="compact-payments"><span><img src="/membership/alipay.svg" alt="" width="20" height="20"><span>支付宝</span></span><span><img src="/membership/wechat-pay.svg" alt="" width="20" height="20"><span>微信支付</span></span></div><button id="account-tools" type="button">我的账户</button></div><nav aria-label="Skill产品">{nav}</nav></header>'''

def reputation(product):
    if product in ('gemini','auth'):
        # Score is explicitly from the user's supplied listing screenshot, not invented API dimensions.
        return '''<section class="reputation" aria-label="平台评价"><div class="rating"><strong>4.6<small>/5</small></strong><span class="stars" aria-hidden="true">★★★★★</span><span>SkillHub 已发布版本评分</span></div><div class="assessment"><h2>平台评测</h2><div><span>科恩实验室</span><b>未标记风险</b></div><div><span>云鼎实验室</span><b>未标记风险</b></div></div><div class="review-entry"><a href="https://tix.qq.com/search/skill?keyword=REDACTED_FOR_HANDOFF" target="_blank" rel="noopener noreferrer">查看技能评测 ↗</a><span>欢迎到 SkillHub 分享使用体验</span><small>评分来自已发布版本；评测范围以报告为准。</small></div></section>'''
    return '''<section class="reputation unscored" aria-label="使用评价"><div><h2>分享你的使用体验</h2><p>你的一次反馈，帮助我们把 Skill 做得更顺手。</p></div><div><span>在 SkillHub 的对应技能页留言</span><small>选题、制作、交付，有建议就告诉我们。</small></div></section>'''

def extract(html, pattern):
    match = re.search(pattern, html, re.S)
    assert match, pattern
    return match.group(0)

manifest = {'version':'0.4.0','payments_changed':False,'files':{},'score_source':'User-supplied SkillHub screenshot: 4.6; published-version score',
    'security_source': 'SkillHub public listing evaluation fields', 'reviews_fabricated':False}
for product in ('gemini','temu'):
    source = ROOT / 'source' / product
    html = (source / 'index.html').read_text(encoding='utf-8')
    target = out / product
    shutil.copytree(source, target, dirs_exist_ok=True)
    name = 'Gemini生图助手' if product=='gemini' else 'Temu图片大师'
    dialogs = extract(html, r'<dialog id="account-dialog"[\s\S]*?</dialog>') + extract(html, r'<dialog id="payment-dialog"[\s\S]*?</dialog>')
    orders = extract(html, r'<section id="payment-order-section"[\s\S]*?</section>')
    api_panel = extract(html, r'<section id="api-panel"[\s\S]*?</section>') if product=='gemini' else ''
    promotion = extract(html, r'<section class="promotion"[\s\S]*?</section>')
    # Existing portal.js keeps the gift entitlement behavior; its catalog chooser is hidden.
    compat = '<div hidden><div id="products"></div></div><p id="product-status" hidden role="status"></p>'
    tools = '<dialog id="tools-dialog"><div class="payment-head"><h2>我的账户</h2><button type="button" id="tools-close" aria-label="关闭">×</button></div>'+orders+api_panel+promotion+'</dialog>'
    scripts = '<script src="app.js?v=1.3.0" defer></script>' + ('<script src="api-keys.js" defer></script>' if product=='gemini' else '') + '<script src="platform.js" defer></script><script src="manual-payment.js?v=1.3.0" defer></script><script src="/membership/compact.js?v=0.4.0" defer></script>'
    body = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>{name} · 充值</title><link rel="icon" href="/membership/platform-mark.svg" type="image/svg+xml"><link rel="stylesheet" href="/membership/compact.css?v=0.4.0">{scripts}</head><body data-product="{product}">{header(product)}<main class="compact-main">
<div class="compact-heading"><h1>{name}</h1><span>补充额度，继续创作</span></div>
<div class="account-line"><span id="account">正在关联账户…</span><div><strong id="balance">— 积分</strong><button id="refresh" type="button" aria-label="刷新余额" title="刷新余额">↻</button></div></div>
<p id="notice" role="status" class="compact-notice">正在检查账户连接…</p>{compat}
<section id="plans-panel" aria-label="选择套餐"><div id="plans" class="plans" role="radiogroup" aria-label="生图套餐"></div><input id="renewal" type="checkbox" hidden disabled></section>
<section id="checkout-panel" class="compact-checkout"><h2 id="summary" class="sr-only">Ultra 月度会员</h2><p id="plan-guidance">一次备足，集中制作更从容。</p><div class="checkout-action"><strong id="total">¥49 / 月</strong><button id="buy" type="button" disabled>扫码开通</button></div><p id="detail" class="sr-only"></p><p class="payment-terms">人工核款到账 · 月度30天不结转；终身2000次长期有效。</p></section>
{reputation(product)}</main>{tools}{dialogs}</body></html>'''
    (target / 'index.html').write_text(body, encoding='utf-8')
    for file in ('app.js','manual-payment.js','payment-qr.png'):
        before = hashlib.sha256((source / file).read_bytes()).hexdigest()
        after = hashlib.sha256((target / file).read_bytes()).hexdigest()
        assert before == after
        manifest['files'][product+'/'+file] = before

# Free XHS remains free; no new product price or payment endpoint is created.
xhs = out / 'xhs'; shutil.copytree(ROOT / 'source/xhs', xhs, dirs_exist_ok=True)
xhs_html = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>XHS选题大师 · MyPlaneStore</title><link rel="icon" href="/membership/platform-mark.svg"><link rel="stylesheet" href="/membership/compact.css?v=0.4.0"><script src="page.js" defer></script><script src="/membership/compact.js?v=0.4.0" defer></script></head><body data-product="xhs">{header('xhs')}<main class="compact-main free-page"><div class="free-heading"><img src="icon.png" width="56" height="56" alt=""><div><h1>XHS选题大师</h1><p>把选题变成可以动手制作的内容方案。</p></div><b>免费版</b></div><div class="free-features"><div><b>先选3个值得做的题</b><span>结合账号定位、受众问题与现有素材。</span></div><div><b>展开一份内容制作包</b><span>标题、封面文案、正文提纲与拍摄清单。</span></div><div><b>用自己的数据复盘</b><span>比较互动表现，安排下一批内容。</span></div></div><a class="download-button" href="/membership/downloads/xhs-topic-master-workbuddy_skill-v0.2.2.zip" download>下载 WorkBuddy 免费版</a><p class="payment-terms">无需购买本站会员，不消耗生图积分。</p><div class="example-line"><p id="example-text">我做家居收纳，有整理前后照片，每周发2篇。请推荐3个选题，再展开最适合的一题。</p><button id="copy-example" type="button">复制需求</button><span id="copy-status" role="status"></span></div>{reputation('xhs')}</main></body></html>'''
(xhs / 'index.html').write_text(xhs_html, encoding='utf-8')

auth = out / 'auth'; shutil.copytree(ROOT / 'source/auth', auth, dirs_exist_ok=True)
old = (auth / 'index.html').read_text(encoding='utf-8')
form = extract(old, r'<form id="form"[\s\S]*?</form>')
form = form.replace('同意使用手机号验证并关联生图账户。图片仅在确认后发送至生图服务；手机号仅向腾讯云短信服务发送以投递验证码。', '同意手机号用于账户关联及腾讯云验证码投递；图片另行确认后发送。')
success = extract(old, r'<section id="success"[\s\S]*?</section>')
auth_html = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gemini生图助手 · 手机号授权</title><link rel="icon" href="/membership/platform-mark.svg"><link rel="stylesheet" href="/membership/compact.css?v=0.4.0"><script src="app.js" defer></script><script src="/membership/compact.js?v=0.4.0" defer></script></head><body data-product="auth">{header('gemini')}<main class="compact-main auth-main"><section class="auth-surface"><p class="auth-label">Gemini生图助手 · 账户授权</p><h1>验证手机号，继续创作</h1><p class="auth-caption">验证后回 WorkBuddy 继续原图片。</p>{form}{success}<p class="auth-footnote">验证码仅在此页面输入；重复验证不重复赠送积分。</p></section>{reputation('auth')}</main></body></html>'''
auth_html = auth_html.replace('<p class="auth-footnote">验证码仅在此页面输入；重复验证不重复赠送积分。</p>', '')
(auth / 'index.html').write_text(auth_html, encoding='utf-8')
assert hashlib.sha256((auth / 'app.js').read_bytes()).digest() == hashlib.sha256((ROOT / 'source/auth/app.js').read_bytes()).digest()
for name in ('compact.css','compact.js'):
    shutil.copy2(ROOT / name, out / name)
(out / 'index.html').write_text('''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MyPlaneStore</title><script src="/membership/entry.js?v=0.4.0" defer></script></head><body><a href="/membership/gemini/">进入 Gemini生图助手</a></body></html>''', encoding='utf-8')
shutil.copy2(ROOT / 'entry.js', out / 'entry.js')
(ROOT / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'built':['gemini','temu','xhs','auth'],'payment_scripts_unchanged':True}))
