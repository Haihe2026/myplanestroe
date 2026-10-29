 'use strict';

function assetCostText(cost){
 if(!cost||!Array.isArray(cost.rates)||!cost.rates.length)return '未登记成本';
 const currency=cost.currency==='USD'?'US$':cost.currency==='CNY'?'¥':String(cost.currency||'');
 const units={image:'张',second:'秒',request:'次',video:'条视频'};
 return cost.rates.map(r=>(r.label?r.label+' ':'')+currency+r.amount+' / '+(units[r.unit]||r.unit)).join('\n');
}
if(typeof module!=='undefined')module.exports={assetCostText};

document.addEventListener('DOMContentLoaded',()=>{
 const consolePanel=document.getElementById('console'),overview=document.getElementById('ops-overview'),nav=document.querySelector('.workspace-sidebar nav');if(!consolePanel||!overview||!nav)return;
 const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=String(text);if(cls)x.className=cls;return x;};
 const menu=el('button');menu.type='button';menu.setAttribute('aria-label','上游资产');menu.append(el('span','◇','nav-icon'),el('span','上游资产','nav-label'));nav.append(menu);
 const section=el('section');section.id='upstream-assets';section.hidden=true;section.append(el('h2','上游资产'));
 section.append(el('p','在这里登记服务地址和KEY，后续开发按资产标识接入。KEY加密保存在服务端，仅显示尾号；现有生图、宠物和外贸配置保持原状。'));
 const status=el('p','','ua-status');status.setAttribute('role','status');section.append(status);
 const controls=el('div',undefined,'ua-controls'),create=el('button','新增资产'),refresh=el('button','刷新资产');create.type=refresh.type='button';controls.append(create,refresh);section.append(controls);
 const filters=el('div',undefined,'ua-filters'),search=el('input'),kindFilter=el('select'),stateFilter=el('select'),count=el('p');search.placeholder='搜索名称、模型、标识或服务地址';search.setAttribute('aria-label','搜索上游资产');
 for(const [select,options] of [[kindFilter,[['','全部类型'],['general','通用'],['data','数据查询'],['image','图片生成'],['vision','图片分析'],['text','文本模型'],['video','视频生成']]],[stateFilter,[['','全部状态'],['enabled','允许引用'],['disabled','停用']]]]){for(const [value,label] of options){const option=el('option',label);option.value=value;select.append(option);}}
 kindFilter.setAttribute('aria-label','资产类型筛选');stateFilter.setAttribute('aria-label','资产状态筛选');filters.append(search,kindFilter,stateFilter);section.append(filters,count);

 const scroll=el('div',undefined,'ua-scroll'),table=el('table'),head=el('thead'),hr=el('tr'),body=el('tbody');['资产标识 / 名称','类型 / 模型','成本价格','服务地址','KEY','状态','操作'].forEach(t=>hr.append(el('th',t)));head.append(hr);table.append(head,body);scroll.append(table);section.append(scroll);
 const form=el('form',undefined,'ua-form');form.hidden=true;form.noValidate=true;const title=el('h3','新增资产');form.append(title);const fields={};
 function input(name,label,placeholder,type='text'){const l=el('label',label),x=el(type==='textarea'?'textarea':'input');x.name=name;x.placeholder=placeholder||'';if(type!=='textarea')x.type=type;x.autocomplete='off';l.append(x);form.append(l);fields[name]=x;return x;}
 function select(name,label,items){const l=el('label',label),x=el('select');for(const [value,text] of items){const o=el('option',text);o.value=value;x.append(o);}l.append(x);form.append(l);fields[name]=x;return x;}
 input('id','资产标识（后续指令引用）','例如 product-search');fields.id.required=true;fields.id.pattern='[a-z][a-z0-9_-]{2,63}';input('name','资产名称','例如 商品数据服务');select('kind','资产类型',[['general','通用'],['data','数据查询'],['image','图片生成'],['vision','图片分析'],['text','文本模型']]);input('base_url','服务基础地址（HTTPS，不含KEY）','https://api.example.com/v1','url');input('docs_url','文档地址（可选）','https://example.com/docs','url');input('model','模型或资源名（可选）','按供应商文档填写');select('auth_type','认证方式',[['bearer','Bearer Token'],['header','自定义认证头'],['none','无需KEY']]);input('auth_header','认证头名称（自定义时填写）','X-API-Key 或 X-RapidAPI-Key');const secret=input('secret','KEY / Token（更新时留空保留原KEY）','只填KEY本身，不含Bearer前缀','password');secret.maxLength=8192;secret.spellcheck=false;input('notes','备注（勿填写密钥）','用途、额度或待接入说明','textarea');const enabled=input('enabled','允许后续服务引用此资产','','checkbox');enabled.checked=false;
 fields.name.required=true;fields.base_url.required=true;
 const feedback=el('p','','ua-feedback');feedback.setAttribute('role','alert');feedback.setAttribute('aria-live','assertive');feedback.hidden=true;form.append(feedback);
 const actions=el('div',undefined,'ua-controls'),save=el('button','保存资产'),cancel=el('button','取消');save.type='submit';cancel.type='button';actions.append(save,cancel);form.append(actions,el('p','保存不会测试连通性或消耗供应商额度。启用仅允许服务端引用配置，不代表业务已经接入；实际调用需完成对应适配、权限和用量保护。'));section.append(form);
 const docs=el('details'),summary=el('summary','后续开发如何引用');docs.append(summary,el('p','直接给开发指令：“使用上游资产 product-search，实现某项功能。”服务端通过统一资产注册表按标识读取配置，Skill与浏览器只调用网站的业务入口，不取得供应商KEY。不同服务的请求格式与计费规则仍需按文档适配。'));section.append(docs);
 const audit=el('details'),auditTitle=el('summary','最近操作记录'),auditList=el('ul');audit.append(auditTitle,auditList);section.append(audit);overview.insertBefore(section,overview.querySelector('footer'));
 let active=false,editing=null,items=[],busy=false;
 function inform(message,error=false){status.textContent=message;feedback.textContent=message;feedback.hidden=false;feedback.classList.toggle('ua-error',error);}
 function invalid(field,message){inform(message,true);field.setAttribute('aria-invalid','true');field.focus();return false;}
 function validate(){
  for(const field of Object.values(fields))field.removeAttribute('aria-invalid');
  if(!/^[a-z][a-z0-9_-]{2,63}$/.test(fields.id.value.trim()))return invalid(fields.id,'资产标识需3–64位小写英文字母、数字、短横线或下划线，且以字母开头。例如 product-search。');
  if(!fields.name.value.trim()||fields.name.value.trim().length>100)return invalid(fields.name,'请填写资产名称，最多100字。');
  for(const [field,label,optional] of [[fields.base_url,'服务基础地址',false],[fields.docs_url,'文档地址',true]]){
   const value=field.value.trim();if(optional&&!value)continue;
   try{const u=new URL(value);if(u.protocol!=='https:'||!u.hostname||u.username||u.password||u.search||u.hash||(u.port&&u.port!=='443'))throw Error();}
   catch(_){return invalid(field,label+'请填写完整HTTPS地址，例如 https://api.example.com/v1；不要附带KEY或查询参数。');}
  }
  if(fields.auth_type.value==='header'&&!/^[A-Za-z][A-Za-z0-9-]{0,63}$/.test(fields.auth_header.value.trim()))return invalid(fields.auth_header,'请选择有效的认证头名称，例如 X-API-Key 或 X-RapidAPI-Key。');
  if(fields.auth_type.value!=='none'&&!secret.value&&!editing?.secret_configured)return invalid(secret,'请在KEY栏填写密钥；已保存的资产留空可保留原KEY。');
  if(secret.value&&!/^[!-~]{8,8192}$/.test(secret.value))return invalid(secret,'KEY需8–8192位字符，不含空格或换行，只填KEY本身。');
  return true;
 }

 async function api(path='',data){const r=await fetch('/ops/api/upstream-assets'+path,{credentials:'same-origin',cache:'no-store',method:data?'POST':'GET',headers:data?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(15000)});let d;try{d=await r.json();}catch(_){throw Error(r.status===429?'操作较频繁，请稍后再试。':'服务器暂未返回操作结果，请先刷新资产列表确认是否已保存。');}if(!r.ok){if(r.status===401){section.hidden=true;consolePanel.hidden=true;document.getElementById('login').hidden=false;}throw Error(typeof d.error==='string'?d.error:'资产操作暂未完成，请核对后重试。');}return d;}
 function edit(item){editing=item||null;form.reset();feedback.hidden=true;for(const field of Object.values(fields))field.removeAttribute('aria-invalid');fields.id.readOnly=!!item;title.textContent=item?'编辑资产 / 更新KEY':'新增资产';save.textContent='保存资产';for(const key of Object.keys(fields)){if(key==='secret'||key==='enabled')continue;fields[key].value=item?.[key]??(key==='kind'?'general':key==='auth_type'?'bearer':'');}fields.enabled.checked=!!item?.enabled;secret.value='';form.hidden=false;fields.name.focus();}
 async function load(){if(!active||consolePanel.hidden)return;status.textContent='正在读取资产…';try{const data=await api();if(!active||consolePanel.hidden)return;items=data.items;render();auditList.replaceChildren();for(const x of data.audit){auditList.append(el('li',new Date(x.created*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})+' · '+x.asset_id+' · '+({create:'新增',update:'更新',rotate_key:'更新KEY',archive:'归档'})[x.action]));}status.textContent='已读取 '+items.length+' 条资产 / 服务成本记录，完整KEY不回显。';
 }catch(e){status.textContent=e.message;}}
 function render(){body.replaceChildren();const query=search.value.trim().toLowerCase(),visible=items.filter(item=>(!kindFilter.value||item.kind===kindFilter.value)&&(!stateFilter.value||item.enabled===(stateFilter.value==='enabled'))&&[item.id,item.name,item.model,item.base_url].join(' ').toLowerCase().includes(query));count.textContent='共 '+items.length+' 项资产 · 当前显示 '+visible.length+' 项，点击详情查看配置。';
 for(const item of visible){const row=el('tr'),name=el('td',item.id);name.append(el('small',item.name));row.append(name);const kind=el('td',({general:'通用',data:'数据查询',image:'图片生成',vision:'图片分析',text:'文本模型',video:'视频生成'})[item.kind]);if(item.model)kind.append(el('small',item.model));row.append(kind,el('td',assetCostText(item.cost),'ua-cost'),el('td',item.base_url),el('td',item.secret_hint));const state=el('td',item.cost_only?(item.status_unknown?'状态暂未读取':item.enabled?'原服务已开放':'原服务未开放'):(item.enabled?'允许引用':'停用'));state.append(el('small',item.cost_only?'服务成本记录，KEY沿用原配置':'待业务适配'));row.append(state);const ops=el('td'),detail=el('details'),detailTitle=el('summary','详情'),detailInfo=el('div'),editButton=el('button','编辑 / 更新KEY'),toggle=el('button',item.enabled?'停用':'启用'),archive=el('button','归档');for(const b of [editButton,toggle,archive])b.type='button';editButton.onclick=()=>edit(item);toggle.onclick=async()=>{try{await api('/save',{...Object.fromEntries(['id','name','kind','base_url','docs_url','auth_type','auth_header','model','notes','revision'].map(k=>[k,item[k]])),enabled:!item.enabled,secret:''});await load();}catch(e){status.textContent=e.message;}};archive.onclick=async()=>{if(!confirm('归档资产 '+item.id+'？归档后停止提供给后续服务引用，历史记录保留。'))return;try{await api('/archive',{id:item.id,revision:item.revision});form.hidden=true;await load();}catch(e){status.textContent=e.message;}};detailInfo.append(el('p','认证方式：'+item.auth_type+(item.auth_header?' / '+item.auth_header:'')),el('p','文档：'+(item.docs_url||'未填写')),el('p','备注：'+(item.notes||'未填写')));detailInfo.prepend(el('p','成本价格：'+assetCostText(item.cost)));if(item.cost){detailInfo.append(el('p','计价依据：'+item.cost.basis),el('p',item.cost.notes));for(const x of item.cost.examples||[])detailInfo.append(el('p',x.label+' · '+x.duration_seconds+'秒成片成本：US$'+x.amount));}detail.append(detailTitle,detailInfo);if(!item.cost_only)detail.append(editButton,toggle,archive);ops.append(detail);row.append(ops);body.append(row);}
 if(!visible.length){const row=el('tr'),td=el('td',items.length?'没有符合筛选条件的资产。':'暂无新增资产，点击“新增资产”开始配置。');td.colSpan=7;row.append(td);body.append(row);}}
 search.oninput=render;kindFilter.onchange=render;stateFilter.onchange=render;
 menu.onclick=()=>{if(consolePanel.hidden)return;nav.querySelector('button[aria-label="用户管理"]')?.click();document.getElementById('users-directory')?.setAttribute('hidden','');document.getElementById('journey-v2')?.setAttribute('hidden','');document.querySelector('.workspace-legacy-users')?.setAttribute('hidden','');active=true;section.hidden=false;nav.querySelectorAll('[aria-current]').forEach(x=>x.removeAttribute('aria-current'));menu.setAttribute('aria-current','page');const h=consolePanel.querySelector('.heading h1');if(h)h.textContent='上游资产';load();};
 nav.addEventListener('click',e=>{if(e.target.closest('button')&&e.target.closest('button')!==menu){active=false;section.hidden=true;secret.value='';menu.removeAttribute('aria-current');}});
 create.onclick=()=>edit(null);refresh.onclick=load;cancel.onclick=()=>{secret.value='';form.hidden=true;};
 form.onsubmit=async e=>{e.preventDefault();if(busy||!validate())return;busy=true;save.disabled=true;cancel.disabled=true;save.textContent='正在保存…';inform('正在保存，请稍候…');const data={};for(const [key,value] of Object.entries(fields))data[key]=key==='enabled'?value.checked:key==='secret'?value.value:value.value.trim();data.revision=editing?.revision||0;try{const saved=await api('/save',data);secret.value='';editing=saved;fields.id.readOnly=true;search.value='';kindFilter.value='';stateFilter.value='';await load();inform('资产已保存。KEY已加密存入服务器；留空保存可保留原KEY。');title.textContent='编辑资产 / 更新KEY';save.textContent='已保存，再次保存';}catch(e){const uncertain=['TimeoutError','AbortError','TypeError'].includes(e.name);inform(uncertain?'保存请求未完成，可能已保存。请先点击“刷新资产”确认，再决定是否重试。':e.message,true);}finally{busy=false;save.disabled=false;cancel.disabled=false;if(save.textContent==='正在保存…')save.textContent='保存资产';}};
 new MutationObserver(()=>{if(consolePanel.hidden){active=false;section.hidden=true;secret.value='';body.replaceChildren();}}).observe(consolePanel,{attributes:true,attributeFilter:['hidden']});
});
