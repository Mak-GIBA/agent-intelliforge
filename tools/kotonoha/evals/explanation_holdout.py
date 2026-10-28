#!/usr/bin/env python3
"""Post-review correction on new inputs; original 48 trials stay immutable."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import random
import shutil
import tempfile
import run_study as base
import explanation_study as study

ARMS=('baseline','improved','revised')

def prompt(root,job,task):
    disclosure=dict(task,id='E07' if task.get('mail') else task['id'])
    return ('文章生成の規範は展開済みです。ツール・検索・他のスキルは使わず、完成稿だけ返してください。\n\n'
            + study.guide(root,job['arm'],disclosure)+'\n\n【依頼】\n'+task['instruction']+'\n【素材】\n'+task['input'])

def prepare(parent):
    root=parent/'holdout'
    if root.exists():raise ValueError('Never overwrite a completed correction study')
    root.mkdir()
    for arm in ARMS:
        source=study.ROOT/'assets' if arm=='revised' else parent/'snapshots'/arm/'assets'
        shutil.copytree(source,root/'snapshots'/arm/'assets',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(parent/'upstream',root/'upstream')
    tasks=json.loads((study.ROOT/'evals/explanation-holdout.json').read_text())['tasks']
    c=json.loads((parent/'contract.json').read_text())
    contract={k:c[k] for k in ('model','effort','cli_version','timeout_seconds','concurrency','automatic_retries')}
    contract.update(schema=1,parent_contract_sha256=base.sha((parent/'contract.json').read_bytes()),
        tasks=tasks,arms=ARMS,repeats=1,seed=c['seed']+2,
        purpose='Check correction of reason-vs-procedure on unseen inputs; do not replace the initial primary outcome',
        primary_tasks=['H01','H02'],acceptance='H01/H02 revised causal clarity and reader understanding >=3; no critical findings or damage to H05/H06. Exploratory, not proof of general superiority.',
        axes=study.AXES,files=study.hashes(root),
        script_sha256=base.sha(Path(__file__).read_bytes()))
    base.save(root/'contract.json',contract)
    jobs=[{'task':t['id'],'arm':a,'repeat':1} for t in tasks for a in ARMS]
    random.Random(contract['seed']).shuffle(jobs);base.save(root/'jobs.json',jobs)
    return contract

def write_one(root,job,c,disabled):
    target=root/'writing'/f"{job['task']}-{job['arm']}-1.json"
    if target.exists():return target.stem,'retained_'+json.loads(target.read_text())['status']
    task=next(t for t in c['tasks'] if t['id']==job['task'])
    with tempfile.TemporaryDirectory(prefix='yomiyasu-depth-holdout-') as tmp:
        result=base.execute(prompt(root,job,task),Path(tmp),c,disabled)
    base.save(target,dict(result,**job));return target.stem,result['status']

def summarize(root):
    mapping=json.loads((root/'blind.private.json').read_text());ratings={}
    for p in (root/'grades').glob('*.json'):
        row=json.loads(p.read_text())
        if row['status']=='completed':
            study.validate_ratings(row['ratings'],row['labels'])
            for rating in row['ratings']:
                name=mapping[rating['id']]
                if name in ratings:raise ValueError('Duplicate grade')
                ratings[name]=rating
    writing={p.name:json.loads(p.read_text()) for p in (root/'writing').glob('*.json')}
    result={'attempted':len(writing),'completed':sum(r['status']=='completed' for r in writing.values()),'rated':len(ratings),'conditions':{}}
    for arm in ARMS:
        rows={n:r for n,r in writing.items() if r['arm']==arm};scored=[ratings[n] for n in rows if n in ratings]
        result['conditions'][arm]={'axes':{a:round(sum(s[a] for s in scored)/len(scored),4) if scored else None for a in study.AXES},
            'meaning_error_outputs':sum(bool(s['meaning_errors']) for s in scored),
            'requester_residue_outputs':sum(bool(s['requester_residue']) for s in scored),
            'target_scores':{t:{a:ratings[f'{t}-{arm}-1.json'][a] for a in ('causal_clarity','reader_understanding')}
                             for t in ('H01','H02') if f'{t}-{arm}-1.json' in ratings}}
    revised=[ratings.get(f'{t}-revised-1.json') for t in ('H01','H02')]
    result['target_gate_pass']=all(s and s['causal_clarity']>=3 and s['reader_understanding']>=3 for s in revised)
    result['ratings_complete']=len(writing)==18 and len(ratings)==result['completed']
    return result

def audit(root):
    c=json.loads((root/'contract.json').read_text());study.verify_inputs(root,c)
    if c['script_sha256']!=base.sha(Path(__file__).read_bytes()):raise ValueError('Holdout runner changed')
    jobs=json.loads((root/'jobs.json').read_text());expected={f"{j['task']}-{j['arm']}-1.json" for j in jobs}
    if len(expected)!=18 or {p.name for p in (root/'writing').glob('*.json')}!=expected:raise ValueError('Incomplete holdout matrix')
    for job in jobs:
        row=json.loads((root/'writing'/f"{job['task']}-{job['arm']}-1.json").read_text())
        task=next(t for t in c['tasks'] if t['id']==job['task'])
        if row['prompt_sha256']!=base.sha(prompt(root,job,task).encode()):raise ValueError('Holdout prompt changed')
    mapping=json.loads((root/'blind.private.json').read_text())
    for p in (root/'grades').glob('*.json'):
        row=json.loads(p.read_text())
        if row['prompt_sha256']!=base.sha(study.grade_prompt(root,row['labels'],mapping,c).encode()):raise ValueError('Holdout grader changed')
    result=summarize(root)
    if result!=json.loads((root/'summary.json').read_text()):raise ValueError('Holdout summary changed')
    return {'writing_prompts_verified':18,'grade_prompts_verified':len(list((root/'grades').glob('*.json'))),'ratings_complete':result['ratings_complete']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['prepare','writing','grading','summary'])
    p.add_argument('--out',type=Path,required=True);args=p.parse_args();parent=args.out.resolve();root=parent/'holdout'
    if args.phase=='prepare':print(json.dumps(prepare(parent),ensure_ascii=False)[:450]);return
    c=json.loads((root/'contract.json').read_text());study.verify_inputs(root,c)
    disabled=json.loads((parent/'locations.private.json').read_text())['disabled']
    if args.phase=='summary':
        result=summarize(root);base.save(root/'summary.json',result);print(json.dumps(result,ensure_ascii=False,indent=2));return
    if args.phase=='writing':
        jobs=json.loads((root/'jobs.json').read_text());fn=lambda j:write_one(root,j,c,disabled)
    else:
        mapping=study.anonymize(root,c);jobs=list(enumerate(json.loads((root/'grading-jobs.json').read_text()),1))
        fn=lambda j:study.grade_one(root,j[0],j[1],mapping,c,disabled)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for job in as_completed([pool.submit(fn,j) for j in jobs]):print(*job.result(),flush=True)

if __name__=='__main__':main()
