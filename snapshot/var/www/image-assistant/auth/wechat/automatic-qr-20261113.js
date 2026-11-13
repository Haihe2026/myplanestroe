(() => {
  'use strict';
  const args = new URLSearchParams(location.hash.slice(1));
  const allowed = ['gemini', 'temu', 'pet', 'trade-leads', 'listing-optimizer'];
  let product = args.get('product') || (location.pathname.endsWith('/listing.html')?'listing-optimizer':'gemini');
  if (!allowed.includes(product) && !/^[a-z][a-z0-9_-]{2,63}$/.test(product)) product = 'gemini';
  const token = value => /^[A-Za-z0-9_-]{43}$/.test(value || '') ? value : null;
  if(product==='listing-optimizer'){
    const terms=document.createElement('a');terms.href='/membership/listing/terms/';terms.target='_blank';terms.rel='noopener';terms.textContent='交易条款';
    document.querySelector('label').append(document.createTextNode(' 同意'),terms,document.createTextNode('。'));
  }
  const entry = token(args.get('entry'));
  const code = /^[A-Z2-9]{8}$/.test(args.get('code') || '') ? args.get('code') : null;
  const accepted = document.querySelector('#accepted');
  const notice = document.querySelector('#notice');
  const scan = document.querySelector('#scan');
  let qr = document.querySelector('#qr');
  const retry = document.querySelector('#retry');
  let timer;
  let attempt = null;
  let generation = 0;
  let busy = false;
  let polling = false;
  let deadline = 0;
  let redirected = false;

  async function call(route, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 14000);
    try {
      const response = await fetch('/platform-api/wechat/' + route, {
        method: 'POST', credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
        headers: {'Content-Type': 'application/json', 'X-Membership-Request': '1'},
        body: JSON.stringify(body)
      });
      let data;
      try {
        data = await response.json();
      } catch (_) {
        const error = Error('暂时未能读取登录进度，请稍候重试。');
        error.status = 503;
        throw error;
      }
      if (!response.ok) {
        const error = Error(data.error || '暂时未能连接，请刷新二维码。');
        error.status = response.status;
        throw error;
      }
      return data;
    } finally {
      clearTimeout(timeout);
    }
  }

  const accountReady = (async () => {
    const ticket = token(args.get('ticket'));
    if (!ticket) return;
    try {
      // A used handoff must not prevent the user from making a fresh OAuth login.
      await fetch('/platform-api/' + product + '/membership-api/redeem', {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: {'Content-Type': 'application/json', 'X-Membership-Request': '1'},
        body: JSON.stringify({ticket}), signal: AbortSignal.timeout(10000)
      });
    } catch (_) {
      // The QR login can recover the existing account independently of the handoff.
    }
    args.delete('ticket');
    history.replaceState(null, '', location.pathname + '#' + args.toString());
  })();

  async function goToPayment(data) {
    const target = new URL(data.return_path === undefined ? data.url : data.return_path, location.origin);
    const paths = ['/membership/', '/membership/gemini/', '/membership/temu/', '/membership/pet/', '/membership/listing/'];
    const keys = [...target.searchParams.keys()];
    const trade = target.pathname === '/pay' && keys.length === 1 && keys[0] === 'skill' && target.searchParams.get('skill') === 'trade-leads';
    const queryAllowed = keys.length === 0 || (target.pathname === '/membership/listing/' && keys.length === 1 && keys[0] === 'skill' && /^[a-z][a-z0-9_-]{2,63}$/.test(target.searchParams.get('skill') || '')) || trade;
    if (target.origin !== location.origin || target.username || target.password || target.hash || !queryAllowed || (!paths.includes(target.pathname) && !trade)) {
      throw Error('付费页面暂未准备好，请刷新后重试。');
    }
    const back=args.get('return_to');
    if(back){
      const desired=new URL(back,location.origin);
      const aliases=['/membership/','/membership/gemini/'];
      if(desired.origin===location.origin&&!desired.username&&!desired.password&&
          (desired.pathname===target.pathname||(product==='gemini'&&aliases.includes(desired.pathname)&&aliases.includes(target.pathname)))){
        target.pathname=desired.pathname;
        if (product === 'listing-optimizer' && desired.pathname === '/membership/listing/' &&
            [...desired.searchParams.keys()].length <= 1 &&
            [...desired.searchParams.keys()].every(key => key === 'skill') &&
            (desired.searchParams.get('skill') === null || /^[a-z][a-z0-9_-]{2,63}$/.test(desired.searchParams.get('skill')))) {
          target.search=desired.search;
        }
      }
    }
    if(product==='listing-optimizer'){
      const response=await fetch('/platform-api/listing/v1/enroll',{
        method:'POST',credentials:'same-origin',cache:'no-store',
        headers:{'Content-Type':'application/json','X-Membership-Request':'1','Idempotency-Key':crypto.randomUUID()},
        body:JSON.stringify({accepted:true}),signal:AbortSignal.timeout(14000)
      });
      if(!response.ok)throw Error('账户确认暂未完成，请稍后重试。');
    }
    redirected = true;
    clearTimeout(timer);
    notice.textContent = '账户已确认，正在进入付费页面…';
    location.replace(target.href);
  }

  async function poll() {
    if (polling || !attempt || !accepted.checked || redirected) return;
    clearTimeout(timer);
    if (Date.now() >= deadline) {
      begin();
      return;
    }
    const current = generation;
    polling = true;
    try {
      const data = await call('finish', attempt);
      if (current !== generation || !accepted.checked) return;
      if (data.status === 'linked') {
        await goToPayment(data);
        return;
      }
      timer = setTimeout(poll, 1000);
    } catch (error) {
      if (current !== generation || !accepted.checked) return;
      if (error.status === 401) {
        attempt = null;
        notice.textContent = '正在更新二维码，请继续扫码。';
        timer = setTimeout(begin, 1000);
      } else {
        notice.textContent = error.message;
        retry.hidden = false;
        timer = setTimeout(poll, 2500);
      }
    } finally {
      polling = false;
    }
  }

  async function begin() {
    if (busy || !accepted.checked || redirected) return;
    busy = true;
    const current = ++generation;
    clearTimeout(timer);
    attempt = null;
    retry.disabled = true;
    notice.textContent = '正在准备微信二维码…';
    try {
      await accountReady;
      if (current !== generation || !accepted.checked) return;
      const request = {product, entry, code, accepted: true, force_scan: true};
      if (product === 'listing-optimizer') {
        const back = args.get('return_to');
        const desired = new URL(back || '/membership/listing/', location.origin);
        if (desired.origin === location.origin && desired.pathname === '/membership/listing/' &&
            !desired.username && !desired.password && !desired.hash &&
            [...desired.searchParams.keys()].every(key => key === 'skill') &&
            (desired.searchParams.get('skill') === null || /^[a-z][a-z0-9_-]{2,63}$/.test(desired.searchParams.get('skill')))) {
          request.return_path = desired.pathname + desired.search;
        } else request.return_path = '/membership/listing/';
      }
      const data = await call('start', request);
      if (current !== generation || !accepted.checked) return;
      if (data.status === 'linked') {
        await goToPayment(data);
        return;
      }
      if (!window.mpsWeChatQR) throw Error('二维码暂未准备好，请刷新重试。');
      qr = window.mpsWeChatQR.render(data, qr, document.querySelector('#fallback'));
      attempt = {state: data.state, verifier: data.verifier, code};
      deadline = Date.now() + Math.min(Number(data.expires_in), 300) * 1000;
      scan.hidden = false;
      retry.hidden = false;
      notice.textContent = '请使用手机微信扫码并确认，随后自动进入付费页面。';
      timer = setTimeout(poll, 1000);
    } catch (error) {
      if (current !== generation || !accepted.checked) return;
      notice.textContent = error.message;
      retry.hidden = false;
    } finally {
      busy = false;
      retry.disabled = false;
      if (current !== generation && accepted.checked && !attempt && !redirected) timer = setTimeout(begin, 0);
    }
  }

  accepted.addEventListener('change', () => {
    if (accepted.checked) {
      begin();
    } else {
      generation++;
      clearTimeout(timer);
      attempt = null;
      scan.hidden = true;
      qr.removeAttribute('src');
      retry.hidden = true;
      notice.textContent = '请先阅读并勾选账户绑定说明。';
    }
  });
  retry.addEventListener('click', begin);
  window.addEventListener('message', event => {
    if (event.origin === location.origin && event.data?.type === 'mps-wechat-approved') poll();
  });
  window.addEventListener('pageshow', () => {if (accepted.checked && !attempt) begin();});
  window.addEventListener('pagehide', () => {generation++; clearTimeout(timer);});
  if (accepted.checked) begin();
  else notice.textContent = '勾选同意后，微信二维码会自动显示。';
})();
