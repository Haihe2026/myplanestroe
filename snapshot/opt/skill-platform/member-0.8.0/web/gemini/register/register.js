'use strict';
let invitation=new URLSearchParams(location.hash.slice(1)).get('entry');
history.replaceState(null,'',location.pathname);
const form=document.getElementById('registration'),consent=document.getElementById('consent'),button=document.getElementById('confirm'),feedback=document.getElementById('feedback');
const valid=typeof invitation==='string'&&/^[A-Za-z0-9_-]{43}$/.test(invitation);
if(!valid){consent.disabled=true;feedback.textContent='请回到 Gemini生图器，点击本次对话中的开通会员链接。';}
consent.addEventListener('change',()=>{button.disabled=!valid||!consent.checked;});
form.addEventListener('submit',async event=>{
  event.preventDefault();if(!valid||!consent.checked||button.disabled)return;
  button.disabled=true;feedback.textContent='正在关联创作账户…';
  try{
    const response=await fetch('/platform-api/gemini/membership-api/confirm-entry',{method:'POST',credentials:'same-origin',cache:'no-store',
      headers:{'Content-Type':'application/json','X-Membership-Request':'1'},body:JSON.stringify({ticket:invitation,accepted:true})});
    const data=await response.json();if(!response.ok||data.ok!==true)throw Error(data.error||'关联暂未完成，请稍后再试。');
    invitation=null;location.replace('/membership/gemini/');
  }catch(error){feedback.textContent=error.message;button.disabled=!consent.checked;}
});
