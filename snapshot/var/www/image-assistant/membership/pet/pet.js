'use strict';
const base='/platform-api/pet/membership-api/';let order=null,accountLinked=false;
const $=id=>document.getElementById(id);
async function api(path,body){const controller=new AbortController(),deadline=setTimeout(()=>controller.abort(),12000);try{const r=await fetch(base+path,{signal:controller.signal,credentials:'same-origin',cache:'no-store',method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok){const e=Error(d.error||'暂时无法读取');e.status=r.status;throw e;}return d;}finally{clearTimeout(deadline);}}
function card(label,value){const a=document.createElement('article'),s=document.createElement('span'),v=document.createElement('strong');s.textContent=label;v.textContent=value;a.append(s,v);return a;}
async function account(){const a=await api('account');accountLinked=true;$('account').hidden=false;$('quota').replaceChildren(card('服务有效期',a.expires_at?new Date(a.expires_at*1000).toLocaleDateString('zh-CN',{timeZone:'Asia/Shanghai'}):'按所选套餐生效'),card('宠物档案',a.profiles_used+' / '+(a.profiles_limit===-1?'不限':a.profiles_limit)));if(a.photo_analysis_ready)$('quota').append(card('剩余照片分析',a.photo_remaining+a.trial_photo_remaining));}
async function main(){const ticket=new URLSearchParams(location.hash.slice(1)).get('ticket');if(ticket){history.replaceState(null,'',location.pathname);await api('redeem',{ticket});}const cfg=await api('plans');$('price-anchor').textContent=cfg.display?.price_anchor||'';
const fallbackNames={pet_monthly:'给毛孩子买个安心',pet_quarterly:'毛孩子季度问安包',pet_annual:'毛孩子年度安康会员'};
for(const [id,p] of Object.entries(cfg.plans)){
 const a=document.createElement('article'),name=document.createElement('h3'),price=document.createElement('strong'),duration=document.createElement('p'),suitable=document.createElement('p'),features=document.createElement('ul'),benefit=document.createElement('p'),button=document.createElement('button');
 name.className='plan-name';name.textContent=typeof p.name==='string'&&p.name.trim()?p.name:fallbackNames[id]||'养护套餐';
 price.textContent='¥'+(p.price_fen/100).toFixed(p.price_fen%100?2:0);duration.className='plan-duration';duration.textContent=p.duration_days+'天';
 suitable.className='plan-suitable';suitable.textContent=p.display?.suitable||'';features.className='plan-features';
 const lines=[...(p.display?.features||[p.duration_days+'天养护服务','宠物档案'+(p.pet_profiles===-1?'不限':p.pet_profiles+'只'),'日常养护问询'])];
 // Closed vision services are never advertised as purchasable/available benefits.
 if(cfg.photo_analysis_ready&&p.display?.photo)lines.push(p.display.photo);
 for(const text of lines){const li=document.createElement('li');li.textContent=text;features.append(li);}
 benefit.className='plan-benefit';benefit.textContent=id==='pet_monthly'&&!cfg.photo_analysis_ready?'':p.display?.benefit||'';
 button.textContent=cfg.payment_ready?'选择套餐':'联系客服开通';button.disabled=!cfg.payment_ready;
 button.onclick=()=>openCheckout(id,p);
 a.append(name,price,duration,suitable,features);if(benefit.textContent)a.append(benefit);a.append(button);$('plans').append(a);
}
try{await account();}catch(e){$('status').textContent='请先在宠物养护中关联账户，关联后回到此页即可选择养护套餐。';}}

let selectedPlan=null,selectedConfig=null,paymentTimer=null,paymentBusy=false,checking=false,checkoutGeneration=0;
function feedback(text){$('payment-feedback').textContent=text;}
function stopPolling(){if(paymentTimer){clearInterval(paymentTimer);paymentTimer=null;}}
function poll(){stopPolling();paymentTimer=setInterval(()=>{if(document.visibilityState==='hidden'||!$('payment').open)return;if(order)checkPayment();else if(!paymentBusy)preparePayment();},5000);}
async function openCheckout(id,p){
 if(paymentBusy)return;
 checkoutGeneration++;selectedPlan=id;selectedConfig=p;order=null;stopPolling();
 $('selected-plan').textContent=p.name+' · '+p.duration_days+'天 · ¥'+(p.price_fen/100).toFixed(2);
 $('qr').hidden=false;$('payment-content').hidden=true;$('payment-identity').hidden=true;$('reported').disabled=false;
 if(!$('payment').open)$('payment').showModal();
 await preparePayment();
}
async function preparePayment(){
 if(paymentBusy||!selectedPlan||!$('payment').open)return;
 paymentBusy=true;$('payment-retry').disabled=true;$('payment-retry').textContent='正在检查账户…';const generation=checkoutGeneration;feedback('正在检查当前浏览器的账户登录状态…');
 try{
  try{await account();}catch(e){if(e.status!==401)throw e;await api('resume',{});await account();}
  if(!$('payment').open)return;
  const created=await api('orders',{plan:selectedPlan});if(generation!==checkoutGeneration||!$('payment').open)return;order=created;
  $('order-info').textContent='订单 '+order.id+' · 应付 ¥'+(order.amount_fen/100).toFixed(2);
  $('payment-identity').hidden=true;$('payment-content').hidden=false;
  $('reported').disabled=order.status==='reported'||order.status==='paid';
  if(order.status==='paid'){await completePayment();return;}
  feedback(order.status==='reported'?'付款信息已登记，正在等待核款确认。':'请用微信或支付宝扫码，按订单金额付款。');poll();
 }catch(e){
  if(e.status===401||e.status===403){accountLinked=false;$('payment-identity').hidden=false;$('payment-content').hidden=true;feedback(e.status===403?'已识别到账户，但还没有确认宠物账户。请回到宠物养护对话回复“会员”，完成确认后再试。':'这次检查还没有识别到账户登录。请先点击“登录已有账户”；首次使用请复制下方指令，发到宠物养护对话完成确认。');}
  else{feedback(e.name==='AbortError'?'本次账户检查超时，请检查网络后重新点击。':'暂时无法打开付款，请稍后重试。');$('payment-identity').hidden=false;}
  $('payment-retry').hidden=false;
 }finally{paymentBusy=false;$('payment-retry').disabled=false;$('payment-retry').textContent='重新检查并显示收款码';}
}
async function completePayment(){
 stopPolling();$('reported').disabled=true;$('qr').hidden=true;$('payment-content').hidden=true;
 feedback('开通成功！回到宠物养护对话，即可使用你的养护权益。');
 $('status').textContent='开通已完成，回到宠物养护对话即可继续使用。';
 await account();
}
async function checkPayment(){
 if(!order||checking)return;
 checking=true;
 const generation=checkoutGeneration,id=order.id;
 try{const updated=await api('orders/'+id);if(generation!==checkoutGeneration||!order||id!==order.id)return;order=updated;if(order.status==='paid')await completePayment();else feedback(order.status==='reported'?'付款信息已登记，正在等待核款确认。':'请扫码付款，完成后点击“我已付款”。');}
 catch(e){feedback('暂时无法读取到账状态，请稍后刷新。');}
 finally{checking=false;}
}
$('reported').onclick=async()=>{
 if(!order)return;const generation=checkoutGeneration,id=order.id;$('reported').disabled=true;
 try{const updated=await api('report-payment',{order_id:id});if(generation!==checkoutGeneration)return;order=updated;feedback('付款信息已登记，核款确认后养护权益自动到账。');poll();await checkPayment();}
 catch(e){$('reported').disabled=false;feedback('暂时未能登记付款，请稍后重试或联系客服。');}
};
$('check-order').onclick=checkPayment;
$('payment-retry').onclick=preparePayment;
$('payment-close').onclick=()=>{$('payment').close();stopPolling();};
$('payment').addEventListener('close',()=>{checkoutGeneration++;stopPolling();});
$('payment').addEventListener('click',e=>{if(e.target!==$('payment'))return;const r=$('payment').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('payment').close();});
main().catch(e=>$('status').textContent='请稍后刷新页面，或联系客服协助完成当前操作。');

$('payment-copy').onclick=async()=>{try{await navigator.clipboard.writeText('会员，请帮我确认宠物账户并打开付款链接');feedback('已复制。请粘贴到宠物养护对话，按返回的链接完成账户确认，再回到这里继续付款。');}catch(e){feedback('请在宠物养护对话中发送：会员，请帮我确认宠物账户并打开付款链接。');}};
globalThis.addEventListener?.('focus',()=>{if($('payment').open&&!order&&!paymentBusy)preparePayment();});
