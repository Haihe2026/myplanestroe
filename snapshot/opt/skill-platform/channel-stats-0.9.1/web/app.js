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
async function summary(){const seq=++summarySeq;const d=await api('summary?days='+$('days').value);if(seq!==summarySeq)return;document.dispatchEvent(new CustomEvent('channel-data-ready',{detail:d.channels}));show();['products','requests','sources'].forEach(id=>$(id).replaceChildren());let u=0,s=0,p=0,paid=0;for(const item of d.products){if(!item.connected){tr('products',[names[item.product],'数据源不可用','—','—','—','—','—','—']);continue;}const j=item.jobs;u+=item.users;s+=j.succeeded||0;p+=j.pending||0;paid+=item.paid.amount_fen;tr('products',[names[item.product],num(item.users),num(item.new_users),num(item.active),num(j.succeeded),num(j.pending),num(j.failed),money(item.paid.amount_fen)]);const acts=item.events.filter(e=>e.event.startsWith('activation_'));const count=acts.reduce((n,e)=>n+e.count,0),failed=acts.filter(e=>e.status>=400).reduce((n,e)=>n+e.count,0);const sum=name=>item.events.filter(e=>e.event===name).reduce((n,e)=>n+e.count,0);tr('requests',[names[item.product],num(count),num(sum('activation_created'))+' / '+num(sum('activation_restored')),num(failed),count?(100*failed/count).toFixed(1)+'%':'—',num(sum('purchase_offer_fetch')),num(sum('native_order_attempt'))]);const groups={};for(const e of acts){const key=e.device+'|'+e.channel;groups[key]??={device:e.device,channel:e.channel,n:0,bad:0};groups[key].n+=e.count;if(e.status>=400)groups[key].bad+=e.count;}for(const g of Object.values(groups)){tr('sources',[names[item.product],({desktop:'桌面',mobile:'手机',cloud:'云端',unknown:'未知'})[g.device]||'未知',({workbuddy_skill:'WorkBuddy技能',workbuddy_expert:'WorkBuddy专家',skillhub:'SkillHub',unknown:'未知'})[g.channel]||'未知',num(g.n),num(g.bad)]);}}
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
  choose(panel.querySelector('[data-range="30"]'));
})();


(() => {
 'use strict';
 const n=value=>Number.isSafeInteger(value)&&value>=0?value.toLocaleString('zh-CN'):'—';
 const dateNow=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const previousDate=(day,offset)=>{const d=new Date(day+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+offset);return d.toISOString().slice(0,10);};
 const delta=(history,day)=>{const a=history[day],b=history[previousDate(day,-1)];if(!a||!b||JSON.stringify(a.skills.map(x=>x.slug).sort())!==JSON.stringify(b.skills.map(x=>x.slug).sort()))return null;const value=a.downloads-b.downloads;return value>=0?value:null;};
 let latest=null;
 function draw(){
  const data=latest,snapshot=data?.skillhub;if(!snapshot)return;
  const panel=document.getElementById('ops-channels'),cards=panel.querySelectorAll('.channel-cards article');
  const history=data.history||{},today=dateNow();
  cards[0].querySelector('strong').textContent=n(delta(history,previousDate(today,-1)));
  cards[0].querySelector('small').textContent='SkillHub · 需连续两日同范围记录';
  cards[1].querySelector('strong').textContent=n(delta(history,today));
  cards[1].querySelector('small').textContent='SkillHub · 需昨日同范围快照';
  cards[2].querySelector('span').textContent='SkillHub 已匹配技能下载小计';
  cards[2].querySelector('strong').textContent=n(snapshot.downloads);
  cards[2].querySelector('small').textContent=snapshot.skill_count+' 个技能 · '+snapshot.date+' · 清单待核全';
  const wb=data.workbuddy;
  if(wb){cards[3].querySelector('strong').textContent=n(wb.installs);cards[3].querySelector('small').textContent='数据日期 '+wb.date;}
  panel.querySelector('.channel-connection').textContent=wb?'已接入 · 技能清单待核全':'SkillHub 已读取 · WorkBuddy 待登录';
  const body=panel.querySelector('#channel-setup tbody');body.rows[0].cells[1].textContent='已读取（部分清单）';body.rows[0].cells[2].textContent=snapshot.scope;
  body.rows[1].cells[1].textContent=wb?'已读取':'等待首次登录';
  body.rows[1].cells[2].textContent=wb?'读取日期 '+wb.date:'请在 Codex 右侧 WorkBuddy 页面登录一次。之后每日自动读取，登录失效时提醒。';
  const caption=document.getElementById('channel-period');
  caption.textContent=caption.textContent.replace('尚未接入统计数据','SkillHub 数据日 '+snapshot.date);
  let note=document.getElementById('channel-collection-note');
  if(!note){note=document.createElement('p');note.id='channel-collection-note';note.className='channel-caption';panel.querySelector('.channel-cards').after(note);}
  note.textContent='每日北京时间09:00由本机自动任务读取，需电脑开机且 Codex 正在运行。最近成功读取：'+snapshot.captured_at.slice(0,19).replace('T',' ')+'。下载量是平台计数，不等同独立用户数。';
  const start=document.getElementById('channel-from').value,end=document.getElementById('channel-to').value;
  const points=Object.keys(history).sort().filter(day=>day>=start&&day<=end).map(day=>({day,value:delta(history,day)})).filter(p=>p.value!==null);
  const empty=panel.querySelector('.channel-empty');
  empty.replaceChildren();
  const title=document.createElement('h3'),text=document.createElement('p');
  title.textContent=points.length>=2?'SkillHub 每日新增下载':'已开始记录，等待形成趋势';
  text.textContent=points.length>=2?'仅展示连续日期、相同技能清单的可比较增量。':'首份快照已保存。至少积累两天同范围记录后显示新增；历史缺失日期不补零。';
  empty.append(title,text);
  if(points.length>=2){
   const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 800 180');svg.setAttribute('role','img');svg.setAttribute('aria-label','SkillHub 每日新增下载趋势');svg.style.width='100%';
   const base=new Date(start+'T00:00:00Z').getTime(),span=Math.max(86400000,new Date(end+'T00:00:00Z').getTime()-base),max=Math.max(1,...points.map(p=>p.value));
   for(const p of points){const dot=document.createElementNS(ns,'circle');dot.setAttribute('cx',String(20+(new Date(p.day+'T00:00:00Z').getTime()-base)/span*760));dot.setAttribute('cy',String(160-p.value/max*140));dot.setAttribute('r','4');dot.setAttribute('fill','#12834e');const label=document.createElementNS(ns,'title');label.textContent=p.day+'：'+p.value;dot.append(label);svg.append(dot);}
   empty.append(svg);
  }
 }
 document.addEventListener('channel-data-ready',event=>{latest=event.detail;draw();});
 document.querySelectorAll('#ops-channels [data-range]').forEach(button=>button.addEventListener('click',draw));
 document.getElementById('channel-custom').addEventListener('submit',draw);
})();
