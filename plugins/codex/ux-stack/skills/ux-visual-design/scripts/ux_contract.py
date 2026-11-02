"""Local UX contracts and editable design exchange; no network or model calls."""
from __future__ import annotations
import argparse
import base64
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

ID = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}\Z')
ASSERTIONS = ('visible','text','value','checked','focused','accessible_name','url')
OWNER = 'ux-visual-design/bundle-v1'

class ContractError(ValueError):
    pass

def validate(contract, project=None):
    """Check structure plus graph invariants; never certify UI quality from JSON."""
    errors=[]
    if not isinstance(contract,dict):return ['contract: expected object']
    if contract.get('schema_version')!=1:errors.append('schema_version: must be 1')
    if type(contract.get('revision')) is not int or contract['revision']<1:errors.append('revision: positive integer required')
    p=contract.get('project',{})
    if not isinstance(p,dict) or not isinstance(p.get('name'),str) or not p.get('name','').strip():errors.append('project.name: required')
    indexes={};all_ids=set()
    for group in ('journeys','screens','actions','transitions','requirements','artifacts'):
        items=contract.get(group)
        if not isinstance(items,list):errors.append(group+': expected array');items=[]
        indexes[group]={}
        for item in items:
            if not isinstance(item,dict):errors.append(group+': expected object');continue
            key=item.get('id')
            if not isinstance(key,str) or not ID.fullmatch(key):errors.append(group+': invalid id');continue
            if key in all_ids:errors.append('duplicate id: '+key)
            all_ids.add(key);indexes[group][key]=item
    screens=indexes['screens'];actions=indexes['actions'];journeys=indexes['journeys']
    def lookup(mapping,key):return mapping.get(key) if isinstance(key,str) else None
    def screen_state(value,location):
        if not isinstance(value,dict):errors.append(location+': expected screen/state');return
        screen=lookup(screens,value.get('screen_id'))
        if not screen:errors.append(location+': missing screen '+str(value.get('screen_id')))
        elif not isinstance(screen.get('states'),list) or value.get('state') not in screen['states']:errors.append(location+': unknown state')
    def locator(value,location):
        if not isinstance(value,dict) or not ((isinstance(value.get('selector'),str) and value['selector'].strip()) or
              (isinstance(value.get('role'),str) and isinstance(value.get('name'),str))):errors.append(location+': selector or role/name required')
    for key,s in screens.items():
        for field in ('title','purpose','route'):
            if not isinstance(s.get(field),str) or not s.get(field,'').strip():errors.append(key+'.'+field+': required')
        route=s.get('route','')
        if not isinstance(route,str) or not route.startswith('/') or route.startswith('//') or '\\' in route:errors.append(key+': route must be a local absolute path')
        states=s.get('states')
        if not isinstance(states,list) or not states or any(not isinstance(x,str) or not ID.fullmatch(x) for x in states):errors.append(key+': nonempty state ids required')
        layout=s.get('layout',{})
        if not isinstance(layout,dict):errors.append(key+': invalid layout')
        else:
            for dimension in ('x','y','width','height'):
                value=layout.get(dimension,1)
                if type(value) not in (int,float) or not -4096<=value<=8192:errors.append(key+': invalid layout dimension')
            if 'fill' in layout and not re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?',str(layout['fill'])):errors.append(key+': invalid layout color')
        fields=s.get('fields',[])
        if not isinstance(fields,list):errors.append(key+': fields must be an array')
        else:
            field_ids=set()
            for field in fields:
                if not isinstance(field,dict) or not ID.fullmatch(str(field.get('id',''))) or not isinstance(field.get('label'),str) or field.get('type','text') not in ('text','search','email','number','textarea','select','checkbox'):errors.append(key+': invalid field')
                elif field['id'] in field_ids:errors.append(key+': duplicate field')
                else:
                    field_ids.add(field['id'])
                    if 'locator' in field:locator(field['locator'],key+'.'+field['id'])
                    if field.get('type')=='select' and (not isinstance(field.get('options'),list) or any(not isinstance(v,str) for v in field['options'])):errors.append(key+': select options must be strings')
        component=s.get('component')
        path=component.get('path') if isinstance(component,dict) else None
        if not isinstance(path,str) or not path or Path(path).is_absolute() or re.search(r'(^|[/\\])\.\.([/\\]|$)|:|\\',path):errors.append(key+': unsafe component path')
        elif project:
            root=Path(project).resolve();target=root/path
            if not target.is_file() or not target.resolve().is_relative_to(root) or any(x.is_symlink() for x in [target,*target.parents] if x!=root and root in x.parents):errors.append(key+': missing or linked component '+path)
    for key,a in actions.items():
        if not lookup(screens,a.get('screen_id')):errors.append(key+': missing screen '+str(a.get('screen_id')))
        if a.get('kind') not in ('click','fill','select','press'):errors.append(key+': unsupported action kind')
        if not isinstance(a.get('label'),str) or not a.get('label','').strip():errors.append(key+': label required')
        locator(a.get('locator'),key)
    for key,j in journeys.items():
        if not isinstance(j.get('purpose'),str) or not j.get('purpose','').strip():errors.append(key+': purpose required')
        if not isinstance(j.get('actions'),list) or not j.get('actions'):errors.append(key+': actions required')
        else:
            for aid in j['actions']:
                if not lookup(actions,aid):errors.append(key+': missing action '+str(aid))
        if type(j.get('required')) is not bool:errors.append(key+': required must be boolean')
    for key,t in indexes['transitions'].items():
        aid=t.get('action_id')
        action=lookup(actions,aid)
        if not action:errors.append(key+': missing action '+str(aid))
        for field in ('from','to'):screen_state(t.get(field),key+'.'+field)
        if t.get('on_error') is not None:screen_state(t['on_error'],key+'.on_error')
        if action and isinstance(t.get('from'),dict) and action.get('screen_id')!=t['from'].get('screen_id'):errors.append(key+': action/from screen mismatch')
        if not isinstance(t.get('condition'),str) or not t.get('condition','').strip():errors.append(key+': condition required')
        retained=t.get('retained_fields')
        if not isinstance(retained,list) or any(not isinstance(x,str) or not ID.fullmatch(x) for x in retained):errors.append(key+': retained_fields must be field ids')
        if 'required' in t and type(t['required']) is not bool:errors.append(key+': required must be boolean')
        if key.endswith('__on_error'):errors.append(key+': reserved error-branch suffix')
    for key,r in indexes['requirements'].items():
        if not lookup(journeys,r.get('journey_id')):errors.append(key+': missing journey')
        if type(r.get('required')) is not bool:errors.append(key+': required must be boolean')
        checks=r.get('acceptance')
        if not isinstance(checks,list) or not checks:errors.append(key+': acceptance required');continue
        for a in checks:
            if not isinstance(a,dict):errors.append(key+': invalid acceptance');continue
            aid=a.get('id')
            if not isinstance(aid,str) or not ID.fullmatch(aid) or aid in all_ids:errors.append(key+': duplicate/invalid acceptance id')
            all_ids.add(str(aid));screen_state(a,key+'.'+str(aid))
            if a.get('type') not in ASSERTIONS:errors.append(str(aid)+': unsupported assertion')
            if a.get('type')!='url':locator(a.get('locator'),str(aid))
            if 'expected' not in a or not isinstance(a.get('expected'),(str,bool,int,float)):errors.append(str(aid)+': scalar expected value required')
            elif a.get('type') in ('visible','checked','focused') and type(a['expected']) is not bool:errors.append(str(aid)+': boolean expected value required')
            elif a.get('type') in ('text','value','accessible_name','url') and not isinstance(a['expected'],str):errors.append(str(aid)+': string expected value required')
    for key,a in indexes['artifacts'].items():
        if a.get('provider') not in ('local','whimsical','figma'):errors.append(key+': unknown provider')
        if not isinstance(a.get('url'),str) or not isinstance(a.get('file_id'),str):errors.append(key+': artifact URL/file_id required')
        if 'snapshot' in a:
            snapshot=a['snapshot'];path=snapshot.get('path') if isinstance(snapshot,dict) else None
            if not isinstance(path,str) or not path or Path(path).is_absolute() or '..' in Path(path).parts or re.search(r':|\\',path) or not re.fullmatch(r'[0-9a-f]{64}',str(snapshot.get('sha256',''))):errors.append(key+': snapshot needs a safe relative path and SHA-256')
        bindings=a.get('bindings')
        if not isinstance(bindings,dict):errors.append(key+': bindings required')
        else:
            for uxid,node in bindings.items():
                if uxid not in all_ids or not isinstance(node,str) or not node:errors.append(key+': unknown or invalid binding '+uxid)
    approval=contract.get('approval',{})
    if not isinstance(approval,dict) or approval.get('status') not in ('not_requested','presented','approved','needs_review','delegated'):errors.append('approval.status: explicit status required')
    elif not isinstance(approval.get('source'),str) or not approval['source'].strip():errors.append('approval.source: evidence or delegation context required')
    if not errors:
        generated=[s['id']+'__'+state for s in screens.values() for state in s['states']]
        generated += [t['id']+'__on_error' for t in indexes['transitions'].values() if t.get('on_error')]
        generated += [branch+'__retain_'+field for t in indexes['transitions'].values() for branch in ([t['id'],t['id']+'__on_error'] if t.get('on_error') else [t['id']]) for field in t['retained_fields']]
        if len(generated)!=len(set(generated)) or set(generated)&all_ids:errors.append('Generated state/error bindings collide; choose unambiguous IDs')
    return errors


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def digest(value):return hashlib.sha256(value if isinstance(value,bytes) else canonical(value)).hexdigest()


