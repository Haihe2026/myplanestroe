 'use strict';
function sortProducts(rows,key,descending){
 const collator=new Intl.Collator('zh-CN',{numeric:true,sensitivity:'base'});
 const value=x=>key==='captured_at'?(x[key]?Date.parse(x[key]):null):key==='name'?x.name:x[key];
 return rows.map((row,index)=>({row,index})).sort((a,b)=>{
  const x=value(a.row),y=value(b.row),missing=v=>v==null||v===''||(typeof v==='number'&&!Number.isFinite(v));
  if(missing(x)||missing(y))return missing(x)===missing(y)?a.index-b.index:missing(x)?1:-1;
  const order=typeof x==='number'&&typeof y==='number'?x-y:collator.compare(String(x),String(y));
  return (descending?-order:order)||a.index-b.index;
 }).map(x=>x.row);
}

document.addEventListener('DOMContentLoaded',()=>{
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 const show=x=>x==null?'未采集':Number(x).toLocaleString('zh-CN');
 let seq=0;const sorts=new Map();
 function panel(id,title){let box=document.getElementById(id);if(box)return box;box=el('div');box.id=id;box.style.cssText='margin-top:22px;max-width:100%;min-width:0';box.append(el('h3',title));return box;}
 function fill(box,d,requests){box.replaceChildren(el('h3',requests?'全部已观测 Skill · 请求覆盖情况':'全部已观测 Skill · 产品明细'));
 box.append(el('p','SkillHub '+d.products.filter(x=>x.channel==='SkillHub').length+' 个技能；WorkBuddy '+d.products.filter(x=>x.channel==='WorkBuddy').length+' 条资产。'+d.scope+'。下载量与安装量分别展示，不代表账户数或使用次数。'));
 const wrap=el('div');wrap.style.cssText='overflow-x:auto;max-width:100%';const table=el('table'),head=el('thead'),hr=el('tr'),body=el('tbody');
 const columns=requests?[['Skill / 标识','name'],['渠道','channel'],['请求统计状态','attribution'],['最近采集','captured_at']]:[['Skill / 标识','name'],['渠道','channel'],['累计下载','downloads'],['近30天安装','installs'],['业务数据','attribution'],['最近采集','captured_at']];
 const displayProducts=requests?d.products.map(x=>({...x,attribution:'未接入逐技能请求统计'})):d.products;
 const headers=[];
 for(const [title,key] of columns){const th=el('th'),button=el('button');button.type='button';button.style.cssText='background:transparent;color:inherit;border:0;padding:6px 0;white-space:nowrap;font:inherit;font-weight:600;cursor:pointer';button.title='点击正序，再次点击倒序';button.addEventListener('click',()=>{const old=sorts.get(box.id);sorts.set(box.id,{key,descending:old?.key===key?!old.descending:false});render();});th.append(button);hr.append(th);headers.push({th,button,title,key});}head.append(hr);
 function render(){
  const order=sorts.get(box.id);
  for(const h of headers){const active=order?.key===h.key;h.th.setAttribute('aria-sort',active?(order.descending?'descending':'ascending'):'none');h.button.textContent=h.title+' '+(active?(order.descending?'▼':'▲'):'△');h.button.setAttribute('aria-label',h.title+'，'+(active?(order.descending?'当前倒序，点击正序':'当前正序，点击倒序'):'点击正序'));}
  body.replaceChildren();
  for(const x of order?sortProducts(displayProducts,order.key,order.descending):displayProducts){const tr=el('tr'),name=el('td',x.name),small=el('small',x.slug||('资产位置 '+(x.page??'—')+' / '+(x.row??'—')));small.style.cssText='display:block;overflow-wrap:anywhere;font-weight:normal';name.append(small);tr.append(name);
   const stamp=x.captured_at?String(x.captured_at).replace('T',' ').slice(0,19):'未采集';
   (requests?[x.channel,'未接入逐技能请求统计',stamp]:[x.channel,x.downloads==null?'—':show(x.downloads),x.installs==null?'—':show(x.installs),x.attribution,stamp]).forEach(t=>tr.append(el('td',t)));body.append(tr);
  }
 }
 render();
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
