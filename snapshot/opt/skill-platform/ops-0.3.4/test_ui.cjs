const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {spawn}=require('node:child_process');const path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const child=spawn('C:/Users/Administrator/AppData/Local/Programs/Python/Python312/python.exe',[path.join(__dirname,'service/ui_fixture.py')],{windowsHide:true});
 let browser;
 try{
  await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>reject(Error('Fixture start timeout')),10000);child.once('error',reject);child.once('exit',code=>reject(Error('Fixture exit '+code)));child.stdout.on('data',chunk=>{if(chunk.toString().includes('READY')){clearTimeout(timeout);resolve();}});child.stderr.on('data',chunk=>process.stderr.write(chunk));});
  browser=await chromium.launch({headless:true,channel:'msedge'});const context=await browser.newContext();const page=await context.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(e.message));const base='http://127.0.0.1:18890';
  await page.goto(base+'/ops/');await page.fill('#password','synthetic-password-for-local-test-only');await page.click('#login-form button');
  const target='a'.repeat(32);await page.locator('[data-settle="'+target+'"]').waitFor();
  await page.locator('[data-settle="'+target+'"]').click();await page.locator('#settlement[open]').waitFor();
  for(const [label,width,height] of [['desktop',1440,1000],['mobile',390,844],['small',320,740]]){
   await page.setViewportSize({width,height});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   assert(await page.locator('#settlement').evaluate(el=>el.scrollWidth<=el.clientWidth));
   await page.screenshot({path:path.join(__dirname,'settle-'+label+'.png')});
  }
  await page.fill('#settlement-amount','48');await page.fill('#settlement-transaction','REDACTED_FOR_HANDOFF');await page.check('#settlement-verified');
  await page.click('#settlement-submit');assert.match(await page.locator('#settlement-error').innerText(),/金额不一致/);
  await page.fill('#settlement-amount','49');const start=Date.now();await page.click('#settlement-submit');
  await page.locator('#settlement[open]').waitFor({state:'hidden'});await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('57,000'));
  const elapsed=Date.now()-start;assert(elapsed<10000);
  assert.equal(await page.locator('[data-settle="'+target+'"]').count(),0);
  await page.selectOption('#order-status','paid');await page.locator('[data-order-id="'+target+'"]').waitFor();
  const response=await context.request.post(base+'/ops/api/settle',{headers:{Origin:base},data:{product:'gemini',order_id:target,amount_fen:4900,transaction_id:'REDACTED_FOR_HANDOFF',verified:true}});
  const retry=await response.json();assert.equal(retry.credited,false);assert.equal(retry.balance_points,57000);
  let calls=0;page.on('request',r=>{if(r.url().includes('/ops/api/orders?'))calls++;});await page.clock.install();
  const next=page.waitForResponse(r=>r.url().includes('/ops/api/orders?'));await page.clock.fastForward(16000);await next;assert(calls>0);
  await page.uncheck('#auto-refresh');const before=calls;await page.clock.fastForward(16000);assert.equal(calls,before);
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'ui-validation.json'),JSON.stringify({synthetic_only:true,real_credits_modified:false,confirm_elapsed_ms:elapsed,amount_mismatch_blocked:true,retry_idempotent:true,auto_refresh:true,viewports:[1440,390,320],page_errors:errors},null,2));
  console.log('PASS: local synthetic browser confirmation, amount validation, retry, balance, polling, 3 viewports. Elapsed '+elapsed+'ms.');
 }finally{if(browser)await browser.close();child.kill();await new Promise(resolve=>{if(child.exitCode!==null)resolve();else child.once('exit',resolve);});}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
