"""Freeze UX requirements and assess browser-owned contract observations."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil


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
    engine=helper();contract=engine.require(engine.read(source),project)
    required=engine.required_checks(contract,journeys)
    if not required:raise ContractBlocked('Selected UX contract has no required checks')
    snapshot=Path(run_dir)/'ux-contract.json';shutil.copyfile(source,snapshot);snapshot.chmod(0o600)
    return {'source':str(source),'snapshot':str(snapshot),'sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            'journeys':journeys or [j['id'] for j in contract['journeys'] if j['required']],'required_checks':required}


def assert_current(spec):
    if not spec:return
    for key in ('source','snapshot'):
        p=Path(spec[key])
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=spec['sha256']:raise ContractBlocked('UX design changed; preserve the run and reconcile before starting a new audit')


def context(spec):
    assert_current(spec)
    return {'contract':json.loads(Path(spec['snapshot']).read_text(encoding='utf-8')),'sha256':spec['sha256'],'journeys':spec['journeys'],'required_checks':spec['required_checks']}


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
        if frame.get('viewport')!=viewport or frame.get('url')!=entry.get('url') or frame.get('source')!='live':invalid.append('frame_metadata_mismatch');continue
        for item in entry.get('checks',[]):
            if item.get('id') in spec['required_checks']:verified[(item['id'],name)]={'passed':item.get('passed') is True,'frame_id':frame['id'],'observed':item.get('observed')}
    missing=[];failed=[]
    for name in viewports:
        for check in spec['required_checks']:
            value=verified.get((check,name))
            if value is None:missing.append({'id':check,'viewport':name})
            elif not value['passed']:failed.append({'id':check,'viewport':name,**value})
    return {'ready':not (missing or failed or invalid),'sha256':spec['sha256'],'required':len(spec['required_checks'])*len(viewports),
            'verified':len(verified),'missing':missing,'failed':failed,'invalid':invalid,'source':'browser receipts; not model self-report'}
