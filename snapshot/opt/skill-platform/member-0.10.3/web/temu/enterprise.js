'use strict';
(() => {
  const byId=id=>document.getElementById(id);
  document.title='Temu企业商品图 · 企业套餐';
  document.querySelector('.compact-heading h1').textContent='Temu企业商品图';
  document.querySelector('.recharge-caption').textContent='从商品实拍到上新素材，为企业持续配图';
  document.querySelector('.current-skill span').textContent='企业服务 · Temu商家生图skill';
  document.querySelector('.payment-terms').textContent='扫码核款到账 · 30天有效 · 新购次数与Gemini共用';
  document.querySelector('.recharge-delivery-note').textContent='关联账户，领取3次Temu体验；每张图交付后，都能反馈修改意见。';
  const trial=document.createElement('p');trial.className='enterprise-trial';trial.setAttribute('role','status');byId('notice').after(trial);
  const history=document.createElement('details');history.className='enterprise-history';
  const summary=document.createElement('summary');summary.textContent='我的Temu体验与制作记录';history.append(summary);
  const records=document.createElement('ul');history.append(records);byId('member-account').append(history);
  const guidance={temu_enterprise_89:'100次，先配齐一批商品图，建立店铺视觉。',temu_enterprise_198:'240次，上新与场景换新一起安排。',temu_enterprise_365:'500次，适合多SKU持续制作与批量上新。'};
  function update(){
    for(const button of byId('plans').children){
      if(!button.querySelector('.enterprise-tag')){const tag=document.createElement('small');tag.className='enterprise-tag';tag.textContent=button.dataset.id==='temu_enterprise_198'?'日常上新':button.dataset.id==='temu_enterprise_365'?'批量制作':'企业起步';button.append(tag);}
      if(button.getAttribute('aria-checked')==='true')byId('plan-guidance').textContent=guidance[button.dataset.id]||'';
    }
  }
  new MutationObserver(update).observe(byId('plans'),{childList:true,subtree:true,attributes:true,attributeFilter:['aria-checked']});update();
  let serial=0;
  async function refresh(){
    const current=++serial;
    try{
      const data=await api('enterprise-history');if(current!==serial)return;
      trial.textContent='Temu体验：已用 '+data.trial_used+'/3 次 · 剩余 '+data.trial_remaining+' 次'+(data.trial_pending?' · 待核查 '+data.trial_pending+' 次':'');
      records.replaceChildren();
      for(const item of data.items){const li=document.createElement('li');li.textContent=new Date(item.created*1000).toLocaleString('zh-CN')+' · '+(item.usage_type==='trial'?'体验':'制作')+' · '+({succeeded:'已完成',pending:'待核查',failed:'已退回'}[item.status]||item.status)+' · 已记录反馈 '+item.feedback_count+' 条';records.append(li);}
      if(!data.items.length){const li=document.createElement('li');li.textContent='关联账户后，回到WorkBuddy开始第一张商品图。';records.append(li);}
    }catch(error){if(current===serial){trial.textContent='首次关联账户可领取3次Temu体验。';records.replaceChildren();}}
  }
  document.addEventListener('image-account-ready',refresh);
  document.addEventListener('member-account-snapshot',refresh);
  history.addEventListener('toggle',()=>{if(history.open)refresh();});
  refresh();
})();
