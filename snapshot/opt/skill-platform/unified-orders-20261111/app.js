'use strict';
const $=id=>document.getElementById(id);
const names={gemini:'Gemini生图器',temu:'Temu图片大师',xhs:'历史入口（已停用）',shared:'共享创作账户'};
const planNames={shared_permanent_29:'共享Plus',shared_permanent_39:'共享Pro',shared_permanent_49:'共享Ultra',shared_permanent_999:'共享终身会员',plus:'Plus（旧套餐）',pro:'Pro（旧套餐）',ultra:'Ultra（旧套餐）',business:'终身会员',gemini_permanent_29:'Plus',gemini_permanent_39:'Pro',gemini_permanent_49:'Ultra',gemini_permanent_999:'终身会员',temu_enterprise_89:'企业入门',temu_enterprise_198:'企业成长',temu_enterprise_365:'企业批量',temu_permanent_89:'企业入门',temu_permanent_198:'企业成长',temu_permanent_365:'企业批量'};
const eventNames={activation_created:'新账户激活',activation_restored:'恢复原账户',activation_attempt:'激活失败',generation_request:'生成请求',balance_view:'查看余额',legacy_membership_link:'获取旧会员链接',legacy_membership_open:'打开旧会员页',legacy_order_create:'创建旧收款订单',purchase_offer_fetch:'获取购买选项',native_order_attempt:'尝试应用内下单'};
const ledgerNames={trial_grant:'首次赠送',reserve:'生成预占',confirmed_failure_refund:'生成失败退分',manual_verified_topup:'人工核实到账',email_verified_topup:'邮件确认到账',monthly_expiry:'月度额度到期',expired_failure_release:'已过期额度解除占用'};
let page=1,total=0,accountSeq=0,summarySeq=0;
const num=n=>Number(n||0).toLocaleString('zh-CN');
const money=n=>'¥'+(Number(n||0)/100).toFixed(2);
const date=n=>n?new Date(n*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'未记录';
function cell(row,value,cls){const td=document.createElement('td');td.textContent=value;if(cls)td.className=cls;row.append(td);return td;}
function tr(body,values){const row=document.createElement('tr');values.forEach(v=>cell(row,v));$(body).append(row);return row;}
function message(text=''){$('message').textContent=text;}
async function api(path,body,extraHeaders={}){const response=await fetch('/ops/api/'+path,{credentials:'same-origin',cache:'no-store',method:body?'POST':'GET',headers:{...(body?{'Content-Type':'application/json'}:{}),...extraHeaders},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(20000)});const result=await response.json();if(!response.ok){if(response.status===401){$('login').hidden=false;$('console').hidden=true;$('logout').hidden=true;if($('journey').open)$('journey').close();if($('settlement').open)$('settlement').close();message('登录已过期，请重新登录后使用原交易单号核查或重试');}const error=Error(result.error||'暂时无法加载数据');error.status=response.status;throw error;}return result;}
function show(){ $('login').hidden=true;$('console').hidden=false;$('logout').hidden=false; }
async function summary(){const seq=++summarySeq;const d=await api('summary?days='+$('days').value);if(seq!==summarySeq)return;document.dispatchEvent(new CustomEvent('channel-data-ready',{detail:d.channels}));show();['products','requests','sources'].forEach(id=>$(id).replaceChildren());let u=0,s=0,p=0,paid=0;for(const item of d.products){if(item.product==='xhs')continue;if(!item.connected){tr('products',[names[item.product],'数据源不可用','—','—','—','—','—','—']);continue;}const j=item.jobs;u+=item.users;s+=j.succeeded||0;p+=j.pending||0;paid+=item.paid.amount_fen;tr('products',[names[item.product],num(item.users),num(item.new_users),num(item.active),num(j.succeeded),num(j.pending),num(j.failed),money(item.paid.amount_fen)]);const acts=item.events.filter(e=>e.event.startsWith('activation_'));const count=acts.reduce((n,e)=>n+e.count,0),failed=acts.filter(e=>e.status>=400).reduce((n,e)=>n+e.count,0);const sum=name=>item.events.filter(e=>e.event===name).reduce((n,e)=>n+e.count,0);tr('requests',[names[item.product],num(count),num(sum('activation_created'))+' / '+num(sum('activation_restored')),num(failed),count?(100*failed/count).toFixed(1)+'%':'—',num(sum('purchase_offer_fetch')),num(sum('native_order_attempt'))]);const groups={};for(const e of acts){const key=e.device+'|'+e.channel;groups[key]??={device:e.device,channel:e.channel,n:0,bad:0};groups[key].n+=e.count;if(e.status>=400)groups[key].bad+=e.count;}for(const g of Object.values(groups)){tr('sources',[names[item.product],({desktop:'桌面',mobile:'手机',cloud:'云端',unknown:'未知'})[g.device]||'未知',({workbuddy_skill:'WorkBuddy技能',workbuddy_expert:'WorkBuddy专家',skillhub:'SkillHub',unknown:'未知'})[g.channel]||'未知',num(g.n),num(g.bad)]);}}
$('users-total').textContent=num(u);$('images-total').textContent=num(s);$('pending-total').textContent=num(p);$('paid-total').textContent=money(paid);$('updated').textContent=document.body.dataset.workspaceView==='users'&&$('updated').dataset.accountReadAt?'账户读取于 '+date(Number($('updated').dataset.accountReadAt)):'后台读取于 '+date(d.generated_at);$('started').textContent='请求采集始于 '+date(d.collection_started);if(!$('sources').children.length)tr('sources',['尚无激活请求记录','—','—','—','—']);}
async function accounts(){const seq=++accountSeq;const product=$('product').value;const data=await api('users?'+new URLSearchParams({product,q:$('search').value,page:String(page)}));if(seq!==accountSeq)return;total=data.total;$('accounts').replaceChildren();for(const u of data.users){const row=tr('accounts',[u.id.slice(0,12),date(u.activated),date(u.last_job),num(u.images),num(u.balance_points/1000)]);const idButton=document.createElement('button');idButton.className='link';idButton.textContent=u.id.slice(0,12);idButton.title=u.id;idButton.addEventListener('click',()=>journey(product,u.id).catch(e=>message(e.message)));row.firstChild.replaceChildren(idButton);const button=document.createElement('button');button.className='link';button.textContent='查看旅程';button.addEventListener('click',()=>journey(product,u.id).catch(e=>message(e.message)));cell(row,'').append(button);}if(!data.users.length)tr('accounts',['暂无账户','—','—','—','—','—']);$('page').textContent='第 '+page+' 页 · '+num(total)+' 个账户';$('prev').disabled=page<=1;$('next').disabled=page*50>=total;}
async function journey(product,uid){if(product==='shared'){document.dispatchEvent(new CustomEvent('ops:show-user',{detail:{uid}}));return;}const d=await api('journey?'+new URLSearchParams({product,uid}));$('journey-id').textContent=names[product]+' / '+d.id;$('journey-balance').textContent=num(d.balance_points/1000)+(product==='shared'?' 共享次':' 次')+(d.legacy_accounts||[]).map(x=>' · 原'+names[x.product]+' '+num(x.remaining_uses)+'次').join('');$('timeline').replaceChildren();const rows=[];for(const x of d.ledger)rows.push({at:x.created,title:ledgerNames[x.kind]||x.kind,note:'业务流水 · '+(x.amount>0?'+':'')+num(x.amount)+'次'});for(const x of d.jobs)rows.push({at:x.created,title:'生成任务 · '+({succeeded:'成功',pending:'待核查',failed:'失败'})[x.status],note:'任务创建时间 · '+x.id.slice(0,12)});for(const x of d.orders){rows.push({at:x.created,title:'创建订单 · '+money(x.amount_fen),note:'当前状态：'+({paid:'已确认到账',reported:'用户报告已付款，待核实',pending:'待付款'})[x.status]});if(x.paid_at)rows.push({at:x.paid_at,title:'收款确认 · '+money(x.amount_fen),note:x.provider==='manual_qr'?'收款确认':x.provider==='manual_email'?'邮件确认核款':'渠道：'+x.provider});}for(const x of d.events)rows.push({at:x.created,title:eventNames[x.event]||x.event,note:'请求事件 · HTTP '+x.status+' · '+x.duration_ms+'ms · 渠道 '+x.channel});rows.sort((a,b)=>b.at-a.at);for(const x of rows){const li=document.createElement('li'),title=document.createElement('strong'),time=document.createElement('time'),note=document.createElement('p');title.textContent=x.title;time.textContent=date(x.at);note.textContent=x.note;li.append(title,time,note);$('timeline').append(li);}if(!rows.length){const li=document.createElement('li');li.textContent='暂无旅程记录';$('timeline').append(li);}if(!$('journey').open)$('journey').showModal();}
const orderStates={test_fulfilled:'已发放（测试标记）',reported:'已报付款 · 待核款',pending:'待付款',paid:'已核款到账'};
let orderPage=1,orderSeq=0;
async function orders(){
 const seq=++orderSeq;
 const d=await api('all-orders?'+new URLSearchParams({status:$('order-status').value,q:$('order-search').value.trim(),page:String(orderPage)}));
 if(seq!==orderSeq)return;
 $('orders').replaceChildren();
 const reported=d.counts.reported||{count:0,amount_fen:0};
 $('order-counts').textContent='全部产品待核款 '+num(reported.count)+' 笔 · '+money(reported.amount_fen);
 for(const x of d.orders){
  const benefit=x.entitlement||(x.units==null?'到账余额 '+money(x.credit_fen):num(x.units)+'额度');
  const plan=(x.plan_name||planNames[x.plan]||x.plan||'充值')+' / '+benefit;
  const row=tr('orders',[x.id,x.user_id.slice(0,12),x.source_name,plan,money(x.amount_fen),orderStates[x.status]||x.status,date(x.created),date(x.paid_at)]);
  row.dataset.orderId=x.id;row.dataset.orderKey=x.row_key;
  row.children[1].title=x.user_id;
  row.children[2].title=x.source_skill==='unknown'?'该订单未记录具体 Skill':x.source_skill;
  if(x.status==='reported')row.children[5].className='warning';
  const actions=document.createElement('div');actions.className='order-actions';
  if(d.settlement_enabled&&x.can_settle&&['pending','reported'].includes(x.status)){
   const settle=document.createElement('button');settle.textContent='核款发放';settle.dataset.settle=x.id;
   settle.addEventListener('click',()=>openSettlement(x.namespace,x.id,x).catch(e=>message(e.message)));actions.append(settle);
  }
  const journeyButton=document.createElement('button');journeyButton.className='link';journeyButton.textContent='查看用户旅程';
  journeyButton.addEventListener('click',()=>journey(x.journey_product,x.user_id).catch(e=>message(e.message)));
  actions.append(journeyButton);cell(row,'').append(actions);row.prepend(row.lastChild);
 }
 if(!d.orders.length)tr('orders',['暂无符合条件的订单','—','—','—','—','—','—','—','—']);
 $('order-page').textContent='第 '+orderPage+' 页 · '+num(d.total)+' 笔订单';
 $('order-prev').disabled=orderPage<=1;$('order-next').disabled=orderPage*50>=d.total;
 $('order-updated').textContent='订单更新于 '+date(d.generated_at);
 document.dispatchEvent(new CustomEvent('ops-orders-rendered',{detail:{data:d,product:'all'}}));
 document.title=(reported.count?'('+reported.count+'笔待核款) ':'')+'MyPlaneStore | 运营监控';
}
let settlementOrder=null,submitting=false,polling=false;
async function openSettlement(product,id,detail=null){
 const special=!['shared','gemini','temu'].includes(product);
 const x=special?detail:await api('order?'+new URLSearchParams({product,id}));
 if(x.status==='paid'){message('该订单已入账，无需再次发放');await orders();return;}
 if(!['pending','reported'].includes(x.status))throw Error('当前订单状态不能核款');
 settlementOrder={...x,product,special};$('settlement-form').reset();$('settlement-error').textContent='';
 $('settlement-order').textContent=x.id;$('settlement-user').textContent=x.user_id;
 $('settlement-expected').textContent=money(x.amount_fen);$('settlement-points').textContent=special?(x.entitlement||'到账余额 '+money(x.credit_fen)):num(x.points/1000)+' 次';
 $('settlement-validity').textContent=special?(x.entitlement||'长期有效'):x.permanent===true||x.plan==='business'||['gemini_permanent_29','gemini_permanent_39','gemini_permanent_49','gemini_permanent_999'].includes(x.plan)?'永久有效':'核款成功起30天';
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
  const target=settlementOrder;
   const endpoint=target.special?(target.product==='pet'?'pet-settle':target.product==='trade-leads'?'trade-leads/settle':target.service_id?'metered/settle':'listing/settle'):'settle';
   const response=await api(endpoint,{product:target.product,service_id:target.service_id,order_id:target.id,amount_fen:amount,transaction_id:$('settlement-transaction').value.trim(),verified:$('settlement-verified').checked},{'X-Membership-Request':'1','Idempotency-Key':'ops-unified-'+target.id});
  $('settlement').close();await refresh();
  message(settlementOrder.special?'核款完成，订单权益已到账。':(response.credited?'已发放 ':'此前已入账，未重复发放：')+num(response.points/1000)+' 次；当前剩余 '+num(response.balance_points/1000)+' 次。');
 }catch(error){$('settlement-error').textContent=error.message+'。如网络中断，请保留原交易单号重试。';}
 finally{submitting=false;$('settlement-submit').disabled=false;$('settlement-close').disabled=false;$('settlement-submit').textContent='确认到账并发放次数';}
});
async function pollOrders(){
 if(refreshFlight||document.getElementById('test-mark-dialog')?.open||polling||submitting||document.hidden||$('console').hidden||!$('auto-refresh').checked)return;
 polling=true;try{await orders();if(!refreshFlight)await summary();}catch(error){$('order-updated').textContent='刷新失败：'+error.message;}
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
let navigationRefresh=new URLSearchParams(location.search).get('refresh')==='1';
function restoreReloadFilters(){
 let state=null;
 try{state=JSON.parse(sessionStorage.getItem('ops-reload-filters-v1'));sessionStorage.removeItem('ops-reload-filters-v1');}catch{}
 if(state&&Number.isFinite(state.savedAt)&&Date.now()-state.savedAt>=0&&Date.now()-state.savedAt<60000){
  for(const id of ['days','order-product','order-status','product']){
   const value=state.values?.[id];
   const apply=()=>{if(id!=='order-product'&&typeof value==='string'&&[...$(id).options].some(o=>o.value===value))$(id).value=value;};
   apply();if(id==='order-status')queueMicrotask(apply);
  }
  for(const id of ['order-search','search'])if(typeof state.values?.[id]==='string'&&state.values[id].length<=64)$(id).value=state.values[id];
  if(typeof state.autoRefresh==='boolean')$('auto-refresh').checked=state.autoRefresh;
  if(Number.isSafeInteger(state.accountPage)&&state.accountPage>=1&&state.accountPage<=100000)page=state.accountPage;
  if(Number.isSafeInteger(state.orderPage)&&state.orderPage>=1&&state.orderPage<=100000)orderPage=state.orderPage;
 }
 const days=new URLSearchParams(location.search).get('days');
 if(['1','2','7','30','90'].includes(days))$('days').value=days;
 if(navigationRefresh)history.replaceState(null,'',location.pathname);
}
restoreReloadFilters();
let refreshFlight=null;
function refreshSnapshot(){return ['users-total','images-total','pending-total','paid-total','products','requests','sources','orders','accounts'].map(id=>$(id).textContent).join('\n')+'\n'+[...document.querySelectorAll('#journey-v2 tbody,#users-directory tbody')].map(x=>x.textContent).join('\n');}
function refresh({manual=false}={}){
 if(refreshFlight)return manual?refreshFlight:refreshFlight.then(()=>refresh());
 const button=$('refresh'),status=$('refresh-status'),before=refreshSnapshot();
 button.disabled=true;button.textContent='刷新中…';button.setAttribute('aria-busy','true');$('days').disabled=true;
 status.textContent='正在查询统计、订单和账户…';status.dataset.state='loading';message();
 refreshFlight=(async()=>{
  const failures=[],completed=[];
  for(const [label,load] of [['统计',summary],['订单',orders],['账户',accounts],['当前页',async()=>{const hook=window.mpsOpsRefreshHooks?.[document.body.dataset.workspaceView];if(hook)await hook();}]]){
   try{await load();completed.push(label);}
   catch(error){
    const detail=['TimeoutError','AbortError'].includes(error.name)?'查询超时，请重试':error.name==='TypeError'?'网络连接未完成，请重试':error.message;
    if($('console').hidden){status.textContent=error.status===401?'请重新登录后刷新':'加载未完成：'+detail;status.dataset.state='error';message(error.status===401?'登录已过期，请重新登录后刷新':detail);return;}
    failures.push(label+'：'+detail);
   }
  }
  if(failures.length){
   status.textContent=(completed.length?'部分刷新完成（'+completed.join('、')+'）；':'刷新失败；')+failures.join('；');status.dataset.state='error';
   message('未成功的项目保留上次数据，请重试。');
  }else{
   const unchanged=manual&&before===refreshSnapshot();
   status.textContent=(navigationRefresh?'整页刷新完成，统计、订单和账户已重新读取':unchanged?'已重新读取，当前记录无变化':'后台读取完成，当前页面数据已刷新')+' · '+new Date().toLocaleTimeString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
   navigationRefresh=false;
   status.dataset.state='success';
  }
 })().finally(()=>{button.disabled=false;button.textContent='刷新';button.removeAttribute('aria-busy');$('days').disabled=false;refreshFlight=null;});
 return refreshFlight;
}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();message();try{await api('login',{password:$('password').value});$('password').value='';await refresh();}catch(e){message(e.message);}});
$('logout').addEventListener('click',async()=>{try{await api('logout',{});location.reload();}catch(e){message(e.message);}});
$('refresh-form').addEventListener('submit',event=>{
 event.preventDefault();
 refresh({manual:true}).catch(error=>message(error.message));
});
$('days').addEventListener('change',()=>refresh({manual:true}));$('product').addEventListener('change',()=>{page=1;accounts().catch(e=>message(e.message));});$('find').addEventListener('click',()=>{page=1;accounts().catch(e=>message(e.message));});$('search').addEventListener('keydown',e=>{if(e.key==='Enter')$('find').click();});$('prev').addEventListener('click',()=>{page--;accounts().catch(e=>message(e.message));});$('next').addEventListener('click',()=>{page++;accounts().catch(e=>message(e.message));});$('close').addEventListener('click',()=>$('journey').close());refresh();


