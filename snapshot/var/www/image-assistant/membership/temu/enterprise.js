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
