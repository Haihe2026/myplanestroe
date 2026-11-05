from pathlib import Path
import re
R=Path(__file__).resolve().parent;web='var/www/image-assistant/membership/listing'
html=(R/'before'/web/'index.html').read_text(encoding='utf-8')
html=html.replace('<div id="account">','<button id="claim-trial" type="button">微信扫码关联，领取1次免费体验</button><div id="account">',1)
html=re.sub(r'listing\.(js|css)\?[^"\s]+',r'listing.\1?v=20261105-metered',html)
s=(R/'before'/web/'listing.js').read_text(encoding='utf-8')
old="prefix='/platform-api/listing/v1';let cfg"
new="serviceId=new URLSearchParams(location.search).get('skill')||'listing-optimizer',generic=serviceId!=='listing-optimizer',prefix=generic?'/platform-api/metered/v1/'+encodeURIComponent(serviceId):'/platform-api/listing/v1';let cfg"
assert old in s;s=s.replace(old,new,1)
needle="const authDialog=$('auth-dialog');"
s=s.replace(needle,needle+"\n const claim=$('claim-trial');claim.onclick=()=>{if(account&&account.trial_state==='available'){$('status').textContent='免费体验已领取，请回到当前技能开始使用。';return;}openAuth();};\n function trialLabel(){claim.textContent=account?({available:'1次免费体验已领取',held:'免费体验正在使用中',used:'免费体验已使用'}[account.trial_state]||'体验状态待确认'):'微信扫码关联，领取1次免费体验';claim.disabled=!!account&&account.trial_state!=='available';}")
s=s.replace("account=a;$('account').textContent=","account=a;trialLabel();$('account').textContent=",1)
s=s.replace("function clearAccount(){account=null;order=null;","function clearAccount(){account=null;trialLabel();order=null;",1)
s=s.replace("$('trust-price').textContent='✓ '+money(cfg.unit_price_fen)+'元/多平台服务';","$('trust-price').textContent='✓ '+money(cfg.unit_price_fen)+'元/次';",1)
s=s.replace("$('trial').textContent='首次免费体验'+cfg.trial_policy.total_successes+'次 · 同一任务不限修改';","$('trial').textContent='微信扫码关联后，首次免费体验'+cfg.trial_policy.total_successes+'次'+(generic?'':' · 同一任务不限修改');",1)
needle="document.title=cfg.display_name+' · MyPlaneStore';"
replacement=needle+"if(generic){document.querySelector('.intro h1').textContent=cfg.display_name+' · 按次服务';document.querySelector('.intro>p:last-child').textContent=cfg.description||'';document.querySelector('.current-product').textContent=cfg.display_name;document.querySelector('.platform-logos')?.remove();document.querySelector('.benefits')?.remove();document.querySelector('.eyebrow').textContent='按次服务';for(const a of document.querySelectorAll('a[href=\"/membership/listing/terms/\"]'))a.href='/membership/metered/terms/';}"
s=s.replace(needle,replacement,1)
old="$('price').textContent='同一商品全部已开放平台完整服务，合计'+money(cfg.unit_price_fen)+'元/次。';"
new="$('price').textContent=generic?(cfg.unit_scope+' · ¥'+money(cfg.unit_price_fen)+'/次'):'同一商品全部已开放平台完整服务，合计'+money(cfg.unit_price_fen)+'元/次。';"
assert old in s;s=s.replace(old,new,1)
s=s.replace("+'次完整多平台服务'","+(generic?'次服务':'次完整多平台服务')")
s=s.replace("const messages={ACCOUNT_REQUIRED:","const messages={WECHAT_REQUIRED:'请先扫码关联微信账户，再领取首次体验。',ACCOUNT_REQUIRED:",1)
s=s.replace("}catch(e){$('status').textContent=e.message;$('pay').disabled=true;}\n})();","}catch(e){if(generic&&!cfg){document.querySelector('.intro h1').textContent='当前服务暂未配置';document.querySelector('.intro>p:last-child').textContent='请从对应技能打开已配置的服务入口。';document.querySelector('.platform-logos')?.remove();document.querySelector('.benefits')?.remove();$('account').textContent='服务配置完成后即可扫码领取体验';claim.disabled=true;}$('status').textContent=e.message;$('pay').disabled=true;}\n})();")
# Keep pending orders and the original Skill credential entry scoped to this service.
s=s.replace("'listing-pending-order'", "('metered-pending-order:'+serviceId)")
s=s.replace("const entry=await call('/entry',{accepted:true},entryKey);", "const incoming=new URLSearchParams(location.hash.slice(1));const existing=incoming.get('entry');const entry=existing&&/^[A-Za-z0-9_-]{43}$/.test(existing)?{url:location.origin+'/auth/wechat/listing.html#product=listing-optimizer&entry='+existing}:await call('/entry',{accepted:true},entryKey);")
s=s.replace("if(account){closeAuth();$('status').textContent=", "if(account){history.replaceState(null,'',location.pathname+location.search);closeAuth();$('status').textContent=",1)
# Existing production wrappers canonicalize entry links to the primary domain.
# Extract only a validated short-lived ticket; OAuth still starts on this page's origin.
s=s.replace("if(target.origin!==location.origin||target.pathname!=='/auth/wechat/listing.html')throw Error('账户入口暂不可用，请刷新后重试。');const q=new URLSearchParams(target.hash.slice(1));", "const trusted=['https://myplanestore.com','https://aistore.zhaopintong.com'];const entryPath=target.pathname==='/auth/wechat/listing.html'||(generic&&target.pathname==='/membership/listing/'&&target.searchParams.get('skill')===serviceId);const q=new URLSearchParams(target.hash.slice(1));if(!trusted.includes(target.origin)||!entryPath||q.get('product')!=='listing-optimizer'||!/^[A-Za-z0-9_-]{43}$/.test(q.get('entry')||''))throw Error('账户入口暂不可用，请刷新后重试。');")
html=html.replace('20261105-metered','20261105-metered-fix1')
# Owner-requested common one-line introduction, with no per-Skill ad override.
html=re.sub(r'<section class="intro">.*?</section>','<section class="intro"><h1>立志于为中小跨境商家助力</h1></section>',html,count=1)
for fragment in ["document.querySelector('.intro h1').textContent=cfg.display_name+' · 按次服务';", "document.querySelector('.intro>p:last-child').textContent=cfg.description||'';", "document.querySelector('.eyebrow').textContent='按次服务';", "document.querySelector('.intro>p:last-child').textContent='请从对应技能打开已配置的服务入口。';"]:
 s=s.replace(fragment,'')
