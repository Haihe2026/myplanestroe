'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const script = fs.readFileSync(path.join(__dirname, '..', 'wechat.js'), 'utf8');

function page(finish = [], startData = null) {
  let clock = 1000000, nextId = 0;
  const timers = new Map(), listeners = {}, calls = [], navigation = [];
  const nodes = Object.fromEntries(['notice', 'start', 'accepted', 'scan', 'qr', 'fallback'].map(id => [id, { hidden: true, disabled: false, textContent: '' }]));
  nodes.accepted.checked = true;
  const response = (status, data) => ({ status, ok: status >= 200 && status < 300, json: async () => data });
  const location = {
    hash: '#product=gemini&entry=' + 'a'.repeat(43), pathname: '/auth/wechat/', origin: 'https://aistore.zhaopintong.com',
    replace: value => navigation.push(value)
  };
  const context = vm.createContext({
    URL, URLSearchParams, AbortController, TypeError, location,
    Date: class extends Date { static now() { return clock; } },
    history: { replaceState() {} },
    document: { querySelector: selector => nodes[selector.slice(1)] },
    window: { addEventListener: (name, fn) => { listeners[name] = fn; } },
    setTimeout(fn, delay) { const id = ++nextId; timers.set(id, { fn, delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
    async fetch(url, options = {}) {
      calls.push({ url, options });
      if (url.endsWith('/status')) return response(200, { wechat_bound: false });
      if (url.endsWith('/start')) return response(200, startData || { state: 's'.repeat(43), verifier: 'v'.repeat(43), expires_in: 900, url: 'https://open.weixin.qq.com/synthetic' });
      assert.ok(url.endsWith('/finish'), 'Unexpected network route');
      const next = finish.shift();
      assert.ok(next, 'No fake finish response available');
      if (next instanceof Error) throw next;
      return response(next.status || 200, next.data);
    }
  });
  vm.runInContext(script, context, { filename: 'wechat.js' });
  return {
    nodes, navigation, calls, listeners,
    async start() { await nodes.start.onclick(); },
    pending() { return [...timers.values()].filter(row => row.delay === 3500).length; },
    advance(seconds) { clock += seconds * 1000; },
    async poll() {
      const row = [...timers.entries()].find(([, row]) => row.delay === 3500);
      assert.ok(row, 'Polling was not scheduled');
      timers.delete(row[0]); await row[1].fn();
    }
  };
}

test('pending then linked navigates to the first-party payment page', async () => {
  const p = page([{ data: { status: 'pending' } }, { data: { status: 'linked', url: '/membership/gemini/' } }]);
  await p.start(); await p.poll(); assert.equal(p.pending(), 1); await p.poll();
  assert.deepEqual(p.navigation, ['https://aistore.zhaopintong.com/membership/gemini/']);
  assert.equal(p.pending(), 0);
  assert.ok(p.calls.filter(c => c.url.endsWith('/finish')).every(c => c.options.credentials === 'same-origin'));
});

for (const status of [401, 409]) {
  test('finish HTTP ' + status + ' shows the actual error and an explicit recovery action', async () => {
    const p = page([{ status, data: { error: status === 401 ? '原技能入口已过期' : '该微信已绑定其他账户' } }]);
    await p.start(); await p.poll();
    assert.match(p.nodes.notice.textContent, status === 401 ? /过期/ : /其他账户/);
    assert.match(p.nodes.notice.textContent, /回到原 Skill 说『继续』获取新链接/);
    assert.equal(p.nodes.start.disabled, false); assert.equal(p.pending(), 0);
  });
}

test('one transient network failure is visible and the same state is queried again', async () => {
  const p = page([new TypeError('模拟：断网'), { data: { status: 'linked', url: '/membership/gemini/' } }]);
  await p.start(); await p.poll();
  assert.match(p.nodes.notice.textContent, /重新查询/); assert.equal(p.pending(), 1);
  await p.poll();
  const requests = p.calls.filter(c => c.url.endsWith('/finish'));
  assert.equal(requests[0].options.body, requests[1].options.body);
  assert.equal(p.navigation.length, 1);
});

test('three consecutive transient errors stop visibly with recovery guidance', async () => {
  const p = page(Array.from({ length: 3 }, () => ({ status: 503, data: { error: '模拟：暂不可用' } })));
  await p.start(); for (let i = 0; i < 3; i++) await p.poll();
  assert.match(p.nodes.notice.textContent, /暂不可用.*回到原 Skill/);
  assert.equal(p.pending(), 0); assert.equal(p.nodes.start.disabled, false);
});

test('expired QR stops before another request and explains how to recover', async () => {
  const p = page(); await p.start(); p.advance(901); await p.poll();
  assert.match(p.nodes.notice.textContent, /二维码已过期.*回到原 Skill/);
  assert.equal(p.calls.filter(c => c.url.endsWith('/finish')).length, 0);
});

test('a malicious cross-origin payment URL is rejected', async () => {
  const p = page([{ data: { status: 'linked', url: 'https://evil.example/membership/gemini/' } }]);
  await p.start(); await p.poll();
  assert.equal(p.navigation.length, 0); assert.match(p.nodes.notice.textContent, /地址无效.*回到原 Skill/);
});

test('pagehide stops polling', async () => {
  const p = page(); await p.start(); p.listeners.pagehide();
  assert.equal(p.pending(), 0); assert.equal(p.navigation.length, 0);
});

test('an already-linked start goes straight to the validated payment page', async () => {
  const p = page([], { status: 'linked', url: '/membership/gemini/' });
  await p.start(); assert.equal(p.navigation.length, 1); assert.equal(p.pending(), 0);
});

test('explicit consent remains necessary before starting OAuth', async () => {
  const p = page(); p.nodes.accepted.checked = false; await p.start();
  assert.equal(p.calls.filter(c => c.url.endsWith('/start')).length, 0);
  assert.match(p.nodes.notice.textContent, /先阅读并同意/);
});