def require(contract,project=None):
    errors=validate(contract,project)
    if errors:raise ContractError('; '.join(errors))
    return contract


def read(path):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>2_000_000:raise ContractError('Linked or oversized design input')
    return json.loads(path.read_text(encoding='utf-8'))


def write(path,value):
    path=Path(path).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):raise ContractError('Linked destination refused')
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');tmp=Path(f.name)
    try:os.replace(tmp,path)
    finally:tmp.unlink(missing_ok=True)

def reconcile(base, local, remote):
    for value in (base,local,remote):require(value)
    missing=object();conflicts=[]
    def merge(b,l,r,path):
        if l==r:return copy.deepcopy(l) if l is not missing else missing
        if l==b:return copy.deepcopy(r) if r is not missing else missing
        if r==b:return copy.deepcopy(l) if l is not missing else missing
        if all(isinstance(x,dict) for x in (b,l,r)):
            out={}
            for key in sorted(set(b)|set(l)|set(r)):
                if key=='revision' and not path:continue
                value=merge(b.get(key,missing),l.get(key,missing),r.get(key,missing),path+[key])
                if value is not missing:out[key]=value
            return out
        if all(isinstance(x,list) and all(isinstance(i,dict) and 'id' in i for i in x) for x in (b,l,r)):
            maps=[{i['id']:i for i in x} for x in (b,l,r)];out=[]
            keys=list(dict.fromkeys([i['id'] for x in (l,r,b) for i in x]))
            for key in keys:
                value=merge(*(m.get(key,missing) for m in maps),path+[key])
                if value is not missing:out.append(value)
            return out
        conflicts.append({'path':'/'.join(path),'local':None if l is missing else l,'remote':None if r is missing else r})
        return copy.deepcopy(l) if l is not missing else missing
    out=merge(base,local,remote,[])
    meaningful=lambda value:{k:v for k,v in value.items() if k!='revision'}
    changed=meaningful(out)!=meaningful(local)
    out['revision']=max(c['revision'] for c in (base,local,remote))+int(changed)
    if out.get('approval',{}).get('status')=='approved' and changed:
        out['approval']={'status':'needs_review','source':'design changed after approval'}
    invalid=validate(out)
    conflicts.extend({'path':'contract','error':error} for error in invalid)
    return {'status':'conflict' if conflicts else 'ready','contract':out,'conflicts':conflicts}


