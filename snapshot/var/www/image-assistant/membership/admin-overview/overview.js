'use strict';
document.addEventListener('DOMContentLoaded',()=>{
 const host=document.getElementById('ops-overview'),consolePanel=document.getElementById('console');if(!host||!consolePanel)return;
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
 const fmt=n=>Number.isFinite(n)?n.toLocaleString('zh-CN'):'未接入',money=n=>Number.isFinite(n)?'¥'+(n/100).toFixed(2):'未接入';
 const nav=label=>document.querySelector('.workspace-sidebar nav button[aria-label="'+label+'"]')?.click();
 const root=el('section',undefined,'ov-dashboard');root.id='workspace-dashboard';root.setAttribute('aria-label','工作区总览');host.prepend(root);
 const oldMetrics=document.querySelector('.metrics'),oldProducts=document.getElementById('products')?.closest('section');oldMetrics?.classList.add('ov-legacy');oldProducts?.classList.add('ov-legacy');
 const intro=el('div',undefined,'ov-intro');intro.append(el('span','SKILL OPERATIONS','ov-eyebrow'),el('p','从用户首次互动到交付，掌握每一步的进展。'));root.append(intro);
 const status=el('p','正在读取总览…','ov-status');status.setAttribute('role','status');root.append(status);
 const alerts=el('div',undefined,'ov-alerts'),grid=el('div',undefined,'ov-grid'),lower=el('div',undefined,'ov-lower');root.append(alerts,grid);
 const foot=el('p','下载按已采集的部分技能清单统计；账户、请求、任务分别计数。业务指标随页头周期变化。','ov-caption');root.append(foot,lower);
 const chart=el('article',undefined,'ov-panel ov-chart'),states=el('article',undefined,'ov-panel');lower.append(chart,states);
 const services=el('article',undefined,'ov-panel ov-products');root.append(services);
 let ticket=0,controller=null,scheduled=null,channels=null;
 function metric(label,value,note,icon,target){const b=el('button',undefined,'ov-card');b.type='button';b.append(el('span',label,'ov-label'),el('span',icon,'ov-icon'),el('strong',value),el('span',note,'ov-card-note'),el('span','↗','ov-arrow'));if(target)b.addEventListener('click',()=>nav(target));else{b.disabled=true;b.classList.add('ov-info');}grid.append(b);}
 function alertCard(label,value,note,target){const b=el('button',undefined,'ov-alert');b.type='button';b.append(el('span',label,'ov-alert-title'),el('small',note),el('strong',value),el('span','↗'));b.onclick=()=>nav(target);alerts.append(b);}
 function drawTrend(data){chart.replaceChildren(el('h3','生图任务趋势'),el('p','近14天 · Gemini / Temu · 按任务创建日','ov-caption'));
  if(!Array.isArray(data?.trend)){chart.append(el('p','趋势数据暂未读取，请刷新重试。','ov-empty'));return;}
  const rows=data.trend,max=Math.max(1,...rows.flatMap(x=>[x.gemini,x.temu]));
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 680 220');svg.setAttribute('role','img');svg.setAttribute('aria-label','近14天Gemini与Temu生图任务趋势');
  for(let i=0;i<4;i++){const y=20+i*50,l=document.createElementNS(ns,'line');l.setAttribute('x1','36');l.setAttribute('x2','660');l.setAttribute('y1',y);l.setAttribute('y2',y);l.setAttribute('stroke','#e8edf6');l.setAttribute('stroke-dasharray','4 5');svg.append(l);const t=document.createElementNS(ns,'text');t.setAttribute('x','4');t.setAttribute('y',y+4);t.textContent=Math.round(max*(1-i/3));svg.append(t);}
  for(const [key,color] of [['gemini','#5368ee'],['temu','#14a38b']]){const line=document.createElementNS(ns,'polyline');line.setAttribute('points',rows.map((r,i)=>(36+i*624/Math.max(1,rows.length-1))+','+(170-r[key]/max*150)).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke',color);line.setAttribute('stroke-width','2.6');svg.append(line);
   rows.forEach((r,i)=>{const dot=document.createElementNS(ns,'circle');dot.setAttribute('cx',36+i*624/Math.max(1,rows.length-1));dot.setAttribute('cy',170-r[key]/max*150);dot.setAttribute('r','3');dot.setAttribute('fill',color);const title=document.createElementNS(ns,'title');title.textContent=r.date+' '+key+' '+r[key]+'个任务';dot.append(title);svg.append(dot);});}
  rows.forEach((r,i)=>{if(i%3&&i!==rows.length-1)return;const t=document.createElementNS(ns,'text');t.setAttribute('x',36+i*624/Math.max(1,rows.length-1));t.setAttribute('y','202');t.setAttribute('text-anchor','middle');t.textContent=r.date.slice(5);svg.append(t);});
  const legend=el('p',undefined,'ov-legend');legend.append(el('span','● Gemini'),el('span','● Temu'));chart.append(svg,legend,el('p',data.scope,'ov-caption'));
 }
 function render(summary,aggregate,directory,health){
  const products=summary?.products?.filter(x=>['gemini','temu'].includes(x.product))||[],connected=products.filter(x=>x.connected),complete=products.length===2&&connected.length===2;
  const total=get=>complete?connected.reduce((a,x)=>a+get(x),0):null;
  const paid=total(x=>x.paid?.amount_fen||0),paidCount=total(x=>x.paid?.orders||0),success=total(x=>x.jobs?.succeeded||0),pending=total(x=>x.jobs?.pending||0);
  const sh=channels?.skillhub||summary?.channels?.skillhub,known=directory?.products?.filter(x=>x.channel==='SkillHub');
  grid.replaceChildren();alerts.replaceChildren();
  alertCard('待核款订单',fmt(aggregate?.pending_orders),'用户已登记付款，仍需核实到账','订单与核款');alertCard('待核查任务',fmt(pending),'Gemini / Temu · 当前选定周期','请求与渠道');
  metric('累计下载（已采集）',fmt(sh?.downloads),(sh?.skill_count??known?.length??'—')+'个匹配技能 · SkillHub部分清单','⇩','渠道下载');
  metric('已观测技能',fmt(known?.length??sh?.skill_count),'SkillHub匹配清单；其他渠道单独展示','◈','渠道下载');
  metric('统一账户数',fmt(aggregate?.unique_accounts??summary?.shared_accounts),'统一账户库记录；不等于独立真人数','♙','用户与额度');
  metric('确认收款笔数',fmt(paidCount),'Gemini / Temu · 当前周期','▤','订单与核款');
  metric('确认收款金额',money(paid),'当前周期确认到账金额，不代表净利润','¥','订单与核款');
  metric('生成成功',fmt(success),'Gemini / Temu · 当前周期成功记录','✓','请求与渠道');
  metric('激活请求',fmt(total(x=>(x.events||[]).filter(e=>e.event.startsWith('activation_')).reduce((a,e)=>a+e.count,0))),'包含注册、恢复和重试；不等于用户数','⌁','请求与渠道');
  metric('上游实际成本','未接入','已登记单价；尚未汇总真实成本流水','◇','上游资产');
  drawTrend(aggregate);states.replaceChildren(el('h3','服务状态'),el('p','当前健康检查；不代表真实生成测试','ov-caption'));
  for(const [key,label] of [['gemini','通用生图'],['temu','Temu商家生图'],['pet','宠物养护']]){const value=health[key],row=el('div',undefined,'ov-state');row.append(el('span',label),el('b',value?.status==='ok'?'服务正常':'暂未读取',value?.status==='ok'?'ov-ok':'ov-muted'));states.append(row);}
  const stateLink=el('button','查看上游资产　↗','ov-text-button');stateLink.onclick=()=>nav('上游资产');states.append(stateLink);
  services.replaceChildren(el('h3','产品使用概况'),el('p','生图沿现有统计口径；独立服务按各自记录展示。','ov-caption'));
  const list=el('div',undefined,'ov-service-list');
  for(const p of products){const row=el('div',undefined,'ov-service');row.append(el('strong',p.product==='temu'?'Temu商家生图':'通用生图'),el('span',p.connected?'累计产品账户 '+fmt(p.users)+' · 周期内成功 '+fmt(p.jobs?.succeeded||0):'数据源暂不可用'));const b=el('button','查看请求　↗','ov-text-button');b.onclick=()=>nav('请求与渠道');row.append(b);list.append(row);}
  for(const p of directory?.services||[]){const row=el('div',undefined,'ov-service');row.append(el('strong',p.name),el('span',p.unavailable?'记录暂不可用':'产品账户 '+fmt(p.users)+' · '+(p.note||'独立服务记录')));list.append(row);}services.append(list);
  status.textContent='更新于 '+new Date().toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})+(complete?'':' · 部分业务统计暂未读取');
 }
 async function request(path,signal){const r=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.any([signal,AbortSignal.timeout(20000)])});if(!r.ok){const e=Error('read_failed');e.status=r.status;throw e;}return r.json();}
 async function load(){if(consolePanel.hidden)return;const seq=++ticket;controller?.abort();controller=new AbortController();const signal=controller.signal;status.textContent='正在刷新总览…';
  const paths=['/ops/api/summary?days='+encodeURIComponent(document.getElementById('days')?.value||'7'),'/ops/api/workspace-overview?days=14','/ops/api/product-directory?days='+encodeURIComponent(document.getElementById('days')?.value||'7'),...['gemini','temu','pet'].map(p=>'/platform-api/'+p+'/health')];
  const results=await Promise.allSettled(paths.map(p=>request(p,signal)));if(seq!==ticket||signal.aborted||consolePanel.hidden)return;
  if(results.some(x=>x.status==='rejected'&&x.reason.status===401)){grid.replaceChildren();alerts.replaceChildren();chart.replaceChildren();states.replaceChildren();services.replaceChildren();status.textContent='登录已过期，请重新登录';return;}
  const values=results.map(x=>x.status==='fulfilled'?x.value:null);render(values[0],values[1],values[2],{gemini:values[3],temu:values[4],pet:values[5]});if(results.some(x=>x.status==='rejected'))status.textContent+=' · 部分数据未读取，未将缺失值计为0';
 }
 function visibility(){const active=document.body.dataset.workspaceView==='overview'&&!consolePanel.hidden;root.hidden=!active;if(active)schedule();}
 function schedule(){clearTimeout(scheduled);scheduled=setTimeout(load,120);}
 document.addEventListener('channel-data-ready',e=>{channels=e.detail;if(!root.hidden)schedule();});
 document.getElementById('refresh')?.addEventListener('click',schedule);document.getElementById('days')?.addEventListener('change',schedule);
 new MutationObserver(visibility).observe(document.body,{attributes:true,attributeFilter:['data-workspace-view']});
 new MutationObserver(()=>{if(consolePanel.hidden){controller?.abort();root.hidden=true;grid.replaceChildren();chart.replaceChildren();services.replaceChildren();alerts.replaceChildren();states.replaceChildren();}else visibility();}).observe(consolePanel,{attributes:true,attributeFilter:['hidden']});
 visibility();window.addEventListener('pagehide',()=>{controller?.abort();clearTimeout(scheduled);},{once:true});
});
