'use strict';
(() => {
  const byId=id=>document.getElementById(id);
  let invitation=new URLSearchParams(location.hash.slice(1)).get('entry');
  history.replaceState(null,'',location.pathname);
  const valid=typeof invitation==='string'&&/^[A-Za-z0-9_-]{43}$/.test(invitation);
  let submitted=false,reading=false;
  const form=byId('registration'),consent=byId('consent'),button=byId('confirm'),feedback=byId('feedback');
  if(!valid){consent.disabled=true;feedback.textContent='请从原技能重新打开体验入口；若刚才已经关联，可点击下方查询恢复状态。';byId('result').hidden=false;byId('retry').hidden=false;}
  consent.addEventListener('change',()=>{button.disabled=!valid||!consent.checked||submitted;});

  async function api(path,body){
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),8000);
    try{
      const response=await fetch('/platform-api/temu/membership-api/'+path,{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',signal:controller.signal,
        headers:body?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},body:body?JSON.stringify(body):undefined});
      const data=await response.json();
      if(!response.ok)throw Error('ACCOUNT_UNAVAILABLE');
      return data;
    }finally{clearTimeout(timer);}
  }

  function draw(data){
    const keys=['trial_total','trial_used','trial_pending','trial_remaining','remaining_uses'];
    if(keys.some(key=>!Number.isSafeInteger(data[key])||data[key]<0)||data.trial_used+data.trial_pending+data.trial_remaining!==data.trial_total)throw Error('INVALID_QUOTA');
    form.hidden=true;byId('result').hidden=false;byId('retry').hidden=true;
    const free=data.trial_remaining>0,pending=data.trial_pending>0;
    byId('title').textContent=free?(data.trial_total===1&&data.trial_used===0&&data.trial_pending===0?'已领取1次免费体验':'账户已关联，可以先体验'):pending?'体验制作中，请回原对话查看':data.remaining_uses>0?'账户已关联，可以继续制作':'免费体验已使用';
    byId('lead').textContent=free?'无需付款。现在回到WorkBuddy原对话发送“继续”，确认这张商品图的方案后即可制作。':pending?'原任务已保留，请回到WorkBuddy原对话发送“继续”查询，不要重复提交或购买。':data.remaining_uses>0?'原账户仍有可用次数，回到WorkBuddy原对话发送“继续”即可，不需要重复购买。':'这次体验已经完成。满意后需要继续制作，可选择Temu企业套餐，核款到账后回到原对话继续。';
    byId('trial-count').textContent='免费体验：已用 '+data.trial_used+' / '+data.trial_total+' 次 · 剩余 '+data.trial_remaining+' 次'+(pending?' · 制作或核查中 '+data.trial_pending+' 次':'');
    byId('result-status').textContent=free?'体验已到账；此页面不会自动生图或扣次。':pending?'当前是原任务处理状态，不代表体验已失败。':data.remaining_uses>0?'可用次数：'+data.remaining_uses+'次。':'免费体验不重复领取，原账户和已付次数保持不变。';
    byId('copy-continue').hidden=!(free||pending||data.remaining_uses>0);
    byId('view-plans').hidden=pending;
    byId('view-plans').classList.toggle('primary-purchase',!free&&!pending&&data.remaining_uses===0);
    byId('view-plans').textContent=free?'体验满意后，再查看企业套餐':'查看Temu企业套餐';
    byId('continuation').textContent='当前只完成账户关联和真实权益查询，没有创建付款订单。专家版与技能版共用原账户体验，不会重复领取。';
  }

  async function readAccount(){
    if(reading)return;reading=true;byId('retry').disabled=true;
    try{draw(await api('account'));}
    catch(error){
      byId('result').hidden=false;byId('retry').hidden=false;
      byId('copy-continue').hidden=true;byId('view-plans').hidden=true;
      byId('trial-count').textContent='体验资格待核对';
      byId('result-status').textContent='尚未取得真实账户次数，暂不显示领取成功。可重新查询，或回到原技能发送“继续”恢复。无需重新付款。';
    }finally{reading=false;byId('retry').disabled=false;}
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(!valid||!consent.checked||submitted)return;
    submitted=true;button.disabled=true;feedback.textContent='正在关联原账户并核对免费体验…';
    try{
      const data=await api('confirm-entry',{ticket:invitation,accepted:true});
      if(data.ok!==true)throw Error('CONFIRM_UNAVAILABLE');
      invitation=null;feedback.textContent='账户已关联，正在核对真实体验次数…';
      await readAccount();
    }catch(error){
      invitation=null;byId('result').hidden=false;byId('retry').hidden=false;
      feedback.textContent='关联结果待核对，请查询原账户状态，或回原技能发送“继续”更新入口；不会自动重复提交。';
    }
  });
  byId('retry').addEventListener('click',readAccount);
  byId('copy-continue').addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText('继续');byId('result-status').textContent='已复制“继续”。请切回WorkBuddy原对话，粘贴发送。';}
    catch(error){byId('result-status').textContent='请切回WorkBuddy原对话，发送：继续';}
  });
  byId('view-plans').addEventListener('click',()=>{location.assign('/membership/temu/');});
})();