html=html.replace('20261105-metered-fix1','20261105-metered-copy1')
css=(R/'before'/web/'listing.css').read_text(encoding='utf-8')+'\n#claim-trial{display:block;width:100%;max-width:520px;margin:10px auto;padding:12px 18px;font-size:16px}#claim-trial:disabled{opacity:.65}\n'
for n,t in [('index.html',html),('listing.js',s),('listing.css',css)]:
 p=R/'after'/web/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
terms='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>按次服务交易说明 · MyPlaneStore</title><body><main><h1>按次服务交易说明</h1><p>服务名称、每次服务范围、价格及充值金额以当前技能付费页和确认订单为准。</p><p>微信扫码关联并确认开通后，每个账户对每个已接入服务首次可体验一次同范围服务。体验不可兑换现金，重复登录或恢复账户不重复领取。领取不代表服务已完成，实际成功交付才消耗体验。</p><p>充值余额长期有效。费用在确认服务范围和价格、成功交付后结算；付款登记不等于核款到账。失败或结果待核对时，按后台核查结果处理，不把客户端自报成功作为核款证明。</p><p>退款依服务协议和适用法律处理；本说明不排除法定消费者权利。数据处理见隐私政策，不要求提交微信授权码或供应商密钥。</p><a href="/membership/privacy/">隐私政策</a> · <a href="/membership/disclaimer/">免责声明</a></main></body></html>'''
p=R/'after/var/www/image-assistant/membership/metered/terms/index.html';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(terms,encoding='utf-8')
print('Built configured service page and WeChat trial claim action')
