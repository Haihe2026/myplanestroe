const fs=require('node:fs/promises');
const path=require('node:path');
const http=require('node:http');
const {chromium}=require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=__dirname;
const viewports=[{width:320,height:568},{width:375,height:667},{width:390,height:844},{width:412,height:915},{width:768,height:1024},{width:1024,height:640},{width:1440,height:900}];
const plans=[['plus','Plus',2900,32],['pro','Pro',3900,43],['ultra','Ultra',4900,54],['business','终身会员',99900,2000]].map(([id,name,price_fen,images])=>({id,name,price_fen,images,points:images*1000,period:id==='business'?'lifetime':'monthly'}));
(async()=>{
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://localhost');let filename;
    if(url.pathname.startsWith('/auth/'))filename=path.join(root,'web/auth',url.pathname.slice(6)||'index.html');
    else if(url.pathname.startsWith('/membership/')){
      const rel=url.pathname.slice(12);filename=url.pathname.endsWith('/')?path.join(root,'web',rel,'index.html'):path.join(root,'web',rel);
      try{await fs.access(filename);}catch{
        const base=path.basename(url.pathname);filename=path.join(root,'source/gemini',base);
      }
    }
    try{
      const content=await fs.readFile(filename);const ext=path.extname(filename);
      res.writeHead(200,{'Content-Type':({'.html':'text/html','.css':'text/css','.js':'application/javascript','.svg':'image/svg+xml','.png':'image/png'})[ext]||'application/octet-stream',
        'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'"});res.end(content);
    }catch{res.writeHead(404);res.end('Not found');}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser=await chromium.launch({headless:true,channel:'msedge'});
  await fs.mkdir(path.join(root,'screens'),{recursive:true});
  const results=[];
  try{
    for(const product of ['gemini','temu','xhs','auth'])for(const viewport of viewports){
      const page=await browser.newPage({viewport});const errors=[];const orders=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.route('**/*',async route=>{
        const req=route.request();const url=new URL(req.url());
        if(url.pathname.includes('/phone-auth/'))return route.fulfill({contentType:'application/json',body:JSON.stringify({ready:false})});
        if(!url.pathname.includes('/membership-api/'))return route.continue();
        const endpoint=url.pathname.split('/membership-api/')[1];let data={};
        if(endpoint==='plans')data={plans,payment_ready:true};
        else if(endpoint==='account')data={label:'测试账户',balance_points:10000};
        else if(endpoint==='catalog')data={products:[{id:'gemini-image-assistant',name:'Gemini生图助手',membership_ready:true,icon:'/membership/gemini/icon.png'},{id:'temu-image-assistant',name:'Temu图片大师',membership_ready:true,icon:'/membership/temu/temu.png'}]};
        else if(endpoint==='gifts')data={items:[]};
        else if(endpoint==='keys')data={enabled:false,eligible:false,keys:[]};
        else if(endpoint==='orders' && req.method()==='POST'){
          const body=req.postDataJSON();orders.push({path:url.pathname,body});const plan=plans.find(p=>p.id===body.plan);
          data={id:'synthetic-order-'+body.plan,plan:body.plan,amount_fen:plan.price_fen,units:plan.images,status:'pending',valid_days:plan.period==='lifetime'?null:30};
        }else if(endpoint==='orders')data={orders:[]};
        else if(endpoint==='redeem')data={ok:true};
        return route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
      });
      const url=`http://127.0.0.1:${server.address().port}/${product==='auth'?'auth/':'membership/'+product+'/'}`;
      await page.goto(url);
      if(product==='gemini'||product==='temu'){
        await page.waitForFunction(()=>document.getElementById('notice').textContent.includes('选好套餐'));
        for(const plan of plans){
          await page.click(`[data-id="${plan.id}"]`);
          if(!(await page.locator('#total').textContent()).includes(String(plan.price_fen/100)))throw Error('Price mismatch');
          const copy=await page.locator('#plan-guidance').textContent();if(!copy)throw Error('Guide missing');
          await page.click('#buy');await page.locator('#payment-dialog').waitFor({state:'visible'});
          const last=orders.at(-1);if(last.body.plan!==plan.id || last.body.product!==`${product}-image-assistant`)throw Error('Wrong product/order');
          if(last.path!==(product==='temu'?'/temu':'')+'/membership-api/orders')throw Error('Wrong endpoint');
          if((await page.locator('#payment-amount').textContent())!==`¥${(plan.price_fen/100).toFixed(2)}`)throw Error('Modal amount mismatch');
          if(plan.id==='ultra' && viewport.width===320)await page.screenshot({path:path.join(root,'screens',`${product}-payment-320.png`),fullPage:true});
          await page.click('#payment-close');
        }
        await page.click('[data-id="ultra"]');
      } else if(product==='auth')await page.waitForFunction(()=>document.getElementById('message').textContent.includes('开放'));
      const bounds=await page.evaluate(()=>({pageWidth:document.documentElement.scrollWidth,pageHeight:document.documentElement.scrollHeight,viewportWidth:innerWidth,viewportHeight:innerHeight}));
      if(bounds.pageWidth>viewport.width+1 || bounds.pageHeight>viewport.height+1){
        await page.screenshot({path:path.join(root,'screens','overflow.png'),fullPage:true});
        console.log(await page.locator('header,main,main>*,#plans,#checkout-panel>*').evaluateAll(nodes=>nodes.map(n=>({name:n.id||n.className||n.tagName,top:n.getBoundingClientRect().top,height:n.getBoundingClientRect().height}))));
        throw Error(`${product} ${viewport.width}x${viewport.height} overflow ${JSON.stringify(bounds)}`);
      }
      const broken=await page.locator('img').evaluateAll(nodes=>nodes.filter(n=>n.getBoundingClientRect().width>0 && (!n.complete||n.naturalWidth===0)).map(n=>n.src));
      if(broken.length)throw Error('Broken assets '+broken.join(','));
      if(errors.length)throw Error(errors.join('\n'));
      await page.screenshot({path:path.join(root,'screens',`${product}-${viewport.width}.png`),fullPage:true});
      results.push({product,...viewport,passed:true,synthetic_payment:orders.length});await page.close();
    }
    const redirected=await browser.newPage();let ticket;
    await redirected.route('**/membership-api/**', async route=>{
      const endpoint=new URL(route.request().url()).pathname.split('/membership-api/')[1];
      if(endpoint==='redeem')ticket=route.request().postDataJSON().ticket;
      const data=endpoint==='plans'?{plans,payment_ready:true}:endpoint==='account'?{label:'测试账户',balance_points:10000}:endpoint==='catalog'?{products:[{id:'gemini-image-assistant',membership_ready:true}]}:endpoint==='orders'?{orders:[]}:endpoint==='keys'?{enabled:false,eligible:false,keys:[]}:{items:[]};
      await route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
    });
    await redirected.goto(`http://127.0.0.1:${server.address().port}/membership/#ticket=synthetic-only`);
    await redirected.waitForFunction(()=>document.getElementById('account')?.textContent==='测试账户');
    if(ticket!=='synthetic-only')throw Error('Legacy membership redirect lost account ticket');
    await redirected.close();
    await fs.writeFile(path.join(root,'web-validation.json'),JSON.stringify({results,root_redirect_preserves_ticket:true,actual_payments:0,actual_sms:0},null,2));
    console.log(JSON.stringify({checks:results.length,passed:true,payment_mode:'unchanged QR',actual_payments:0}));
  }finally{await browser.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
