const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const {chromium} = require('C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root = __dirname;
(async()=>{
  const server = http.createServer(async(req,res)=>{
    const names = {'/auth/':'index.html','/auth/style.css':'style.css','/auth/app.js':'app.js'};
    if (!names[req.url]) {res.writeHead(404);res.end();return;}
    const mime = req.url.endsWith('.css')?'text/css':req.url.endsWith('.js')?'application/javascript':'text/html';
    res.writeHead(200,{'Content-Type':mime,'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'"});
    res.end(await fs.readFile(path.join(root,'web',names[req.url])));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const browser = await chromium.launch({headless:true,channel:'msedge'});
  const results=[];
  await fs.mkdir(path.join(root,'screens'),{recursive:true});
  try{
    for(const ready of [false,true])for(const width of [320,390,1024,1440]){
      const page=await browser.newPage({viewport:{width,height:900}});
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      await page.route('**/phone-auth/**',async route=>{
        const endpoint=new URL(route.request().url()).pathname.split('/').pop();
        const body=endpoint==='status'?{ready}:endpoint==='send'?{sent:true,retry_after:60}:endpoint==='verify'?{verified:true}:{ok:true};
        await route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
      });
      await page.goto(`http://127.0.0.1:${server.address().port}/auth/#ticket=${'a'.repeat(43)}`);
      await page.waitForFunction(()=>!document.getElementById('message').textContent.includes('正在检查'));
      if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Horizontal overflow '+width);
      if(ready){
        await page.fill('#phone','13800000000');await page.check('#accepted');await page.click('#send');
        await page.waitForFunction(()=>document.getElementById('message').textContent.includes('已发送'));
        await page.fill('#code','123456');
      }else if(!(await page.locator('#send').isDisabled()))throw Error('Unavailable SMS send enabled');
      await page.screenshot({path:path.join(root,'screens',`${ready?'configured':'disabled'}-${width}.png`),fullPage:true});
      if(ready){await page.click('#verify');await page.locator('#success').waitFor({state:'visible'});}
      if(errors.length)throw Error(errors.join('\n'));
      results.push({ready,width,passed:true,synthetic:true});await page.close();
    }
    await fs.writeFile(path.join(root,'web-validation.json'),JSON.stringify({results,real_sms_sent:0},null,2));
    console.log(JSON.stringify({checks:results.length,passed:true,real_sms_sent:0}));
  }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