// Manager-only channel view. Counts remain unavailable until verified sources
// are connected; screenshots and public example numbers are never used as data.
(() => {
  'use strict';
  const consolePanel=document.getElementById('console');
  const overview=document.createElement('div');overview.id='ops-overview';
  overview.append(...consolePanel.childNodes);
  const navigation=document.createElement('nav');navigation.className='ops-views';navigation.setAttribute('aria-label','管理后台页面');
  navigation.innerHTML='<button type="button" id="ops-overview-tab" aria-pressed="true">运营概览</button><button type="button" id="ops-channels-tab" aria-pressed="false">渠道下载</button>';
  const panel=document.createElement('section');panel.id='ops-channels';panel.hidden=true;panel.setAttribute('aria-labelledby','channel-title');
  panel.innerHTML=`<div class="channel-heading"><div><p class="eyebrow">渠道表现</p><h1 id="channel-title" tabindex="-1">渠道下载</h1><p>分别查看 SkillHub 下载量与 WorkBuddy 安装量。</p></div><span class="channel-connection">数据源待接入</span></div>
    <div class="channel-ranges" role="group" aria-label="渠道统计周期"><button type="button" data-range="today">今日</button><button type="button" data-range="yesterday">昨日</button><button type="button" data-range="7">近7天</button><button type="button" data-range="14">近14天</button><button type="button" data-range="30" aria-pressed="true">近30天</button><button type="button" data-range="90">近90天</button><button type="button" data-range="month">上个月</button><button type="button" data-range="custom">自定义</button></div>
    <form id="channel-custom" hidden><label>开始日期<input id="channel-from" type="date" required></label><label>结束日期<input id="channel-to" type="date" required></label><button type="submit">应用</button></form>
    <p id="channel-period" class="channel-caption" role="status"></p>
    <div class="channel-cards"><article><span>昨日新增下载</span><strong>—</strong><small>SkillHub · 待接入每日快照</small></article><article><span>今日至今</span><strong>—</strong><small>SkillHub · 待接入每日快照</small></article><article><span>SkillHub 累计下载</span><strong>—</strong><small>待接入官方统计</small></article><article><span>WorkBuddy 最新安装量</span><strong>—</strong><small>待接入 · 数据日期尚未提供</small></article></div>
    <div class="channel-chart"><div class="channel-chart-heading"><h2 id="channel-chart-title">近30天渠道趋势</h2><p>两个渠道独立展示，不作合并</p></div><div class="channel-empty"><span aria-hidden="true">↗</span><h3>等待接入真实数据</h3><p>接入后在这里展示趋势。未采集的日期留空，不按零计算。</p><a href="#channel-setup">查看需要提供的资料 ↓</a></div><div class="channel-legend"><span>● SkillHub 每日新增下载</span><span>● WorkBuddy 安装量快照</span></div></div>
    <section id="channel-setup"><div class="section-head"><h2>数据接入清单</h2><span>无需在 Skill 内安装统计代码</span></div><div class="table-wrap"><table><thead><tr><th>渠道</th><th>接入状态</th><th>需要提供</th></tr></thead><tbody><tr><td>SkillHub</td><td>待接入</td><td>要统计的技能公开链接或作者主页，注明是否统计全部技能。</td></tr><tr><td>WorkBuddy</td><td>待接入</td><td>对应技能／专家的发布后台页面链接，及安装统计的导出文件或截图（带数据日期）。</td></tr><tr><td>历史趋势</td><td>尚无记录</td><td>如需补充历史，请提供带日期的历史统计表；否则从开始采集日起积累。</td></tr></tbody></table></div><p class="channel-caption">这里只展示平台公开或授权提供的汇总数据，不采集客户对话、文件内容或个人凭证。</p></section>`;
  consolePanel.append(navigation,overview,panel);
  const overviewTab=document.getElementById('ops-overview-tab'),channelsTab=document.getElementById('ops-channels-tab');
  function switchView(channels){
    overview.hidden=channels;panel.hidden=!channels;
    overviewTab.setAttribute('aria-pressed',String(!channels));channelsTab.setAttribute('aria-pressed',String(channels));
    if(channels)document.getElementById('channel-title').focus({preventScroll:true});
  }
  overviewTab.addEventListener('click',()=>switchView(false));channelsTab.addEventListener('click',()=>switchView(true));
  // Returning to login discards the selected view, including session expiry.
  new MutationObserver(()=>{if(consolePanel.hidden)switchView(false);}).observe(consolePanel,{attributes:true,attributeFilter:['hidden']});
  const ranges=panel.querySelectorAll('[data-range]');
  const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  const shift=(date,days)=>{const value=new Date(date+'T00:00:00Z');value.setUTCDate(value.getUTCDate()+days);return value.toISOString().slice(0,10);};
  const from=document.getElementById('channel-from'),to=document.getElementById('channel-to');from.max=to.max=today;
  const caption=document.getElementById('channel-period');
  function showPeriod(start,end,label){
    from.value=start;to.value=end;
    caption.textContent=start+' 至 '+end+' · 北京时间 · 尚未接入统计数据';
    document.getElementById('channel-chart-title').textContent=label+'渠道趋势';
  }
  function choose(button){
    ranges.forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
    const range=button.dataset.range;document.getElementById('channel-custom').hidden=range!=='custom';
    if(range==='custom'){from.focus();return;}
    let start=today,end=today;
    if(range==='yesterday')start=end=shift(today,-1);
    else if(range==='month'){end=shift(today.slice(0,8)+'01',-1);start=end.slice(0,8)+'01';}
    else if(/^\d+$/.test(range))start=shift(today,1-Number(range));
    showPeriod(start,end,button.textContent);
  }
  ranges.forEach(button=>button.addEventListener('click',()=>choose(button)));
  document.getElementById('channel-custom').addEventListener('submit',event=>{
    event.preventDefault();
    if(!from.value||!to.value||from.value>to.value||to.value>today){caption.textContent='请选择有效日期：开始日期不能晚于结束日期，结束日期不能晚于今天。';return;}
    showPeriod(from.value,to.value,'所选日期');
  });
  function syncBusinessPeriod(){
    const count=Number(document.getElementById('days').value);
    if(!Number.isFinite(count)||count<1)return;
    const button=panel.querySelector('[data-range="'+(count===1?'today':count)+'"]');
    if(button)choose(button);else{ranges.forEach(b=>b.setAttribute('aria-pressed','false'));showPeriod(shift(today,1-count),today,'所选日期');}
  }
  document.getElementById('days').addEventListener('change',syncBusinessPeriod);
  syncBusinessPeriod();
})();


