 'use strict';
document.addEventListener('DOMContentLoaded',()=>{
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 const show=x=>x==null?'未采集':Number(x).toLocaleString('zh-CN');
 let seq=0;
 function panel(id,title){let box=document.getElementById(id);if(box)return box;box=el('div');box.id=id;box.style.cssText='margin-top:22px;max-width:100%;min-width:0';box.append(el('h3',title));return box;}
 function fill(box,d,requests){box.replaceChildren(el('h3',requests?'全部已观测 Skill · 请求覆盖情况':'全部已观测 Skill · 产品明细'));
 box.append(el('p','SkillHub '+d.products.filter(x=>x.channel==='SkillHub').length+' 个技能；WorkBuddy '+d.products.filter(x=>x.channel==='WorkBuddy').length+' 条资产。'+d.scope+'。下载量与安装量分别展示，不代表账户数或使用次数。'));
 const wrap=el('div');wrap.style.cssText='overflow-x:auto;max-width:100%';const table=el('table'),head=el('thead'),hr=el('tr'),body=el('tbody');
 (requests?['Skill / 标识','渠道','请求统计状态','最近采集']:['Skill / 标识','渠道','累计下载','近30天安装','业务数据','最近采集']).forEach(t=>hr.append(el('th',t)));head.append(hr);
 for(const x of d.products){const tr=el('tr'),name=el('td',x.name),small=el('small',x.slug||('资产位置 '+(x.page??'—')+' / '+(x.row??'—')));small.style.cssText='display:block;overflow-wrap:anywhere;font-weight:normal';name.append(small);tr.append(name);
 const stamp=x.captured_at?String(x.captured_at).replace('T',' ').slice(0,19):'未采集';
 (requests?[x.channel,'未接入逐技能请求统计',stamp]:[x.channel,x.downloads==null?'—':show(x.downloads),x.installs==null?'—':show(x.installs),x.attribution,stamp]).forEach(t=>tr.append(el('td',t)));body.append(tr);}
 table.append(head,body);wrap.append(table);box.append(wrap,el('p','公开下载清单为部分匹配范围；无逐技能归属时留空，不把共享通道数据重复分配。WorkBuddy 为采集时所选近30天，独立于上方统计周期。'));
 }
 async function load(){const n=++seq,days=document.getElementById('days')?.value||'7';try{const r=await fetch('/ops/api/product-directory?days='+encodeURIComponent(days),{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});if(n!==seq)return;if(!r.ok)throw Error('产品明细暂未读取成功，请刷新重试');const d=await r.json();if(n!==seq||document.getElementById('console')?.hidden)return;
 for(const [id,title,target,requests] of [['all-skill-products','产品明细','products',false],['all-skill-requests','请求覆盖','requests',true]]){const table=document.getElementById(target)?.closest('table');if(!table)continue;const box=panel(id,title);if(!box.isConnected)(table.parentElement.tagName==='DIV'?table.parentElement.parentElement:table.parentElement).append(box);fill(box,d,requests);}
 const tbody=document.getElementById('products');tbody?.querySelectorAll('[data-extra-product]').forEach(x=>x.remove());for(const s of d.services){const tr=el('tr');tr.dataset.extraProduct=s.product;[s.name+(s.product==='pet'?'（照片分析）':''),s.unavailable?'暂不可用':show(s.users),s.new_users==null?'未采集':show(s.new_users),'—',s.product==='pet'?show(s.jobs?.succeeded||0):'不适用',s.product==='pet'?show((s.jobs?.reserved||0)+(s.jobs?.unknown||0)):'不适用',s.product==='pet'?show(s.jobs?.failed||0):'不适用',s.paid_fen==null?'未采集':'¥'+(s.paid_fen/100).toFixed(2)].forEach(t=>tr.append(el('td',t)));tr.title=s.note;tbody?.append(tr);}
 const requests=document.getElementById('requests');requests?.querySelectorAll('[data-extra-product]').forEach(x=>x.remove());for(const s of d.services){const tr=el('tr');tr.dataset.extraProduct=s.product;[s.name,'未采集','未采集','未采集','—','未采集','未采集'].forEach(t=>tr.append(el('td',t)));requests?.append(tr);}
 const note=document.getElementById('all-skill-products');note?.append(el('p','上方首页汇总卡片沿用 Gemini / Temu 生图口径；宠物照片分析和外贸服务单独列示。宠物账户与订单包含历史测试记录（无可靠标记可筛除）；外贸已排除标记测试数据。'));

 }catch(e){for(const id of ['all-skill-products','all-skill-requests']){const b=document.getElementById(id);if(b)b.replaceChildren(el('p',e.message));}}}
 document.addEventListener('channel-data-ready',()=>queueMicrotask(load));
});
