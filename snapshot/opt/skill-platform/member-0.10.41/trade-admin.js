(()=>{
 const go=()=>{
  if(document.getElementById('trade-admin-open'))return;
  const btn=document.createElement('button');btn.id='trade-admin-open';btn.textContent='外贸获客 · 钱包与数据';btn.style.cssText='margin:8px;padding:10px;border:1px solid #167855;border-radius:8px;cursor:pointer';
  const host=document.querySelector('aside,nav,header')||document.body;host.append(btn);
  btn.onclick=async()=>{
   document.getElementById('trade-admin-dialog')?.remove();
   const dialog=document.createElement('dialog');dialog.id='trade-admin-dialog';dialog.style.cssText='width:min(1100px,92vw);max-height:88vh;overflow:auto;border:1px solid #bcd6cb;border-radius:12px;padding:24px';
   const close=document.createElement('button');close.textContent='关闭';close.onclick=()=>dialog.close();dialog.append(close);
   const h=document.createElement('h2');h.textContent='外贸获客管理';dialog.append(h);
   const p=document.createElement('p');p.textContent='加载中';dialog.append(p);document.body.append(dialog);dialog.showModal();
   dialog.onclick=e=>{const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()};
   try{
    const r=await fetch('/ops/api/trade-leads/summary',{cache:'no-store'});if(!r.ok)throw Error('请先登录管理后台');const d=await r.json();
    const q=d.quota;p.textContent=`本月已用 ${q?.local_used||0} / ${d.monthly_limit} credits；上游剩余 ${q?.remote_remaining??'待首个真实响应确认'}；映射失败 ${d.mapping_failures} 次`;
    if(q?.alerted)p.style.color='#bf2626';
    const note=document.createElement('p');note.textContent='报付款不代表到账。仅核对真实收款后发放；合成测试数据另行标记。公开信息整理，与 LinkedIn 无官方合作。';dialog.append(note);
    for(const o of d.orders){
     const row=document.createElement('div');row.style.cssText='display:flex;flex-wrap:wrap;gap:10px;padding:12px 0;border-bottom:1px solid #ddd';
     const label=document.createElement('span');label.textContent=`${o.is_test?'[测试] ':''}${o.id} · 账户 ${o.account_id.slice(0,8)} · ¥${(o.amount_fen/100).toFixed(2)} · ${o.status}`;row.append(label);
     if(o.status==='reported'){
      const settle=document.createElement('button');settle.textContent='核款到账';row.append(settle);
      settle.onclick=async()=>{const transaction_id=prompt('请输入已核对的收款流水（不填客户信息）');if(!transaction_id)return;if(!confirm(`已实际收到 ¥${(o.amount_fen/100).toFixed(2)}，确认入账？`))return;
       const result=await fetch('/ops/api/trade-leads/settle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order_id:o.id,amount_fen:o.amount_fen,transaction_id,verified:true})});const body=await result.json();if(!result.ok)return alert(body.error?.message||body.error||'请核对订单');settle.disabled=true;settle.textContent='已入账';};
     }dialog.append(row);
    }
    const fh=document.createElement('h3');fh.textContent='真实响应脱敏样例';dialog.append(fh);
    for(const f of d.fixtures){const b=document.createElement('button');b.textContent=f.endpoint+(f.mapping_failed?' · 映射失败':'');b.onclick=async()=>{const r=await fetch('/ops/api/trade-leads/fixtures/'+f.id);const pre=document.createElement('pre');pre.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere';pre.textContent=JSON.stringify(await r.json(),null,2);b.after(pre)};dialog.append(b)}
    const details=document.createElement('pre');details.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere';details.textContent=JSON.stringify({日收入_分:d.daily_revenue,日上游调用:d.daily_upstream,单次估算成本_USD:d.cost_per_call_usd,说明:d.profit_currency_note},null,2);dialog.append(details);
   }catch(e){p.textContent=e.message}
  };
 };document.readyState==='loading'?document.addEventListener('DOMContentLoaded',go):go();
})();
