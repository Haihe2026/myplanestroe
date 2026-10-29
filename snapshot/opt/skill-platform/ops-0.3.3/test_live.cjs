const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const cfg=JSON.parse(fs.readFileSync('C:/Users/Administrator/Desktop/Skill项目/MyPlaneStore运营后台.private.json','utf8'));
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const context=await browser.newContext(),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const base='https://myplanestore.com';
  assert.equal((await context.request.get(base+'/ops/api/orders')).status(),401);
  await page.goto(base+'/ops/');await page.fill('#password',cfg.password);await page.click('#login-form button');
  const id='REDACTED_FOR_HANDOFF';
  const row=page.locator('[data-order-id="'+id+'"]');await row.waitFor();
  assert.match(await row.innerText(),/54,000/);assert.match(await row.innerText(),/49\.00/);assert.match(await row.innerText(),/待核款/);
  const data=await (await context.request.get(base+'/ops/api/orders?status=reported&q='+id)).json();
  assert.equal(data.total,1);assert.equal(data.orders[0].status,'reported');assert.equal(data.orders[0].paid_at,null);
  await page.fill('#order-search',id);await page.click('#order-find');await page.waitForFunction(()=>document.querySelector('#order-page').textContent.includes('1 笔订单'));
  await row.locator('button').click();await page.locator('#journey[open]').waitFor();
  assert.match(await page.locator('#journey-id').innerText(),/00000000-0000-4000-8000-000000000000/);
  await page.click('#close');
  for(const [label,width,height] of [['desktop',1440,1000],['mobile',390,844],['small',320,740]]){
   await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),label+' overflow');
   await page.screenshot({path:path.join(__dirname,'ops-'+label+'.png'),fullPage:true});
  }
  await page.selectOption('#order-status','paid');await page.waitForFunction(()=>document.querySelector('#order-page').textContent.includes('0 笔订单'));
  await page.click('#logout');await page.locator('#login-form').waitFor();
  assert.equal((await context.request.get(base+'/ops/api/orders')).status(),401);assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'live-validation.json'),JSON.stringify({tested_at:new Date().toISOString(),reported_order_visible:true,search:true,journey_link:true,paid_filter_excludes_reported:true,auth:true,viewports:[1440,390,320],page_errors:errors,payment_confirmed:false,credits_modified:false},null,2));
  console.log('PASS: live order visibility, search, linked journey, paid filter, authentication, 3 viewports. No payment or credits changed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
