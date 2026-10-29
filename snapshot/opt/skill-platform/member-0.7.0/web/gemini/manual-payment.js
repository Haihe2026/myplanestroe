'use strict';
let paymentOrder=null;
let returnOrder=null,accountGeneration=0;
const paymentDialog=document.getElementById('payment-dialog');
const payEl=id=>document.getElementById(id);
function displayPaymentOrder(order){
  paymentOrder=order;
  payEl('payment-qr').src=order.qr_url;payEl('payment-save').href=order.qr_url;
  const paid=order.status==='paid';
  const planName={plus:'Plus',pro:'Pro',ultra:'Ultra',business:'终身会员'}[order.plan]||'会员';
  payEl('payment-plan').textContent='Gemini生图器 · '+planName;
  payEl('payment-amount').textContent='¥'+(order.amount_fen/100).toFixed(2);
  payEl('payment-term').textContent=order.units.toLocaleString('zh-CN')+' 次生图 · '+(order.valid_days?'核款到账后30天有效，到期不结转':'长期有效');
  payEl('payment-order-id').value=order.id;
  payEl('payment-status').textContent=paid?'已核款到账，请回 WorkBuddy 刷新次数。':order.status==='reported'?'付款登记已提交，核款确认后发放次数。':'请按上方金额扫码付款，完成后点击“我已付款”。';
  payEl('payment-qr').hidden=paid;
  payEl('payment-save').hidden=paid;
  payEl('payment-qr').style.display=paid?'none':'';
  payEl('payment-save').style.display=paid?'none':'';
  payEl('payment-report').hidden=paid;
  payEl('payment-report').disabled=false;
  payEl('payment-report').textContent=order.status==='reported'?'返回 WorkBuddy':'我已付款';
  payEl('payment-expiry').textContent=paid&&order.expires_at?'到期时间：'+new Date(order.expires_at*1000).toLocaleString('zh-CN'):'';
}
window.showPaymentOrder=order=>{
  displayPaymentOrder(order);
  if(!paymentDialog.open){paymentDialog.showModal();document.body.classList.add('payment-open');}
};
payEl('payment-close').addEventListener('click',()=>paymentDialog.close());
paymentDialog.addEventListener('close',()=>{document.body.classList.remove('payment-open');paymentOrder=null;});
paymentDialog.addEventListener('click',event=>{if(event.target===paymentDialog){const r=paymentDialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)paymentDialog.close();}});
async function copyPaymentValue(input,button){
  try{await navigator.clipboard.writeText(input.value);button.textContent='已复制';setTimeout(()=>{button.textContent='复制';},1500);}
  catch{input.focus();input.select();payEl('payment-status').textContent='请复制已选中的内容。';}
}
payEl('copy-payment-order').addEventListener('click',event=>copyPaymentValue(payEl('payment-order-id'),event.currentTarget));
payEl('copy-payment-support').addEventListener('click',event=>copyPaymentValue(payEl('payment-support'),event.currentTarget));
function showPaymentReturn(order){
  returnOrder=order;
  if(paymentDialog.open)paymentDialog.close();
  let panel=payEl('payment-return');
  if(!panel){
    panel=document.createElement('section');panel.id='payment-return';panel.className='payment-return';panel.setAttribute('role','status');panel.setAttribute('aria-live','polite');
    const mark=document.createElement('span');mark.className='return-mark';mark.textContent='✓';mark.setAttribute('aria-hidden','true');
    const title=document.createElement('h2');title.id='payment-return-title';
    const detail=document.createElement('p');detail.id='payment-return-detail';
    const continueText=document.createElement('p');continueText.textContent='图片方案已保留，到账后回到原对话继续制作。';
    const actions=document.createElement('div');actions.className='return-actions';
    const back=document.createElement('button');back.type='button';back.id='payment-back';back.textContent='返回 WorkBuddy';
    const view=document.createElement('button');view.type='button';view.id='payment-view-order';view.textContent='查看订单';
    const help=document.createElement('small');help.id='payment-return-help';help.textContent='若页面未自动关闭，请关闭当前付款标签，返回 WorkBuddy。';
    back.addEventListener('click',()=>{try{window.close();}catch{}help.textContent='请关闭当前付款标签，返回 WorkBuddy 对话继续。';});
    view.addEventListener('click',()=>{const saved=returnOrder;document.body.classList.remove('payment-returning');panel.hidden=true;if(saved)window.showPaymentOrder(saved);});
    actions.append(back,view);panel.append(mark,title,detail,continueText,actions,help);document.querySelector('main').prepend(panel);
  }
  payEl('payment-return-title').textContent=order.status==='paid'?'已核款到账':'付款登记已提交';
  payEl('payment-return-detail').textContent=order.status==='paid'?'请返回 WorkBuddy，刷新次数后继续刚才的图片。':'请返回 WorkBuddy。核款确认后预计1分钟内发放。';
  panel.hidden=false;document.body.classList.add('payment-returning');payEl('payment-back').focus();
  document.dispatchEvent(new CustomEvent('payment-return-ready',{detail:{status:order.status}}));
  // Host-created/ordinary browser tabs may disallow closing; the return view remains usable.
  try{window.close();}catch{}
}
payEl('payment-report').addEventListener('click',async()=>{
  if(!paymentOrder)return;
  if(paymentOrder.status==='reported'){showPaymentReturn(paymentOrder);return;}
  const orderId=paymentOrder.id,version=accountGeneration;
  payEl('payment-report').disabled=true;
  try{
    const order=await api('report-payment',{order_id:orderId});
    if(order.id!==orderId||!['reported','paid'].includes(order.status))throw Error('付款登记尚未确认，请刷新订单后重试。');
    if(version!==accountGeneration)return;
    showPaymentReturn(order);await loadPaymentOrders();
  }
  catch(error){payEl('payment-status').textContent=error.message;payEl('payment-report').disabled=false;}
});
payEl('payment-refresh').addEventListener('click',async()=>{
  if(!paymentOrder)return;
  payEl('payment-refresh').disabled=true;
  try{const order=await api('orders/'+encodeURIComponent(paymentOrder.id));displayPaymentOrder(order);if(order.status==='paid'){await account();await loadPaymentOrders();}}
  catch(error){payEl('payment-status').textContent=error.message;}
  finally{payEl('payment-refresh').disabled=false;}
});
async function loadPaymentOrders(){
  const list=payEl('payment-orders');list.replaceChildren();
  try{const data=await api('orders');for(const order of data.orders){
    const button=document.createElement('button');button.type='button';button.className='payment-order-row';
    const names={plus:'Plus',pro:'Pro',ultra:'Ultra',business:'终身会员'};
    button.textContent=(names[order.plan]||'会员')+' · ¥'+(order.amount_fen/100)+' · '+({paid:'已到账',reported:'待核款',pending:'待付款'}[order.status]||order.status)+' · '+order.id.slice(0,8);
    button.addEventListener('click',()=>window.showPaymentOrder(order));list.append(button);
  }if(!data.orders.length)list.textContent='暂无订单';}
  catch(error){list.textContent=error.message;}
}
document.addEventListener('image-account-ready',event=>{
  accountGeneration++;
  payEl('payment-order-section').hidden=!event.detail.signedIn;
  if(event.detail.signedIn)loadPaymentOrders();
  else{payEl('payment-orders').replaceChildren();if(paymentDialog.open)paymentDialog.close();returnOrder=null;document.body.classList.remove('payment-returning');if(payEl('payment-return'))payEl('payment-return').hidden=true;}
});
