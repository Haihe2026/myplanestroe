'use strict';
(() => {
  const history=document.createElement('details');history.className='enterprise-history';
  const summary=document.createElement('summary');summary.textContent='我的Temu体验与制作记录';history.append(summary);
  const trial=document.createElement('p');trial.className='enterprise-trial';trial.setAttribute('role','status');history.append(trial);
  const records=document.createElement('ul');history.append(records);document.getElementById('member-account').append(history);
  let serial=0;
  function clear(){serial++;trial.textContent='';records.replaceChildren();}
  async function refresh(){
    const current=++serial;
    try{
      const data=await api('enterprise-history');if(current!==serial)return;
      trial.textContent='Temu专用体验：已用 '+data.trial_used+'/3 次 · 剩余 '+data.trial_remaining+' 次'+(data.trial_pending?' · 待核查 '+data.trial_pending+' 次':'');
      records.replaceChildren();
      for(const item of data.items){const li=document.createElement('li');li.textContent=new Date(item.created*1000).toLocaleString('zh-CN')+' · '+(item.usage_type==='trial'?'体验':'制作')+' · '+({succeeded:'已完成',pending:'待核查',failed:'已退回'}[item.status]||item.status)+' · 已记录反馈 '+item.feedback_count+' 条';records.append(li);}
      if(!data.items.length){const li=document.createElement('li');li.textContent='回到原Skill对话，开始第一张商品图。';records.append(li);}
    }catch{if(current===serial){trial.textContent='';records.replaceChildren();}}
  }
  document.addEventListener('image-account-ready',event=>{clear();if(event.detail.signedIn&&history.open)refresh();});
  document.addEventListener('member-account-snapshot',()=>{if(history.open)refresh();});
  history.addEventListener('toggle',()=>{if(history.open)refresh();else clear();});
})();
