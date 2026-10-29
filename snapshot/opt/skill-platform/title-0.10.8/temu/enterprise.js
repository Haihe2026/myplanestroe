'use strict';
(() => {
  const byId=id=>document.getElementById(id);
  document.title='Temu商家生图skill · 为商家上新助力 | MyPlaneStore';
  document.querySelector('.compact-heading h1').textContent='Temu商家生图skill';
  document.querySelector('.recharge-caption').textContent='为Temu商家助力，让好产品更出彩';
  document.querySelector('.current-skill span').textContent='WorkBuddy官方认证技能 · 企业生图服务';
  document.querySelector('.payment-terms').textContent='扫码核款到账 · 30天有效 · 新购次数与Gemini共用';
  document.querySelector('.recharge-delivery-note').textContent='一套商品实拍，主图、SKU图、场景图接着做。先体验3次，再为企业持续备图。';
  const reputation=document.querySelector('.reputation');
  reputation.querySelector('h2').textContent='为商家多想一步，把商品图一起打磨好';
  reputation.querySelector('p').textContent='从商品还原到场景构图，告诉我们哪里要改，让下一次制作更贴近您的需求。';
  reputation.querySelector('span').textContent='您的建议，记录到每一张图';
  reputation.querySelector('small').textContent='原任务接着改，商品素材持续积累。';
  const trial=document.createElement('p');trial.className='enterprise-trial';trial.setAttribute('role','status');byId('notice').after(trial);
  const history=document.createElement('details');history.className='enterprise-history';
  const summary=document.createElement('summary');summary.textContent='我的Temu体验与制作记录';history.append(summary);
  const records=document.createElement('ul');history.append(records);byId('member-account').append(history);
  const guidance={temu_enterprise_89:'100次，为新品备好主图与场景，把商品展示做扎实。',temu_enterprise_198:'240次，主图、场景、细节持续换新，为每轮上新备好素材。',temu_enterprise_365:'500次，面向多SKU批量备图，让店铺视觉跟上上新节奏。'};
  function update(){
    for(const button of byId('plans').children){
      if(!button.querySelector('.enterprise-tag')){const tag=document.createElement('small');tag.className='enterprise-tag';tag.textContent=button.dataset.id==='temu_enterprise_198'?'成长优选':button.dataset.id==='temu_enterprise_365'?'批量备图':'上新起步';button.append(tag);}
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