(() => {
 'use strict';
 const n=value=>Number.isSafeInteger(value)&&value>=0?value.toLocaleString('zh-CN'):'—';
 const dateNow=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const previousDate=(day,offset)=>{const d=new Date(day+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+offset);return d.toISOString().slice(0,10);};
 const delta=(history,day)=>{
  const a=history[day]?.skills,b=history[previousDate(day,-1)]?.skills;
  if(!Array.isArray(a)||!Array.isArray(b)||!a.length||a.length!==b.length)return null;
  const prior=new Map(b.map(s=>[s.slug,s.downloads]));
  if(prior.size!==b.length||new Set(a.map(s=>s.slug)).size!==a.length)return null;
  let total=0;
  for(const s of a){
   const last=prior.get(s.slug);
   if(typeof s.slug!=='string'||!s.slug||!Number.isSafeInteger(s.downloads)||s.downloads<0||!Number.isSafeInteger(last)||last<0||s.downloads<last)return null;
   total+=s.downloads-last;
  }
  return Number.isSafeInteger(total)?total:null;
 };
 let latest=null;
 function draw(){
  const data=latest,snapshot=data?.skillhub;if(!snapshot)return;
  const panel=document.getElementById('ops-channels'),cards=panel.querySelectorAll('.channel-cards article');
  const history=data.history||{},today=dateNow();
  const selectedStart=document.getElementById('channel-from').value,selectedEnd=document.getElementById('channel-to').value;
  if(!selectedStart||!selectedEnd||selectedStart>selectedEnd||selectedEnd>today)return;
  const selectedDays=[];for(let day=selectedStart;day<=selectedEnd&&selectedDays.length<366;day=previousDate(day,1))selectedDays.push(day);
  const recordedDays=Object.keys(history).filter(d=>d>=selectedStart&&d<=selectedEnd).sort();
  const comparable=selectedDays.map(d=>delta(history,d)).filter(v=>v!==null);
  cards[0].querySelector('span').textContent='所选期间新增下载';
  cards[0].querySelector('strong').textContent=n(comparable.length?comparable.reduce((a,b)=>a+b,0):null);
  cards[0].querySelector('small').textContent='SkillHub · '+comparable.length+'/'+selectedDays.length+' 天可比较；缺失及计数回退不计入';
  cards[1].querySelector('span').textContent='所选期间已采集天数';
  cards[1].querySelector('strong').textContent=recordedDays.length+' / '+selectedDays.length;
  cards[1].querySelector('small').textContent=selectedStart+' 至 '+selectedEnd+' · 缺失日期留空';
  const endpoint=recordedDays.length?history[recordedDays.at(-1)]:null;
  cards[2].querySelector('span').textContent='期间最后快照 · 下载小计';
  cards[2].querySelector('strong').textContent=n(endpoint?.downloads);
  cards[2].querySelector('small').textContent=endpoint?recordedDays.at(-1)+' · '+(endpoint.skill_count??endpoint.skills?.length??0)+' 个技能 · 清单待核全':'所选日期没有快照';
  const allWb={...(data.workbuddy_history||{})};if(data.workbuddy)allWb[data.workbuddy.date]=data.workbuddy;
  const wbDays=Object.keys(allWb).filter(d=>d>=selectedStart&&d<=selectedEnd).sort();
  const selectedWb=wbDays.length?allWb[wbDays.at(-1)]:null;
  const wb=data.workbuddy;
  cards[3].querySelector('span').textContent='期间最后快照 · WorkBuddy安装量';
  cards[3].querySelector('strong').textContent=n(selectedWb?.installs);
  cards[3].querySelector('small').textContent=selectedWb?(selectedWb.period_label||'已记录范围')+' · 采集日 '+wbDays.at(-1)+'；非期间新增':'所选日期没有安装量快照';
  panel.querySelector('.channel-connection').textContent=wb?'已接入 · 技能清单待核全':'SkillHub 已读取 · WorkBuddy 待登录';
  const body=panel.querySelector('#channel-setup tbody');body.rows[0].cells[1].textContent='已读取（部分清单）';body.rows[0].cells[2].textContent=snapshot.scope;
  body.rows[1].cells[1].textContent=wb?'已读取':'等待首次登录';
  body.rows[1].cells[2].textContent=wb?(wb.period_label||'已记录统计')+' · 采集日 '+wb.date+' · '+wb.scope:'请在 Codex 右侧 WorkBuddy 页面登录一次。之后每日自动读取，登录失效时提醒。';
  const caption=document.getElementById('channel-period');
  caption.textContent=caption.textContent.replace('尚未接入统计数据','SkillHub 数据日 '+snapshot.date);
  let note=document.getElementById('channel-collection-note');
  if(!note){note=document.createElement('p');note.id='channel-collection-note';note.className='channel-caption';panel.querySelector('.channel-cards').after(note);}
  note.textContent='最近成功采集：'+snapshot.captured_at.slice(0,19).replace('T',' ')+'（北京时间）；已保存 '+Object.keys(history).length+' 天快照。曲线按 SkillHub、WorkBuddy 两个平台展示，缺失日期留空。';
  const start=document.getElementById('channel-from').value,end=document.getElementById('channel-to').value;
  const empty=panel.querySelector('.channel-empty');
  empty.replaceChildren();
  const el=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
  document.getElementById('channel-skill-controls')?.remove();
  document.getElementById('channel-workbuddy-detail')?.remove();
  empty.classList.add('channel-platform-trend');
  panel.querySelector('.channel-chart-heading p').textContent='SkillHub · WorkBuddy';
  const days=selectedDays,ns='http://www.w3.org/2000/svg';
  const valid=value=>Number.isSafeInteger(value)&&value>=0?value:null;
  const series=[
   {id:'skillhub',label:'SkillHub 日增量',color:'#4e68ed',values:days.map(day=>delta(history,day))},
   {id:'workbuddy',label:'WorkBuddy 安装量',color:'#f59b36',values:days.map(day=>valid(allWb[day]?.installs))}
  ];
  const mobile=window.matchMedia('(max-width:600px)').matches;
  const width=mobile?360:1040,height=mobile?280:350;
  const left=mobile?38:58,right=width-(mobile?14:22),top=24,bottom=height-36;
  const maximum=Math.max(1,...series.flatMap(s=>s.values.filter(v=>v!==null)));
  const step=Math.max(1,Math.ceil(maximum/4)),ceiling=step*4;
  const x=i=>days.length===1?(left+right)/2:left+i/(days.length-1)*(right-left);
  const y=value=>bottom-value/ceiling*(bottom-top);
  const frame=el('div');frame.className='channel-platform-frame';
  const svg=document.createElementNS(ns,'svg');
  svg.setAttribute('viewBox','0 0 '+width+' '+height);
  svg.setAttribute('role','img');svg.setAttribute('tabindex','0');
  svg.setAttribute('aria-label','SkillHub每日新增下载和WorkBuddy安装量，左右方向键查看日期');
  svg.classList.add('channel-platform-chart');
  frame.append(svg);
  const shape=(tag,attrs,text,parent=svg)=>{
   const node=document.createElementNS(ns,tag);
   for(const [key,value] of Object.entries(attrs))node.setAttribute(key,String(value));
   if(text!==undefined)node.textContent=text;parent.append(node);return node;
  };
  for(let i=0;i<=4;i++){
   const value=step*i;
   shape('line',{x1:left,x2:right,y1:y(value),y2:y(value),stroke:'#e8ecf5','stroke-width':1});
   shape('text',{x:left-10,y:y(value)+4,'text-anchor':'end','font-size':12,fill:'#8892a7'},n(value));
  }
  const labelCount=mobile?3:8;
  const labelIndexes=new Set([0,days.length-1]);
  for(let i=0;i<labelCount;i++)labelIndexes.add(Math.round(i*Math.max(0,days.length-1)/Math.max(1,labelCount-1)));
  for(const i of [...labelIndexes].sort((a,b)=>a-b)){
   if(i<0||!days[i])continue;
   shape('text',{x:x(i),y:height-12,'text-anchor':'middle','font-size':12,fill:'#8892a7'},days[i].slice(5));
  }
  // Each path is limited to observed consecutive dates. No interpolation across missing days.
  const curve=points=>{
   let path='M '+points[0][0]+' '+points[0][1];
   for(let i=1;i<points.length;i++){
    const a=points[i-1],b=points[i],dx=(b[0]-a[0])/3;
    // Controls stay between endpoint values, so smoothing never invents an overshoot.
    path+=' C '+(a[0]+dx)+' '+a[1]+' '+(b[0]-dx)+' '+b[1]+' '+b[0]+' '+b[1];
   }
   return path;
  };
  for(const s of series){
   let points=[],segments=0;
   const flush=()=>{
    if(points.length>1){
     const d=curve(points);
     if(s.id==='skillhub')shape('path',{d:d+' L '+points.at(-1)[0]+' '+bottom+' L '+points[0][0]+' '+bottom+' Z',fill:s.color,'fill-opacity':.045,'data-series-fill':s.id});
     shape('path',{d,fill:'none',stroke:s.color,'stroke-width':s.id==='skillhub'?3:2.5,'stroke-linecap':'round','stroke-linejoin':'round','data-series':s.id,'data-segment':segments++});
    }
    points=[];
   };
   s.values.forEach((value,i)=>{
    if(value===null){flush();return;}
    points.push([x(i),y(value)]);
    shape('circle',{cx:x(i),cy:y(value),r:days.length<35?2.5:1.5,fill:s.color,'data-platform':s.id,'data-date':days[i],'data-value':value});
   });flush();
  }
  const focus=shape('g',{'aria-hidden':'true'});focus.style.display='none';
  const rule=shape('line',{x1:left,x2:left,y1:top,y2:bottom,stroke:'#a9b1c3','stroke-dasharray':'4 4'},undefined,focus);
  const markers=series.map(s=>shape('circle',{r:5,fill:'#fff',stroke:s.color,'stroke-width':2},undefined,focus));
  const tooltip=el('div');tooltip.className='channel-platform-tooltip';tooltip.hidden=true;tooltip.setAttribute('role','status');frame.append(tooltip);
  const date=el('div');date.className='channel-platform-tooltip-date';tooltip.append(date);
  const rows=series.map(s=>{
   const row=el('div'),label=el('span'),dot=el('i'),value=el('strong');
   row.className='channel-platform-tooltip-row';dot.style.background=s.color;
   label.append(dot,document.createTextNode(s.label));row.append(label,value);tooltip.append(row);return value;
  });
  const hint=el('small');hint.textContent='WorkBuddy：近30天安装量快照';tooltip.append(hint);
  let active=days.length-1;
  const hide=()=>{tooltip.hidden=true;focus.style.display='none';};
  const show=index=>{
   if(!days.length)return;
   active=Math.max(0,Math.min(days.length-1,index));
   date.textContent=days[active].slice(5);
   series.forEach((s,i)=>{
    const value=s.values[active];rows[i].textContent=value===null?'—':n(value);
    markers[i].style.display=value===null?'none':'';
    if(value!==null){markers[i].setAttribute('cx',x(active));markers[i].setAttribute('cy',y(value));}
   });
   rule.setAttribute('x1',x(active));rule.setAttribute('x2',x(active));focus.style.display='';
   tooltip.hidden=false;
   const bounds=svg.getBoundingClientRect(),frameBounds=frame.getBoundingClientRect();
   const px=bounds.left-frameBounds.left+x(active)/width*bounds.width;
   const tipWidth=tooltip.offsetWidth,pad=8;
   tooltip.style.left=Math.max(pad,Math.min(frame.clientWidth-tipWidth-pad,px-tipWidth-14))+'px';
   const observed=series.map(s=>s.values[active]).filter(v=>v!==null);
   const py=(observed.length?y(Math.max(...observed)):bottom)*bounds.height/height;
   tooltip.style.top=Math.max(8,Math.min(frame.clientHeight-tooltip.offsetHeight-8,py-tooltip.offsetHeight-12))+'px';
  };
  svg.addEventListener('pointermove',event=>{
   const bounds=svg.getBoundingClientRect(),px=(event.clientX-bounds.left)*width/Math.max(1,bounds.width);
   show(days.length===1?0:Math.round((px-left)/(right-left)*(days.length-1)));
  });
  svg.addEventListener('pointerdown',event=>{
   if(event.pointerType==='mouse')return;
   const bounds=svg.getBoundingClientRect(),px=(event.clientX-bounds.left)*width/Math.max(1,bounds.width);
   show(days.length===1?0:Math.round((px-left)/(right-left)*(days.length-1)));
  });
  svg.addEventListener('pointerleave',event=>{if(event.pointerType==='mouse')hide();});
  svg.addEventListener('focus',()=>show(active));svg.addEventListener('blur',hide);
  svg.addEventListener('keydown',event=>{
   if(!['ArrowLeft','ArrowRight','Home','End','Escape'].includes(event.key))return;
   event.preventDefault();
   if(event.key==='Escape')hide();
   else show(event.key==='Home'?0:event.key==='End'?days.length-1:active+(event.key==='ArrowRight'?1:-1));
  });
  empty.append(frame);
  const legend=el('div');legend.className='channel-platform-legend';
  for(const s of series){
   const item=el('span'),dot=el('i');dot.style.borderColor=s.color;
   item.append(dot,document.createTextNode(s.label));legend.append(item);
  }
  empty.append(legend);
  const footnote=el('p','WorkBuddy：近30天安装量快照 · 缺失日期留空');footnote.className='channel-platform-note';empty.append(footnote);
  if(!series.some(s=>s.values.some(v=>v!==null)))empty.append(el('p','所选日期暂无记录'));
  panel.querySelector('.channel-legend').hidden=true;

 }
 document.addEventListener('channel-data-ready',event=>{latest=event.detail;draw();});
 document.querySelectorAll('#ops-channels [data-range]').forEach(button=>button.addEventListener('click',draw));
 document.getElementById('channel-custom').addEventListener('submit',draw);
 document.getElementById('days').addEventListener('change',draw);
 let resizeFrame=0;
 window.addEventListener('resize',()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{if(latest)draw();});});
})();


