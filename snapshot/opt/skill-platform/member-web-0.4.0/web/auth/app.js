const $ = id => document.getElementById(id);
let active = false, sent = false, busy = false, cooldown = 0;
function message(text) { $('message').textContent = text; }
function controls() {
  $('phone').disabled = !active || busy;
  $('code').disabled = !active || busy;
  $('accepted').disabled = !active || busy;
  $('send').disabled = !active || busy || cooldown > 0 || !$('accepted').checked;
  $('verify').disabled = !active || busy || !sent || !$('accepted').checked;
}
async function api(path, payload) {
  const response = await fetch('/phone-auth/' + path, {method:'POST', credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-Phone-Request':'1'}, body:JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '操作未完成，请稍后重试。');
  return result;
}
async function init() {
  const ticket = new URLSearchParams(location.hash.slice(1)).get('ticket');
  history.replaceState(null, '', location.pathname);
  try {
    const response = await fetch('/phone-auth/status', {cache:'no-store'});
    if (!response.ok) throw new Error('授权服务暂不可用。');
    const status = await response.json();
    if (!status.ready) { message('手机号验证即将开放。已有账户可回到 WorkBuddy 继续使用。'); return; }
    if (!ticket) { message('请在 WorkBuddy 对生图助手说“开通”，打开与你的账户关联的授权页面。'); return; }
    await api('redeem', {ticket}); active = true; message('请输入手机号并获取验证码。');
  } catch (error) { message(error.message); }
  controls();
}
$('accepted').addEventListener('change', controls);
$('phone').addEventListener('input', () => { sent = false; controls(); });
$('send').addEventListener('click', async () => {
  if (!active || busy || cooldown || !$('accepted').checked) return;
  if (!/^1[3-9][0-9]{9}$/.test($('phone').value.trim())) { message('请输入中国大陆11位手机号。'); return; }
  busy = true; controls();
  try {
    const result = await api('send', {phone:$('phone').value.trim(), accepted:true});
    sent = result.sent === true; cooldown = result.retry_after || 60;
    message('验证码已发送，5分钟内有效。');
    const timer = setInterval(() => { cooldown--; $('send').textContent = cooldown > 0 ? cooldown + '秒后重发' : '获取验证码'; controls(); if (!cooldown) clearInterval(timer); }, 1000);
  } catch (error) { message(error.message); }
  finally { busy = false; controls(); }
});
$('form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!sent || busy || !$('accepted').checked) return;
  busy = true; controls();
  try {
    const result = await api('verify', {code:$('code').value});
    if (!result.verified) throw new Error('验证尚未完成。');
    $('phone').value = ''; $('code').value = ''; active = false;
    $('form').hidden = true; $('success').hidden = false;
  } catch (error) { message(error.message); }
  finally { busy = false; controls(); }
});
$('copy').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText('已验证，继续刚才的图片'); $('copy').textContent = '已复制'; }
  catch { $('copy').textContent = '已验证，继续刚才的图片'; }
});
init();
