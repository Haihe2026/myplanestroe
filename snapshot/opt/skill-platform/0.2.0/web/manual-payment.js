'use strict';
let paymentOrder=null;
const paymentDialog=document.getElementById('payment-dialog');
const payEl=id=>document.getElementById(id);
function displayPaymentOrder(order){
  paymentOrder=order;
  const paid=order.status==='paid';
  const planName={plus:'Plus',pro:'Pro',ultra:'Ultra',business:'终身会员'}[order.plan]||'会员';
  payEl('payment-plan').textContent='Gemini生图助手 · '+planName;
  payEl('payment-amount').textContent='¥'+(order.amount_fen/100).toFixed(2);
  payEl('payment-term').textContent=order.units+' 次标准生图 · '+(order.valid_days?'核款到账后30天有效，到期不结转':'长期有效');
  payEl('payment-order-id').value=order.id;
  payEl('payment-status').textContent=paid?'已核款到账，请回 WorkBuddy 刷新积分。':order.status==='reported'?'已登记付款意向，尚待人工核款。请把订单号和付款凭证发给客服。':'请按上方金额扫码付款，再把订单号和付款凭证发给客服核款。';
  payEl('payment-qr').hidden=paid;
  payEl('payment-save').hidden=paid;
  payEl('payment-report').hidden=paid;
  payEl('payment-report').disabled=order.status==='reported';
  payEl('payment-report').textContent=order.status==='reported'?'已登记，等待客服核款':'我已付款';
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
payEl('payment-report').addEventListener('click',async()=>{
  if(!paymentOrder)return;
  payEl('payment-report').disabled=true;
  try{displayPaymentOrder(await api('report-payment',{order_id:paymentOrder.id}));await loadPaymentOrders();}
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
  payEl('payment-order-section').hidden=!event.detail.signedIn;
  if(event.detail.signedIn)loadPaymentOrders();
  else{payEl('payment-orders').replaceChildren();if(paymentDialog.open)paymentDialog.close();}
});
