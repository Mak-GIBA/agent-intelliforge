#!/usr/bin/env python3
"""Frozen, anonymous old/new prose comparison. Does not install user skills."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile

import run_study as base

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('baseline', 'improved')
AXES = ('specificity', 'causal_clarity', 'reader_understanding', 'naturalness',
        'information_efficiency', 'paragraph', 'meaning_preservation', 'reader_boundary')
PRIMARY = {'E01', 'E02', 'E03', 'E04', 'E05', 'E09', 'E10', 'E11', 'E12'}
RUBRIC = '''文章の使用条件や作成方法を推測せず、依頼、素材、保護事項と完成稿だけを評価してください。
8軸は具体性、因果の明瞭さ、読者理解、自然さ、情報効率、段落構造、意味保持、指示者向け表現の不在。
各0〜4: 0=目的不達、1=大幅な修正、2=局所修正が必要、3=実用可能、4=ほぼ修正不要。
説明不要の原稿・メールでは、余計な説明を足さず理解できる状態を高く評価してください。
素材にない原因・数値・実績、条件や確信度の変化をmeaning_errorsへ、制作説明の混入をrequester_residueへ記録。
素材から分かる処理の展開と、許された仮想例は捏造としない。接続詞の数だけで判定せず内容を読む。
重要な理由や処理が分からない、抽象語の言い換え、必要のない例や結論はその箇所を理由に示す。
各完成稿を独立に採点し、異なる文面を作ったこと自体は改善としない。ツールは使わずJSONだけ返してください。'''

def hashes(directory):
    return {p.relative_to(directory).as_posix(): base.sha(p.read_bytes())
            for p in sorted(directory.rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and not p.name.endswith('.private.json')}

def guide(root, arm, task):
    assets = root/'snapshots'/arm/'assets'
    paths = [p for p in sorted(assets.rglob('*.md')) if p.name not in {'sources.md', 'AGENTS_APPEND.md'}
             and (p.name != 'explanation.md' or task['explanation'])]
    upstream = root/'upstream'
    paths += [upstream/'SKILL.upstream.md', upstream/'references/slop-catalog.md',
              upstream/'references/gemini-syntax.md']
    domain = 'business' if task['id'] == 'E07' else 'tech'
    paths += [upstream/f'references/domains/{domain}.md']
    return '\n\n'.join('【'+p.relative_to(root).as_posix().split('/assets/')[-1]+'】\n'+p.read_text()
                        for p in paths)

def writing_prompt(root, job, task):
    return ('文章生成の規範は展開済みです。ツール・検索・他のスキルは使わず、完成稿だけ返してください。\n\n'
            + guide(root, job['arm'], task) + '\n\n【依頼】\n'+task['instruction']+'\n【素材】\n'+task['input'])

def prepare(root, upstream):
    import tomllib  # Research only; offline installation remains Python 3.10+.
    if (root/'contract.json').exists():
        raise ValueError('Use a new contract; do not overwrite published results')
    baseline = root/'snapshots/baseline/assets'
    if not baseline.is_dir():
        raise ValueError('Snapshot the actual prior release before editing')
    shutil.copytree(ROOT/'assets',root/'snapshots/improved/assets',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(upstream,root/'upstream',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (root/'method').mkdir()
    for name in ('explanation_study.py', 'explanation-tasks.json', 'EXPLANATION_STUDY.md', 'run_study.py'):
        shutil.copy2(ROOT/'evals'/name,root/'method'/name)
    tasks = json.loads((root/'method/explanation-tasks.json').read_text())['tasks']
    cfg = tomllib.loads((Path.home()/'.codex/config.toml').read_text())
    contract = {'schema':1,'created':datetime.now(timezone.utc).isoformat(),'arms':ARMS,'repeats':2,
        'model':cfg['model'],'effort':cfg.get('model_reasoning_effort','medium'),
        'cli_version':subprocess.check_output(['codex','--version'],text=True).strip(),
        'seed':20261012,'temperature':'uncontrolled','tasks':tasks,'axes':AXES,
        'primary_tasks':sorted(PRIMARY),'primary_threshold':0.25,
        'grader':'Anonymous separate same-model sessions; no independent human raters',
        'timeout_seconds':480,'concurrency':2,'automatic_retries':0,
        'files':{p:base.sha((root/p).read_bytes()) for folder in ('snapshots','upstream','method')
                 for p in [folder+'/'+rel for rel in hashes(root/folder)]}}
    base.save(root/'contract.json',contract)
    base.save(root/'locations.private.json',{'disabled':base.globals_to_disable()})
    jobs = [{'task':t['id'],'arm':a,'repeat':r} for t in tasks for a in ARMS for r in (1,2)]
    random.Random(contract['seed']).shuffle(jobs);base.save(root/'jobs.json',jobs)
    return contract

def verify_inputs(root, contract):
    for rel, expected in contract['files'].items():
        if base.sha((root/rel).read_bytes()) != expected:
            raise ValueError('Frozen input changed: '+rel)

def write_one(root, job, contract, disabled):
    target = root/'writing'/f"{job['task']}-{job['arm']}-{job['repeat']}.json"
    if target.exists():
        return target.stem,'retained_'+json.loads(target.read_text())['status']
    task = next(t for t in contract['tasks'] if t['id']==job['task'])
    with tempfile.TemporaryDirectory(prefix='yomiyasu-depth-writing-') as tmp:
        result = base.execute(writing_prompt(root,job,task),Path(tmp),contract,disabled)
    if result['status']=='completed' and not (result.get('output') or '').strip():
        result['status']='empty_output'
    base.save(target,dict(result,**job))
    return target.stem,result['status']

def anonymize(root, contract):
    if (root/'blind.private.json').exists():
        return json.loads((root/'blind.private.json').read_text())
    rows=[]
    for p in sorted((root/'writing').glob('*.json')):
        if json.loads(p.read_text())['status']=='completed':rows.append(p.name)
    random.Random(contract['seed']+1).shuffle(rows)
    mapping={f'O{i+1:03}':name for i,name in enumerate(rows)}
    base.save(root/'blind.private.json',mapping)
    base.save(root/'grading-jobs.json',[list(mapping)[i:i+4] for i in range(0,len(mapping),4)])
    return mapping

def grade_prompt(root, labels, mapping, contract):
    rows=[]
    for label in labels:
        row=json.loads((root/'writing'/mapping[label]).read_text())
        task=next(t for t in contract['tasks'] if t['id']==row['task'])
        rows.append({'id':label,'instruction':task['instruction'],'material':task['input'],
                     'requirements':task['requirements'],'text':row['output']})
    return RUBRIC+'\n\n'+json.dumps(rows,ensure_ascii=False)

def schema():
    properties={'id':{'type':'string'},**{a:{'type':'integer','minimum':0,'maximum':4} for a in AXES},
                'meaning_errors':{'type':'array','items':{'type':'string'}},
                'requester_residue':{'type':'array','items':{'type':'string'}},
                'reason':{'type':'string'}}
    return {'type':'object','additionalProperties':False,'required':['ratings'],'properties':{
        'ratings':{'type':'array','items':{'type':'object','additionalProperties':False,
            'required':list(properties),'properties':properties}}}}

def validate_ratings(ratings, labels):
    if len(ratings)!=len(labels) or Counter(r.get('id') for r in ratings)!=Counter(labels):
        raise ValueError('Missing, duplicate or unknown anonymous output')
    for row in ratings:
        for axis in AXES:
            if type(row.get(axis)) is not int or not 0<=row[axis]<=4:
                raise ValueError('Invalid rating: '+axis)
        for field in ('meaning_errors','requester_residue'):
            if not isinstance(row.get(field),list) or not all(isinstance(v,str) for v in row[field]):
                raise ValueError('Invalid critical findings')
        if not isinstance(row.get('reason'),str) or not row['reason'].strip():
            raise ValueError('Missing rationale')

def grade_one(root, index, labels, mapping, contract, disabled):
    target=root/'grades'/f'B{index:02}.json'
    if target.exists():return target.stem,'retained_'+json.loads(target.read_text())['status']
    with tempfile.TemporaryDirectory(prefix='yomiyasu-depth-grading-') as tmp:
        result=base.execute(grade_prompt(root,labels,mapping,contract),Path(tmp),contract,disabled,schema=schema())
    ratings=[]
    if result['status']=='completed':
        try:
            ratings=json.loads(result['output'])['ratings'];validate_ratings(ratings,labels)
        except (ValueError,KeyError,TypeError) as exc:
            result['status']='invalid_rating';result['error']=str(exc);ratings=[]
    base.save(target,dict(result,labels=labels,ratings=ratings))
    return target.stem,result['status']

def summarize(root):
    contract=json.loads((root/'contract.json').read_text());mapping=json.loads((root/'blind.private.json').read_text())
    writing={p.name:json.loads(p.read_text()) for p in (root/'writing').glob('*.json')}
    ratings={}
    for p in (root/'grades').glob('*.json'):
        receipt=json.loads(p.read_text())
        if receipt['status']=='completed':
            validate_ratings(receipt['ratings'],receipt['labels'])
            for row in receipt['ratings']:
                name=mapping[row['id']]
                if name in ratings:raise ValueError('Duplicate rating: '+name)
                ratings[name]=row
    result={'attempted':len(writing),'expected':48,'completed':sum(r['status']=='completed' for r in writing.values()),
            'rated':len(ratings),'conditions':{},'paired':[]}
    for arm in ARMS:
        rows=[(n,r) for n,r in writing.items() if r['arm']==arm]
        scored=[ratings[n] for n,r in rows if n in ratings]
        primary=[ratings[n] for n,r in rows if n in ratings and r['task'] in PRIMARY]
        mean=lambda vals:round(sum(vals)/len(vals),4) if vals else None
        result['conditions'][arm]={'attempted':len(rows),'statuses':dict(Counter(r['status'] for n,r in rows)),
            'rated':len(scored),'axes':{a:mean([s[a] for s in scored]) for a in AXES},
            'primary':mean([s[a] for s in primary for a in AXES[:3]]),
            'meaning_error_outputs':sum(bool(s['meaning_errors']) for s in scored),
            'requester_residue_outputs':sum(bool(s['requester_residue']) for s in scored),
            'mean_output_characters':mean([len(r['output']) for n,r in rows if r['status']=='completed']),
            'mean_elapsed_seconds':mean([r['elapsed_seconds'] for n,r in rows]),
            'mean_input_tokens':mean([r['usage']['input_tokens'] for n,r in rows if r.get('usage')]),
            'mean_output_tokens':mean([r['usage']['output_tokens'] for n,r in rows if r.get('usage')])}
    for task in contract['tasks']:
        for repeat in (1,2):
            names=[f"{task['id']}-{arm}-{repeat}.json" for arm in ARMS]
            if all(n in ratings for n in names):
                before,after=[ratings[n] for n in names]
                result['paired'].append({'task':task['id'],'repeat':repeat,
                    'deltas':{a:after[a]-before[a] for a in AXES}})
    primary_pairs=[r for r in result['paired'] if r['task'] in PRIMARY]
    result['primary_paired_delta']=round(sum(p['deltas'][a] for p in primary_pairs for a in AXES[:3])/(len(primary_pairs)*3),4) if primary_pairs else None
    result['ratings_complete']=len(ratings)==result['completed'] and len(writing)==48
    result['improvement_threshold_met']=bool(result['ratings_complete'] and result['primary_paired_delta'] is not None
        and result['primary_paired_delta']>=contract['primary_threshold'])
    return result

def audit(root):
    contract=json.loads((root/'contract.json').read_text());verify_inputs(root,contract)
    jobs=json.loads((root/'jobs.json').read_text())
    expected={f"{j['task']}-{j['arm']}-{j['repeat']}.json" for j in jobs}
    if len(expected)!=48 or {p.name for p in (root/'writing').glob('*.json')}!=expected:
        raise ValueError('Incomplete writing matrix')
    for job in jobs:
        row=json.loads((root/'writing'/f"{job['task']}-{job['arm']}-{job['repeat']}.json").read_text())
        task=next(t for t in contract['tasks'] if t['id']==job['task'])
        if row['prompt_sha256']!=base.sha(writing_prompt(root,job,task).encode()):
            raise ValueError('Writing prompt changed')
    mapping=json.loads((root/'blind.private.json').read_text())
    for p in (root/'grades').glob('*.json'):
        row=json.loads(p.read_text())
        if row['prompt_sha256']!=base.sha(grade_prompt(root,row['labels'],mapping,contract).encode()):
            raise ValueError('Grading prompt changed')
    result=summarize(root)
    if result!=json.loads((root/'summary.json').read_text()):raise ValueError('Summary changed')
    return {'writing_prompts_verified':48,'grade_prompts_verified':len(list((root/'grades').glob('*.json'))),
            'inputs_verified':len(contract['files']),'ratings_complete':result['ratings_complete']}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','writing','grading','summary','audit'])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--upstream-dir',type=Path)
    args=parser.parse_args();root=args.out.resolve()
    if args.phase=='prepare':
        c=prepare(root,args.upstream_dir);print(json.dumps({k:c[k] for k in ('model','effort','cli_version','repeats')}));return
    c=json.loads((root/'contract.json').read_text());verify_inputs(root,c)
    disabled=json.loads((root/'locations.private.json').read_text())['disabled']
    if args.phase in {'writing','grading'}:
        if args.phase=='writing':
            jobs=json.loads((root/'jobs.json').read_text())
            fn=lambda j:write_one(root,j,c,disabled)
        else:
            mapping=anonymize(root,c);units=json.loads((root/'grading-jobs.json').read_text())
            jobs=list(enumerate(units,1));fn=lambda j:grade_one(root,j[0],j[1],mapping,c,disabled)
        with ThreadPoolExecutor(max_workers=2) as pool:
            # Submit once; print as completed without retrying saved failures.
            from concurrent.futures import as_completed
            for future in as_completed([pool.submit(fn,j) for j in jobs]):print(*future.result(),flush=True)
    elif args.phase=='summary':
        result=summarize(root);base.save(root/'summary.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        result=audit(root);base.save(root/'audit.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
