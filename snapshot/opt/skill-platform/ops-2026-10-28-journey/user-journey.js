'use strict';
const opsJourneyLabels={invitation_created:'创建账户入口',registration_page_entered:'进入账户页面',recharge_page_entered:'进入付费页面',account_linked:'完成账户关联',order_created:'创建订单',payment_reported:'登记付款（尚未核款）',image_succeeded:'观察到出图成功',return_visit:'再次使用',activity:'认证活动记录'};
function opsJourneyEvents(data,account={}){
 const result=[],seen=new Set(),channel=x=>({workbuddy_skill:'WorkBuddy技能',workbuddy_expert:'WorkBuddy专家',skillhub:'SkillHub'})[x]||x||'渠道未记录';
 function add(at,title,detail,key){if(typeof at!=='number'||!Number.isFinite(at)||at<0)return;if(key&&seen.has(key))return;if(key)seen.add(key);result.push({at,title,detail:String(detail||'')});}
 if(account.registered_at!=null)add(account.registered_at,'账户创建 / 首次登记',account.registration_basis||'按原登记记录','registration');
 for(const e of data.first_dialogues||[])add(e.received_at,'首次互动上报',e.skill_name+' · '+channel(e.channel)+' · '+(e.skill_version||'版本未提供')+(e.client_occurred_at?'；客户端自报时间另有记录':''),'first:'+e.event_id);
 for(const e of data.events||[])add(e.created,opsJourneyLabels[e.event]||'服务端事件：'+e.event,[e.source&&e.source!=='unknown'?e.source:'来源未记录',channel(e.channel),e.object_id||''].join(' · '),e.event+':'+(e.object_id||e.id||e.created));
 for(const o of data.orders||[]){add(o.created,'创建订单','订单 '+o.id+' · ¥'+(o.amount_fen/100).toFixed(2)+' · '+(o.gateway_product||'通用'),'order_created:'+o.id);add(o.reported_at,'登记付款（尚未核款）','订单 '+o.id,'payment_reported:'+o.id);if(o.paid_authoritative===true)add(o.paid_at,'核款到账','订单 '+o.id+' · ¥'+(o.amount_fen/100).toFixed(2),'paid:'+o.id);}
 for(const j of data.jobs||[]){add(j.created,'提交制作任务','任务 '+j.id+' · '+(j.product||'产品未记录')+' · 当前状态 '+j.status,'task:'+j.id);add(j.success_observed_at,'观察到任务成功','任务 '+j.id,'image_succeeded:'+j.id);}
 for(const l of data.ledger||[])add(l.created,'额度流水',l.kind+' · 变动值 '+l.amount+(l.job_id?' · 任务 '+l.job_id:''),'ledger:'+l.database+':'+l.id);
 for(const [product,old] of Object.entries(data.legacy||{})){
  for(const j of old.jobs||[])add(j.created,'历史任务提交',product+' · 任务 '+j.id+' · 当前状态 '+j.status+'；未记录完成时间','legacy:'+product+':job:'+j.id);
  for(const l of old.ledger||[])add(l.created,'历史额度流水',product+' · '+l.kind+' · 变动值 '+l.amount,'legacy:'+product+':ledger:'+l.id);
 }
 for(const r of data.additional_activity?.items||[]){
  if(r.record_type==='wechat_bound')add(r.created,'绑定微信账户','沿用原账户','wechat-bound');
  else if(r.record_type==='orders'){add(r.created,'创建订单',r.product+' · 订单 '+r.id+' · ¥'+(r.amount_fen/100).toFixed(2),r.product+':order_created:'+r.id);if(r.status==='paid')add(r.paid_at,'核款到账',r.product+' · 订单 '+r.id,r.product+':paid:'+r.id);}
  else add(r.created,'宠物服务记录',r.kind+(r.reference?' · '+r.reference:''),'pet-audit:'+r.id);
 }
 return result.sort((a,b)=>b.at-a.at);
}
if(typeof module!=='undefined')module.exports={opsJourneyEvents};
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',()=>{
 const root=document.getElementById('console');if(!root)return;
 const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e;};
 const modal=node('dialog',undefined,'uj-drawer');modal.setAttribute('aria-labelledby','uj-title');
 const head=node('header',undefined,'uj-head'),heading=node('div'),title=node('h2','用户旅程');title.id='uj-title';heading.append(node('p','USER JOURNEY','uj-kicker'),title);
 const close=node('button','×','uj-close');close.type='button';close.setAttribute('aria-label','关闭用户旅程');head.append(heading,close);
 const body=node('div',undefined,'uj-body');modal.append(head,body);document.body.append(modal);
 let selected=null,revision=0,controller=null;
 const when=t=>typeof t==='number'?new Date(t*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'未记录';
 function dismiss(){if(modal.open)modal.close();}
 modal.addEventListener('close',()=>{revision++;controller?.abort();selected=null;body.replaceChildren();document.body.classList.remove('user-journey-open');});
 close.addEventListener('click',dismiss);modal.addEventListener('click',e=>{const r=modal.getBoundingClientRect();if(e.target===modal&&(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom))dismiss();});
 const stateObserver=new MutationObserver(()=>{if(root.hidden)dismiss();});stateObserver.observe(root,{attributes:true,attributeFilter:['hidden']});
 async function read(url){const r=await fetch(url,{credentials:'same-origin',cache:'no-store',signal:controller.signal});if(r.status===401){dismiss();throw Error('登录已失效，请重新登录后台');}if(!r.ok)throw Error('旅程记录暂未读取成功，请点击刷新旅程重试');return r.json();}
 function fact(grid,label,value){const box=node('div',undefined,'uj-fact');box.append(node('small',label),node('strong',value));grid.append(box);}
 function toolbar(){const bar=node('div',undefined,'uj-toolbar'),refresh=node('button','刷新旅程');refresh.type='button';refresh.addEventListener('click',load);bar.append(node('span','北京时间 · 按服务端已记录数据','uj-meta'),refresh);body.append(bar);}
 function render(data,account){
  body.replaceChildren();toolbar();const summary=node('section',undefined,'uj-summary'),first=(data.first_dialogues||[]).slice().sort((a,b)=>a.received_at-b.received_at)[0];
  summary.append(node('span','统一账户','uj-meta'),node('h3',first?.skill_name||'账户 '+data.id.slice(0,8)),node('p',data.id,'uj-meta'));
  const grid=node('div',undefined,'uj-grid');fact(grid,'账户创建 / 首次登记',when(account.registered_at));fact(grid,'首次互动上报 · 服务端接收',data.first_dialogues_unavailable?'暂时无法读取':first?when(first.received_at):'未上报');fact(grid,'共享生图次数',data.quota?.shared==null?'暂未读取':data.quota.shared+' 次');fact(grid,'Temu 可用次数',data.quota?.available?.temu==null?'暂未读取':data.quota.available.temu+' 次');
  if(account.pet)fact(grid,'宠物照片额度','订阅 '+account.pet.photo_remaining+' 次 · 体验 '+account.pet.trial_photo_remaining+' 次');
  if(account.trade)fact(grid,'外贸获客可用余额','¥'+(account.trade.available_fen/100).toFixed(2));
  summary.append(grid);body.append(summary,node('h3','操作记录'));
  body.append(node('p','首次互动来自 Skill 主动上报，不含用户原话；未上报不代表没有互动。创建入口、注册、登记付款和核款到账分别记录。','uj-note'));
  const items=opsJourneyEvents(data,account),list=node('ol',undefined,'uj-events');
  for(const e of items){const row=node('li',undefined,'uj-event');row.append(node('time',when(e.at)),node('h4',e.title),node('p',e.detail));list.append(row);}body.append(list);
  if(!items.length)body.append(node('p','暂无可核验的操作记录。','uj-note'));
  if(Object.values(data.truncated||{}).some(Boolean)||data.additional_activity?.truncated)body.append(node('p','较长历史按来源保留最近记录，当前不是完整历史。','uj-note'));
  if(data.additional_activity?.unavailable||data.additional_activity?.missing?.length)body.append(node('p','部分独立服务记录暂时无法读取，其他已记录事件正常展示。','uj-note'));
 }
 function renderAnonymous(item){
  body.replaceChildren();toolbar();const box=node('section',undefined,'uj-summary');box.append(node('span','尚未关联账户的互动事件','uj-meta'),node('h3',item.skill_name),node('p','事件 '+item.event_id,'uj-meta'));const grid=node('div',undefined,'uj-grid');fact(grid,'首次互动上报 · 服务端接收',when(item.received_at));fact(grid,'客户端自报时间',when(item.client_occurred_at));fact(grid,'Skill 渠道',({workbuddy_skill:'WorkBuddy技能',workbuddy_expert:'WorkBuddy专家',skillhub:'SkillHub'})[item.channel]||'未记录');fact(grid,'版本',item.skill_version||'未提供');box.append(grid);body.append(box,node('h3','操作记录'));const list=node('ol',undefined,'uj-events'),row=node('li',undefined,'uj-event');row.append(node('time',when(item.received_at)),node('h4','首次互动上报'),node('p',item.skill_name));list.append(row);body.append(list,node('p','只记录首次互动元数据，不保存对话正文。未关联账户的事件不当作已注册用户或独立人数。账户关联后会沿真实关联继续展示。','uj-note'));
 }
 async function load(){if(!selected||!modal.open)return;const rev=++revision;controller?.abort();controller=new AbortController();body.replaceChildren(node('p','正在读取最新操作记录…','uj-meta'));try{
  let snapshot=selected;
  if(snapshot.eventId){const d=await read('/ops/api/user-journey/anonymous?event_id='+encodeURIComponent(snapshot.eventId));if(rev!==revision)return;if(!d.item.user_id){renderAnonymous(d.item);return;}snapshot={uid:d.item.user_id,account:{}};selected=snapshot;}
  const d=await read('/ops/api/journey-v2/user?uid='+encodeURIComponent(snapshot.uid));if(rev!==revision||!modal.open)return;render(d,snapshot.account||{});
 }catch(e){if(rev!==revision||!modal.open)return;body.replaceChildren();toolbar();body.append(node('p',e.message,'uj-error'));}}
 document.addEventListener('ops:open-user-journey',e=>{const d=e.detail||{};if(typeof d.uid!=='string'&&typeof d.eventId!=='string')return;selected=d;if(!modal.open){modal.showModal();document.body.classList.add('user-journey-open');}load();});
});
