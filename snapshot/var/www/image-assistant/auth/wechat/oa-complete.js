(() => {
  'use strict';
  const status = document.getElementById('complete-status');
  function destination(value) {
    if (typeof value !== 'string') throw Error('付费页面暂未准备好，请在原页面刷新关联进度。');
    const target = new URL(value, location.origin);
    const simple = ['/membership/', '/membership/gemini/', '/membership/temu/', '/membership/pet/'];
    const params = [...target.searchParams.keys()];
    const listing = target.pathname === '/membership/listing/' &&
      (params.length === 0 || (params.length === 1 && params[0] === 'skill' && /^[a-z][a-z0-9_-]{2,63}$/.test(target.searchParams.get('skill') || '')));
    const trade = target.pathname === '/pay' && params.length === 1 && params[0] === 'skill' && target.searchParams.get('skill') === 'trade-leads';
    if (target.origin !== location.origin || target.username || target.password || target.hash ||
        !(listing || trade || (simple.includes(target.pathname) && params.length === 0))) {
      throw Error('付费页面暂未准备好，请在原页面刷新关联进度。');
    }
    return target.href;
  }
  (async () => {
    const params = new URLSearchParams(location.hash.slice(1));
    const ticket = params.get('ticket');
    history.replaceState(null, '', location.pathname + location.search);
    if ([...params.keys()].length !== 1 || !/^[A-Za-z0-9_-]{43}$/.test(ticket || '')) {
      throw Error('本次关联链接已过期，请在原页面重新扫码。');
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 14000);
    let response, data;
    try {
      response = await fetch('/platform-api/wechat/oa/redeem', {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: {'Content-Type': 'application/json', 'X-Membership-Request': '1'},
        body: JSON.stringify({ticket}), signal: controller.signal
      });
      try { data = await response.json(); }
      catch (_) { throw Error('暂时无法确认关联结果，请在原页面刷新关联进度。'); }
    } finally {
      clearTimeout(timeout);
    }
    if (!response.ok || data.status !== 'linked') {
      throw Error(typeof data.error === 'string' ? data.error : '账户关联暂未完成，请在原页面重新扫码。');
    }
    const url = destination(data.return_path === undefined ? data.url : data.return_path);
    status.textContent = '账户已关联，正在进入付费页面…';
    location.replace(url);
  })().catch(error => {
    status.textContent = error.name === 'AbortError' || error instanceof TypeError ?
      '暂时未能确认关联结果，请在原页面刷新关联进度。' : error.message;
  });
})();
