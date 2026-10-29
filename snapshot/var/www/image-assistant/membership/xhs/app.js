'use strict';
let catalog=[], selected='gemini_permanent_49', signedIn=false, ready=false;
const el=id=>document.getElementById(id);
async function api(path,body){
  const response=await fetch('/platform-api/xhs/membership-api/'+path,{credentials:'same-origin',cache:'no-store',
    headers:body?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},
    method:body?'POST':'GET',body:body?JSON.stringify(body):undefined});
  const result=await response.json(); if(!response.ok)throw new Error(result.error||'连接暂不可用');return result;
}
function choose(id){selected=id;for(const button of el('plans').children){button.setAttribute('aria-checked',String(button.dataset.id===id));button.tabIndex=button.dataset.id===id?0:-1;}
  const plan=catalog.find(p=>p.id===id);const lifetime=['lifetime','permanent'].includes(plan.period);
  el('renewal').disabled=true;el('renewal').checked=false;
  el('summary').textContent=plan.name+(lifetime?' 次数包':' 月度会员');
  el('detail').textContent=plan.images.toLocaleString('zh-CN')+' 次生图 · '+(lifetime?'永久有效':'付款确认后30天有效，到期不结转');
  el('total').textContent='¥'+((el('renewal').checked&&!lifetime?plan.renewal_price_fen:plan.price_fen)/100)+(lifetime?'':' / 月');
}
function render(){for(const plan of catalog){const button=document.createElement('button');button.type='button';button.className='plan';button.dataset.id=plan.id;button.setAttribute('role','radio');
  const name=document.createElement('b');name.textContent=plan.period==='lifetime'?'终身会员':plan.name;button.append(name);
  const check=document.createElement('span');check.className='check';check.textContent='✓';check.setAttribute('aria-hidden','true');button.append(check);
  const price=document.createElement('span');price.className='price';price.textContent='¥'+plan.price_fen/100;button.append(price);
  const count=document.createElement('span');count.className='count';count.textContent=['lifetime','permanent'].includes(plan.period)?'永久有效':'核款到账后30天有效';button.append(count);
  const points=document.createElement('span');points.className='points';points.textContent=plan.images.toLocaleString('zh-CN')+' 次';button.append(points);
  button.addEventListener('click',()=>choose(plan.id));button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowDown','ArrowUp'].includes(event.key))return;event.preventDefault();const direction=['ArrowLeft','ArrowUp'].includes(event.key)?-1:1;const index=(catalog.findIndex(p=>p.id===selected)+direction+catalog.length)%catalog.length;choose(catalog[index].id);el('plans').children[index].focus();});el('plans').append(button);}if(!catalog.some(plan=>plan.id===selected))selected=catalog[0].id;choose(selected);}
async function account(){try{const data=await api('account');signedIn=true;el('account').textContent=data.label;el('balance').replaceChildren(document.createTextNode(data.remaining_uses.toLocaleString('zh-CN')+' '));const small=document.createElement('small');small.textContent='次';el('balance').append(small);el('notice').textContent=ready?'已关联原生图账户。扫码付款后联系客服核款，到账后回 Skill 客户端 刷新次数即可。':'已关联原生图账户。收款暂未开放，已有次数可继续使用。';}catch(error){signedIn=false;el('account').textContent='尚未关联生图账户';el('balance').replaceChildren(document.createTextNode('— '));const small=document.createElement('small');small.textContent='次';el('balance').append(small);el('notice').textContent=error.message+'。在 Skill 客户端 对生图助手说“打开会员中心”，无需重新注册。';}el('buy').disabled=!ready||!signedIn;el('buy').textContent=ready?'扫码开通':'收款暂未开放';document.dispatchEvent(new CustomEvent('image-account-ready',{detail:{signedIn}}));}
el('refresh').addEventListener('click',account);
el('renewal').addEventListener('change',()=>choose(selected));
function updateBuy(){el('buy').disabled=!ready;el('buy').textContent=ready?(signedIn?'扫码开通':'关联账户并开通'):'收款暂未开放';}
function showAccountDialog(){el('account-plan').textContent=el('summary').textContent+' · '+el('total').textContent;el('account-feedback').textContent='';el('account-dialog').showModal();document.body.classList.add('payment-open');}
document.addEventListener('image-account-ready',()=>{updateBuy();if(signedIn&&el('account-dialog').open)el('account-dialog').close();});
el('account-close').addEventListener('click',()=>el('account-dialog').close());
el('account-dialog').addEventListener('close',()=>document.body.classList.remove('payment-open'));
el('account-copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(el('account-prompt').value);el('account-feedback').textContent='已复制，请到 Skill 客户端 发送。';}catch(error){el('account-prompt').focus();el('account-prompt').select();el('account-feedback').textContent='请复制上面已选中的文字，到 Skill 客户端 发送。';}});
el('account-recheck').addEventListener('click',async()=>{el('account-recheck').disabled=true;try{await account();if(!signedIn)el('account-feedback').textContent='还未关联，请打开 Skill 客户端 返回的会员链接。';}finally{el('account-recheck').disabled=false;}});
el('buy').addEventListener('click',async()=>{if(!ready)return;if(!signedIn){showAccountDialog();return;}el('buy').disabled=true;try{const order=await api('orders',{plan:selected,product:'gemini-image-assistant'});window.showPaymentOrder(order);}catch(error){el('notice').textContent=error.message;await account();if(!signedIn)showAccountDialog();}finally{updateBuy();}});
window.addEventListener('hashchange',async()=>{
  const ticket=new URLSearchParams(location.hash.slice(1)).get('ticket');
  history.replaceState(null,'',location.pathname);
  if(!ticket)return;
  signedIn=false;el('buy').disabled=true;
  document.dispatchEvent(new CustomEvent('image-account-ready',{detail:{signedIn:false}}));
  try{await api('redeem',{ticket});await account();}
  catch(error){signedIn=false;el('notice').textContent=error.message+'。请从 Skill 客户端 重新打开会员中心。';updateBuy();}
});
(async()=>{const ticket=new URLSearchParams(location.hash.slice(1)).get('ticket');history.replaceState(null,'',location.pathname);try{const data=await api('plans');catalog=data.plans;ready=data.payment_ready===true;render();if(ticket)await api('redeem',{ticket});await account();}catch(error){signedIn=false;el('notice').textContent=error.message+'。请从 Skill 客户端 重新打开会员中心。';updateBuy();}})();
