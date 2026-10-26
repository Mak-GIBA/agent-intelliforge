#!/usr/bin/env python3
"""Explicit repository maintenance. Never installs Skills or starts a model."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
if 'I' not in globals():
    spec = importlib.util.spec_from_file_location('kotonoha_update_engine', HERE/'installer.py')
    I = importlib.util.module_from_spec(spec); sys.modules[spec.name] = I; spec.loader.exec_module(I)
SOURCE = HERE/'assets/kotonoha'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def digest(root):
    return {name: I.sha(raw) for name,raw in I.inventory(root).items()
            if '__pycache__' not in Path(name).parts and not name.endswith('.pyc')}


def resources(root):
    values = I.inventory(root)
    save(root/'resources.json', {'schema':1,'kind':'kotonoha-source-integrity',
         'files':{name:I.sha(raw) for name,raw in values.items() if name.startswith(('upstream/','meiseki-upstream/'))}})


def prepare(candidate, source='all', ref=None, destination=SOURCE):
    I.safe_path(candidate); I.safe_path(destination)
    if candidate.exists(): raise ValueError('Use a new candidate directory')
    if candidate.is_relative_to(destination) or destination.is_relative_to(candidate):
        raise ValueError('Candidate and maintained source must not contain each other')
    if ref and source=='all': raise ValueError('A tag pin needs one selected source')
    active = json.loads((destination/'UPSTREAMS.json').read_text('utf-8'))
    selected = ('yomiyasu','meiseki') if source=='all' else (source,)
    fetched = {}
    for name in selected:
        meta = I.resolve_release(ref) if name=='yomiyasu' else I.resolve_meiseki(ref)
        files = I.fetch_release(meta) if name=='yomiyasu' else I.fetch_meiseki_release(meta)
        if name=='yomiyasu': files['UPSTREAM.json']=(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()
        fetched[name] = (meta,files)
    candidate.mkdir(parents=True)
    try:
        adapter = candidate/'adapter'; shutil.copytree(destination, adapter)
        before = digest(destination)
        for name,(meta,files) in fetched.items():
            directory = adapter/('upstream' if name=='yomiyasu' else 'meiseki-upstream')
            if directory.exists(): shutil.rmtree(directory)
            for rel,raw in files.items():
                path=adapter/I.safe_rel(rel); path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            active['sources'][name] = meta
        active['integration']={'status':'pending','scope':'writing and revision only'}
        save(adapter/'UPSTREAMS.json',active); resources(adapter)
        immutable = {k:v for k,v in digest(adapter).items() if k.startswith(('upstream/','meiseki-upstream/'))}
        save(candidate/'candidate.json',{'schema':1,'base_sha256':before,'original_sha256':immutable,
             'sources':active['sources'],'selected':list(selected)})
        save(candidate/'changes.json',{'added':sorted(set(immutable)-set(before)),
             'changed':sorted(k for k in immutable if k in before and immutable[k]!=before[k]),
             'removed':sorted(k for k in before if k.startswith(('upstream/','meiseki-upstream/')) and k not in immutable)})
        save(candidate/'review.json',{'reviewed':False,'capabilities':[], 'unintegrated':[],
             'source_changes':[], 'scope':'writing and revision; hooks/quizzes excluded'})
    except BaseException:
        shutil.rmtree(candidate);raise
    return {'status':'prepared','candidate':str(candidate),'applied':False,'sources':active['sources']}


def inspect(candidate):
    I.safe_path(candidate)
    state=json.loads((candidate/'candidate.json').read_text('utf-8'))
    if state.get('schema')!=1:raise ValueError('Invalid candidate')
    actual=digest(candidate/'adapter')
    originals={k:v for k,v in actual.items() if k.startswith(('upstream/','meiseki-upstream/'))}
    if originals!=state['original_sha256']:raise ValueError('Frozen originals changed')
    active=json.loads((candidate/'adapter/UPSTREAMS.json').read_text('utf-8'))
    if active.get('sources')!=state['sources']:raise ValueError('Frozen source identities changed')
    return state,actual


def verify(candidate):
    state,actual=inspect(candidate); adapter=candidate/'adapter'
    review=json.loads((candidate/'review.json').read_text('utf-8'))
    capabilities=json.loads((adapter/'capabilities.json').read_text('utf-8'))['capabilities']
    if review.get('reviewed') is not True or review.get('unintegrated') or set(review.get('capabilities',[]))!={x['id'] for x in capabilities}:
        raise ValueError('Capability/source review is incomplete')
    if not review.get('source_changes'):raise ValueError('Explain adopted and excluded upstream changes')
    quality=json.loads((candidate/'quality.json').read_text('utf-8'))
    expected={'E'+str(n).zfill(2) for n in range(1,13)}|{'K'+str(n).zfill(2) for n in range(1,7)}
    if quality.get('status')!='passed' or len(quality.get('case_ids',[]))!=len(expected) or set(quality.get('case_ids',[]))!=expected or quality.get('critical_errors') or quality.get('unresolved_regressions'):
        raise ValueError('Paired quality comparison is incomplete or failed')
    # The model runner binds evidence to the exact normative text, scripts and originals.
    bound={k:v for k,v in actual.items() if k not in {'UPSTREAMS.json','resources.json'}}
    if quality.get('adapter_sha256')!=bound:raise ValueError('Quality evidence belongs to another adapter')
    artifacts=quality.get('artifacts',{})
    if not artifacts:raise ValueError('Missing actual quality outputs/reviews')
    for name,expected_hash in artifacts.items():
        path=candidate/I.safe_rel(name);I.safe_path(path)
        if not path.is_file() or I.sha(path.read_bytes())!=expected_hash:raise ValueError('Quality artifact changed')
    for path in adapter.rglob('*.py'):ast.parse(path.read_text('utf-8'),filename=str(path))
    I.upstream_contract(I.inventory(adapter))
    resources(adapter)
    with tempfile.TemporaryDirectory(prefix='kotonoha-verify-') as td:
        root=Path(td);left=root/'before.md';right=root/'after.md'
        left.write_text('# 確認\n\n入力値は3件です。\n',encoding='utf-8');right.write_bytes(left.read_bytes())
        command=[sys.executable,'-B',str(adapter/'scripts/check.py'),'compare',str(left),str(right)]
        r=subprocess.run(command,capture_output=True,text=True,timeout=45)
        if r.returncode not in (0,1) or json.loads(r.stdout)['upstream']['status']!='EXECUTED':
            raise ValueError('Relocatable source checker failed: '+r.stderr[-800:])
    save(candidate/'verification.json',{'schema':1,'status':'passed', 'adapter_sha256':digest(adapter),
        'review_sha256':I.sha((candidate/'review.json').read_bytes()),
        'quality_sha256':I.sha((candidate/'quality.json').read_bytes()),'scope':'recorded fixtures, not universal quality proof'})
    return {'status':'verified','applied':False}


def promote(candidate, destination=SOURCE):
    I.safe_path(destination)
    with I.lock(destination):
        return _promote_locked(candidate, destination)


def _promote_locked(candidate, destination):
    state,actual=inspect(candidate)
    evidence=json.loads((candidate/'verification.json').read_text('utf-8'))
    if (evidence.get('status')!='passed' or evidence.get('adapter_sha256')!=actual
        or evidence.get('review_sha256')!=I.sha((candidate/'review.json').read_bytes())
        or evidence.get('quality_sha256')!=I.sha((candidate/'quality.json').read_bytes())):
        raise ValueError('Verification is missing or stale')
    quality=json.loads((candidate/'quality.json').read_text('utf-8'))
    for name,sha in quality['artifacts'].items():
        path=candidate/I.safe_rel(name);I.safe_path(path)
        if I.sha(path.read_bytes())!=sha:raise ValueError('Quality artifact changed')
    if digest(destination)!=state['base_sha256']:raise ValueError('Maintained source changed since preparation')
    I.safe_path(destination)
    stage=Path(tempfile.mkdtemp(prefix='.kotonoha-promote-',dir=destination.parent))
    try:
        shutil.copytree(candidate/'adapter',stage,dirs_exist_ok=True)
        active=json.loads((stage/'UPSTREAMS.json').read_text('utf-8'))
        active['integration']={'status':'verified','scope':'recorded capability and quality tests',
            'quality_sha256':evidence['quality_sha256'],'review_sha256':evidence['review_sha256']}
        save(stage/'UPSTREAMS.json',active)
        shutil.copytree(destination,candidate/'previous')
        if digest(destination)!=state['base_sha256']:raise ValueError('Source changed during preparation')
        I.replace_directories([(stage,destination)])
    finally:
        if stage.exists():shutil.rmtree(stage)
    return {'status':'promoted','applied':True,'destination':str(destination)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('check','prepare','verify','promote'))
    p.add_argument('--source',choices=('all','yomiyasu','meiseki'),default='all')
    p.add_argument('--candidate',type=Path);p.add_argument('--ref')
    a=p.parse_args()
    try:
        if a.action=='check':
            if a.ref and a.source=='all':raise ValueError('A tag pin needs one selected source')
            result=I.check_updates(Path('/nonexistent-kotonoha-preview'),ref=a.ref,source=a.source)
        else:
            if a.candidate is None:p.error('--candidate is required')
            candidate=I.abs_path(a.candidate)
            result=prepare(candidate,a.source,a.ref) if a.action=='prepare' else verify(candidate) if a.action=='verify' else promote(candidate)
        # Avoid dumping full inventories into routine update output.
        if 'sources' in result:result['sources']={n:{k:m.get(k) for k in ('tag','commit')} for n,m in result['sources'].items()}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,RuntimeError,KeyError,subprocess.SubprocessError) as exc:
        print(json.dumps({'status':'held','applied':False,'error':str(exc)},ensure_ascii=False));return 2



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':raise SystemExit(main())
