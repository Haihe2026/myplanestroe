'use strict';
let catalog=[], selected='ultra', signedIn=false, ready=false;
const el=id=>document.getElementById(id);
async function api(path,body){
  const response=await fetch('/membership-api/'+path,{credentials:'same-origin',cache:'no-store',
    headers:body?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},
    method:body?'POST':'GET',body:body?JSON.stringify(body):undefined});
  const result=await response.json(); if(!response.ok)throw new Error(result.error||'连接暂不可用');return result;
}
function choose(id){selected=id;for(const button of el('plans').children){button.setAttribute('aria-checked',String(button.dataset.id===id));button.tabIndex=button.dataset.id===id?0:-1;}
  const plan=catalog.find(p=>p.id===id);const lifetime=plan.period==='lifetime';
  el('renewal').disabled=lifetime;if(lifetime)el('renewal').checked=false;
  el('summary').textContent=(lifetime?'终身':plan.name+' 月度')+'会员';
  el('detail').textContent=(lifetime?'一次发放 ':'每月 ')+plan.images+' 次标准生图 · '+plan.points.toLocaleString('zh-CN')+' 积分';
  el('total').textContent='¥'+((el('renewal').checked&&!lifetime?plan.renewal_price_fen:plan.price_fen)/100)+(lifetime?'':' / 月');
}
function render(){for(const plan of catalog){const button=document.createElement('button');button.type='button';button.className='plan';button.dataset.id=plan.id;button.setAttribute('role','radio');
  const name=document.createElement('b');name.textContent=plan.period==='lifetime'?'终身会员':plan.name;button.append(name);
  const check=document.createElement('span');check.className='check';check.textContent='✓';check.setAttribute('aria-hidden','true');button.append(check);
  const price=document.createElement('span');price.className='price';price.textContent='¥'+plan.price_fen/100;button.append(price);
  const count=document.createElement('span');count.className='count';count.textContent=(plan.period==='lifetime'?'共 ':'每月 ')+plan.images+' 次标准生图';button.append(count);
  const points=document.createElement('span');points.className='points';points.textContent=plan.points.toLocaleString('zh-CN')+' 积分';button.append(points);
  button.addEventListener('click',()=>choose(plan.id));button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowDown','ArrowUp'].includes(event.key))return;event.preventDefault();const direction=['ArrowLeft','ArrowUp'].includes(event.key)?-1:1;const index=(catalog.findIndex(p=>p.id===selected)+direction+catalog.length)%catalog.length;choose(catalog[index].id);el('plans').children[index].focus();});el('plans').append(button);}choose(selected);}
async function account(){try{const data=await api('account');signedIn=true;el('account').textContent=data.label;el('balance').replaceChildren(document.createTextNode(data.balance_points.toLocaleString('zh-CN')+' '));const small=document.createElement('small');small.textContent='积分';el('balance').append(small);el('notice').textContent=ready?'已关联原生图账户。购买后回 WorkBuddy 刷新积分即可继续使用。':'已关联原生图账户。收款通道接入中，暂不收款；免费生图照常使用。';}catch(error){signedIn=false;el('notice').textContent=error.message+'。在 WorkBuddy 对生图助手说“打开会员中心”，无需重新注册。';}el('buy').disabled=!ready||!signedIn;}
el('refresh').addEventListener('click',account);
el('renewal').addEventListener('change',()=>choose(selected));
el('buy').addEventListener('click',async()=>{if(!ready||!signedIn)return;el('buy').disabled=true;try{await api('orders',{plan:selected});el('notice').textContent='订单已创建，请等待收款通道指引。';}catch(error){el('notice').textContent=error.message;}finally{el('buy').disabled=!ready||!signedIn;}});
(async()=>{const ticket=new URLSearchParams(location.hash.slice(1)).get('ticket');history.replaceState(null,'',location.pathname);try{const data=await api('plans');catalog=data.plans;ready=data.payment_ready===true;render();if(ticket)await api('redeem',{ticket});await account();}catch(error){el('notice').textContent=error.message+'。请从 WorkBuddy 重新打开会员中心。';}})();
