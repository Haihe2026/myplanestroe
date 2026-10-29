'use strict';
(() => {
  const byId=id=>document.getElementById(id);
  let invitation=new URLSearchParams(location.hash.slice(1)).get('entry');
  history.replaceState(null,'',location.pathname);
  const valid=typeof invitation==='string'&&/^[A-Za-z0-9_-]{43}$/.test(invitation);
  let submitted=false;
  const form=byId('registration'),consent=byId('consent'),button=byId('confirm'),feedback=byId('feedback');
  const remembered=byId('remembered'),linkConsent=byId('link-consent'),linkButton=byId('link'),linkFeedback=byId('link-feedback');
  const original={title:byId('title').textContent,lead:byId('lead').textContent,continuation:byId('continuation').textContent};
  if(!valid){consent.disabled=true;feedback.textContent='请回到 Gemini生图器，点击本次对话中的开通会员链接。';}
  consent.addEventListener('change',()=>{button.disabled=!valid||!consent.checked||submitted;});
  linkConsent.addEventListener('change',()=>{linkButton.disabled=!valid||!linkConsent.checked||submitted;});

  async function api(path,body){
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),8000);
    try{
      const response=await fetch('/platform-api/gemini/membership-api/'+path,{method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',signal:controller.signal,
        headers:body?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},body:body?JSON.stringify(body):undefined});
      const data=await response.json();
      if(!response.ok)throw Error('ACCOUNT_UNAVAILABLE');
      return data;
    }finally{clearTimeout(timer);}
  }

  function showNewAccount(){
    remembered.hidden=true;form.hidden=false;
    byId('title').textContent=original.title;byId('lead').textContent=original.lead;byId('continuation').textContent=original.continuation;
  }

  async function checkRemembered(){
    if(!valid)return;
    let data;
    try{data=await api('remembered');}catch(error){return;}
    if(submitted||!data||data.remembered!==true||!Number.isSafeInteger(data.remaining_uses)||data.remaining_uses<0||typeof data.account_label!=='string')return;
    form.hidden=true;remembered.hidden=false;
    byId('title').textContent='检测到你已有账户';
    byId('lead').textContent='次数保存在原账户里，不会因为新开对话清零。把这个新对话关联到原账户，就能接着用原来的次数。';
    byId('remembered-account').textContent='这个浏览器已登录：'+data.account_label+' · 可用 '+data.remaining_uses+' 次';
    byId('continuation').textContent='关联只确认账户归属，不创建订单、不扣次数。';
  }

  form.addEventListener('submit',async event=>{
    event.preventDefault();if(!valid||!consent.checked||submitted)return;
    submitted=true;button.disabled=true;feedback.textContent='正在关联创作账户…';
    try{
      const data=await api('confirm-entry',{ticket:invitation,accepted:true});
      if(data.ok!==true)throw Error('关联暂未完成，请稍后再试。');
      invitation=null;location.replace('/membership/gemini/');
    }catch(error){submitted=false;feedback.textContent='关联暂未完成，请稍后再试，或回到对话重新获取链接。';button.disabled=!consent.checked;}
  });
  linkButton.addEventListener('click',async()=>{
    if(!valid||!linkConsent.checked||submitted)return;
    submitted=true;linkButton.disabled=true;linkFeedback.textContent='正在关联原账户…';
    try{
      const data=await api('link-entry',{ticket:invitation,accepted:true});
      if(data.ok!==true||data.linked!==true)throw Error('LINK_UNAVAILABLE');
      invitation=null;
      byId('title').textContent='已关联原账户';
      byId('lead').textContent='次数没有清零。回到原对话发送“已关联”即可继续，原图片需求还在。';
      linkConsent.closest('label').hidden=true;linkButton.hidden=true;byId('use-new').hidden=true;byId('forget').hidden=true;
      byId('remembered-account').textContent='已关联这个浏览器登录的原账户。';
      linkFeedback.textContent='这次关联没有重复开户，也没有下单或扣费。';
    }catch(error){
      invitation=null;linkFeedback.textContent='没有完成关联，原账户次数不受影响。请回到原对话说“找回账户”重新获取链接；不会自动重复提交。';
    }
  });
  byId('use-new').addEventListener('click',showNewAccount);
  byId('forget').addEventListener('click',async()=>{
    byId('forget').disabled=true;
    try{await api('forget-device',{});}catch(error){}
    showNewAccount();feedback.textContent='已退出这个浏览器的登录。新账户按下面的说明继续。';
  });
  checkRemembered();
})();
