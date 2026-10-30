'use strict';
(() => {
  const byId=id=>document.getElementById(id);
  document.title='Temu商家生图skill · 为商家上新助力 | MyPlaneStore';
  document.querySelector('.compact-heading h1').textContent='Temu商家生图skill';
  document.querySelector('.recharge-caption').textContent='做一个Temu团队懂得转化的智能美工助手';
  document.querySelector('.current-skill span').textContent='WorkBuddy官方认证技能 · 企业生图服务';
  document.querySelector('.recharge-delivery-note').textContent='一套商品实拍，主图、SKU图、场景图接着做。新用户先体验1次，再为企业持续备图。';
  const trial=document.createElement('p');trial.hidden=true;trial.className='enterprise-trial';trial.setAttribute('role','status');byId('notice').after(trial);
  const history=document.createElement('details');history.className='enterprise-history';
  const summary=document.createElement('summary');summary.textContent='我的Temu体验与制作记录';history.append(summary);
  const records=document.createElement('ul');history.append(records);byId('member-account').append(history);
  const guidance={"temu_permanent_89": "适合日常商品上新，次数永久有效。", "temu_permanent_198": "适合持续上新与多款商品制作，次数永久有效。", "temu_permanent_365": "低至约¥0.18／张，适合批量制作，次数永久有效。", "temu_image20_89": "适合日常商品上新，次数永久有效。", "temu_image20_198": "适合持续上新与多款商品制作，次数永久有效。", "temu_image20_365": "低至约¥0.18／张，适合批量制作，次数永久有效。"};
  function update(){
    for(const button of byId('plans').children){
      if(!button.querySelector('.enterprise-tag')){const tag=document.createElement('small');tag.className='enterprise-tag';tag.textContent=/_(198)$/.test(button.dataset.id)?'成长优选':/_(365)$/.test(button.dataset.id)?'批量备图':'上新起步';button.append(tag);}
      if(button.getAttribute('aria-checked')==='true'){const plan=typeof catalog!=='undefined'?catalog.find(p=>p.id===button.dataset.id):null;byId('plan-guidance').textContent='<0.20元/张，'+(plan?plan.images.toLocaleString('zh-CN')+'张，':'')+(guidance[button.dataset.id]||'商品图按需制作，次数永久有效。');}
    }
  }
  new MutationObserver(update).observe(byId('plans'),{childList:true,subtree:true,attributes:true,attributeFilter:['aria-checked']});update();
  let serial=0;
  async function refresh(){
    const current=++serial;
    try{
      const data=await api('enterprise-history');if(current!==serial)return;
      trial.textContent='Temu体验：已用 '+data.trial_used+'/'+data.trial_total+' 次 · 剩余 '+data.trial_remaining+' 次'+(data.trial_pending?' · 待核查 '+data.trial_pending+' 次':'');
      records.replaceChildren();
      for(const item of data.items){const li=document.createElement('li');li.textContent=new Date(item.created*1000).toLocaleString('zh-CN')+' · '+(item.usage_type==='trial'?'体验':'制作')+' · '+({succeeded:'已完成',pending:'待核查',failed:'已退回'}[item.status]||item.status)+' · 已记录反馈 '+item.feedback_count+' 条';records.append(li);}
      if(!data.items.length){const li=document.createElement('li');li.textContent='关联账户后，回到WorkBuddy开始第一张商品图。';records.append(li);}
    }catch(error){if(current===serial){trial.textContent='新用户关联账户可体验1次；原账户以实际权益为准。';records.replaceChildren();}}
  }
  document.addEventListener('image-account-ready',refresh);
  document.addEventListener('member-account-snapshot',refresh);
  history.addEventListener('toggle',()=>{if(history.open)refresh();});
  refresh();
})();
