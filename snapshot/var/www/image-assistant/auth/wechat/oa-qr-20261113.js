(() => {
  'use strict';
  const token = value => typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value);
  const error = () => Error('微信二维码暂未准备好，请刷新重试。');
  function officialUrl(value, kind, state) {
    if (typeof value !== 'string' || (kind === 'qr' && !value.startsWith('/platform-api/wechat/oa/qr?'))) throw error();
    if (kind === 'authorize' && !value.startsWith('https://www.myplanestore.com/platform-api/wechat/oa/authorize?')) throw error();
    let url;
    try { url = new URL(value, location.origin); } catch (_) { throw error(); }
    const origin = kind === 'qr' ? location.origin : 'https://www.myplanestore.com';
    const pathname = '/platform-api/wechat/oa/' + (kind === 'qr' ? 'qr' : 'authorize');
    const keys = [...url.searchParams.keys()].sort();
    if (url.origin !== origin || url.pathname !== pathname || url.username || url.password || url.hash ||
        keys.length !== 2 || keys[0] !== 'scan' || keys[1] !== 'state' ||
        !token(url.searchParams.get('scan')) || url.searchParams.get('state') !== state) throw error();
    return url;
  }
  function render(data, element, fallback) {
    if (!data || typeof data !== 'object' || !element || !fallback || !token(data.state) || !token(data.verifier) ||
        !Number.isFinite(Number(data.expires_in)) || Number(data.expires_in) <= 0) throw error();
    let source, target, tag;
    if (data.mode === 'official_account') {
      source = officialUrl(data.qr_url, 'qr', data.state);
      target = officialUrl(data.authorize_url, 'authorize', data.state);
      if (source.searchParams.get('scan') !== target.searchParams.get('scan')) throw error();
      tag = 'IMG';
    } else {
      if (data.mode && data.mode !== 'website') throw error();
      try { source = new URL(data.url); } catch (_) { throw error(); }
      if (source.origin !== 'https://open.weixin.qq.com' || source.pathname !== '/connect/qrconnect' ||
          source.username || source.password || source.searchParams.get('state') !== data.state) throw error();
      target = source;
      tag = 'IFRAME';
    }
    if (element.tagName !== tag) {
      const replacement = document.createElement(tag.toLowerCase());
      replacement.id = element.id;
      element.replaceWith(replacement);
      element = replacement;
    }
    element.referrerPolicy = 'no-referrer';
    if (tag === 'IMG') {
      element.className = 'mps-wechat-oa-qr';
      element.alt = '请用手机微信扫描，关联 MyPlaneStore 账户';
      element.width = 300;
      element.height = 300;
    } else {
      element.classList.remove('mps-wechat-oa-qr');
      element.title = '微信官方扫码登录';
    }
    element.src = source.href;
    const inWeChat = /MicroMessenger/i.test(navigator.userAgent);
    fallback.href = tag === 'IMG' && !inWeChat ? source.href : target.href;
    fallback.textContent = tag === 'IMG' ? (inWeChat ? '在微信中继续授权' : '单独打开微信二维码') : '单独打开微信扫码页';
    return element;
  }
  window.mpsWeChatQR = Object.freeze({render});
})();