def required_checks(contract,journey_ids=None):
    require(contract)
    selected=set(journey_ids or [j['id'] for j in contract['journeys'] if j['required']])
    known={j['id'] for j in contract['journeys']}
    if selected-known:raise ContractError('Unknown journey ids: '+','.join(sorted(selected-known)))
    actions={a for j in contract['journeys'] if j['id'] in selected for a in j['actions']}
    checks=[a['id'] for r in contract['requirements'] if r['required'] and r['journey_id'] in selected for a in r['acceptance']]
    checks += [t['id'] for t in contract['transitions'] if t['action_id'] in actions and t.get('required',True)]
    checks += [t['id']+'__on_error' for t in contract['transitions'] if t['action_id'] in actions and t.get('required',True) and t.get('on_error')]
    checks += [branch+'__retain_'+field for t in contract['transitions'] if t['action_id'] in actions and t.get('required',True) for branch in ([t['id'],t['id']+'__on_error'] if t.get('on_error') else [t['id']]) for field in t['retained_fields']]
    return checks


def _preview(contract):
    data=canonical(contract).decode().replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return '''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>UX設計プレビュー</title><style>*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,sans-serif;background:#f4f5f7;color:#17202b}header,main{max-width:1040px;margin:auto;padding:24px}header{border-bottom:1px solid #cbd2db}nav{display:flex;gap:12px;flex-wrap:wrap}button,input,select{font:inherit;padding:10px 14px;border:1px solid #8593a3;border-radius:6px}button{background:white;cursor:pointer}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #1260bd;outline-offset:3px}article{background:white;border:1px solid #bac5d0;border-radius:12px;padding:28px;max-width:760px}label{display:block;margin:18px 0}input{display:block;max-width:100%;width:100%}.actions{display:flex;gap:12px;flex-wrap:wrap}aside{margin-top:20px;color:#475569}#notice{min-height:2em}small{display:block}@media(max-width:600px){header,main{padding:16px}article{padding:20px}.actions button{width:100%}}</style>
<header><h1>UX設計プレビュー</h1><p>導線と状態を確認するワイヤーフレームです。実サービスへの保存・送信・決済は行いません。</p><nav id="screens" aria-label="画面の一覧"></nav></header>
<main><article id="screen"></article><p id="notice" role="status"></p><aside>外部デザインの読み込みは行いません。設計変更は契約または編集可能なSVG／Mermaidへ反映し、差分を確認してください。</aside></main>
<script type="application/json" id="ux-contract">'''+data+'''</script><script>
const c=JSON.parse(document.querySelector('#ux-contract').textContent), values={},host=document.querySelector('#screen');
let current=c.screens[0].id,currentState=c.screens[0].states[0];
function text(tag,value,parent){const el=document.createElement(tag);el.textContent=value;parent.append(el);return el}
function move(to,message){current=to.screen_id;currentState=to.state;render();document.querySelector('#notice').textContent=message;}
function render(){const s=c.screens.find(x=>x.id===current);host.replaceChildren();host.dataset.screenId=s.id;host.dataset.state=currentState;text('h2',s.title,host);text('p',s.purpose,host);text('small',s.route+' / '+currentState,host);
if(currentState!=='normal'){const message=text('p',(s.state_messages||{})[currentState]||('確認中の状態: '+currentState),host);message.setAttribute('role',currentState==='failure'?'alert':'status');}
const stateLabel=text('label','確認する状態',host),state=document.createElement('select');state.setAttribute('aria-label','確認する状態');s.states.forEach(v=>{state.add(new Option(v,v))});state.value=currentState;state.onchange=()=>{currentState=state.value;render()};stateLabel.append(state);
const declared=s.fields||c.actions.filter(a=>a.screen_id===s.id&&['fill','select'].includes(a.kind)).map(a=>({id:a.field_id||a.id,label:a.label,type:a.kind==='select'?'select':'text',options:a.options||[]}));
for(const field of declared){const label=text('label',field.label,host),input=document.createElement(field.type==='textarea'?'textarea':field.type==='select'?'select':'input');input.id='field-'+field.id;input.dataset.field=field.id;if(input.tagName==='INPUT')input.type=field.type||'text';if(field.type==='select')for(const value of field.options||[])input.add(new Option(value,value));if(field.type==='checkbox')input.checked=Boolean(values[field.id]);else input.value=values[field.id]||'';input.oninput=()=>values[field.id]=field.type==='checkbox'?input.checked:input.value;label.append(input)}
const group=text('div','',host);group.className='actions';for(const a of c.actions.filter(x=>x.screen_id===s.id&&x.kind!=='fill'&&x.kind!=='select')){const options=c.transitions.filter(t=>t.action_id===a.id&&t.from.state===currentState);const wrap=text('div','',group);let branch;if(options.length>1){branch=document.createElement('select');branch.setAttribute('aria-label',a.label+'の条件');options.forEach(t=>branch.add(new Option(t.condition,t.id)));wrap.append(branch)}const b=text('button',a.label,wrap);b.dataset.actionId=a.id;b.disabled=!options.length;b.onclick=()=>{const t=options.find(t=>t.id===branch?.value)||options[0];if(t)move(t.to,t.condition);};for(const t of options.filter(t=>t.on_error)){const error=text('button',a.label+'のエラーを確認',wrap);error.dataset.errorFor=t.id;error.onclick=()=>move(t.on_error,'エラー時の経路: '+t.condition);}}
}
for(const s of c.screens){const b=text('button',s.title,document.querySelector('#screens'));b.dataset.screenTarget=s.id;b.onclick=()=>move({screen_id:s.id,state:s.states[0]},'画面を選択');}
render();</script></html>'''

