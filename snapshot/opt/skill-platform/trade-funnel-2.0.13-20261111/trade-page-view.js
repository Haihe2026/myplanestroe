(() => {
  'use strict';
  const endpoint = '/platform-api/telemetry/v2/trade-page-view';
  const sent = new Set();
  function optedOut() {
    if (navigator.doNotTrack === '1' || window.MYPLANE_TELEMETRY_DISABLED === true) return true;
    try { return localStorage.getItem('mps-telemetry-disabled') === '1'; }
    catch (_) { return true; }
  }
  function record(body) {
    if (optedOut() || sent.has(body.page)) return;
    sent.add(body.page);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1200);
    // A failed measurement never delays login or payment, and is not retried.
    fetch(endpoint, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store', keepalive: true,
      signal: controller.signal,
      headers: {'Content-Type': 'application/json', 'X-Membership-Request': '1'},
      body: JSON.stringify(body)
    }).catch(() => {}).finally(() => clearTimeout(timer));
  }
  const args = new URLSearchParams(location.hash.slice(1));
  if (['/auth/wechat/', '/auth/wechat/index.html'].includes(location.pathname) &&
      args.get('product') === 'trade-leads' && /^[A-Z2-9]{8}$/.test(args.get('code') || '')) {
    record({page: 'skill-activate', code: args.get('code')});
  }
  // The payment script emits this only after the original authenticated account
  // endpoint succeeds. Loading a pay page or clicking a package alone is not L4.
  window.addEventListener('mps:trade-account-ready', event => {
    if (event.detail?.remembered !== true) return;
    const query = new URLSearchParams(location.search);
    if ((location.pathname === '/pay' && (query.get('skill') || 'trade-leads') === 'trade-leads') ||
        ['/membership/trade-leads/', '/membership/trade-leads/trade.html'].includes(location.pathname)) {
      record({page: 'recharge'});
    }
  });
})();
