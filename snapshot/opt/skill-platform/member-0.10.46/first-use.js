 'use strict';
document.addEventListener('DOMContentLoaded',()=>{
 const el=(tag,text)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=String(text);return x;};
 const labels={gemini:'通用生图通道',temu:'Temu通道',pet:'宠物通道',skillhub:'SkillHub',workbuddy_skill:'WorkBuddy技能',workbuddy_expert:'WorkBuddy专家',unknown:'未识别', 'gemini-image-assistant':'Gemini生图器'};
 let seq=0;
 function draw(box,d){box.replaceChildren(el('h3','首用入口与账户关联'));
 const t=d.totals;box.append(el('p','所选周期：生成入口 '+t.entries+' 次 · 尚未关联 '+t.unlinked+' 条 · 已关联 '+t.linked+' 条 · 已关联账户 '+t.linked_accounts+' 个（去重）'));
 box.append(el('p','账户列表只显示已创建或关联的账户。用户在 Skill 中取得开通链接、但尚未开通，也会在此记录；重试或刷新链接可能产生多条入口，不代表不同用户。'));
 const wrap=el('div');wrap.style.cssText='overflow-x:auto;max-width:100%;min-width:0';const table=el('table'),head=el('thead'),row=el('tr'),body=el('tbody');['日期（北京时间）','技能来源','渠道','入口次数','尚未关联','已关联','已关联账户'].forEach(x=>row.append(el('th',x)));head.append(row);
 for(const r of d.rows){const tr=el('tr');[r.day,labels[r.source]||r.source,labels[r.channel]||r.channel,r.entries,r.unlinked,r.linked,r.linked_accounts].forEach(x=>tr.append(el('td',x)));body.append(tr);}
 if(!d.rows.length){const tr=el('tr'),td=el('td','当前周期暂无入口记录');td.colSpan=7;tr.append(td);body.append(tr);}table.append(head,body);wrap.append(table);box.append(wrap);
 box.append(el('p','仅统计服务器已生成的入口；下载、仅在宿主聊天、网络未到达、入口生成前失败均无法据此判断。已排除标记测试账户关联的 '+d.excluded_marked_test_entries+' 条记录；匿名测试记录无法识别。关联状态截至本次刷新，关联账户不等于新增注册。'));
 }
 async function load(){const revision=++seq;const hosts=[document.getElementById('users-directory'),document.getElementById('requests')?.closest('section')].filter(Boolean);if(!hosts.length||document.getElementById('console')?.hidden)return;
 try{const r=await fetch('/ops/api/first-use?days='+encodeURIComponent(document.getElementById('days')?.value||'7'),{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('首用入口记录暂未读取成功，请刷新重试');const d=await r.json();if(revision!==seq||document.getElementById('console')?.hidden)return;
 for(const [i,host] of hosts.entries()){const id='first-use-'+host.id;let box=document.getElementById(id);if(!box){box=el('section');box.id=id;box.style.cssText='margin:20px 0;padding:16px;border:1px solid #d9e6e0;border-radius:10px;min-width:0;max-width:100%';if(host.id==='users-directory')host.insertBefore(box,host.querySelector('form'));else host.insertBefore(box,host.querySelector('.table-wrap'));}draw(box,d);}
 }catch(e){document.querySelectorAll('[id^="first-use-"]').forEach(b=>b.replaceChildren(el('p',e.message)));}}
 document.addEventListener('channel-data-ready',()=>queueMicrotask(load));
 document.addEventListener('click',e=>{if(e.target.closest('button')?.textContent.trim()==='刷新额度')load();});
});
