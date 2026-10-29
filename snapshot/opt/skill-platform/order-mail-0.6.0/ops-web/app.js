'use strict';
const $=id=>document.getElementById(id);
const names={gemini:'Gemini生图器',temu:'Temu图片大师',xhs:'XHS选题大师',shared:'共享创作账户'};
const eventNames={activation_created:'新账户激活',activation_restored:'恢复原账户',activation_attempt:'激活失败',generation_request:'生成请求',balance_view:'查看余额',legacy_membership_link:'获取旧会员链接',legacy_membership_open:'打开旧会员页',legacy_order_create:'创建旧收款订单',purchase_offer_fetch:'获取购买选项',native_order_attempt:'尝试应用内下单'};
const ledgerNames={trial_grant:'首次赠送',reserve:'生成预占',confirmed_failure_refund:'生成失败退分',manual_verified_topup:'人工核实到账',email_verified_topup:'邮件确认到账',monthly_expiry:'月度额度到期',expired_failure_release:'已过期额度解除占用'};
let page=1,total=0,accountSeq=0,summarySeq=0;
const num=n=>Number(n||0).toLocaleString('zh-CN');
const money=n=>'¥'+(Number(n||0)/100).toFixed(2);
const date=n=>n?new Date(n*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'未记录';
function cell(row,value,cls){const td=document.createElement('td');td.textContent=value;if(cls)td.className=cls;row.append(td);return td;}
function tr(body,values){const row=document.createElement('tr');values.forEach(v=>cell(row,v));$(body).append(row);return row;}
function message(text=''){$('message').textContent=text;}
async function api(path,body){const response=await fetch('/ops/api/'+path,{credentials:'same-origin',method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(20000)});const result=await response.json();if(!response.ok){if(response.status===401){$('login').hidden=false;$('console').hidden=true;$('logout').hidden=true;if($('journey').open)$('journey').close();if($('settlement').open)$('settlement').close();message('登录已过期，请重新登录后使用原交易单号核查或重试');}throw Error(result.error||'暂时无法加载数据');}return result;}
function show(){ $('login').hidden=true;$('console').hidden=false;$('logout').hidden=false; }
async function summary(){const seq=++summarySeq;const d=await api('summary?days='+$('days').value);if(seq!==summarySeq)return;show();['products','requests','sources'].forEach(id=>$(id).replaceChildren());let u=0,s=0,p=0,paid=0;for(const item of d.products){if(!item.connected){tr('products',[names[item.product],'数据源不可用','—','—','—','—','—','—']);continue;}const j=item.jobs;u+=item.users;s+=j.succeeded||0;p+=j.pending||0;paid+=item.paid.amount_fen;tr('products',[names[item.product],num(item.users),num(item.new_users),num(item.active),num(j.succeeded),num(j.pending),num(j.failed),money(item.paid.amount_fen)]);const acts=item.events.filter(e=>e.event.startsWith('activation_'));const count=acts.reduce((n,e)=>n+e.count,0),failed=acts.filter(e=>e.status>=400).reduce((n,e)=>n+e.count,0);const sum=name=>item.events.filter(e=>e.event===name).reduce((n,e)=>n+e.count,0);tr('requests',[names[item.product],num(count),num(sum('activation_created'))+' / '+num(sum('activation_restored')),num(failed),count?(100*failed/count).toFixed(1)+'%':'—',num(sum('purchase_offer_fetch')),num(sum('native_order_attempt'))]);const groups={};for(const e of acts){const key=e.device+'|'+e.channel;groups[key]??={device:e.device,channel:e.channel,n:0,bad:0};groups[key].n+=e.count;if(e.status>=400)groups[key].bad+=e.count;}for(const g of Object.values(groups)){tr('sources',[names[item.product],({desktop:'桌面',mobile:'手机',cloud:'云端',unknown:'未知'})[g.device]||'未知',({workbuddy_skill:'WorkBuddy技能',workbuddy_expert:'WorkBuddy专家',skillhub:'SkillHub',unknown:'未知'})[g.channel]||'未知',num(g.n),num(g.bad)]);}}
$('users-total').textContent=num(u);$('images-total').textContent=num(s);$('pending-total').textContent=num(p);$('paid-total').textContent=money(paid);$('updated').textContent='更新于 '+date(d.generated_at);$('started').textContent='请求采集始于 '+date(d.collection_started);if(!$('sources').children.length)tr('sources',['尚无激活请求记录','—','—','—','—']);}
async function accounts(){const seq=++accountSeq;const product=$('product').value;const data=await api('users?'+new URLSearchParams({product,q:$('search').value,page:String(page)}));if(seq!==accountSeq)return;total=data.total;$('accounts').replaceChildren();for(const u of data.users){const row=tr('accounts',[u.id.slice(0,12),date(u.activated),date(u.last_job),num(u.images),num(u.balance_points/1000)]);const button=document.createElement('button');button.className='link';button.textContent='查看旅程';button.addEventListener('click',()=>journey(product,u.id).catch(e=>message(e.message)));cell(row,'').append(button);}if(!data.users.length)tr('accounts',['暂无账户','—','—','—','—','—']);$('page').textContent='第 '+page+' 页 · '+num(total)+' 个账户';$('prev').disabled=page<=1;$('next').disabled=page*50>=total;}
async function journey(product,uid){const d=await api('journey?'+new URLSearchParams({product,uid}));$('journey-id').textContent=names[product]+' / '+d.id;$('journey-balance').textContent=num(d.balance_points/1000)+(product==='shared'?' 共享次':' 次')+(d.legacy_accounts||[]).map(x=>' · 原'+names[x.product]+' '+num(x.remaining_uses)+'次').join('');$('timeline').replaceChildren();const rows=[];for(const x of d.ledger)rows.push({at:x.created,title:ledgerNames[x.kind]||x.kind,note:'业务流水 · '+(x.amount>0?'+':'')+num(x.amount)+'次'});for(const x of d.jobs)rows.push({at:x.created,title:'生成任务 · '+({succeeded:'成功',pending:'待核查',failed:'失败'})[x.status],note:'任务创建时间 · '+x.id.slice(0,12)});for(const x of d.orders){rows.push({at:x.created,title:'创建订单 · '+money(x.amount_fen),note:'当前状态：'+({paid:'已确认到账',reported:'用户报告已付款，待核实',pending:'待付款'})[x.status]});if(x.paid_at)rows.push({at:x.paid_at,title:'收款确认 · '+money(x.amount_fen),note:x.provider==='manual_qr'?'人工核款':x.provider==='manual_email'?'邮件确认核款':'渠道：'+x.provider});}for(const x of d.events)rows.push({at:x.created,title:eventNames[x.event]||x.event,note:'请求事件 · HTTP '+x.status+' · '+x.duration_ms+'ms · 渠道 '+x.channel});rows.sort((a,b)=>b.at-a.at);for(const x of rows){const li=document.createElement('li'),title=document.createElement('strong'),time=document.createElement('time'),note=document.createElement('p');title.textContent=x.title;time.textContent=date(x.at);note.textContent=x.note;li.append(title,time,note);$('timeline').append(li);}if(!rows.length){const li=document.createElement('li');li.textContent='暂无旅程记录';$('timeline').append(li);}if(!$('journey').open)$('journey').showModal();}
const orderStates={reported:'已报付款 · 待核款',pending:'待付款',paid:'已核款到账'};
let orderPage=1,orderSeq=0;
async function orders(){
 const seq=++orderSeq,product=$('order-product').value;
 const d=await api('orders?'+new URLSearchParams({product,status:$('order-status').value,q:$('order-search').value.trim(),page:String(orderPage)}));
 if(seq!==orderSeq)return;
 $('orders').replaceChildren();
 const reported=d.counts.reported||{count:0,amount_fen:0};
 $('order-counts').textContent='该产品待核款 '+num(reported.count)+' 笔 · '+money(reported.amount_fen);
 for(const x of d.orders){
  const row=tr('orders',[x.id,x.user_id.slice(0,12),(names[x.source_product]||names[product])+' · '+x.plan+' / '+num(x.units)+'次',money(x.amount_fen),orderStates[x.status]||x.status,date(x.created),date(x.paid_at)]);
  row.dataset.orderId=x.id;
  row.children[1].title=x.user_id;
  if(x.status==='reported')row.children[4].className='warning';
  const button=document.createElement('button');button.className='link';button.textContent='查看用户旅程';
  button.addEventListener('click',()=>journey(product,x.user_id).catch(e=>message(e.message)));
  const actions=document.createElement('div');actions.className='order-actions';
  if(d.settlement_enabled&&['pending','reported'].includes(x.status)){
   const settle=document.createElement('button');settle.textContent='核款发放';settle.dataset.settle=x.id;
   settle.addEventListener('click',()=>openSettlement(product,x.id).catch(e=>message(e.message)));actions.append(settle);
  }
  actions.append(button);const actionCell=cell(row,'');actionCell.append(actions);row.prepend(actionCell);
 }
 if(!d.orders.length)tr('orders',['暂无符合条件的订单','—','—','—','—','—','—','—']);
 $('order-page').textContent='第 '+orderPage+' 页 · '+num(d.total)+' 笔订单';
 $('order-prev').disabled=orderPage<=1;$('order-next').disabled=orderPage*50>=d.total;
 $('order-updated').textContent='订单更新于 '+date(d.generated_at);
 document.title=(reported.count?'('+reported.count+'笔待核款) ':'')+'MyPlaneStore | 运营监控';
}
let settlementOrder=null,submitting=false,polling=false;
async function openSettlement(product,id){
 const x=await api('order?'+new URLSearchParams({product,id}));
 if(x.status==='paid'){message('该订单已入账，无需再次发放');await orders();return;}
 if(!['pending','reported'].includes(x.status))throw Error('当前订单状态不能核款');
 settlementOrder={...x,product};$('settlement-form').reset();$('settlement-error').textContent='';
 $('settlement-order').textContent=x.id;$('settlement-user').textContent=x.user_id;
 $('settlement-expected').textContent=money(x.amount_fen);$('settlement-points').textContent=num(x.points/1000)+' 次';
 $('settlement-validity').textContent=x.plan==='business'?'长期有效':'核款成功起30天';
 $('settlement-amount').placeholder=(x.amount_fen/100).toFixed(2);
 if(!$('settlement').open)$('settlement').showModal();$('settlement-amount').focus();
}
$('settlement-close').addEventListener('click',()=>{if(!submitting)$('settlement').close();});
$('settlement').addEventListener('cancel',e=>{if(submitting)e.preventDefault();});
$('settlement-form').addEventListener('submit',async e=>{
 e.preventDefault();if(submitting||!settlementOrder)return;
 const raw=$('settlement-amount').value.trim();
 if(!/^\d+(\.\d{1,2})?$/.test(raw)){$('settlement-error').textContent='请填写实收金额';return;}
 const [whole,fraction='']=raw.split('.'),amount=Number(whole)*100+Number(fraction.padEnd(2,'0'));
 if(amount!==settlementOrder.amount_fen){$('settlement-error').textContent='实收金额与应收金额不一致，未发放次数';return;}
 submitting=true;$('settlement-submit').disabled=true;$('settlement-close').disabled=true;$('settlement-error').textContent='';
 $('settlement-submit').textContent='正在入账…';
 try{
  const response=await api('settle',{product:settlementOrder.product,order_id:settlementOrder.id,amount_fen:amount,transaction_id:$('settlement-transaction').value.trim(),verified:$('settlement-verified').checked});
  $('settlement').close();await refresh();
  message((response.credited?'已发放 ':'此前已入账，未重复发放：')+num(response.points/1000)+' 次；当前剩余 '+num(response.balance_points/1000)+' 次。');
 }catch(error){$('settlement-error').textContent=error.message+'。如网络中断，请保留原交易单号重试。';}
 finally{submitting=false;$('settlement-submit').disabled=false;$('settlement-close').disabled=false;$('settlement-submit').textContent='确认到账并发放次数';}
});
async function pollOrders(){
 if(polling||submitting||document.hidden||$('console').hidden||!$('auto-refresh').checked)return;
 polling=true;try{await orders();await summary();}catch(error){$('order-updated').textContent='刷新失败：'+error.message;}
 finally{polling=false;}
}
setInterval(pollOrders,15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)pollOrders();});
$('auto-refresh').addEventListener('change',()=>{if($('auto-refresh').checked)pollOrders();});
function findOrders(){orderPage=1;orders().catch(e=>message(e.message));}
$('order-find').addEventListener('click',findOrders);
$('order-product').addEventListener('change',findOrders);
$('order-status').addEventListener('change',findOrders);
$('order-search').addEventListener('keydown',e=>{if(e.key==='Enter')findOrders();});
$('order-prev').addEventListener('click',()=>{orderPage--;orders().catch(e=>message(e.message));});
$('order-next').addEventListener('click',()=>{orderPage++;orders().catch(e=>message(e.message));});
async function refresh(){message();try{await summary();await orders();await accounts();}catch(e){message(e.message);}}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();message();try{await api('login',{password:$('password').value});$('password').value='';await refresh();}catch(e){message(e.message);}});
$('logout').addEventListener('click',async()=>{try{await api('logout',{});location.reload();}catch(e){message(e.message);}});
$('refresh').addEventListener('click',refresh);$('days').addEventListener('change',()=>summary().catch(e=>message(e.message)));$('product').addEventListener('change',()=>{page=1;accounts().catch(e=>message(e.message));});$('find').addEventListener('click',()=>{page=1;accounts().catch(e=>message(e.message));});$('search').addEventListener('keydown',e=>{if(e.key==='Enter')$('find').click();});$('prev').addEventListener('click',()=>{page--;accounts().catch(e=>message(e.message));});$('next').addEventListener('click',()=>{page++;accounts().catch(e=>message(e.message));});$('close').addEventListener('click',()=>$('journey').close());refresh();
