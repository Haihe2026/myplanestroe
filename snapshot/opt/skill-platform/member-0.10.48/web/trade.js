(async()=>{
 const $=id=>document.getElementById(id),q=new URLSearchParams(location.search),skill=q.get('skill')||'trade-leads';
 if(skill==='pet'){location.replace('/membership/pet/');return}
 if(skill!=='trade-leads'){$('message').textContent='请从当前技能的充值入口继续。';return}
 const api=async(path,body)=>{const r=await fetch('/platform-api/trade-leads/web'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Membership-Request':'1'}:{},body:body?JSON.stringify(body):undefined,cache:'no-store'});const d=await r.json();if(!r.ok)throw Error(d.error?.message||'账户读取失败');return d};
 let order=null,timer=null;
 try{
  const account=await api('/account');
  if(location.pathname==='/link'){
   $('title').textContent='关联外贸获客账户';$('link').hidden=false;
   $('account-label').textContent=account.remembered?'检测到你已有账户：'+account.account_label:'请使用已关联账户的浏览器继续，或在下方关联当前账户。';
   $('new-account').hidden=account.remembered;$('message').textContent='确认关联后，回到 WorkBuddy 对话里说“继续”。';
   $('approve').onclick=async()=>{try{const d=await api('/approve',{code:q.get('code'),accepted:$('accepted').checked,new_account:$('create').checked});$('message').textContent='关联成功，回到 WorkBuddy 对话里说“继续”即可接着整理。';$('approve').disabled=true}catch(e){$('message').textContent='请稍后刷新页面，或联系客服协助完成当前操作。'}};
  }else{
   $('pay').hidden=false;if(account.price_list){const p=account.price_list;$('price-note').textContent=`搜索 ¥${(p.search/100).toFixed(2)} / 次 · 公司档案 ¥${(p.company/100).toFixed(2)} / 家 · 采购联系人 ¥${(p.contact/100).toFixed(2)} / 位\n${account.daily_free_trial>0?'每天免费搜索 '+account.daily_free_trial+' 次。':''}只为有效结果付费：没搜到公司、没有公司档案、没找到联系人，都不扣钱。`;}$('message').textContent=account.remembered?account.account_label:'请先在 WorkBuddy 中使用「外贸获客」并关联账户，关联后回到此页即可充值。';$('balance').textContent='¥'+(account.balance_fen/100).toFixed(2);
   for(const amount of account.tiers){const b=document.createElement('button');b.className='tier-choice';const meta=(account.tier_details||[]).find(x=>x.amount_fen===amount);const name=document.createElement('span'),price=document.createElement('strong'),description=document.createElement('small'),credit=document.createElement('small');name.textContent=meta?.name||'充值套餐';price.textContent='¥'+(amount/100).toFixed(2);description.textContent=meta?.description||'用于外贸获客的搜索和整理。';credit.textContent='到账余额 ¥'+(amount/100).toFixed(2);b.append(name,price,description,credit);b.disabled=!account.remembered;b.onclick=async()=>{b.disabled=true;try{order=await api('/orders',{amount_fen:amount});$('order').hidden=false;$('order-label').textContent='订单 '+order.id+' · 应付 ¥'+(order.amount_fen/100).toFixed(2);$('message').textContent='请按订单金额扫码支付，等待人工核款。';$('reported').disabled=order.status==='paid';if(timer)clearInterval(timer);timer=setInterval(check,5000)}catch(e){$('message').textContent='请稍后刷新页面，或联系客服协助完成当前操作。'}finally{b.disabled=false}};$('tiers').append(b)}
   async function check(){try{const d=await api('/orders/'+order.id);if(d.status==='paid'){clearInterval(timer);$('message').textContent='充值成功，回到 WorkBuddy 对话里说『继续』即可接着整理。';$('reported').disabled=true;const a=await api('/account');$('balance').textContent='¥'+(a.balance_fen/100).toFixed(2)}}catch(e){$('message').textContent='请稍后刷新页面，或联系客服协助完成当前操作。'}}
   $('reported').onclick=async()=>{try{await api('/report-payment',{order_id:order.id});$('message').textContent='付款信息已提交，确认到账后余额会自动更新。';await check()}catch(e){$('message').textContent='请稍后刷新页面，或联系客服协助完成当前操作。'}};
  }
 }catch(e){$('message').textContent='请稍后刷新页面，或联系客服协助完成当前操作。'}
})();
