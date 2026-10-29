'use strict';
(() => {
  const product = document.body.dataset.product;
  const byId = id => document.getElementById(id);
  const skillName = {gemini:'Gemini生图器',temu:'Temu图片大师',xhs:'XHS选题大师'}[product] || '当前技能';
  const names = {plus:'Plus', pro:'Pro', ultra:'Ultra', business:'终身会员',gemini_permanent_29:'Plus',gemini_permanent_39:'Pro',gemini_permanent_49:'Ultra',gemini_permanent_999:'终身会员',temu_enterprise_89:'企业入门',temu_enterprise_198:'企业成长',temu_enterprise_365:'企业批量'};
  const states = {pending:'待付款', reported:'待核款', paid:'已到账'};
  const storageKey = 'myplane-account-view-' + product;
  let revision = 0, timer, flight, focusedOrder = null, wanted = false;
  try { wanted = sessionStorage.getItem(storageKey) === 'yes'; } catch {}

  const panel = document.createElement('section');
  panel.id = 'member-account'; panel.hidden = true;
  panel.setAttribute('aria-labelledby', 'member-title');
  panel.innerHTML = `<div class="member-heading"><div><p class="member-kicker">MY ACCOUNT</p><h1 id="member-title">我的账户</h1><p id="member-label">正在关联账户…</p></div><button id="member-refresh" type="button" title="刷新账户" aria-label="刷新账户">↻</button></div>
    <div class="member-overview"><div><span>剩余使用次数</span><strong id="member-uses">—<small> 次</small></strong></div><div><span>最近订单</span><strong id="member-order-state">正在查询</strong><p id="member-order-detail"></p></div></div>
    <p id="member-update" role="status" aria-live="polite">正在获取账户数据…</p>
    <div class="member-section-title"><h2>我的订单</h2><span>最近20笔</span></div><div id="member-orders" aria-label="我的订单列表"></div>
    <div class="member-actions"><button id="member-recharge" type="button">选套餐充值</button><button id="member-more" type="button">更多账户功能</button></div>
    <p id="member-continue" class="member-continue">图片需求已保留，到账后回到原 Skill 对话继续制作。</p>`;
  document.querySelector('main').prepend(panel);

  function remember(value) {
    wanted = value;
    try { value ? sessionStorage.setItem(storageKey, 'yes') : sessionStorage.removeItem(storageKey); } catch {}
  }
  function stop() {
    clearTimeout(timer);
    if (flight) flight.controller.abort();
    flight = null;
  }
  function clear() {
    byId('member-title').textContent = '我的账户';
    byId('member-continue').textContent = '图片需求已保留，到账后回到原 Skill 对话继续制作。';
    byId('member-label').textContent = '正在关联账户…';
    byId('member-uses').textContent = '— 次';
    byId('member-order-state').textContent = '正在查询';
    delete byId('member-order-state').dataset.status;
    byId('member-order-detail').textContent = '';
    byId('member-orders').replaceChildren();
    byId('member-update').textContent = '正在获取账户数据…';
    delete byId('member-update').dataset.fresh;
    byId('member-refresh').disabled = false;
  }
  function mount() {
    for (const id of ['payment-dialog', 'tools-dialog', 'account-dialog']) {
      if (byId(id)?.open) byId(id).close();
    }
    const previous = byId('payment-return');
    if (previous) previous.hidden = true;
    document.body.classList.remove('payment-returning', 'payment-open');
    document.body.classList.add('member-account-open');
    panel.hidden = false;
  }
  function show(order) {
    if (typeof signedIn !== 'undefined' && !signedIn) { showAccountDialog(); return; }
    remember(true);
    if (order) focusedOrder = order.id;
    mount();
    byId('member-title').tabIndex = -1;
    byId('member-title').focus({preventScroll:true});
    refresh();
  }
  window.showMemberAccount = show;

  async function read(endpoint, signal) {
    const response = await fetch('/platform-api/' + product + '/membership-api/' + endpoint,
      {credentials:'same-origin', cache:'no-store', signal});
    const data = await response.json();
    if (!response.ok) { const error = Error(data.error || '账户连接暂不可用'); error.status = response.status; throw error; }
    return data;
  }
  function validOrder(order) {
    return order && /^[a-f0-9]{32}$/.test(order.id) && Object.hasOwn(states, order.status)
      && Object.hasOwn(names, order.plan) && Number.isSafeInteger(order.units) && order.units >= 0
      && Number.isSafeInteger(order.amount_fen) && order.amount_fen >= 0;
  }
  function draw(data, orders) {
    if (typeof data.label !== 'string' || !Number.isSafeInteger(data.remaining_uses) || data.remaining_uses < 0
      || !Array.isArray(orders.orders) || orders.orders.some(order => !validOrder(order))) throw Error('账户数据正在核对，请刷新。');
    byId('member-label').textContent = data.label;
    byId('member-uses').replaceChildren(document.createTextNode(data.remaining_uses.toLocaleString('zh-CN')));
    const unit = document.createElement('small'); unit.textContent = ' 次'; byId('member-uses').append(unit);
    // This response contains only the authenticated account's orders, never URL-supplied account IDs.
    const current = orders.orders.find(order => order.id === focusedOrder) || orders.orders[0];
    const paid = current?.status === 'paid';
    byId('member-title').textContent = paid ? '充值成功' : '我的账户';
    byId('member-continue').textContent = paid ? '无需领取、复制密钥或兑换码，回到原技能对话即可继续使用。' : '核款确认后，额度自动到账；届时回到原技能对话即可使用。';
    byId('member-order-state').textContent = current ? states[current.status] : '暂无订单';
    byId('member-order-state').dataset.status = current?.status || '';
    if (current) {
      focusedOrder = current.id;
      byId('member-order-detail').textContent = names[current.plan] + ' · ¥' + (current.amount_fen / 100).toFixed(2)
        + ' · ' + current.units.toLocaleString('zh-CN') + '次';
      panel.dataset.orderId = current.id; panel.dataset.paymentStatus = current.status;
    } else {
      byId('member-order-detail').textContent = '选好套餐，扫码核款后开始制作。';
      delete panel.dataset.orderId; delete panel.dataset.paymentStatus;
    }
    const list = byId('member-orders'); list.replaceChildren();
    for (const order of orders.orders) {
      const row = document.createElement('button'); row.type = 'button'; row.className = 'member-order';
      row.setAttribute('aria-label', names[order.plan] + '，' + states[order.status] + '，订单尾号' + order.id.slice(-8));
      const title = document.createElement('span'); title.className = 'member-order-name'; title.textContent = names[order.plan];
      const detail = document.createElement('small'); detail.textContent = '尾号 ' + order.id.slice(-8)
        + (order.expires_at ? ' · 有效至 ' + new Date(order.expires_at * 1000).toLocaleDateString('zh-CN') : order.status === 'paid' && !order.valid_days ? ' · 永久有效' : '');
      title.append(detail);
      const amount = document.createElement('span'); amount.textContent = '¥' + (order.amount_fen / 100).toFixed(2);
      const count = document.createElement('span'); count.textContent = order.units.toLocaleString('zh-CN') + '次';
      const state = document.createElement('span'); state.className = 'member-status'; state.dataset.status = order.status; state.textContent = states[order.status];
      row.append(title, amount, count, state);
      row.addEventListener('click', () => window.showPaymentOrder(order)); list.append(row);
    }
    if (!orders.orders.length) list.textContent = '暂无订单记录';
    const now = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
    byId('member-update').textContent = (current?.status === 'reported' ? '付款已登记，核款确认后预计1分钟内发放。'
      : current?.status === 'paid' ? '额度已到账，请回到「' + skillName + '」技能对话继续使用，无需额外领取。' : '账户已同步。') + ' 每10秒自动刷新 · ' + now;
    byId('member-update').dataset.fresh = 'yes';
    // Keep the checkout's hidden balance aligned without re-dispatching login events.
    byId('balance').textContent = data.remaining_uses.toLocaleString('zh-CN') + ' 次';
    byId('account').textContent = data.label;
    document.dispatchEvent(new CustomEvent('member-account-snapshot', {detail:{skill_key:data.skill_key}}));
  }
  async function refresh() {
    if (!wanted || panel.hidden || document.hidden || flight) return;
    clearTimeout(timer);
    const current = {revision, controller:new AbortController()}; flight = current;
    const timeout = setTimeout(() => current.controller.abort(), 8000);
    byId('member-refresh').disabled = true;
    try {
      const data = await read('account', current.controller.signal);
      const orders = await read('orders', current.controller.signal);
      if (revision !== current.revision || flight !== current || !wanted) return;
      draw(data, orders);
    } catch (error) {
      if (revision !== current.revision || flight !== current) return;
      if ([401, 403].includes(error.status)) {
        signedIn = false; updateBuy();
        document.dispatchEvent(new CustomEvent('image-account-ready', {detail:{signedIn:false}}));
        mount();
        byId('member-label').textContent = '请关联原账户';
        byId('member-order-state').textContent = '待关联';
        byId('member-update').textContent = '回到 Skill 说“我的账户”，打开新链接即可继续查看。';
        return;
      }
      byId('member-update').textContent = '本次刷新未完成，上方为上次查询结果。稍后自动重试，也可点击刷新。';
      byId('member-update').dataset.fresh = 'no';
    } finally {
      clearTimeout(timeout);
      if (flight === current) {
        flight = null; byId('member-refresh').disabled = false;
        if (wanted && !panel.hidden && !document.hidden) timer = setTimeout(refresh, 10000);
      }
    }
  }
  byId('member-refresh').addEventListener('click', refresh);
  byId('member-recharge').addEventListener('click', () => {
    remember(false); stop(); panel.hidden = true; document.body.classList.remove('member-account-open');
    byId('plans-panel').scrollIntoView({block:'nearest'});
  });
  byId('member-more').addEventListener('click', () => byId('tools-dialog').showModal());
  // Capture before the legacy account-tools handler opens its advanced-settings dialog.
  byId('account-tools').addEventListener('click', event => { event.stopImmediatePropagation(); show(); }, true);
  document.addEventListener('image-account-ready', event => {
    revision++; stop(); clear(); focusedOrder = null;
    delete panel.dataset.orderId; delete panel.dataset.paymentStatus;
    if (event.detail.signedIn) { if (wanted) { mount(); refresh(); } }
    else {
      byId('balance').textContent = '— 次';
      byId('account').textContent = '尚未关联账户';
      panel.hidden = true; document.body.classList.remove('member-account-open');
    }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); else refresh(); });
  window.addEventListener('pagehide', stop);
  window.addEventListener('pageshow', refresh);
  if (typeof signedIn !== 'undefined' && signedIn && wanted) { mount(); refresh(); }
})();
