'use strict';
document.addEventListener('DOMContentLoaded',()=>{
 const consolePanel=document.getElementById('console'),overview=document.getElementById('ops-overview'),nav=document.querySelector('.workspace-sidebar nav');
 if(!consolePanel||!overview||!nav)return;
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
 const menu=el('button');menu.type='button';menu.title='用户与额度';menu.setAttribute('aria-label','用户与额度');const icon=el('span','♙','nav-icon');icon.setAttribute('aria-hidden','true');menu.append(icon,el('span','用户与额度','nav-label'));
 const oldUsers=nav.querySelector('button[aria-label="用户管理"]');nav.insertBefore(menu,oldUsers||null);
 const section=el('section');section.id='users-directory';section.hidden=true;section.append(el('h2','全部用户与额度'));
 section.append(el('p','按已记录的注册 / 首次登记时间倒序，未知时间排在最后。统一账户全量分页展示，含宠物及外贸获客账户；未关联的旧独立产品账户仍可在“用户管理”的历史查询中查看。不同产品额度分别列示，不合并、不换算。','ud-note'));
 const controls=el('form',undefined,'ud-controls'),input=el('input');input.type='search';input.maxLength=64;input.placeholder='搜索账户编号';input.setAttribute('aria-label','搜索账户编号');const find=el('button','查询用户');find.type='submit';const refresh=el('button','刷新额度');refresh.type='button';controls.append(input,find,refresh);section.append(controls);
 const status=el('p','','ud-status');status.setAttribute('role','status');section.append(status);
 const scroll=el('div',undefined,'ud-scroll'),table=el('table'),head=el('thead'),tr=el('tr'),body=el('tbody');
 ['用户账户 / 详情','注册 / 首次登记','共享生图次数','Temu 可用 / 体验','宠物独立额度','外贸获客余额'].forEach(x=>tr.append(el('th',x)));head.append(tr);table.append(head,body);scroll.append(table);section.append(scroll);
 const pager=el('div',undefined,'ud-pager'),prev=el('button','上一页'),next=el('button','下一页'),label=el('span');prev.type=next.type='button';pager.append(prev,label,next);section.append(pager);overview.insertBefore(section,overview.querySelector('footer'));
 let active=false,detailFromHere=false,page=1,revision=0,total=0;
 const when=x=>x==null?'未知 / 未记录':new Date(x*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
 const money=n=>'¥'+(n/100).toFixed(2),basis={account_created:'账户创建',credential_registered:'首次凭证登记',trade_account_linked:'首次外贸账户关联',pet_enrolled:'宠物开通记录',unknown:'历史注册时间未记录'};
 function activate(loadData=true){if(consolePanel.hidden)return;oldUsers?.click();active=true;detailFromHere=false;document.getElementById('journey-v2')?.setAttribute('hidden','');document.querySelector('.workspace-legacy-users')?.setAttribute('hidden','');nav.querySelectorAll('[aria-current]').forEach(x=>x.removeAttribute('aria-current'));menu.setAttribute('aria-current','page');section.hidden=false;document.body.dataset.workspaceView='all-users';const heading=consolePanel.querySelector('.heading h1');if(heading)heading.textContent='用户与额度';if(loadData)load();}
 menu.addEventListener('click',()=>activate());
 nav.addEventListener('click',e=>{if(e.target.closest('button')!==menu&&e.target.closest('button')){active=false;detailFromHere=false;section.hidden=true;menu.removeAttribute('aria-current');revision++;}});
 async function load(){if(!active||consolePanel.hidden)return;const rev=++revision;refresh.disabled=true;status.textContent='正在读取用户及额度…';try{const r=await fetch('/ops/api/users-directory?'+new URLSearchParams({page:String(page),q:input.value}),{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});if(r.status===401){body.replaceChildren();consolePanel.hidden=true;const login=document.getElementById('login');if(login)login.hidden=false;const logout=document.getElementById('logout');if(logout)logout.hidden=true;throw Error('登录已失效，请重新登录');}if(!r.ok)throw Error('用户额度暂未读取成功，请刷新重试');const data=await r.json();if(rev!==revision||consolePanel.hidden||!active)return;body.replaceChildren();total=data.total;
 for(const u of data.users){const row=el('tr'),id=el('td'),choose=el('button',u.id,'ud-id');choose.type='button';choose.title='查看该用户的全部详情';choose.addEventListener('click',()=>{detailFromHere=true;section.hidden=true;document.dispatchEvent(new CustomEvent('ops:show-user',{detail:{uid:u.id}}));});id.append(choose);row.append(id);
 const date=el('td',when(u.registered_at));date.append(el('small',basis[u.registration_basis]||'首次登记记录'));row.append(date);
 const image=el('td',u.image?u.image.shared+' 次':'暂未读取');if(u.image)image.append(el('small','旧 Gemini 专用：'+(u.image.legacy.gemini??'未读取')+' 次'));row.append(image);
 const temu=el('td',u.image?(u.image.available.temu??'未读取')+' 次':'暂未读取');if(u.image)temu.append(el('small','其中体验 '+u.image.temu_trial+' 次；旧专用 '+(u.image.legacy.temu??'未读取')+' 次'));row.append(temu);
 const pet=el('td',u.pet?'订阅照片 '+u.pet.photo_remaining+' 次':u.missing.includes('pet_quota_unavailable')?'暂未读取':'未开通');if(u.pet){pet.append(el('small','体验照片 '+u.pet.trial_photo_remaining+' 次；档案 '+u.pet.profiles_used+' / '+(u.pet.profiles_limit===-1?'不限':u.pet.profiles_limit)),el('small','订阅到期：'+(u.pet.expires_at?when(u.pet.expires_at):'无有效订阅')),el('small','照片分析是否开放以宠物服务状态为准'));}row.append(pet);
 const trade=el('td',u.trade?money(u.trade.available_fen):'未开通');if(u.trade)trade.append(el('small','预占 '+money(u.trade.reserved_fen)));row.append(trade);body.append(row);}
 if(!data.users.length){const td=el('td','当前查询没有匹配用户');td.colSpan=6;const row=el('tr');row.append(td);body.append(row);}label.textContent='第 '+page+' / '+Math.max(1,Math.ceil(total/data.page_size))+' 页 · 共 '+total+' 位用户';prev.disabled=page<=1;next.disabled=page*data.page_size>=total;status.textContent='更新于 '+when(data.generated_at);
 }catch(e){if(rev===revision){body.replaceChildren();label.textContent='';status.textContent=e.message;prev.disabled=next.disabled=true;}}finally{if(rev===revision)refresh.disabled=false;}}
 controls.addEventListener('submit',e=>{e.preventDefault();page=1;load();});refresh.addEventListener('click',load);prev.addEventListener('click',()=>{if(page>1){page--;load();}});next.addEventListener('click',()=>{page++;load();});
 document.addEventListener('ops:account-close',()=>{if(detailFromHere)activate(false);});
 new MutationObserver(()=>{if(consolePanel.hidden){revision++;active=false;detailFromHere=false;body.replaceChildren();section.hidden=true;menu.removeAttribute('aria-current');}else if(active&&!detailFromHere){activate(false);load();}}).observe(consolePanel,{attributes:true,attributeFilter:['hidden']});
});
