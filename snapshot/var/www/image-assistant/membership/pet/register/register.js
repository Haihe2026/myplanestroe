'use strict';
const $=id=>document.getElementById(id),base='/platform-api/pet/membership-api/';
const ticket=new URLSearchParams(location.hash.slice(1)).get('entry');history.replaceState(null,'',location.pathname);
async function api(path,body){const r=await fetch(base+path,{credentials:'same-origin',cache:'no-store',method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||'操作未完成');return d;}
$('accepted').onchange=()=>{$('create').disabled=!$('accepted').checked;$('link').disabled=!$('accepted').checked;};$('link').disabled=true;
async function submit(route){if(!$('accepted').checked)return;try{$('create').disabled=true;$('link').disabled=true;await api(route,{ticket,accepted:true});$('status').textContent='账户已关联，请回到原宠物养护 Skill 继续；开通不等于已付款。';$('create').hidden=true;$('remembered').hidden=true;}catch(e){$('status').textContent=e.message;$('create').disabled=false;$('link').disabled=false;}}
$('create').onclick=()=>submit('confirm-entry');$('link').onclick=()=>submit('link-entry');$('forget').onclick=async()=>{try{await api('forget-device',{});$('remembered').hidden=true;}catch(e){$('status').textContent=e.message;}};
if(!ticket){$('status').textContent='请从原宠物养护 Skill 重新打开账户入口。';$('accepted').disabled=true;}else api('remembered').then(d=>{if(d.remembered){$('remembered').hidden=false;$('label').textContent=d.account_label;}}).catch(e=>$('status').textContent=e.message);
