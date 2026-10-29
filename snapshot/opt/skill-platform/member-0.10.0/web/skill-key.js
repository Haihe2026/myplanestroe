'use strict';
(() => {
  const panel = document.createElement('section'); panel.id = 'skill-key-status'; panel.hidden = true;
  panel.innerHTML = '<div><strong>Gemini 专属 Key</strong><p id="skill-key-message">正在同步专属服务…</p></div><div><button id="skill-key-rotate" type="button" hidden>重新绑定</button><button id="skill-key-revoke" type="button" hidden>停用</button></div>';
  document.getElementById('member-update').after(panel);
  let revision = 0, busy = false;
  const el = id => document.getElementById(id);
  async function request(action) {
    const response = await fetch('/platform-api/gemini/membership-api/skill-key' + (action ? '/manage' : ''),
      {credentials:'same-origin', cache:'no-store', method:action?'POST':'GET',
        headers:action?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},
        body:action?JSON.stringify({action}):undefined});
    const data = await response.json(); if (!response.ok) throw Error(data.error || '专属服务正在同步'); return data;
  }
  function draw(data) {
    const ready = data.state === 'ready', revoked = data.state === 'revoked';
    panel.hidden = data.state === 'pending_payment';
    el('skill-key-message').textContent = ready ? '专属Key已开通，无需额外领取。' + (data.bound ? ' 已在Skill完成自动绑定。' : ' 返回Skill后自动绑定。') + ' 标识尾号 ' + data.fingerprint
      : revoked ? '专属Key已停用；重新绑定后，返回Skill即可自动更新。' : '专属服务正在同步，原次数已保留。';
    el('skill-key-rotate').hidden = !['ready','revoked'].includes(data.state);
    el('skill-key-revoke').hidden = !ready;
  }
  document.addEventListener('member-account-snapshot', event => {
    if (!busy) draw(event.detail.skill_key || {state:'pending_payment'});
  });
  document.addEventListener('image-account-ready', () => { revision++; busy=false; panel.hidden=true; el('skill-key-message').textContent='正在同步专属服务…'; el('skill-key-rotate').disabled=false;el('skill-key-revoke').disabled=false; });
  for (const action of ['rotate', 'revoke']) el('skill-key-' + action).addEventListener('click', async () => {
    if (busy || !confirm(action==='revoke' ? '停用后，该Key将停止生图。确认停用？' : '重新绑定会使原Key失效，返回Skill会自动更新。确认继续？')) return;
    busy=true; const version=revision;
    el('skill-key-rotate').disabled=true;el('skill-key-revoke').disabled=true;
    try { const data=await request(action); if(version===revision)draw(data); }
    catch(error){if(version===revision)el('skill-key-message').textContent=error.message;}
    finally {if(version===revision){busy=false;el('skill-key-rotate').disabled=false;el('skill-key-revoke').disabled=false;}}
  });
})();
