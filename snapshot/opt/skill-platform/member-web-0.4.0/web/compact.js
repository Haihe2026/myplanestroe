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
    plus:'轻量起步，先完成眼前这一批配图。',
    pro:'日常配图，给连续创作多留一些余量。',
    ultra:'一次备足54次，集中制作更从容。',
    business:'一次开通2000次，按自己的节奏长期使用。'
  };
  const plans = byId('plans');
  if (!plans) return;
  function update() {
    for (const button of plans.children) {
      const plan = typeof catalog !== 'undefined' ? catalog.find(value=>value.id===button.dataset.id) : null;
      if (!plan) continue;
      const count = button.querySelector('.count');
      const text = (plan.images ?? plan.points / 1000) + ' 次标准生图';
      if (count.textContent !== text) count.textContent = text;
      if (plan.id === 'ultra' && !button.querySelector('.recommended')) {
        const badge=document.createElement('small');badge.className='recommended';badge.textContent='推荐';button.append(badge);
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
  function noticeVisibility() {
    notice.hidden = ['已关联原账户，选好套餐即可扫码。','从 Skill 打开会员链接，即可关联原账户。'].includes(notice.textContent);
  }
  new MutationObserver(noticeVisibility).observe(notice,{childList:true,characterData:true,subtree:true});
  noticeVisibility();
  update();
})();
