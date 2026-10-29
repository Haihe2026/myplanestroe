'use strict';
(() => {
  const params = new URLSearchParams(location.hash.slice(1));
  let entry = params.get('entry');
  const registration = /\/membership\/(gemini|temu)\/register\//.test(location.pathname);
  const product = location.pathname.includes('/temu/') ? 'temu' : location.pathname.includes('/xhs/') ? 'xhs' : 'gemini';
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  const view = Array.from(bytes, x => x.toString(16).padStart(2, '0')).join('');
  let sent = false;
  async function observe(ready) {
    if (sent || document.visibilityState !== 'visible') return;
    if (registration ? !/^[A-Za-z0-9_-]{43}$/.test(entry || '') : !ready) return;
    if (!registration) {
      const plans = document.getElementById('plans-panel') || document.getElementById('plans');
      if (!plans || !plans.getClientRects().length || document.body.classList.contains('member-account-open')) return;
    }
    sent = true;
    const body = {page:registration ? 'registration' : 'recharge', view_id:view};
    if (registration) body.entry = entry;
    entry = null;
    try {
      await fetch('/platform-api/' + product + '/membership-api/journey-page', {
        method:'POST', credentials:'same-origin', cache:'no-store', keepalive:true, signal:AbortSignal.timeout(5000),
        headers:{'Content-Type':'application/json', 'X-Membership-Request':'1'}, body:JSON.stringify(body)
      });
    } catch {}
  }
  let authenticated = false;
  function currentAccount() {
    // Read only the registration script's existing in-memory entry. Never create a window cache.
    if (registration && !sent && !entry) {
      try { if (typeof invitation !== 'undefined' && /^[A-Za-z0-9_-]{43}$/.test(invitation || '')) entry = invitation; } catch {}
    }
    try { if (typeof signedIn !== 'undefined') authenticated = signedIn === true; } catch {}
    observe(authenticated);
  }
  document.addEventListener('image-account-ready', event => {
    authenticated = event.detail?.signedIn === true;
    observe(authenticated);
  });
  document.addEventListener('visibilitychange', () => observe(authenticated));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', currentAccount, {once:true});
  else currentAccount();
  const watchPage = () => {
    if (document.body) new MutationObserver(currentAccount).observe(document.body, {attributes:true, attributeFilter:['class']});
  };
  if (document.body) watchPage();
  else document.addEventListener('DOMContentLoaded', watchPage, {once:true});
})();
