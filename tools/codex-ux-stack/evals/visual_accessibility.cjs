#!/usr/bin/env node
'use strict';
// Supplemental scan, outside the frozen primary metric. No exclusions/suppression.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium}=require(path.join(process.env.UX_GAN_RUNTIME,'node_modules/playwright'));
const axe=require(path.join(process.env.UX_AXE_RUNTIME,'node_modules/axe-core'));
async function main(job,caseName){
  const stable=process.argv.includes('--stable-frames');
  const app=path.join(job,'app'),results=[];
  const server=http.createServer((req,res)=>{
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname),file=path.resolve(app,'.'+pathname);
    if(!file.startsWith(path.resolve(app)+path.sep)&&file!==path.resolve(app)){res.writeHead(403).end();return;}
    try{const p=fs.statSync(file).isDirectory()?path.join(file,'index.html'):file;res.setHeader('Content-Type','text/html; charset=utf-8');res.end(fs.readFileSync(p));}catch{res.writeHead(404).end();}
  });await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url='http://127.0.0.1:'+server.address().port,b=await chromium.launch({headless:true});
  try{for(const [viewport,width,height] of [['desktop',1440,900],['tablet',768,1024],['mobile',390,844]]){
    const context=await b.newContext({viewport:{width,height}}),p=await context.newPage();p.setDefaultTimeout(2000);
    await p.goto(url,{waitUntil:'domcontentloaded'});
    async function scan(state){
      if(stable)await p.evaluate(async()=>{const finite=document.getAnimations().filter(a=>Number.isFinite(a.effect?.getComputedTiming().endTime));await Promise.race([Promise.allSettled(finite.map(a=>a.finished)),new Promise(r=>setTimeout(r,5000))]);});
      await p.addScriptTag({content:axe.source});const r=await p.evaluate(async()=>window.axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}}));
      const snapshot=path.join(job,`axe-${stable?'stable-':''}${viewport}-${state}.png`);await p.screenshot({path:snapshot,...(stable?{animations:'disabled'}:{})});
      results.push({viewport,state,screenshot:snapshot,violations:r.violations,incomplete:r.incomplete.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),passes:r.passes.map(v=>v.id)});}
    await scan('initial');
    try{
      if(caseName==='documents'){await p.locator('#open-contract').click();await scan('detail');await p.locator('#note').fill('アクセシビリティ確認');await p.evaluate(()=>window.__UX_TEST.failNext=true);await p.locator('#save-note').click();await scan('failure');}
      else if(caseName==='settings'){await p.locator('#display-name').fill('');await p.locator('#save').click();await scan('invalid');}
      else if(caseName==='application'){await p.locator('#continue-details').click();await scan('invalid');await p.locator('#full-name').fill('試験太郎');await p.locator('#email').fill('test@example.test');await p.locator('#plan').selectOption('basic');await p.locator('#continue-details').click();await p.locator('#continue-confirm').click();await scan('payment');}
      else if(caseName==='landing'){await p.locator('#cta').click();await scan('signup');}
    }catch(error){results.push({viewport,state:'unavailable',reason:error.message.slice(0,400)});}
    await context.close();
  }}finally{await b.close();await new Promise(resolve=>server.close(resolve));}
  const value={engine:'axe-core '+axe.version,method:'supplemental automated WCAG-tagged scan; not complete accessibility or human usability testing',...(stable?{observation:'finite animations waited <=5s before scanning; no animation quality claim'}:{}),results};
  fs.writeFileSync(path.join(job,stable?'accessibility-stable.json':'accessibility.json'),JSON.stringify(value,null,2)+'\n',{mode:0o600});
  console.log(JSON.stringify({job,scans:results.filter(r=>r.violations).length,violations:results.flatMap(r=>r.violations||[]).map(v=>v.id)}));
}
main(path.resolve(process.argv[2]),process.argv[3]).catch(error=>{console.error(error);process.exit(1)});
