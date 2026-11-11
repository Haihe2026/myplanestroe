(() => {
  'use strict';
  const q = new URLSearchParams(location.hash.slice(1));
  const allowed = ['gemini', 'temu', 'pet', 'trade-leads'];
  let product = q.get('product') || (location.pathname.includes('/pet/') ? 'pet' : location.pathname.includes('/temu/') ? 'temu' : 'gemini');
  if (!allowed.includes(product)) product = 'gemini';
  const entry = q.get('entry'), code = q.get('code');
  const notice = document.querySelector('#notice'), start = document.querySelector('#start');
  const recovery = '请回到原 Skill 说『继续』获取新链接。';
  let timer, deadline = 0, attempt = null, errors = 0, stopped = false;

  function fail(message) {
    clearTimeout(timer);
    notice.textContent = message + ' ' + recovery;
    start.disabled = false;
  }

  function goToPayment(data) {
    const target = new URL(data.url, location.origin);
    const paths = ['/membership/', '/membership/gemini/', '/membership/temu/', '/membership/pet/'];
    if (target.origin !== location.origin || target.username || target.password ||
        (!paths.includes(target.pathname) && !(target.pathname === '/pay' && target.searchParams.get('skill') === 'trade-leads'))) {
      throw Error('付费页面地址无效');
    }
    clearTimeout(timer);
    document.querySelector('#scan').hidden = true;
    start.disabled = true;
    notice.textContent = '账户已确认，正在进入付费页面…';
    location.replace(target.href);
  }

  async function call(route, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 14000);
    try {
      const response = await fetch('/platform-api/wechat/' + route, {
        method: 'POST', credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
        headers: { 'Content-Type': 'application/json', 'X-Membership-Request': '1' },
        body: JSON.stringify(body)
      });
      let data;
      try { data = await response.json(); }
      catch (_) { const error = Error('暂时无法读取关联进度'); error.retryable = true; throw error; }
      if (!response.ok) {
        const error = Error(typeof data.error === 'string' ? data.error : '账户关联未完成');
        error.retryable = response.status === 429 || response.status >= 500;
        throw error;
      }
      return data;
    } finally { clearTimeout(timeout); }
  }

  const ticket = q.get('ticket');
  const accountReady = ticket ? (async () => {
    if (!/^[A-Za-z0-9_-]{43}$/.test(ticket)) throw Error('账户链接已过期');
    const response = await fetch('/platform-api/' + product + '/membership-api/redeem', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Membership-Request': '1' },
      body: JSON.stringify({ ticket })
    });
    if (!response.ok) throw Error('账户链接已过期');
    q.delete('ticket');
    history.replaceState(null, '', location.pathname + '#' + q.toString());
  })() : Promise.resolve();
  accountReady.catch(error => fail(error.message));

  async function poll() {
    const active = attempt;
    if (stopped || !active) return;
    if (Date.now() > deadline) { fail('二维码已过期。'); return; }
    try {
      const data = await call('finish', active);
      if (stopped || attempt !== active) return;
      if (data.status === 'linked') { goToPayment(data); return; }
      if (data.status !== 'pending') throw Error('账户关联进度未能确认');
      errors = 0;
    } catch (error) {
      if (stopped || attempt !== active) return;
      errors += 1;
      const transient = error.retryable === true || error.name === 'AbortError' || error instanceof TypeError;
      if (!transient || errors >= 3 || Date.now() > deadline) { fail(error.message); return; }
      notice.textContent = '暂时未能读取关联进度，正在重新查询。 ' + recovery;
    }
    timer = setTimeout(poll, 3500);
  }

  start.onclick = async () => {
    if (!document.querySelector('#accepted').checked) { notice.textContent = '请先阅读并同意账户绑定。'; return; }
    clearTimeout(timer);
    attempt = null; errors = 0; stopped = false; start.disabled = true;
    notice.textContent = '正在准备微信二维码…';
    try {
      await accountReady;
      const data = await call('start', { product, entry, code, accepted: true });
      if (stopped) return;
      if (data.status === 'linked') { goToPayment(data); return; }
      attempt = { state: data.state, verifier: data.verifier, code };
      deadline = Date.now() + data.expires_in * 1000;
      document.querySelector('#qr').src = data.url;
      document.querySelector('#fallback').href = data.url;
      document.querySelector('#scan').hidden = false;
      notice.textContent = '请使用手机微信扫码，并在微信中确认。';
      timer = setTimeout(poll, 3500);
    } catch (error) { fail(error.message); }
  };
  fetch('/platform-api/wechat/status', { credentials: 'same-origin', cache: 'no-store' })
    .then(response => response.json()).then(data => {
      if (data.wechat_bound && !attempt && !start.disabled) {
        start.textContent = '继续使用已绑定账户';
        notice.textContent = '已记住你的微信绑定账户，无需重复扫码。';
      }
    }).catch(() => {});
  window.addEventListener('pagehide', () => { stopped = true; clearTimeout(timer); });
})();
