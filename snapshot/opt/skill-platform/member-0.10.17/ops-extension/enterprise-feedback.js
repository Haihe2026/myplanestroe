'use strict';
(() => {
  const root=document.getElementById('console');if(!root)return;
  const section=document.createElement('section');const title=document.createElement('h2');title.textContent='Temu企业体验与反馈';section.append(title);
  const button=document.createElement('button');button.type='button';button.textContent='查看企业反馈';section.append(button);
  const output=document.createElement('div');section.append(output);root.append(section);
  const names={product_identity:'商品还原',background:'背景',composition:'构图',detail:'细节',workflow:'流程体验',other:'其他'};
  function table(headings,rows){const wrap=document.createElement('div');wrap.className='table-wrap';const t=document.createElement('table');const head=t.createTHead().insertRow();for(const h of headings){const th=document.createElement('th');th.textContent=h;head.append(th);}const body=t.createTBody();for(const row of rows){const tr=body.insertRow();for(const value of row){const td=tr.insertCell();td.textContent=String(value);}}wrap.append(t);return wrap;}
  button.addEventListener('click',async()=>{
    button.disabled=true;output.textContent='正在读取…';
    try{const response=await fetch('/ops/api/enterprise-feedback',{cache:'no-store'});const data=await response.json();if(!response.ok)throw new Error(data.error||'读取失败');output.replaceChildren();
      const stats=document.createElement('p');stats.textContent=Object.entries(data.totals).map(([key,n])=>(names[key]||key)+' '+n+'条').join(' · ')||'暂无客户反馈';output.append(stats);
      output.append(table(['账户','体验已用/3','待核查'],data.trials.map(r=>[r.user_id,r.used,r.pending])));
      output.append(table(['账户','对应图片','分类','客户原话','时间'],data.items.map(r=>[r.user_id,r.job_id,names[r.category]||r.category,r.body,new Date(r.created*1000).toLocaleString('zh-CN')])));
    }catch(error){output.textContent=error.message;}finally{button.disabled=false;}
  });
})();
