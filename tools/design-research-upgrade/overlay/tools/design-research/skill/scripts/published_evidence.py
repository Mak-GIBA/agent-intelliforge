"""Immutable, dependency-complete research evidence, independent of local runtime."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

GENERATOR='design-research-evidence-v1'


def safe(base,name):
    if not isinstance(name,str) or not name or '\\' in name:
        raise ValueError('Invalid evidence path')
    rel=Path(name)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Evidence path escapes its root')
    path=Path(os.path.abspath(Path(base)/rel))
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('Evidence symlinks are not supported')
    return path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def closure(workspace,run_id):
    files={};pending=[]
    def add(name,expected=None):
        path=safe(workspace,name)
        if not path.is_file():
            raise ValueError('Required evidence is missing: '+name)
        raw=path.read_bytes()
        if expected and sha(raw)!=expected:
            raise ValueError('Required evidence changed: '+name)
        if name not in files:
            files[name]=raw;pending.append(name)
    state_name=f'runs/{run_id}/state.json';add(state_name)
    state=json.loads(files[state_name])
    if (state.get('schema_version')!=1 or state.get('run_id')!=run_id
            or state.get('config',{}).get('mode')!='research' or state.get('status')!='research_complete'
            or not isinstance(state.get('dossier'),dict)):
        raise ValueError('Export requires an exact completed research run')
    if state.get('report_contract_version') == 2:
        # This verifier is also distributed in Upstream without the harness modules.
        def digest(value):
            return sha(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())
        writing=state.get('report_polish',{})
        basis={k:state.get(k) for k in ('dossier','review','evaluation_summary','expected_source','iteration','config')}
        if state.get('original_first_contract_version') == 1:basis['original_first']=state.get('original_first')
        science=digest(basis)
        required={'question','methods','results','support','adoption','limits','readability'}
        review=writing.get('review',{})
        if (writing.get('status')!='complete' or writing.get('science_sha256')!=science
                or review.get('status')!='reviewed' or review.get('accepted') is not True
                or review.get('issues') or set(review.get('checks',{}))!=required
                or not all(v is True for v in review['checks'].values())):
            raise ValueError('Report composition has no matching complete semantic review')
        paths=writing.get('artifacts',{})
        candidate=safe(workspace,paths.get('after')).read_text('utf-8')
        pack=json.loads(safe(workspace,paths.get('evidence')).read_text('utf-8'))
        if (candidate!=writing.get('approved_document') or sha(candidate.encode())!=writing.get('candidate_sha256')
                or digest(pack)!=writing.get('evidence_sha256') or pack.get('science_sha256')!=science
                or review.get('candidate_sha256')!=writing.get('candidate_sha256')
                or review.get('evidence_sha256')!=writing.get('evidence_sha256')):
            raise ValueError('Report composition approval/evidence changed')
    report=f'runs/{run_id}/reports/report.md'
    if not safe(workspace,report).is_file():
        report=f'runs/{run_id}/reports/design-research.md'
    add(report)
    writing=state.get('report_polish',{})
    writing_names=set()
    if writing.get('status')=='complete':
        for key,name in writing.get('artifacts',{}).items():
            add(name,writing['artifact_hashes'][key]);writing_names.add(name)
    if state.get('original_first_contract_version') == 1:
        for row in state.get('original_first',{}).get('artifacts',[]):add(row['path'],row['sha256'])
    for row in state.get('evidence',{}).values():
        add(row['path'],row['sha256'])
    for key in ('requirements_context','workstream_context'):
        ctx=state.get(key)
        if ctx:
            add(ctx['snapshot'],ctx.get('sha256') or ctx.get('plan_sha256'))
    for name,expected in state.get('unit_inputs',{}).items():
        # Old absolute paths remain unchanged inside the archived state.
        original=Path(state.get('workspace') or (Path(state['config']['project'])/'docs/design-research'/state['config']['slug']))
        rel=Path(name).relative_to(original).as_posix()
        add(rel,expected)
    for invocation in state.get('roles',[]):
        if invocation.get('receipt'):add(invocation['receipt'])
    def references(value):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and value.get('sha256'):
                add(value['path'],value['sha256'])
            for v in value.values():references(v)
        elif isinstance(value,list):
            for v in value:references(v)
    while pending:
        name=pending.pop();raw=files[name];path=Path(name)
        if path.name=='receipt.json':
            receipt=json.loads(raw);references(receipt)
            # Retain the actual role input as well as its validated output.
            for sibling in ('input.json','prompt.md','prompt.txt'):
                p=path.with_name(sibling)
                if safe(workspace,p.as_posix()).is_file():add(p.as_posix())
        if path.name=='state.json':
            for row in state.get('dossier',{}).get('sources',[]):
                if row.get('local_path'):add(row['local_path'])
            for row in state.get('dossier',{}).get('experiments',[]):
                if row.get('status')=='executed':
                    for artifact in row.get('artifacts',[]):add(artifact)
            for artifact in state.get('dossier',{}).get('evaluation_result',{}).get('artifact_paths',[]):add(artifact)
        if path.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',raw.decode('utf-8')):
                if target.startswith(('http:','https:','#','mailto:')):continue
                target=target.split('#',1)[0]
                if not target:continue
                origin=Path() if name in writing_names and writing.get('artifact_link_root')=='workspace' else path.parent
                absolute=Path(os.path.abspath(workspace/origin/target))
                if not absolute.is_relative_to(workspace):
                    raise ValueError('Archived report links outside workspace: '+target)
                add(absolute.relative_to(workspace).as_posix())
    return state,report,files


def verify(package):
    package=Path(os.path.abspath(package));manifest=safe(package,'manifest.json')
    data=json.loads(manifest.read_text('utf-8'))
    if data.get('generator')!=GENERATOR or data.get('schema_version')!=1 or not isinstance(data.get('files'),dict):
        raise ValueError('Unsupported evidence manifest')
    base=safe(package,'files')
    for name,expected in data['files'].items():
        path=safe(base,name)
        if not path.is_file() or sha(path.read_bytes())!=expected:
            raise ValueError('Published evidence missing or changed: '+name)
    # Reconstruct the dependency closure from frozen source bytes, not manifest claims alone.
    state,report,files=closure(base,data['run_id'])
    if set(files)-set(data['files']) or report!=data['report'] or state.get('config',{}).get('slug')!=data['topic']:
        raise ValueError('Evidence manifest omits required dependencies or mismatches identity')
    return data


def export(project,topic,run_id,apply=False,related_ids=()):
    try:from .workspace_paths import topic_workspace,checked,refresh_navigation
    except ImportError:from workspace_paths import topic_workspace,checked,refresh_navigation
    root=checked(project);workspace=topic_workspace(root,topic)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',run_id):raise ValueError('Unsafe run ID')
    state,report,files=closure(workspace,run_id)
    if state.get('config',{}).get('slug')!=topic:raise ValueError('Topic identity differs')
    target=checked(root/'docs/design-research'/topic/'evidence'/run_id)
    manifest={'schema_version':1,'generator':GENERATOR,'topic':topic,'run_id':run_id,
              'source_head':state.get('original_source',state.get('expected_source',{})).get('head',''),
              'related_ids':list(related_ids),'state':f'runs/{run_id}/state.json','report':report,
              'files':{name:sha(raw) for name,raw in sorted(files.items())}}
    binding={'state':(target/'files'/manifest['state']).relative_to(root).as_posix(),
             'report':(target/'files'/report).relative_to(root).as_posix(),
             'state_sha256':sha(files[manifest['state']]),'report_sha256':sha(files[report]),
             'evidence_manifest':(target/'manifest.json').relative_to(root).as_posix(),
             'evidence_manifest_sha256':sha((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())}
    if target.exists():
        if verify(target)!=manifest:raise ValueError('Published evidence is immutable; use a new run')
    elif apply:
        target.parent.mkdir(parents=True,exist_ok=True)
        staging=Path(tempfile.mkdtemp(prefix='.evidence-',dir=target.parent))
        try:
            for name,raw in files.items():
                p=safe(staging/'files',name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            (staging/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            # Absolute unit inputs in historical states are resolved via recorded workspace below.
            verify(staging)
            os.rename(staging,target)
        finally:
            if staging.exists():shutil.rmtree(staging)
        refresh_navigation(root)
    if apply:
        public=checked(root/'docs/design-research'/topic/'report.md')
        if public.is_file():
            text=public.read_text('utf-8')
            if run_id in text and text.startswith('<!-- Generated by design-research public-v1 -->'):
                def rebase(match):
                    name=match[1]
                    if name.startswith(('http:','https:','#','mailto:')):return match[0]
                    path=Path(os.path.abspath(public.parent/name))
                    if path.is_relative_to(workspace):
                        rel=path.relative_to(workspace).as_posix()
                        if rel.startswith('.internal/') or rel in {'status.json','evidence.json','research-log.json'}:
                            rel=f'runs/{run_id}/reports/'+Path(rel).name
                        if rel not in files:raise ValueError('Public report dependency missing from export: '+rel)
                        return ']('+os.path.relpath(target/'files'/rel,public.parent)+')'
                    return match[0]
                changed=re.sub(r'\]\(([^)]+)\)',rebase,text)
                temp=public.with_name('.report-export.tmp')
                try:
                    temp.write_text(changed,encoding='utf-8');os.replace(temp,public)
                finally:temp.unlink(missing_ok=True)
    return {'applied':apply,'package':target.relative_to(root).as_posix(),'files':len(files),
            'bytes':sum(map(len,files.values())),'binding':binding,
            'scope':'Integrity and complete recorded dependencies; no scientific or approval certification'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('export-evidence');q.add_argument('--project',default='.');q.add_argument('--topic',required=True)
    q.add_argument('--run-id',required=True);q.add_argument('--apply',action='store_true');q.add_argument('--related-id',action='append',default=[])
    q=sub.add_parser('verify-evidence');q.add_argument('--package',required=True)
    a=p.parse_args(argv)
    try:
        result=export(a.project,a.topic,a.run_id,a.apply,a.related_id) if a.cmd=='export-evidence' else {'valid':True,**verify(a.package)}
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('ERROR: '+str(exc));return 2

if __name__=='__main__':raise SystemExit(main())
