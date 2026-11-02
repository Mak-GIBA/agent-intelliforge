#!/usr/bin/env node
'use strict';
// Fixed synthetic tasks. Actual browser outcomes are separate from image ratings.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require(path.join(process.env.UX_GAN_RUNTIME,'node_modules/playwright'));
async function run(job,caseName) {
  const settled=process.argv.includes('--settled-observations'),corrected=settled||process.argv.includes('--corrected-async');
  const app=path.join(job,'app'),out=path.join(job,settled?'screens-settled':corrected?'screens-corrected':'screens');fs.mkdirSync(out,{recursive:true});
  const server=http.createServer((req,res)=>{
    const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname);const file=path.resolve(app,'.'+relative);
    if(!file.startsWith(path.resolve(app)+path.sep)&&file!==path.resolve(app)){res.writeHead(403).end();return;}
    try{const p=fs.statSync(file).isDirectory()?path.join(file,'index.html'):file;res.setHeader('Content-Type',p.endsWith('.html')?'text/html; charset=utf-8':'application/octet-stream');res.end(fs.readFileSync(p));}catch{res.writeHead(404).end();}
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url='http://127.0.0.1:'+server.address().port,b=await chromium.launch({headless:true}),checks=[],images=[];
  try {
    for(const [view,width,height] of [['desktop',1440,900],['tablet',768,1024],['mobile',390,844]]) {
      const context=await b.newContext({viewport:{width,height},deviceScaleFactor:1}),p=await context.newPage();p.setDefaultTimeout(1600);
      const errors=[];p.on('pageerror',e=>errors.push(e.message));
      async function shot(state){const file=path.join(out,view+'-'+state+'.png');await p.screenshot({path:file,fullPage:false});images.push({path:file,viewport:{width,height},state,url:p.url()});}
      async function check(id,operation){let observed;try{observed=await operation();checks.push({id,viewport:view,passed:observed!==false,observed});return observed!==false;}catch(e){checks.push({id,viewport:view,passed:false,error:e.message.slice(0,400)});return false;}}
      async function observe(read){if(!settled)return read();const until=Date.now()+5000;do{try{if(await read())return true;}catch{}await p.waitForTimeout(50);}while(Date.now()<until);return false;}
      await p.goto(url,{waitUntil:'domcontentloaded'});await shot('initial');
      await check('no-horizontal-overflow',()=>p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await check('inputs-labelled',()=>p.locator('input:not([type=hidden]),select,textarea').evaluateAll(els=>els.filter(e=>e.checkVisibility()).every(e=>e.labels?.length||e.getAttribute('aria-label')||e.getAttribute('aria-labelledby'))));
      await check('keyboard-focus',async()=>{await p.keyboard.press('Tab');await shot('focus');return p.evaluate(()=>document.activeElement!==document.body);});
      if(caseName==='documents') {
        await check('search-and-kind',async()=>{await p.locator('#query').fill('契約');await p.locator('#kind').selectOption('pdf');return p.locator('#open-contract').isVisible();});
        await check('selection',async()=>{await p.locator('#select-contract').check();return p.locator('#select-contract').isChecked();});
        await check('open-detail',async()=>{await p.locator('#open-contract').click();return observe(async()=>(await p.locator('#detail').isVisible())&&p.url().endsWith('#detail'));});await shot('detail');
        await check('save-error-preserves-draft',async()=>{await p.locator('#note').fill('共有する契約メモ');await p.evaluate(()=>window.__UX_TEST.failNext=true);await p.locator('#save-note').click();return (await p.locator('#error').innerText()).trim().length>0&&await p.locator('#note').inputValue()==='共有する契約メモ';});await shot('failure');
        await check('retry-save',async()=>{await p.locator('#retry').click();return observe(async()=>(await p.locator('#status').innerText()).includes('保存')&&(!settled||!(await p.locator('#error').isVisible())||!(await p.locator('#error').innerText()).trim()));});
        await check('related-document',async()=>{await p.locator('#related-policy').click();return (await p.locator('#detail').innerText()).includes('利用規約');});
        await check('return-retains-context',async()=>{await p.locator('#back').click();return observe(async()=>await p.locator('#list').isVisible()&&await p.locator('#query').inputValue()==='契約'&&await p.locator('#kind').inputValue()==='pdf'&&await p.locator('#select-contract').isChecked());});
        await check('document-draft-retained',async()=>{await p.locator('#open-contract').click();return await p.locator('#note').inputValue()==='共有する契約メモ';});await shot('completed');
      } else if(caseName==='settings') {
        await check('invalid-input',async()=>{await p.locator('#display-name').fill('');await p.locator('#email').fill('invalid');await p.locator('#save').click();return (await p.locator('#error').innerText()).trim().length>0;});await shot('invalid');
        await check('save-error-preserves-input',async()=>{await p.locator('#display-name').fill('佐藤');await p.locator('#email').fill('sato@example.test');await p.evaluate(()=>window.__UX_TEST.failNext=true);await p.locator('#save').click();return (await p.locator('#error').innerText()).trim().length>0&&await p.locator('#display-name').inputValue()==='佐藤';});await shot('failure');
        await check('retry-save',async()=>{await p.locator('#retry').click();return observe(async()=>(await p.locator('#status').innerText()).includes('保存')&&(!settled||!(await p.locator('#error').isVisible())||!(await p.locator('#error').innerText()).trim()));});
        await check('cancel-restores-latest-save',async()=>{await p.locator('#display-name').fill('変更途中');p.once('dialog',d=>d.accept());await p.locator('#cancel').click();return await p.locator('#display-name').inputValue()==='佐藤';});await shot('completed');
      } else if(caseName==='landing') {
        await check('sections-and-price',async()=>{for(const id of ['#features','#pricing','#faq'])if(await p.locator(id).count()!==1)return false;return (await p.locator('#pricing').innerText()).includes('2,980');});
        await check('cta-reaches-signup',async()=>{await p.locator('#cta').click();return observe(async()=>await p.locator('#signup').isVisible()&&(await p.locator('#signup').boundingBox()).y<height);});await shot('signup');
        await check('email-signup',async()=>{await p.locator('#email').fill('owner@example.test');await p.locator('#start').click();return observe(async()=>(await p.locator('#status').innerText()).trim().length>0);});await shot('completed');
      } else if(caseName==='application') {
        await check('invalid-input',async()=>{await p.locator('#continue-details').click();return p.url().endsWith('#details')&&(await p.locator('#error').innerText()).trim().length>0;});await shot('invalid');
        await check('details-to-confirm',async()=>{await p.locator('#full-name').fill('山田花子');await p.locator('#email').fill('hanako@example.test');await p.locator('#plan').selectOption('advanced');await p.locator('#continue-details').click();return p.url().endsWith('#confirm')&&(await p.locator('#summary').innerText()).includes('山田花子');});await shot('confirm');
        await check('edit-retains-input',async()=>{await p.locator('#edit-details').click();return p.url().endsWith('#details')&&await p.locator('#full-name').inputValue()==='山田花子'&&await p.locator('#plan').inputValue()==='advanced';});
        await check('confirm-to-payment',async()=>{await p.locator('#continue-details').click();await p.locator('#continue-confirm').click();return p.url().endsWith('#payment');});await shot('payment');
        await check('payment-back',async()=>{await p.locator('#back-payment').click();return p.url().endsWith('#confirm')&&(await p.locator('#summary').innerText()).includes('山田花子');});
        await check('payment-error',async()=>{await p.locator('#continue-confirm').click();await p.evaluate(()=>window.__UX_TEST.failNext=true);await p.locator('#pay').click();return p.url().endsWith('#payment')&&(await p.locator('#error').innerText()).trim().length>0;});await shot('failure');
        await check('retry-completes',async()=>{await p.locator('#retry').click();if(corrected)await p.waitForURL('**/#complete',{timeout:5000});else await p.waitForTimeout(350);return p.url().endsWith('#complete')&&(await p.locator('#receipt').innerText()).includes('山田花子');});await shot('completed');
        await check('cancel-preserves-draft',async()=>{
          const fresh=corrected?await b.newContext({viewport:{width,height}}):null,active=fresh?await fresh.newPage():p;
          try{await active.goto(url+'/#details');await active.locator('#full-name').fill('再開する下書き');await active.locator('#email').fill('draft@example.test');active.once('dialog',d=>d.accept());await active.locator('#cancel-application').click();return active.url().endsWith('#details')&&await active.locator('#full-name').inputValue()==='再開する下書き';}
          finally{if(fresh)await fresh.close();}
        });
      }
      await check('no-browser-errors',()=>errors.length===0);await context.close();
    }
  } finally {await b.close();await new Promise(resolve=>server.close(resolve));}
  const result={case:caseName,revision:settled?3:corrected?2:1,checks,images,passed:checks.filter(c=>c.passed).length,failed:checks.filter(c=>!c.passed).length,source:'actual Chromium; fixed synthetic task; not human usability testing'};
  fs.writeFileSync(path.join(job,settled?'operations-settled.json':corrected?'operations-corrected.json':'operations.json'),JSON.stringify(result,null,2)+'\n',{mode:0o600});console.log(JSON.stringify({job,revision:result.revision,passed:result.passed,failed:result.failed}));
  if(process.argv.includes('--require-pass')&&result.failed)process.exitCode=1;
}
run(path.resolve(process.argv[2]),process.argv[3]).catch(e=>{console.error(e);process.exit(1)});