def render_bundle(contract, destination):
    require(contract);destination=Path(destination).absolute()
    if any(p.is_symlink() for p in (destination,*destination.parents)):raise ContractError('Linked destination refused')
    encoded=base64.b64encode(canonical(contract)).decode()
    quote=lambda value:html.escape(str(value),quote=True)
    flow=['flowchart LR','%% ux-base '+encoded]
    for s in contract['screens']:
        flow.append('  '+s['id']+'["'+quote(s['title'])+'"]')
        for state in s['states']:flow.append('  '+s['id']+'__'+state+'["'+quote(s['title']+' / '+state)+'"]')
    for t in contract['transitions']:
        source=t['from']['screen_id']+'__'+t['from']['state'];target=t['to']['screen_id']+'__'+t['to']['state']
        flow.append('  '+source+' -->|"'+t['id']+': '+quote(t['condition'])+'"| '+target)
        if t.get('on_error'):flow.append('  '+source+' -->|"'+t['id']+'__on_error: on_error"| '+t['on_error']['screen_id']+'__'+t['on_error']['state'])
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900" role="img" aria-label="編集可能なワイヤーフレーム">',
         '<metadata id="ux-base">'+encoded+'</metadata>']
    for i,s in enumerate(contract['screens']):
        layout=s.get('layout',{});x=layout.get('x',24+(i%3)*390);y=layout.get('y',24+(i//3)*460);w=layout.get('width',350);h=layout.get('height',410)
        svg += [f'<g data-screen-id="{s["id"]}" transform="translate({x} {y})">',
                f'<rect data-frame="true" width="{w}" height="{h}" rx="10" fill="{quote(layout.get("fill","#ffffff"))}" stroke="#94a3b8"/>',
                '<text data-field="title" x="20" y="38" font-family="sans-serif" font-size="22">'+quote(s['title'])+'</text>',
                '<text x="20" y="68" font-family="sans-serif" font-size="14">'+quote(s['purpose'])+'</text>',
                '<text x="20" y="92" font-family="sans-serif" font-size="13">'+quote(' / '.join(s['states']))+'</text>']
        for n,field in enumerate(s.get('fields',[])):
            fy=116+n*62
            svg += [f'<text x="20" y="{fy}" font-family="sans-serif" font-size="13">'+quote(field['label'])+'</text>',f'<rect x="20" y="{fy+8}" width="{max(80,w-40)}" height="30" fill="#f8fafc" stroke="#cbd5e1"/>']
        for n,a in enumerate(a for a in contract['actions'] if a['screen_id']==s['id']):
            svg += [f'<text data-action-id="{a["id"]}" x="20" y="{135+len(s.get("fields",[]))*62+n*40}" font-family="sans-serif" font-size="16">'+quote(a['label'])+'</text>']
        svg.append('</g>')
    svg.append('</svg>')
    outputs={'flow.mmd':'\n'.join(flow)+'\n','wireframes.svg':'\n'.join(svg)+'\n','wireframes.html':_preview(contract)}
    marker=destination/'design-manifest.json';previous=read(marker) if marker.is_file() else {}
    if marker.exists() and previous.get('owner')!=OWNER:raise ContractError('Unmanaged design manifest')
    for name in outputs:
        p=destination/name
        if p.is_symlink() or p.exists() and digest(p.read_bytes())!=previous.get('files',{}).get(name):raise ContractError('Edited/unmanaged design output preserved: '+name)
    manifest={'owner':OWNER,'contract_sha256':digest(contract),'files':{n:digest(t.encode()) for n,t in outputs.items()}}
    outputs['design-manifest.json']=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    destination.mkdir(parents=True,exist_ok=True);committed=[]
    with tempfile.TemporaryDirectory(prefix='.ux-design-',dir=destination.parent) as temporary:
        stage=Path(temporary);old={name:(destination/name).read_bytes() if (destination/name).exists() else None for name in outputs}
        for name,text in outputs.items():(stage/name).write_text(text,encoding='utf-8')
        try:
            for name in outputs:os.replace(stage/name,destination/name);committed.append(name)
        except BaseException:
            for name in reversed(committed):
                if old[name] is None:(destination/name).unlink(missing_ok=True)
                else:
                    backup=stage/('restore-'+name);backup.write_bytes(old[name]);os.replace(backup,destination/name)
            raise
    return manifest

def import_design(contract, source):
    require(contract);source=Path(source)
    if source.is_symlink() or source.stat().st_size>2_000_000:raise ContractError('Linked or oversized design')
    text=source.read_text(encoding='utf-8')
    if source.suffix=='.svg':
        if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():raise ContractError('XML declarations refused')
        root=ET.fromstring(text);metadata=next((e.text for e in root.iter() if e.get('id')=='ux-base'),None)
        if not metadata:raise ContractError('Missing design baseline')
        base=require(json.loads(base64.b64decode(metadata,validate=True)));remote=copy.deepcopy(base);screens={s['id']:s for s in remote['screens']};actions={a['id']:a for a in remote['actions']};seen=set();seen_actions=set()
        defaults={s['id']:{'x':24+(i%3)*390,'y':24+(i//3)*460,'width':350,'height':410,'fill':'#ffffff'} for i,s in enumerate(base['screens'])}
        for e in root.iter():
            if e.tag.rsplit('}',1)[-1] in ('script','foreignObject') or any(k.lower().startswith('on') for k in e.attrib):raise ContractError('Executable SVG content refused')
            sid=e.get('data-screen-id')
            if not sid:continue
            if sid not in screens or sid in seen:raise ContractError('Unknown/duplicate screen id: '+sid)
            seen.add(sid);s=screens[sid]
            transform=re.fullmatch(r'translate\(\s*([-+\d.]+)[ ,]+([-+\d.]+)\s*\)',e.get('transform',''))
            if not transform:raise ContractError('Unsupported transform; retain IDs and translate(x y)')
            layout=dict(s.get('layout',{}));incoming={'x':float(transform[1]),'y':float(transform[2])};titles=frames=0
            for child in e:
                if child.get('data-field')=='title':s['title']=''.join(child.itertext());titles+=1
                if child.get('data-frame'):
                    frames+=1
                    for key in ('width','height'):incoming[key]=float(child.get(key))
                    incoming['fill']=child.get('fill','#ffffff')
                aid=child.get('data-action-id')
                if aid:
                    if aid not in actions or actions[aid]['screen_id']!=sid or aid in seen_actions:raise ContractError('Unknown/duplicate action binding')
                    seen_actions.add(aid)
                    actions[aid]['label']=''.join(child.itertext())
            for key,value in incoming.items():
                if key in layout or value!=defaults[sid][key]:layout[key]=value
            if layout:s['layout']=layout
            if titles!=1 or frames!=1:raise ContractError('Missing/duplicate screen title or frame')
        if seen!=set(screens) or seen_actions!=set(actions):raise ContractError('Missing screen/action bindings')
    elif source.suffix=='.mmd':
        match=re.search(r'^%% ux-base (.+)$',text,re.M)
        if not match:raise ContractError('Missing design baseline')
        base=require(json.loads(base64.b64decode(match[1],validate=True)));remote=copy.deepcopy(base)
        screens={s['id']:s for s in remote['screens']};transitions={t['id']:t for t in remote['transitions']};seen=set();error_sources={}
        state_nodes={s['id']+'__'+state:{'screen_id':s['id'],'state':state} for s in remote['screens'] for state in s['states']}
        for line in text.splitlines():
            node=re.fullmatch(r'\s*([A-Za-z][\w-]*)\["(.*)"\]\s*',line)
            edge=re.fullmatch(r'\s*([A-Za-z][\w-]*) -->\|"([A-Za-z][\w-]*): (.*)"\| ([A-Za-z][\w-]*)\s*',line)
            if node:
                if node[1] in seen:raise ContractError('Duplicate node binding')
                if node[1] in state_nodes:
                    value=state_nodes[node[1]];original=next(s for s in base['screens'] if s['id']==value['screen_id'])
                    if html.unescape(node[2])!=original['title']+' / '+value['state']:raise ContractError('State labels are derived; edit the canonical state and retain bindings')
                    seen.add(node[1]);continue
                if node[1] not in screens:raise ContractError('Unknown screen binding')
                screens[node[1]]['title']=html.unescape(node[2]);seen.add(node[1])
            elif edge:
                is_error=edge[2].endswith('__on_error');tid=edge[2].removesuffix('__on_error') if is_error else edge[2]
                if tid not in transitions:raise ContractError('Unknown transition binding')
                from_state=state_nodes.get(edge[1]);to_state=state_nodes.get(edge[4])
                if not from_state or not to_state:raise ContractError('Unknown transition state binding')
                t=transitions[tid]
                if edge[2] in seen:raise ContractError('Duplicate transition binding')
                seen.add(edge[2])
                if is_error:
                    if not t.get('on_error'):raise ContractError('New error edge requires a contract edit')
                    t['on_error']=copy.deepcopy(to_state);error_sources[tid]=from_state
                else:t['from']=copy.deepcopy(from_state);t['to']=copy.deepcopy(to_state);t['condition']=html.unescape(edge[3])
            elif line.strip() and not line.startswith(('flowchart','%%')):raise ContractError('Unmapped Mermaid syntax; review before importing')
        expected=set(screens)|set(state_nodes)|set(transitions)|{t['id']+'__on_error' for t in base['transitions'] if t.get('on_error')}
        if seen!=expected:raise ContractError('Missing design bindings; delete or add paths explicitly in the contract')
        if any(source!=transitions[tid]['from'] for tid,source in error_sources.items()):raise ContractError('Error edge source must match its transition source')
    elif source.suffix=='.json':
        value=read(source);base=value['base'];remote=value['contract']
    else:raise ContractError('Supported exchange: .svg, .mmd or {base,contract} JSON')
    marker=source.parent/'design-manifest.json'
    if source.suffix in ('.svg','.mmd') and marker.is_file():
        manifest=read(marker)
        if manifest.get('owner')==OWNER and manifest.get('contract_sha256')!=digest(base):raise ContractError('Embedded baseline changed; recover the original before reconciling')
    result=reconcile(base,contract,remote)
    if result['conflicts']:raise ContractError('Design conflicts require review: '+', '.join(c['path'] for c in result['conflicts']))
    return result['contract']


def can_regenerate(contract,source):
    """Only acknowledge source edits fully represented by the canonical model.

    Extra annotations/styles remain protected in their original file. Importing
    supported fields must never license removal of an unrelated human edit.
    """
    source=Path(source)
    if source.suffix not in ('.svg','.mmd'):return False
    with tempfile.TemporaryDirectory(prefix='ux-roundtrip-') as td:
        render_bundle(contract,td);expected=(Path(td)/('wireframes.svg' if source.suffix=='.svg' else 'flow.mmd')).read_text(encoding="utf-8")
    actual=source.read_text(encoding='utf-8')
    if source.suffix=='.mmd':
        states={s['id']+'__'+state for s in contract['screens'] for state in s['states']}
        def normalize(text):
            lines=[]
            for line in text.splitlines():
                if line.startswith('%% ux-base '):continue
                node=re.fullmatch(r'\s*([A-Za-z][\w-]*)\["(.*)"\]\s*',line)
                lines.append(node[1] if node and node[1] in states else line.strip())
            return sorted(line for line in lines if line)
        return normalize(actual)==normalize(expected)
    def normalize(text):
        root=ET.fromstring(text,parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
        def node(element):
            attrs=dict(element.attrib)
            for key in ('x','y','width','height','rx','font-size'):
                if key in attrs:
                    try:attrs[key]=str(float(attrs[key]))
                    except ValueError:pass
            if 'transform' in attrs:
                match=re.fullmatch(r'translate\(\s*([-+\d.]+)[ ,]+([-+\d.]+)\s*\)',attrs['transform'])
                if match:attrs['transform']='translate('+str(float(match[1]))+' '+str(float(match[2]))+')'
            content='' if element.get('id')=='ux-base' else element.text or ''
            return (str(element.tag),sorted(attrs.items()),content if content.strip() else '',[node(child) for child in element])
        return node(root)
    return normalize(actual)==normalize(expected)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for name in ('validate','export','import','diff'):
        p=commands.add_parser(name);p.add_argument('--contract',type=Path,required=True);p.add_argument('--project',type=Path)
        if name in ('export','import'):p.add_argument('--design',type=Path,required=True)
        if name in ('import','diff'):p.add_argument('--incoming',type=Path) if name=='diff' else p.add_argument('--apply',action='store_true')
    a=parser.parse_args(argv);contract=read(a.contract);require(contract,a.project)
    if a.command=='validate':result={'valid':True,'sha256':digest(contract),'required_checks':required_checks(contract)}
    elif a.command=='export':result=render_bundle(contract,a.design)
    elif a.command=='import':
        imported=import_design(contract,a.design);regenerable=can_regenerate(imported,a.design)
        result={'status':'ready','contract':imported,'applied':a.apply,'contract_changed':imported!=contract,
                'source_regeneration':'safe' if regenerable else 'preserved_unmapped_edits; export to another directory or reconcile explicitly'}
        if a.apply:
            if imported!=contract:write(a.contract,imported)
            marker=a.design.parent/'design-manifest.json'
            if marker.is_file():
                manifest=read(marker)
                if regenerable and manifest.get('owner')==OWNER and a.design.name in manifest.get('files',{}):
                    value=digest(a.design.read_bytes())
                    if manifest['files'][a.design.name]!=value:manifest['files'][a.design.name]=value;write(marker,manifest)
    else:
        if not a.incoming:parser.error('diff requires --incoming')
        incoming=read(a.incoming);result=reconcile(incoming['base'],contract,incoming['contract'])
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result.get('status')!='conflict' else 1



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':
    try:raise SystemExit(main())
    except (ContractError,OSError,ValueError,KeyError,TypeError,ET.ParseError) as error:
        print(json.dumps({'status':'blocked','error':str(error)},ensure_ascii=False));raise SystemExit(1)
