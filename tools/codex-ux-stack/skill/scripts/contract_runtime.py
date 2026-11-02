"""Freeze UX requirements and assess browser-owned contract observations."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import os


class ContractBlocked(ValueError):pass


def helper():
    here=Path(__file__).resolve().parent
    candidates=[here/'ux_contract.py',here.parents[1]/'ux-visual-design/scripts/ux_contract.py']
    path=next((p for p in candidates if p.is_file()),None)
    if path is None:raise ContractBlocked('UX contract helper is missing; update the managed harness')
    spec=importlib.util.spec_from_file_location('_ux_contract_runtime',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def freeze(path,project,run_dir,journeys=None):
    project=Path(project).resolve();source=Path(path).absolute()
    if not source.resolve().is_relative_to(project) or any(p.is_symlink() for p in (source,*source.parents)):raise ContractBlocked('Contract must be an unlinked file in the project')
    raw=source.read_bytes()
    contract_sha=hashlib.sha256(raw).hexdigest()
    if len(raw)>2_000_000:raise ContractBlocked('Oversized UX contract')
    engine=helper();contract=engine.require(json.loads(raw.decode('utf-8')),project)
    required=engine.required_checks(contract,journeys)
    if not required:raise ContractBlocked('Selected UX contract has no required checks')
    snapshot=Path(run_dir)/'ux-contract.json'
    with snapshot.open('wb') as stream:os.chmod(snapshot,0o600);stream.write(raw)
    references=[]
    for artifact in contract['artifacts']:
        spec=artifact.get('snapshot')
        if not spec:continue
        original=project/spec['path']
        if original.is_symlink() or not original.resolve().is_relative_to(project) or any(p.is_symlink() for p in (original,*original.parents)) or not original.is_file():raise ContractBlocked('Missing or linked design reference')
        raw=original.read_bytes()
        if len(raw)>20_000_000 or len(raw)<24 or raw[:8]!=b'\x89PNG\r\n\x1a\n' or hashlib.sha256(raw).hexdigest()!=spec['sha256']:raise ContractBlocked('Design reference hash or PNG mismatch')
        target=Path(run_dir)/'design-references'/(artifact['id']+'.png');target.parent.mkdir(exist_ok=True)
        with target.open('wb') as stream:os.chmod(target,0o600);stream.write(raw)
        references.append({'id':artifact['id'],'source':str(original),'snapshot':str(target),'sha256':spec['sha256'],'url':artifact['url'],'revision':artifact.get('revision','not_recorded')})
    result={'source':str(source),'snapshot':str(snapshot),'sha256':contract_sha,
            'journeys':journeys or [j['id'] for j in contract['journeys'] if j['required']],'required_checks':required,
            'design_references':references,'design_reference_required':contract['approval']['status']=='approved'}
    assert_current(result);return result


def assert_current(spec):
    if not spec:return
    for key in ('source','snapshot'):
        p=Path(spec[key])
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=spec['sha256']:raise ContractBlocked('UX design changed; preserve the run and reconcile before starting a new audit')
    for reference in spec.get('design_references',[]):
        for key in ('source','snapshot'):
            p=Path(reference[key])
            if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=reference['sha256']:raise ContractBlocked('Approved design reference changed; reconcile before starting a new audit')


def context(spec):
    assert_current(spec)
    return {'contract':json.loads(Path(spec['snapshot']).read_text(encoding='utf-8')),'sha256':spec['sha256'],'journeys':spec['journeys'],'required_checks':spec['required_checks'],
            'design_references':spec.get('design_references',[]),'design_reference_required':spec.get('design_reference_required',False)}


def validate_plan(plan,spec):
    contract=context(spec)['contract'];flow_ids={f['id'] for f in plan['flows'] if f['required']};screen_ids={s['id'] for s in plan['screens']}
    actions={aid for j in contract['journeys'] if j['id'] in spec['journeys'] for aid in j['actions']}
    required_screens={a['screen_id'] for a in contract['actions'] if a['id'] in actions}
    if not set(spec['journeys']).issubset(flow_ids) or not required_screens.issubset(screen_ids):raise ContractBlocked('Planner must retain the selected Journey and Screen IDs')


def observations(spec,role_dir,viewports):
    assert_current(spec);root=(Path(role_dir)/'screenshots').resolve();frames={};checks=[]
    for path in sorted(root.rglob('browser-receipts.jsonl')):
        for line in path.read_text(encoding='utf-8').splitlines():
            entry=json.loads(line)
            if entry.get('kind')=='frame':frames[entry['id']]=entry
            elif entry.get('kind')=='contract_check':checks.append(entry)
    verified={};invalid=[]
    widths={'desktop':(1440,900),'tablet':(768,1024),'mobile':(390,844)}
    for entry in checks:
        if entry.get('contract_sha256')!=spec['sha256']:continue
        frame=frames.get(entry.get('frame_id'));viewport=entry.get('viewport',{})
        size=(viewport.get('width'),viewport.get('height'));name=next((n for n,s in widths.items() if s==size),None)
        if not frame or name not in viewports:continue
        path=Path(frame.get('path','')).absolute()
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=frame.get('sha256'):
            invalid.append('invalid_frame');continue
        data=path.read_bytes()
        if len(data)<24 or data[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',data[16:24])!=size:
            invalid.append('invalid_frame_dimensions');continue
        if frame.get('viewport')!=viewport or frame.get('url')!=entry.get('url') or frame.get('source')!='live':invalid.append('frame_metadata_mismatch');continue
        for item in entry.get('checks',[]):
            if item.get('id') in spec['required_checks']:verified[(item['id'],name)]={'passed':item.get('passed') is True,'frame_id':frame['id'],'observed':item.get('observed')}
    missing=[];failed=[]
    for name in viewports:
        for check in spec['required_checks']:
            value=verified.get((check,name))
            if value is None:missing.append({'id':check,'viewport':name})
            elif not value['passed']:failed.append({'id':check,'viewport':name,**value})
    design_ready=not spec.get('design_reference_required') or bool(spec.get('design_references'))
    return {'ready':not (missing or failed or invalid) and design_ready,'sha256':spec['sha256'],'required':len(spec['required_checks'])*len(viewports),'design_reference_status':'ready' if spec.get('design_references') else 'missing' if spec.get('design_reference_required') else 'not_requested',
            'verified':len(verified),'missing':missing,'failed':failed,'invalid':invalid,'source':'browser receipts; not model self-report'}
