'use strict';
const $=id=>document.getElementById(id);
const names={gemini:'Gemini生图大师',temu:'Temu图片大师',xhs:'XHS选题大师'};
const eventNames={activation_created:'新账户激活',activation_restored:'恢复原账户',activation_attempt:'激活失败',generation_request:'生成请求',balance_view:'查看余额',legacy_membership_link:'获取旧会员链接',legacy_membership_open:'打开旧会员页',legacy_order_create:'创建旧收款订单',purchase_offer_fetch:'获取购买选项',native_order_attempt:'尝试应用内下单'};
const ledgerNames={trial_grant:'首次赠送',reserve:'生成预占',confirmed_failure_refund:'生成失败退分',manual_verified_topup:'人工核实到账',monthly_expiry:'月度额度到期',expired_failure_release:'已过期额度解除占用'};
let page=1,total=0,accountSeq=0,summarySeq=0;
const num=n=>Number(n||0).toLocaleString('zh-CN');
const money=n=>'¥'+(Number(n||0)/100).toFixed(2);
const date=n=>n?new Date(n*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'未记录';
function cell(row,value,cls){const td=document.createElement('td');td.textContent=value;if(cls)td.className=cls;row.append(td);return td;}
function tr(body,values){const row=document.createElement('tr');values.forEach(v=>cell(row,v));$(body).append(row);return row;}
function message(text=''){$('message').textContent=text;}
async function api(path,body){const response=await fetch('/ops/api/'+path,{credentials:'same-origin',method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const result=await response.json();if(!response.ok){if(response.status===401){$('login').hidden=false;$('console').hidden=true;$('logout').hidden=true;if($('journey').open)$('journey').close();}throw Error(result.error||'暂时无法加载数据');}return result;}
function show(){ $('login').hidden=true;$('console').hidden=false;$('logout').hidden=false; }
async function summary(){const seq=++summarySeq;const d=await api('summary?days='+$('days').value);if(seq!==summarySeq)return;show();['products','requests','sources'].forEach(id=>$(id).replaceChildren());let u=0,s=0,p=0,paid=0;for(const item of d.products){if(!item.connected){tr('products',[names[item.product],'数据源不可用','—','—','—','—','—','—']);continue;}const j=item.jobs;u+=item.users;s+=j.succeeded||0;p+=j.pending||0;paid+=item.paid.amount_fen;tr('products',[names[item.product],num(item.users),num(item.new_users),num(item.active),num(j.succeeded),num(j.pending),num(j.failed),money(item.paid.amount_fen)]);const acts=item.events.filter(e=>e.event.startsWith('activation_'));const count=acts.reduce((n,e)=>n+e.count,0),failed=acts.filter(e=>e.status>=400).reduce((n,e)=>n+e.count,0);const sum=name=>item.events.filter(e=>e.event===name).reduce((n,e)=>n+e.count,0);tr('requests',[names[item.product],num(count),num(sum('activation_created'))+' / '+num(sum('activation_restored')),num(failed),count?(100*failed/count).toFixed(1)+'%':'—',num(sum('purchase_offer_fetch')),num(sum('native_order_attempt'))]);const groups={};for(const e of acts){const key=e.device+'|'+e.channel;groups[key]??={device:e.device,channel:e.channel,n:0,bad:0};groups[key].n+=e.count;if(e.status>=400)groups[key].bad+=e.count;}for(const g of Object.values(groups)){tr('sources',[names[item.product],({desktop:'桌面',mobile:'手机',cloud:'云端',unknown:'未知'})[g.device]||'未知',({workbuddy_skill:'WorkBuddy技能',workbuddy_expert:'WorkBuddy专家',skillhub:'SkillHub',unknown:'未知'})[g.channel]||'未知',num(g.n),num(g.bad)]);}}
tr('products',[names.xhs,'未接入','—','—','—','—','—','—']);$('users-total').textContent=num(u);$('images-total').textContent=num(s);$('pending-total').textContent=num(p);$('paid-total').textContent=money(paid);$('updated').textContent='更新于 '+date(d.generated_at);$('started').textContent='请求采集始于 '+date(d.collection_started);if(!$('sources').children.length)tr('sources',['尚无激活请求记录','—','—','—','—']);}
async function accounts(){const seq=++accountSeq;const product=$('product').value;const data=await api('users?'+new URLSearchParams({product,q:$('search').value,page:String(page)}));if(seq!==accountSeq)return;total=data.total;$('accounts').replaceChildren();for(const u of data.users){const row=tr('accounts',[u.id.slice(0,12),date(u.activated),date(u.last_job),num(u.images),num(u.balance_points)]);const button=document.createElement('button');button.className='link';button.textContent='查看旅程';button.addEventListener('click',()=>journey(product,u.id).catch(e=>message(e.message)));cell(row,'').append(button);}if(!data.users.length)tr('accounts',['暂无账户','—','—','—','—','—']);$('page').textContent='第 '+page+' 页 · '+num(total)+' 个账户';$('prev').disabled=page<=1;$('next').disabled=page*50>=total;}
async function journey(product,uid){const d=await api('journey?'+new URLSearchParams({product,uid}));$('journey-id').textContent=names[product]+' / '+d.id;$('journey-balance').textContent=num(d.balance_points);$('timeline').replaceChildren();const rows=[];for(const x of d.ledger)rows.push({at:x.created,title:ledgerNames[x.kind]||x.kind,note:'业务流水 · '+(x.amount>0?'+':'')+num(x.amount*1000)+'积分'});for(const x of d.jobs)rows.push({at:x.created,title:'生成任务 · '+({succeeded:'成功',pending:'待核查',failed:'失败'})[x.status],note:'任务创建时间 · '+x.id.slice(0,12)});for(const x of d.orders){rows.push({at:x.created,title:'创建订单 · '+money(x.amount_fen),note:'当前状态：'+({paid:'已确认到账',reported:'用户报告已付款，待核实',pending:'待付款'})[x.status]});if(x.paid_at)rows.push({at:x.paid_at,title:'收款确认 · '+money(x.amount_fen),note:x.provider==='manual_qr'?'人工核款':'渠道：'+x.provider});}for(const x of d.events)rows.push({at:x.created,title:eventNames[x.event]||x.event,note:'请求事件 · HTTP '+x.status+' · '+x.duration_ms+'ms · 渠道 '+x.channel});rows.sort((a,b)=>b.at-a.at);for(const x of rows){const li=document.createElement('li'),title=document.createElement('strong'),time=document.createElement('time'),note=document.createElement('p');title.textContent=x.title;time.textContent=date(x.at);note.textContent=x.note;li.append(title,time,note);$('timeline').append(li);}if(!rows.length){const li=document.createElement('li');li.textContent='暂无旅程记录';$('timeline').append(li);}if(!$('journey').open)$('journey').showModal();}
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
  const row=tr('orders',[x.id,x.user_id.slice(0,12),x.plan+' / '+num(x.points),money(x.amount_fen),orderStates[x.status]||x.status,date(x.created),date(x.paid_at)]);
  row.dataset.orderId=x.id;
  row.children[1].title=x.user_id;
  if(x.status==='reported')row.children[4].className='warning';
  const button=document.createElement('button');button.className='link';button.textContent='查看用户旅程';
  button.addEventListener('click',()=>journey(product,x.user_id).catch(e=>message(e.message)));cell(row,'').append(button);
 }
 if(!d.orders.length)tr('orders',['暂无符合条件的订单','—','—','—','—','—','—','—']);
 $('order-page').textContent='第 '+orderPage+' 页 · '+num(d.total)+' 笔订单';
 $('order-prev').disabled=orderPage<=1;$('order-next').disabled=orderPage*50>=d.total;
}
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
