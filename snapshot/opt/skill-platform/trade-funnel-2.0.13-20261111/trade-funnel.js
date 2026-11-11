(() => {
  'use strict';
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = String(text);
    if (cls) node.className = cls;
    return node;
  };
  const num = value => Number.isSafeInteger(value) && value >= 0 ? value.toLocaleString('zh-CN') : '未采集';
  const stamp = value => {
    if (!Number.isFinite(value)) return '未记录';
    return new Date(value * 1000).toLocaleString('zh-CN', {timeZone: 'Asia/Shanghai', hour12: false});
  };
  function mount() {
    const parent = document.getElementById('journey-v2');
    const consolePanel = document.getElementById('console');
    if (!parent || !consolePanel || document.getElementById('trade-funnel')) return;
    const section = el('section', undefined, 'tf-panel'); section.id = 'trade-funnel';
    section.append(el('h2', '外贸获客转化漏斗'));
    section.append(el('p', '从首次对话到首充到账；关联采用本站微信扫码流程。', 'tf-subtitle'));
    const form = el('form', undefined, 'tf-range');
    const start = el('input'), end = el('input');
    start.type = end.type = 'date'; start.setAttribute('aria-label', '开始日期'); end.setAttribute('aria-label', '结束日期');
    const submit = el('button', '查看日期范围'); submit.type = 'submit';
    const reset = el('button', '跟随顶部统计周期'); reset.type = 'button';
    form.append(el('label', '北京日期：'), start, el('span', '至'), end, submit, reset);
    const status = el('p', undefined, 'tf-status'); status.setAttribute('role', 'status');
    const cards = el('div', undefined, 'tf-stages');
    const metrics = el('div', undefined, 'tf-metrics');
    const note = el('div', undefined, 'tf-notes');
    const detail = el('div', undefined, 'tf-detail'); detail.hidden = true;
    section.append(form, status, cards, metrics, note, detail); parent.append(section);
    let query = null, revision = 0, detailRevision = 0, loading = false, loaded = false;
    let stage = null, page = 1;
    const active = () => !consolePanel.hidden && document.body.dataset.workspaceView === 'traffic';
    const params = () => new URLSearchParams(query || {days: document.getElementById('days')?.value || '7'});
    async function get(path, values) {
      const response = await fetch(path + '?' + values, {
        credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(12000)
      });
      if (response.status === 401) throw Error('请登录后台后查看外贸旅程。');
      if (!response.ok) throw Error('外贸旅程暂未读取成功，请点击顶部刷新重试。');
      return response.json();
    }
    async function load() {
      if (!active() || loading) return;
      const rev = ++revision; loading = true; loaded = false;
      status.textContent = '正在读取外贸转化旅程…'; cards.replaceChildren(); metrics.replaceChildren(); note.replaceChildren();
      stage = null; detailRevision++; detail.hidden = true; detail.replaceChildren();
      try {
        const data = await get('/ops/api/trade-funnel', params());
        if (rev !== revision || !active()) return;
        if (data.contract !== 'trade-funnel-v1' || !Array.isArray(data.stages)) throw Error('外贸旅程格式暂不匹配，请刷新后重试。');
        for (const item of data.stages) {
          const card = el('button', undefined, 'tf-stage'); card.type = 'button';
          card.append(el('span', item.id + ' · ' + item.label), el('strong', item.available ? num(item.count) : '未采集'), el('small', item.basis || ''));
          card.disabled = !item.available;
          card.addEventListener('click', () => { stage = item.id; page = 1; loadItems(); });
          cards.append(card);
        }
        const opens = data.skill_first_opens || {}, activations = data.skill_activations || {}, recharges = data.recharge_entries || {};
        const extras = [
          ['技能启用数', num(opens.total), '新设备 ' + num(opens.new_machine) + ' · 老设备 ' + num(opens.existing_machine)],
          ['技能激活数', num(activations.total), '新账户 ' + num(activations.new_account) + ' · 已有账户 ' + num(activations.existing_account)],
          ['全量充值入账', num(recharges.total) + ' 笔', Number.isSafeInteger(recharges.amount_fen) ? '¥' + (recharges.amount_fen / 100).toFixed(2) : '金额未采集']
        ];
        for (const [title, value, caption] of extras) {
          const box = el('article'); box.append(el('span', title), el('strong', value), el('small', caption)); metrics.append(box);
        }
        for (const text of data.limitations || []) note.append(el('p', text));
        note.append(el('p', '首次对话可在“用户与额度”查看；匿名记录完成关联后续接到账户旅程。点击阶段可查看实际记录。'));
        const windowText = data.window?.mode === 'calendar' || data.window?.since ? (data.window.since || '') + ' 至 ' + (data.window.until || '') + '（北京日期）' : '跟随顶部统计周期';
        status.textContent = windowText + ' · 更新于 ' + stamp(data.generated_at);
        loaded = true;
      } catch (error) {
        if (rev === revision) status.textContent = error.message;
      } finally { loading = false; }
    }
    async function loadItems() {
      const rev = ++detailRevision, current = stage;
      if (!current || !/^L[0-5]$/.test(current)) return;
      detail.hidden = false; detail.replaceChildren(el('h3', current + ' 阶段记录'), el('p', '正在读取…'));
      try {
        const p = params(); p.set('stage', current); p.set('page', String(page));
        const data = await get('/ops/api/trade-funnel/items', p);
        if (rev !== detailRevision || !active()) return;
        detail.replaceChildren(el('h3', current + ' 阶段记录'));
        if (!Array.isArray(data.items)) throw Error('阶段记录暂未读取成功。');
        if (!data.items.length) { detail.append(el('p', '当前范围暂无记录。')); return; }
        const wrap = el('div', undefined, 'tf-table-wrap'), table = el('table'), thead = el('thead'), tbody = el('tbody'), header = el('tr');
        for (const title of ['发生时间（北京）', '账户 / 匿名记录', '来源技能', '渠道']) header.append(el('th', title));
        thead.append(header); table.append(thead, tbody); wrap.append(table);
        for (const item of data.items) {
          const row = el('tr');
          for (const text of [stamp(item.occurred_at), item.user_id || item.event_id || item.id || '匿名记录', item.skill_code || '外贸获客', item.channel || '未记录']) row.append(el('td', text));
          tbody.append(row);
        }
        const pager = el('div', undefined, 'tf-pager'), previous = el('button', '上一页'), next = el('button', '下一页');
        previous.type = next.type = 'button'; previous.disabled = page <= 1;
        next.disabled = !Number.isSafeInteger(data.total) || page * (data.page_size || 50) >= data.total;
        previous.onclick = () => { page--; loadItems(); }; next.onclick = () => { page++; loadItems(); };
        pager.append(previous, el('span', '第 ' + page + ' 页 · ' + num(data.total) + ' 条'), next); detail.append(wrap, pager);
      } catch (error) { if (rev === detailRevision) detail.replaceChildren(el('p', error.message)); }
    }
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (!start.value || !end.value || start.value > end.value) { status.textContent = '请选择完整且顺序正确的开始、结束日期。'; return; }
      query = {since: start.value, until: end.value}; load();
    });
    reset.onclick = () => { query = null; start.value = end.value = ''; load(); };
    document.getElementById('days')?.addEventListener('change', () => { query = null; start.value = end.value = ''; load(); });
    document.getElementById('refresh')?.addEventListener('click', () => { load(); });
    const sync = () => { section.hidden = !active(); if (active() && !loaded && !loading) load(); };
    new MutationObserver(sync).observe(document.body, {attributes: true, attributeFilter: ['data-workspace-view']});
    new MutationObserver(sync).observe(consolePanel, {attributes: true, attributeFilter: ['hidden']});
    sync();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once: true});
  else mount();
})();