(() => {
 'use strict';
 const selected=new Set();let allowed=[],batch=null,busy=false;
 const tableBody=document.getElementById('orders');
 const toolbar=document.createElement('div');toolbar.className='test-mark-toolbar';
 toolbar.innerHTML='<label><input id="test-select-all" type="checkbox"> 选择本页待处理订单</label><span id="test-selected-count">已选 0 笔</span><button id="test-mark-open" type="button" disabled>标记已发放（测试订单）</button><small>仅改测试状态，不增加额度，不计入收款。</small>';
 tableBody.closest('.table-wrap').before(toolbar);
 const dialog=document.createElement('dialog');dialog.id='test-mark-dialog';dialog.setAttribute('aria-labelledby','test-mark-title');
 dialog.innerHTML='<form id="test-mark-form"><div class="dialog-head"><h2 id="test-mark-title">标记测试订单已发放</h2><button type="button" id="test-mark-close">关闭</button></div><p>这项操作只把所选订单改为“已发放（测试标记）”，移出待核款；不增加账户额度，不登记真实收款。</p><p id="test-mark-orders"></p><label for="test-mark-reason">操作备注</label><input id="test-mark-reason" required minlength="2" maxlength="200" placeholder="例如：内部测试订单已结束" autocomplete="off"><label class="test-mark-confirm"><input id="test-mark-confirmed" type="checkbox" required> 我确认所选全部是测试订单，仅作状态标记。</label><p id="test-mark-error" role="alert"></p><button id="test-mark-submit" type="submit">确认标记已发放</button></form>';
 document.body.append(dialog);
 const byId=id=>document.getElementById(id);
 const option=document.createElement('option');option.value='test_fulfilled';option.textContent='已发放 · 测试标记';byId('order-status').append(option);
 function sync(){
  byId('test-selected-count').textContent='已选 '+selected.size+' 笔';
  byId('test-mark-open').disabled=!selected.size||busy;
  byId('test-select-all').checked=allowed.length>0&&selected.size===allowed.length;
  byId('test-select-all').indeterminate=selected.size>0&&selected.size<allowed.length;
  byId('test-select-all').disabled=!allowed.length||busy;
  tableBody.querySelectorAll('input[data-test-order]').forEach(box=>box.checked=selected.has(box.dataset.testOrder));
 }
 document.addEventListener('ops-orders-rendered',event=>{
  const {data,product}=event.detail;
  allowed=data.settlement_enabled?data.orders.filter(order=>order.can_mark_test&&['pending','reported'].includes(order.status)).map(order=>order.row_key):[];
  for(const oid of selected)if(!allowed.includes(oid))selected.delete(oid);
  for(const order of data.orders){
   const row=[...tableBody.rows].find(row=>row.dataset.orderKey===order.row_key);if(!row||!allowed.includes(order.row_key))continue;
   const label=document.createElement('label');label.className='test-order-select';
   const box=document.createElement('input');box.type='checkbox';box.dataset.testOrder=order.row_key;box.setAttribute('aria-label','选择测试订单 '+order.id);
   box.addEventListener('change',()=>{box.checked?selected.add(order.row_key):selected.delete(order.row_key);sync();});
   label.append(box,document.createTextNode('选择'));row.cells[0].prepend(label);
  }
  sync();
 });
 byId('test-select-all').addEventListener('change',event=>{selected.clear();if(event.target.checked)allowed.forEach(id=>selected.add(id));sync();});
 byId('test-mark-open').addEventListener('click',()=>{
  if(!selected.size)return;batch={order_keys:[...selected]};byId('test-mark-form').reset();byId('test-mark-error').textContent='';
  byId('test-mark-orders').textContent='所选 '+batch.order_keys.length+' 笔订单：'+batch.order_keys.join('、');dialog.showModal();byId('test-mark-reason').focus();
 });
 byId('test-mark-close').addEventListener('click',()=>{if(!busy)dialog.close();});dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});
 byId('test-mark-form').addEventListener('submit',async event=>{
  event.preventDefault();if(!batch||busy)return;busy=true;byId('test-mark-submit').disabled=true;byId('test-mark-close').disabled=true;
  try{
   const groups=new Map();
   for(const key of batch.order_keys){const slash=key.indexOf('/'),product=key.slice(0,slash),id=key.slice(slash+1);if(!groups.has(product))groups.set(product,[]);groups.get(product).push(id);}
   const result={marked:0,already_marked:0};
   for(const [product,order_ids] of groups){
    const done=await api('test-orders/mark-fulfilled',{product,order_ids,confirmed_test_only:byId('test-mark-confirmed').checked,reason:byId('test-mark-reason').value.trim()});
    result.marked+=done.marked;result.already_marked+=done.already_marked;
    order_ids.forEach(id=>selected.delete(product+'/'+id));
   }
   selected.clear();dialog.close();await orders();await summary();
   message('已标记 '+result.marked+' 笔测试订单'+(result.already_marked?'，另有 '+result.already_marked+' 笔此前已标记':'')+'。本次未增加额度，未计入实际收款。');
  }catch(error){byId('test-mark-error').textContent=error.message;}
  finally{busy=false;byId('test-mark-submit').disabled=false;byId('test-mark-close').disabled=false;sync();}
 });
 new MutationObserver(()=>{if(byId('console').hidden){selected.clear();batch=null;if(dialog.open&&!busy)dialog.close();sync();}}).observe(byId('console'),{attributes:true,attributeFilter:['hidden']});
})();
