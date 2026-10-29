const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const cfg=JSON.parse(fs.readFileSync('C:/Users/Administrator/Desktop/Skill项目/MyPlaneStore运营后台.private.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const context=await browser.newContext(),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const base='https://myplanestore.com';await page.goto(base+'/ops/');await page.fill('#password',cfg.password);await page.click('#login-form button');await page.locator('#console:not([hidden])').waitFor();
  await page.selectOption('#order-status','all');await page.locator('[data-order-id]').first().waitFor();
  const data=await (await context.request.get(base+'/ops/api/orders?status=all')).json();assert(data.settlement_enabled);
  const id='REDACTED_FOR_HANDOFF';const paid=data.orders.find(o=>o.id===id);assert.equal(paid.status,'paid');
  assert.equal(await page.locator('[data-settle="'+id+'"]').count(),0);
  for(const [label,width,height] of [['desktop',1440,1000],['mobile',390,844],['small',320,740]]){
   await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   assert(await page.locator('.brand img').evaluate(img=>img.complete&&img.naturalWidth>0));
   await page.screenshot({path:path.join(__dirname,'live-'+label+'.png'),fullPage:true});
  }
  let preview=false;const button=page.locator('[data-settle]').first();
  if(await button.count()){
   await button.click();await page.locator('#settlement[open]').waitFor();
   assert.equal(await page.locator('#settlement-transaction').inputValue(),'');assert.equal(await page.locator('#settlement-verified').isChecked(),false);
   await page.screenshot({path:path.join(__dirname,'live-preview.png')});await page.click('#settlement-close');preview=true;
  }
  await page.clock.install();const next=page.waitForResponse(r=>r.url().includes('/ops/api/orders?'));await page.clock.fastForward(16000);await next;
  await page.click('#logout');await page.locator('#login-form').waitFor();assert.equal((await context.request.get(base+'/ops/api/order?id='+id)).status(),401);assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'live-validation.json'),JSON.stringify({tested_at:new Date().toISOString(),capability_enabled:true,paid_order_not_actionable:true,preview_tested:preview,polling:true,viewports:[1440,390,320],page_errors:errors,production_settlement_submitted:false},null,2));
  console.log('PASS: live capability, paid-order guard, preview, auto-refresh, logout and 3 viewports. No production settlement submitted.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
