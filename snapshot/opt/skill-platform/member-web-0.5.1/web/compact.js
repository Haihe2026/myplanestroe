'use strict';
(() => {
  const byId = id => document.getElementById(id);
  const tools = byId('tools-dialog');
  const accountButton = byId('account-tools');
  if (tools) {
    accountButton.addEventListener('click', () => tools.showModal());
    byId('tools-close').addEventListener('click', () => tools.close());
  } else accountButton.hidden = true;
  const guidance = {
    plus:'32次轻松起步，把眼前的想法先做出来。',
    pro:'43次日常常备，商品与内容配图接着做。',
    ultra:'54次集中创作，一批素材从容安排。',
    business:'2000次长期畅享，让创作跟着自己的节奏。'
  };
  const plans = byId('plans');
  if (!plans) return;
  function update() {
    for (const button of plans.children) {
      const plan = typeof catalog !== 'undefined' ? catalog.find(value=>value.id===button.dataset.id) : null;
      if (!plan) continue;
      const count = button.querySelector('.count');
      const text = (plan.images ?? plan.points / 1000).toLocaleString('zh-CN') + ' 次生图';
      if (count.textContent !== text) count.textContent = text;
      if (plan.id === 'ultra' && !button.querySelector('.recommended')) {
        const badge=document.createElement('small');badge.className='recommended';badge.textContent='推荐';button.append(badge);
      }
      if (plan.period === 'lifetime' && !button.querySelector('.lifetime-badge')) {
        const badge=document.createElement('small');badge.className='lifetime-badge';badge.textContent='长期畅享';button.append(badge);
      }
      if (!button.querySelector('.plan-period')) {
        const period=document.createElement('small');period.className='plan-period';period.textContent=plan.period==='lifetime'?'长期有效':'30天有效';button.append(period);
      }
      const price=button.querySelector('.price');
      if (!price.querySelector('.currency')) {
        const currency=document.createElement('small');currency.className='currency';currency.textContent='¥';
        price.replaceChildren(currency,document.createTextNode(plan.price_fen/100));
      }
      if (button.getAttribute('aria-checked')==='true') byId('plan-guidance').textContent=guidance[plan.id] || '按你的使用需求选择套餐。';
    }
  }
  const observer = new MutationObserver(update);
  observer.observe(plans,{childList:true,subtree:true,attributes:true,attributeFilter:['aria-checked']});
  document.addEventListener('image-account-ready', event => {
    const notice=byId('notice');
    if (event.detail.signedIn && typeof ready!=='undefined' && ready) notice.textContent='已关联原账户，选好套餐即可扫码。';
    else if (!event.detail.signedIn && typeof ready!=='undefined' && ready) notice.textContent='从 Skill 打开会员链接，即可关联原账户。';
  });
  const notice = byId('notice');
  // A fast account response can arrive before this deferred script attaches listeners.
  if (typeof ready!=='undefined' && ready && typeof signedIn!=='undefined'
      && (notice.textContent.startsWith('已关联原生图账户。')
          || notice.textContent.startsWith('请从 WorkBuddy 生图助手打开会员页面。'))) {
    notice.textContent=signedIn?'已关联原账户，选好套餐即可扫码。':'从 Skill 打开会员链接，即可关联原账户。';
  }
  function noticeVisibility() {
    notice.hidden = ['已关联原账户，选好套餐即可扫码。','从 Skill 打开会员链接，即可关联原账户。'].includes(notice.textContent);
  }
  new MutationObserver(noticeVisibility).observe(notice,{childList:true,characterData:true,subtree:true});
  noticeVisibility();
  update();
})();
