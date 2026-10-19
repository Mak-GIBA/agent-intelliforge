#!/usr/bin/env node
'use strict';

// No model, downloads or personal browser profile: the real stdio bridge is used.
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const readline = require('node:readline');
const crypto = require('node:crypto');
let child, server, lines, stage = 'local_fixture', stderr = '', sequence = 0;
const pending = new Map();
let deadline;

function rpc(method, params) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    pending.set(id, {resolve, reject});
    child.stdin.write(JSON.stringify({jsonrpc:'2.0', id, method, params})+'\n');
  });
}

async function call(name, args) {
  stage = name;
  const result = await rpc('tools/call', {name, arguments:args});
  if (result.isError) throw new Error(result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n'));
  return result;
}

async function main() {
  server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.end('<title>MCP probe</title><label>Name<input id="name"></label><button id="save" onclick="document.getElementById(\'result\').textContent=document.getElementById(\'name\').value">Save</button><p id="result"></p>');
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const url = 'http://127.0.0.1:'+server.address().port;
  child = spawn(process.execPath, [path.join(__dirname,'visual-browser.cjs')], {
    env:{...process.env, UX_GAN_TARGET:url}, stdio:['pipe','pipe','pipe']});
  child.stderr.on('data',bytes=>{stderr=(stderr+bytes.toString()).slice(-8000);});
  child.on('error',error=>{for(const item of pending.values())item.reject(error);pending.clear();});
  child.on('exit',(code)=>{for(const item of pending.values())item.reject(new Error('MCP exited '+code+' '+stderr));pending.clear();});
  lines=readline.createInterface({input:child.stdout});
  lines.on('line',line=>{
    try {
      const message=JSON.parse(line), item=pending.get(message.id);
      if(!item)return;
      pending.delete(message.id);
      if(message.error)item.reject(new Error(message.error.message));else item.resolve(message.result);
    }catch(error){for(const item of pending.values())item.reject(error);pending.clear();}
  });
  stage='initialize';
  const initialized=await rpc('initialize',{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'ux-doctor',version:'1'}});
  if(!initialized.capabilities?.tools)throw new Error('MCP did not advertise tools');
  child.stdin.write(JSON.stringify({jsonrpc:'2.0',method:'notifications/initialized'})+'\n');
  stage='tools/list';
  const catalog=await rpc('tools/list',{});
  for(const name of ['ux_navigate','ux_fill','ux_click']) {
    if(!catalog.tools.some(tool=>tool.name===name))throw new Error('MCP tool missing: '+name);
  }
  await call('ux_navigate',{url});
  await call('ux_fill',{selector:'#name',value:'probe'});
  await call('ux_click',{selector:'#save'});
  stage='evidence_write';
  const out=process.env.UX_GAN_SCREENSHOTS;
  const receipts=fs.readFileSync(path.join(out,'browser-receipts.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
  const frames=receipts.filter(item=>item.kind==='frame');
  if(frames.length<5)throw new Error('Browser screenshots or before/after frames missing');
  for(const frame of frames) {
    if(path.dirname(path.resolve(frame.path))!==path.resolve(out))throw new Error('Evidence outside probe directory');
    if(crypto.createHash('sha256').update(fs.readFileSync(frame.path)).digest('hex')!==frame.sha256)throw new Error('Screenshot hash mismatch');
  }
  process.stdout.write(JSON.stringify({ready:true,initialized:true,tools_available:true,tool_calls:3,image_count:frames.length,receipt_count:receipts.length})+'\n');
}

async function cleanup() {
  clearTimeout(deadline);
  lines?.close();
  if(child) {
    child.stdin.end();
    const exited=new Promise(resolve=>child.once('exit',resolve));
    child.kill('SIGTERM');
    let timer;
    await Promise.race([exited,new Promise(resolve=>{timer=setTimeout(()=>{child.kill('SIGKILL');resolve();},2000);})]);
    clearTimeout(timer);
  }
  server?.close();
}

const timedOut=new Promise((_,reject)=>{deadline=setTimeout(()=>reject(new Error('MCP probe timeout')),45000);});
Promise.race([main(),timedOut]).catch(error=>{
  process.stderr.write('Browser MCP probe '+stage+': '+error.message+'\n');
  process.exitCode=1;
}).finally(cleanup);
