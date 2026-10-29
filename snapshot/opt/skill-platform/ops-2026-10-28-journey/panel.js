'use strict';

(() => {

  const consolePanel = document.getElementById('console');

  if (!consolePanel) return;

  const node = (tag, text, cls) => {

    const el = document.createElement(tag);

    if (text !== undefined) el.textContent = String(text);

    if (cls) el.className = cls;

    return el;

  };

  const section = node('section'); section.id = 'journey-v2';

  const sourceNames = {'gemini-image-assistant':'Gemini生图器', 'amazon-image-assistant':'亚马逊生图',

    'temu-image-master':'Temu商家生图', 'shein-image-assistant':'SHEIN生图', 'shopee-image-assistant':'Shopee生图',

    'shopify-image-assistant':'Shopify生图', 'independent-site-image-assistant':'独立站生图',

    'tiktokshop-image-assistant':'TikTok Shop生图', 'facebook-image-assistant':'Facebook生图',

    'pinterest-image-assistant':'Pinterest生图', 'ebay-image-assistant':'eBay生图',

    'etsy-image-assistant':'Etsy生图', 'wayfair-image-assistant':'Wayfair生图', unknown:'来源未记录'};

  const sourceName = value => sourceNames[value] || String(value || '来源未记录');

  const keyName = key => ({issued:'已签发', revoked:'已停用', not_issued:'未签发'}[key.state] || '状态未知') +

    (key.mask ? ' ' + key.mask : '') + (key.state === 'not_issued' ? '' : key.bound ? ' · 已绑定' : ' · 未绑定');

  section.setAttribute('aria-label', '来源与真实旅程');

  section.append(node('h2', '来源与真实旅程'));

  section.append(node('p', '按周期展示阶段量，非同批次转化漏斗。来源为客户端声明或本次邀请会话关联，不代表认证。unknown 不反推；邀请创建不代表用户看见引导。充值页统计已关联账户的可验证进入，匿名访问未采集。'));

  const controls = node('div', undefined, 'j-controls');

  function check(label, checked) {

    const el = node('label'), input = node('input'); input.type = 'checkbox'; input.checked = checked;

    el.append(input, document.createTextNode(label)); controls.append(el); return input;

  }

  const excludeUnknown = check('排除 unknown 来源', false);

  const excludeAccounts = check('排除明确标记测试账户', true);

  const excludeOrders = check('排除已标记测试订单', true);

  const refresh = node('button', '↻', 'j-icon'); refresh.type = 'button'; refresh.title = '刷新旅程数据';

  refresh.setAttribute('aria-label', '刷新旅程数据'); controls.append(refresh); section.append(controls);

  const status = node('p', '', 'j-status'); status.setAttribute('role', 'status'); section.append(status);

  const coverage = node('p'); section.append(coverage);

  function table(headers) {

    const wrap = node('div', undefined, 'j-scroll'), tbl = node('table'), head = node('thead'), row = node('tr'), body = node('tbody');

    headers.forEach(text => row.append(node('th', text))); head.append(row); tbl.append(head, body); wrap.append(tbl); section.append(wrap); return body;

  }

  const stages = table(['Skill 来源', '渠道', '服务入口', '邀请数', '引导页邀请数', '充值页账户', '关联账户', '报付款订单', '成功出图账户', '回访账户', '周期建单', '周期到账']);

  section.append(node('h3', '匿名账户'));

  const searchForm = node('form', undefined, 'j-controls'), search = node('input');

  search.type = 'search'; search.maxLength = 64; search.placeholder = '匿名账户编号'; search.setAttribute('aria-label', '查询匿名账户');

  const submit = node('button', '查询账户'); submit.type = 'submit'; searchForm.append(search, submit); section.append(searchForm);

  const accounts = table(['匿名 ID', '首次记录来源', '可用次数 / 共享 / 专用', '最近认证请求', 'Key 状态', '测试账户']);

  const pager = node('div', undefined, 'j-controls'), prev = node('button', '←', 'j-icon'), next = node('button', '→', 'j-icon'), pageLabel = node('span');

  for (const [el, title] of [[prev, '上一页账户'], [next, '下一页账户']]) { el.type = 'button'; el.title = title; el.setAttribute('aria-label', title); }

  pager.append(prev, pageLabel, next); section.append(pager);

  const modal = node('div', undefined, 'j-account-page'); modal.hidden = true;

  const modalHead = node('div', undefined, 'j-account-head');

  const modalTitle = node('h2', '用户详情'); modalTitle.tabIndex = -1;

  const closeButton = node('button', '← 返回列表'); closeButton.type = 'button';

  closeButton.setAttribute('aria-label', '返回原列表');

  modalHead.append(closeButton, modalTitle);

  const detail = node('div', undefined, 'j-detail');

  modal.append(modalHead, detail); section.append(modal);

  function openDetail() {

    document.dispatchEvent(new CustomEvent('ops:account-open'));

    modal.hidden = false; modalTitle.focus({preventScroll:true});

  }

  function dismissModal() {

    detailRevision++; selected = null; modal.hidden = true; detail.replaceChildren();

    document.dispatchEvent(new CustomEvent('ops:account-close'));

  }

  closeButton.addEventListener('click', dismissModal);

  (document.getElementById('ops-overview') || consolePanel).append(section);

  let page = 1, revision = 0, selected = null, detailRevision = 0;

  const when = value => value === null || value === undefined ? '未知 / 未采集' : new Date(value * 1000).toLocaleString('zh-CN', {timeZone:'Asia/Shanghai', hour12:false});

  const labels = {invitation_created:'邀请创建', registration_page_entered:'引导页实际进入', recharge_page_entered:'充值页实际进入', account_linked:'网页账户关联成功', order_created:'订单创建', payment_reported:'用户报付款（未到账）', image_succeeded:'成功出图观察', return_visit:'回访观察', activity:'认证活动观察'};

  async function read(path, options) {

    const res = await fetch('/ops/api/journey-v2/' + path, {credentials:'same-origin', cache:'no-store', signal:AbortSignal.timeout(15000), ...options});

    if (res.status === 401) {

      clear(); const error = Error('请登录后台后查看旅程'); error.unauthorized = true; throw error;

    }

    if (!res.ok) throw Error('旅程数据缺失或暂不可用');

    return res.json();

  }

  function clear() { revision++; detailRevision++; selected = null; stages.replaceChildren(); accounts.replaceChildren(); clearDetail(); coverage.textContent = ''; refresh.disabled = false; status.textContent = '请登录后台后查看旅程'; }

  function clearDetail() { detailRevision++; selected = null; detail.replaceChildren(); if (!modal.hidden) dismissModal(); }

  function cells(body, values) { const row = node('tr'); values.forEach(value => row.append(node('td', value ?? '未知'))); body.append(row); return row; }

  async function load() {

    if (consolePanel.hidden) return;

    const rev = ++revision; refresh.disabled = true; status.textContent = '正在读取…';

    const days = document.getElementById('days')?.value || '7';

    const q = new URLSearchParams({days, exclude_unknown:excludeUnknown.checked ? '1' : '0', exclude_test_accounts:excludeAccounts.checked ? '1' : '0', exclude_test_orders:excludeOrders.checked ? '1' : '0'});

    try {

      const summary = await read('summary?' + q);

      const users = await read('users?' + new URLSearchParams({page:String(page), q:search.value}));

      if (rev !== revision || consolePanel.hidden) return;

      stages.replaceChildren();

      for (const g of summary.groups) {

        const s = g.stages;

        const row = cells(stages, [sourceName(g.source), g.channel, g.gateway_product, s.invitation_created || 0, s.registration_page_entered || 0, s.recharge_page_entered || 0, s.account_linked || 0, s.payment_reported || 0, s.image_succeeded || 0, s.return_visit || 0, g.orders_created, g.orders_paid]);

        row.firstChild.title = g.source;

      }

      accounts.replaceChildren();

      for (const u of users.users) {

        const quota = u.quota;

        const row = cells(accounts, ['', sourceName(u.first_observed_source), 'Gemini ' + (quota.available.gemini ?? '缺失') + ' / Temu ' + (quota.available.temu ?? '缺失') + '；共享 ' + quota.shared + '；旧 Gemini ' + (quota.legacy.gemini ?? '缺失') + ' / Temu ' + (quota.legacy.temu ?? '缺失') + '；Temu体验 ' + quota.temu_trial, when(u.last_active), keyName(u.key), u.test_account ? '明确标记' : '未标记']);

        row.children[1].title = u.first_observed_source;

        const choose = node('button', u.id); choose.type = 'button'; choose.className = 'j-id'; choose.addEventListener('click', () => showUser(u.id)); row.firstChild.append(choose);

      }

      pageLabel.textContent = page + ' / ' + Math.max(1, Math.ceil(users.total / users.page_size));

      prev.disabled = page === 1; next.disabled = page * users.page_size >= users.total;

      coverage.textContent = '采集起点：' + when(Number(summary.collection.collection_started)) + '。各阶段可能缺失；历史任务无成功时刻。剔除：未知事件 ' + summary.exclusions.unknown_events + '、测试账户事件 ' + summary.exclusions.test_account_events + '、测试订单 ' + summary.exclusions.test_orders + '。' + (summary.truncated ? '已截断，最多 ' + summary.limit + ' 条，非完整统计。' : '');

      status.textContent = summary.groups.length ? '更新于 ' + when(summary.generated_at) : '当前范围暂无可验证记录';

    } catch (error) {

      if (rev === revision && !consolePanel.hidden) { stages.replaceChildren(); accounts.replaceChildren(); clearDetail(); status.textContent = error.message; }

    } finally { if (rev === revision) refresh.disabled = false; }

  }

  async function showUser(uid) {

    selected = uid; const rev = ++detailRevision;

    openDetail(); detail.scrollTop = 0; detail.replaceChildren(node('p', '正在读取账户…'));

    try {

      const u = await read('user?' + new URLSearchParams({uid}));

      if (rev !== detailRevision || consolePanel.hidden) return;

      detail.replaceChildren(node('h3', '账户 ' + u.id));

      const quotaCards = node('div', undefined, 'j-quota-cards');

      for (const [label, value] of [['共享次数', u.quota.shared], ['Gemini 可用次数', u.quota.available?.gemini], ['Temu 可用次数', u.quota.available?.temu], ['共享库成功任务', u.historical_succeeded_jobs]]) {

        const card = node('article'); card.append(node('span', label), node('strong', value ?? '未采集')); quotaCards.append(card);

      }

      detail.append(quotaCards);
      detail.append(node('h3','首次对话（Skill上报）'));
      detail.append(node('p','仅记录事件元数据。服务器接收时间可核验，客户端时间为自报；不含用户原话。'));
      if(u.first_dialogues_unavailable) detail.append(node('p','首次对话记录暂时无法读取，请稍后重试。'));
      else if(!(u.first_dialogues||[]).length) detail.append(node('p','尚无首轮上报记录。Skill需要升级接入后才会出现此事件。'));
      else {
        const wrap=node('div',undefined,'j-scroll'),table=node('table'),head=node('tr');
        ['Skill / 渠道','首次对话 · 服务端接收','客户端自报时间','版本'].forEach(label=>head.append(node('th',label)));table.append(head);
        for(const item of u.first_dialogues){const row=node('tr');[item.skill_name+' / '+({workbuddy_skill:'WorkBuddy技能',workbuddy_expert:'WorkBuddy专家',skillhub:'SkillHub'})[item.channel],when(item.received_at),when(item.client_occurred_at),item.skill_version||'未记录'].forEach(value=>row.append(node('td',value)));table.append(row);}wrap.append(table);detail.append(wrap);
      }


      const dl = node('dl');

      for (const [name, value] of [['首次记录来源', sourceName(u.first_observed_source)], ['来源依据', u.source_evidence], ['首次观察', when(u.first_observed_at)], ['最近认证请求', when(u.last_active)], ['Key 状态', keyName(u.key)], ['共享库成功任务数', u.historical_succeeded_jobs], ['最早新成功观察', when(u.first_success_observed_at)]]) dl.append(node('dt', name), node('dd', value));

      dl.children[1].title = u.first_observed_source;

      detail.append(dl, node('p', '首次记录来源不代表历史激活来源。最近认证请求可能含自动轮询。已到账仅投影权威 paid + paid_at。历史 succeeded 只有创建时间；成功时刻未知。'));

      if (u.quota.missing.length) detail.append(node('p', '次数数据缺失：' + u.quota.missing.join('、')));

      if (Object.values(u.truncated).some(Boolean)) detail.append(node('p', '记录已截断：任务/订单各最多100条、事件最多200条。'));

      const markLabel = node('label'), markCheck = node('input'); markCheck.type = 'checkbox'; markLabel.append(markCheck, document.createTextNode(u.test_account ? '确认移除此账户的测试标记' : '确认整个账户仅用于测试（不由测试订单推断）'));

      const mark = node('button', u.test_account ? '移除测试账户标记' : '标记测试账户'); mark.type = 'button'; mark.disabled = true;

      markCheck.addEventListener('change', () => { mark.disabled = !markCheck.checked; });

      mark.addEventListener('click', async () => {

        mark.disabled = true;

        try {

          await read('test-account', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({uid, marked:!u.test_account, confirmed:true})});

          if (rev !== detailRevision || consolePanel.hidden) return;

          await showUser(uid); await load();

        } catch (error) { if (rev === detailRevision && !consolePanel.hidden) { status.textContent = error.message; mark.disabled = !markCheck.checked; } }

      });

      const marks = node('div', undefined, 'j-controls'); marks.append(markLabel, mark); detail.append(marks);

      function detailTable(title, headers, rows) {

        detail.append(node('h3', title)); const scroll = node('div', undefined, 'j-scroll'), tbl = node('table'), head = node('thead'), tr = node('tr'), body = node('tbody');

        headers.forEach(h => tr.append(node('th', h))); head.append(tr); rows.forEach(values => cells(body, values)); tbl.append(head, body); scroll.append(tbl); detail.append(scroll);

      }

      detailTable('订单时间轴', ['订单', 'Skill来源 / 渠道 / 服务入口', '创建', '状态', '报付款观察', '权威到账', '测试标记'], u.orders.map(o => [o.id, sourceName(o.source) + ' / ' + o.channel + ' / ' + o.gateway_product, when(o.created), o.status, when(o.reported_at), o.paid_authoritative ? when(o.paid_at) : '未核款到账', o.test_order ? '测试订单' : '未标记']));

      detailTable('任务流水', ['任务', '来源 / 渠道 / 服务入口', '创建', '状态', '成功观察', '完成时间'], u.jobs.map(j => [j.id, sourceName(j.source) + ' / ' + j.channel + ' / ' + (j.product || 'unknown'), when(j.created), j.status, when(j.success_observed_at), '未知']));

      detailTable('共享账本 / 预占与释放', ['记录', '任务', '时间', '类型', '次数变动'], u.ledger.map(l => [l.id, l.job_id || '—', when(l.created), l.kind, l.amount]));

      for (const [product, old] of Object.entries(u.legacy)) {

        if (!old.available) { detail.append(node('p', product + ' 旧库记录缺失，未合并为零。')); continue; }

        detail.append(node('p', '旧库 ' + product + '：成功 ' + (old.job_counts.succeeded || 0) + ' / 预占 ' + (old.job_counts.pending || 0) + '；来源未采集、完成时间未知。' + (Object.values(old.truncated).some(Boolean) ? '各类最多100条，已截断。' : '')));

        detailTable(product + ' 旧库任务', ['任务', '创建', '状态', '完成时间'], old.jobs.map(j => [j.id, when(j.created), j.status, '未知']));

        detailTable(product + ' 旧库账本 / 预占与释放', ['记录', '任务', '时间', '类型', '次数变动'], old.ledger.map(l => [l.id, l.job_id || '—', when(l.created), l.kind, l.amount]));

      }

      detailTable('事件记录', ['服务端观察时间', '节点', '来源 / 渠道 / 服务入口'], u.events.map(e => [when(e.created), labels[e.event] || e.event, sourceName(e.source) + ' / ' + e.channel + ' / ' + e.product]));

    } catch (error) { if (rev === detailRevision && !consolePanel.hidden) detail.replaceChildren(node('p', error.message)); }

  }

  document.addEventListener('ops:show-user', event => { if (!consolePanel.hidden && typeof event.detail?.uid === 'string') showUser(event.detail.uid); });

  refresh.addEventListener('click', load);

  document.getElementById('days')?.addEventListener('change', () => { clearDetail(); load(); });

  for (const input of [excludeUnknown, excludeAccounts, excludeOrders]) input.addEventListener('change', () => { clearDetail(); load(); });

  searchForm.addEventListener('submit', event => { event.preventDefault(); clearDetail(); page = 1; load(); });

  prev.addEventListener('click', () => { if (page > 1) { clearDetail(); page--; load(); } });

  next.addEventListener('click', () => { clearDetail(); page++; load(); });

  new MutationObserver(() => {

    if (consolePanel.hidden) clear(); else load();

  }).observe(consolePanel, {attributes:true, attributeFilter:['hidden']});

  setupWorkspace();

  if (!consolePanel.hidden) load();

  function setupWorkspace() {

    const feedbackSection = Array.from(consolePanel.children).find(el => el.tagName === 'SECTION' && el.querySelector('h2')?.textContent === 'Temu企业体验与反馈');

    const overview = document.getElementById('ops-overview');

    if (!overview) return;

    const traffic = node('div'), userList = node('div');

    const children = Array.from(section.children); const split = children.findIndex(el => el.tagName === 'H3');

    children.forEach((el, i) => { if (el !== modal) (i < split ? traffic : userList).append(el); });

    section.prepend(traffic, userList);

    const ordersSection = document.getElementById('orders')?.closest('section');

    const oldUsers = document.getElementById('accounts')?.closest('section');

    const oldUsersWrap = node('details', undefined, 'workspace-legacy-users');

    const oldUsersSummary = node('summary', '其他产品账户与历史记录查询');

    oldUsersWrap.append(oldUsersSummary); if (oldUsers) oldUsersWrap.append(oldUsers);

    overview.append(oldUsersWrap);

    const foot = overview.querySelector('footer'); if (foot) overview.append(foot);

    const metrics = overview.querySelector('.metrics');

    const productSection = document.getElementById('products')?.closest('section');

    const requestSection = document.getElementById('requests')?.closest('section');

    const heading = overview.querySelector('.heading');

    const headingText = heading?.querySelector('h1');

    if (heading) consolePanel.prepend(heading);

    for (const id of ['refresh-status', 'updated']) {

      const el = document.getElementById(id); if (el) consolePanel.insertBefore(id === 'updated' ? el.parentElement : el, overview);

    }

    const oldNavigation = consolePanel.querySelector('.ops-views'); if (oldNavigation) oldNavigation.hidden = true;

    const aside = node('aside', undefined, 'workspace-sidebar');

    const brand = node('a', undefined, 'workspace-brand'); brand.href = '/ops/';

    const logo = node('img'); logo.src = '/ops/logo.svg'; logo.alt = ''; logo.width = logo.height = 32;

    brand.append(logo, node('strong', 'MyPlaneStore', 'nav-label')); aside.append(brand);

    const toggle = node('button', undefined, 'workspace-toggle'); toggle.type = 'button';

    const toggleIcon = node('span', '☰'); toggleIcon.setAttribute('aria-hidden', 'true');

    toggle.append(toggleIcon, node('span', '收起菜单', 'nav-label')); aside.append(toggle);

    const nav = node('nav'); nav.setAttribute('aria-label', '管理工作区'); aside.append(nav);

    const definitions = [['overview','◫','工作区总览'],['orders','▤','订单与核款'],['users','♙','用户管理'],['traffic','↗','来源与旅程'],['channels','⇩','渠道下载'],['requests','≋','请求与渠道'],['feedback','☏','企业体验反馈']];

    const menuButtons = new Map();

    let active = 'overview', returnView = 'users', returnScroll = 0, returnFocus = null;

    function saveCollapse(value) { try { localStorage.setItem('mps-ops-menu-collapsed', String(value)); } catch (_) {} }

    let collapsed = window.innerWidth < 800;

    try { const saved = localStorage.getItem('mps-ops-menu-collapsed'); if (saved !== null) collapsed = saved === 'true'; } catch (_) {}

    function applyCollapse() {

      document.body.classList.toggle('workspace-collapsed', collapsed);

      toggle.setAttribute('aria-expanded', String(!collapsed));

      toggle.setAttribute('aria-label', collapsed ? '展开菜单' : '收起菜单');

      toggle.title = collapsed ? '展开菜单' : '收起菜单';

    }

    toggle.addEventListener('click', () => { collapsed = !collapsed; saveCollapse(collapsed); applyCollapse(); }); applyCollapse();

    function navigate(view, preserveScroll = false) {

      active = view; const channels = view === 'channels';

      document.getElementById(channels ? 'ops-channels-tab' : 'ops-overview-tab')?.click();

      for (const [key, button] of menuButtons) {

        const selected = key === view || (view === 'account' && key === 'users');

        if (selected) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');

      }

      if (headingText) headingText.textContent = view === 'account' ? '用户详情' : definitions.find(item => item[0] === view)?.[2] || '工作区总览';

      for (const [el, show] of [[feedbackSection,view==='feedback'],[ordersSection,view==='orders'],[oldUsersWrap,view==='users'],[oldUsers,view==='users'],[metrics,view==='overview'],[productSection,view==='overview'],[requestSection,view==='requests'],[section,['users','traffic','account'].includes(view)],[traffic,view==='traffic'],[userList,view==='users'],[modal,view==='account']]) if (el) el.hidden = !show;

      document.body.dataset.workspaceView = view;

      if (!preserveScroll) window.scrollTo({top:0,behavior:'instant'});

    }

    for (const [key, iconText, label] of definitions) {

      const button = node('button'); button.type = 'button'; button.title = label; button.setAttribute('aria-label',label);

      const icon = node('span',iconText,'nav-icon'); icon.setAttribute('aria-hidden','true');

      button.append(icon,node('span',label,'nav-label')); button.addEventListener('click', () => {

        if (active === 'account') { detailRevision++; selected = null; detail.replaceChildren(); }

        navigate(key);

      }); nav.append(button); menuButtons.set(key, button);

    }

    document.body.prepend(aside);

    document.addEventListener('ops:account-open', () => {

      if (active !== 'account') { returnView = active; returnScroll = window.scrollY; returnFocus = document.activeElement; }

      navigate('account');

    });

    document.addEventListener('ops:account-close', () => {

      if (active !== 'account') return;

      navigate(returnView, true); window.scrollTo({top:returnScroll,behavior:'instant'});

      if (returnFocus?.isConnected) returnFocus.focus({preventScroll:true});

    });

    function syncLogin() {

      document.body.classList.toggle('workspace-active', !consolePanel.hidden);

      aside.hidden = consolePanel.hidden;

      if (consolePanel.hidden) { active = 'overview'; modal.hidden = true; }

      else navigate(active);

    }

    new MutationObserver(syncLogin).observe(consolePanel,{attributes:true,attributeFilter:['hidden']});

    syncLogin();

  }



})();

