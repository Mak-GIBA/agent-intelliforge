'use strict';
// Browser-owned assertions. Model responses are never accepted as observations.
const fs = require('node:fs');
const crypto = require('node:crypto');
function locator(page, spec) {
  return spec.selector ? page.locator(spec.selector) : page.getByRole(spec.role, {name:spec.name,exact:true});
}
function routeMatches(url, route) {
  const actual = new URL(url), expected = new URL(route, actual.origin);
  const pattern = expected.pathname.split('/').map(s=>s.startsWith(':')?'[^/]+':s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('/');
  return new RegExp('^'+pattern+'$').test(actual.pathname) && actual.search===expected.search && actual.hash===expected.hash;
}
class ContractObserver {
  constructor(file,journeys) {
    const raw = fs.readFileSync(file);
    this.sha = crypto.createHash('sha256').update(raw).digest('hex');
    this.contract = JSON.parse(raw); this.checkpoint = null; this.operation = null;this.pending=new Map();this.values={};
    this.journeys=new Set(journeys||this.contract.journeys.filter(j=>j.required).map(j=>j.id));
  }
  field(page,id) {
    const declared=this.contract.screens.flatMap(s=>s.fields||[]).find(f=>f.id===id);
    return declared?.locator ? locator(page,declared.locator) : page.locator('[id='+JSON.stringify(id)+'],[data-field='+JSON.stringify(id)+']');
  }
  async value(control) {
    if(await control.count()!==1)return {available:false};
    const type=await control.getAttribute('type');
    return {available:true,value:['checkbox','radio'].includes(type)?await control.isChecked():await control.inputValue()};
  }
  async before(page,name,args) {
    if(name==='ux_navigate'){this.checkpoint=null;this.operation=null;return;}
    if(!['ux_click','ux_fill','ux_select','ux_press','ux_back'].includes(name))return;
    const kind={ux_click:'click',ux_fill:'fill',ux_select:'select',ux_press:'press',ux_back:'press'}[name];
    let element;
    if(args.selector)element=page.locator(args.selector);
    else if(name==='ux_press')element=page.locator(':focus');
    const actionIds=[];
    for(const action of this.contract.actions.filter(a=>a.kind===kind)) {
      const candidate=locator(page,action.locator);
      if(await candidate.count()!==1)continue;
      if(element && await element.count()===1) {
        const handle=await element.elementHandle();
        if(await candidate.evaluate((node,other)=>node===other||node.contains(other),handle))actionIds.push(action.id);
      } else if(Number.isFinite(args.x)&&Number.isFinite(args.y)) {
        if(await candidate.evaluate((node,p)=>node.contains(document.elementFromPoint(p.x,p.y)),args))actionIds.push(action.id);
      }
    }
    const fields={};
    for(const id of new Set(this.contract.transitions.flatMap(t=>t.retained_fields))) {
      const observed=await this.value(this.field(page,id));fields[id]=observed.available?observed:(this.values[id]||observed);
      if(observed.available)this.values[id]=observed;
    }
    this.operation={kind,actionIds,beforeUrl:page.url(),from:this.checkpoint,fields};
  }
  async check(page,args) {
    const screen=this.contract.screens.find(s=>s.id===args.screen_id);
    if(!screen || !screen.states.includes(args.state))throw Error('Unknown contract screen/state');
    const checks=[],matched=routeMatches(page.url(),screen.route);
    const assertions=this.contract.requirements.filter(r=>r.required&&this.journeys.has(r.journey_id)).flatMap(r=>r.acceptance).filter(a=>a.screen_id===screen.id&&a.state===args.state);
    for(const a of assertions) {
      let observed,passed=false;
      try {
        if(a.type==='url')observed=a.expected.startsWith('/')?new URL(page.url()).pathname+new URL(page.url()).search+new URL(page.url()).hash:page.url();
        else {
          const control=locator(page,a.locator);
          if(a.type==='visible')observed=await control.isVisible();
          else if(a.type==='text')observed=(await control.innerText()).trim();
          else if(a.type==='value')observed=await control.inputValue();
          else if(a.type==='checked')observed=await control.isChecked();
          else if(a.type==='focused')observed=await control.evaluate(el=>el===document.activeElement);
          else if(a.type==='accessible_name') {
            const snapshot=await control.ariaSnapshot();
            const first=snapshot.split('\n')[0],match=first.match(/^- [\w]+(?: "((?:\\.|[^"\\])*)")?/);
            observed=match?.[1]===undefined?'':JSON.parse('"'+match[1]+'"');
          }
        }
        passed=matched&&observed===a.expected;
      } catch {observed='unavailable';}
      checks.push({id:a.id,passed,observed});
    }
    const stateVerified=matched&&checks.length>0&&checks.every(c=>c.passed);
    for(const [id,pending] of this.pending) {
      const actual=await this.value(this.field(page,pending.field));
      if(actual.available&&stateVerified){checks.push({id,passed:pending.expected===actual.value,observed:actual.value});this.pending.delete(id);}
    }
    if(args.transition_id) {
      const error=args.transition_id.endsWith('__on_error');
      const id=error?args.transition_id.slice(0,-10):args.transition_id;
      const transition=this.contract.transitions.find(t=>t.id===id);
      if(!transition || (error&&!transition.on_error))throw Error('Unknown contract transition');
      const destination=error?transition.on_error:transition.to,op=this.operation;
      const fromScreen=this.contract.screens.find(s=>s.id===transition.from.screen_id);
      const passed=Boolean(stateVerified&&destination.screen_id===screen.id&&destination.state===args.state&&op?.from?.verified&&
        op.from.screen_id===transition.from.screen_id&&op.from.state===transition.from.state&&routeMatches(op.beforeUrl,fromScreen.route)&&
        op.actionIds.includes(transition.action_id));
      checks.push({id:args.transition_id,passed,observed:{from:op?.from||null,action:op?.actionIds||[],destination:{screen_id:screen.id,state:args.state},route:matched}});
      for(const field of transition.retained_fields) {
        const id=args.transition_id+'__retain_'+field,before=op?.fields[field],after=await this.value(this.field(page,field));
        if(!passed||!before?.available)checks.push({id,passed:false,observed:'Retention origin unverified'});
        else if(after.available)checks.push({id,passed:before.value===after.value,observed:after.value});
        else this.pending.set(id,{field,expected:before.value});
      }
      this.operation=null;
    }
    for(const id of new Set(this.contract.transitions.flatMap(t=>t.retained_fields))) {
      const observed=await this.value(this.field(page,id));if(observed.available)this.values[id]=observed;
    }
    this.checkpoint={screen_id:screen.id,state:args.state,verified:stateVerified};
    return {contract_sha256:this.sha,screen_id:screen.id,state:args.state,checks,route_matches:matched};
  }
}
module.exports={ContractObserver,routeMatches};
