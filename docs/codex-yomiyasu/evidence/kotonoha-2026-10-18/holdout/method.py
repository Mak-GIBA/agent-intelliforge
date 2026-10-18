#!/usr/bin/env python3
"""Three-arm frozen prose comparison; never installs user Skills or stores reasoning."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import shutil
import tempfile
import tomllib
import subprocess
import run_study as base
import explanation_study as grading

ROOT=Path(__file__).resolve().parents[1]
ARMS=('baseline','stacked','kotonoha')


def save(path,value):base.save(path,value)


def prepare(out,baseline,holdout=None):
    global ARMS
    if holdout: ARMS=('baseline','initial','revised')
    if out.exists():raise ValueError('Use a new immutable study directory')
    out.mkdir(parents=True)
    shutil.copytree(baseline,out/'snapshots/baseline',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(ROOT/'assets',out/'snapshots'/('revised' if holdout else 'kotonoha'),ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    if holdout:shutil.copytree(holdout/'snapshots/kotonoha',out/'snapshots/initial')
    upstream=ROOT/'evaluation-explanation/upstream'
    shutil.copytree(upstream,out/'upstream',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    tasks=json.loads((ROOT/'evals/explanation-tasks.json').read_text(encoding='utf-8'))['tasks']
    tasks[8]={'id':'E09','explanation':False,'instruction':'技術マニュアルの意味と確信度を保って推敲し、完成稿だけ返してください。',
        'input':'設定が無効でない限り、再送が行われないということはない。ただし、負荷の増大を招かないとは言えない。ログを出さないことを推奨しているわけではない。',
        'requirements':['二重否定の向きと条件を保持','負荷増大は可能性であり必然にしない','ログ出力を必須にしない']}
    tasks[9]={'id':'E10','explanation':False,'instruction':'説明の順序と専門用語を保ち、読みやすく推敲してください。',
        'input':'利用者が入力した値の妥当性の検証の実施の後にその値の保存の処理を担当するsaveValue関数は、検証に失敗したときには保存を行わず、成功したときだけ保存することができます。',
        'requirements':['saveValueを保持','検証成功時だけ保存','検証失敗時は保存しない']}
    if holdout:tasks=json.loads((ROOT/'evals/kotonoha-holdout.json').read_text(encoding='utf-8'))['tasks']
    cfg=tomllib.loads((Path.home()/'.codex/config.toml').read_text(encoding='utf-8'))
    c={'schema':1,'created':datetime.now(timezone.utc).isoformat(),'arms':ARMS,'tasks':tasks,'repeats':2,
       'model':cfg['model'],'effort':cfg.get('model_reasoning_effort','medium'),
       'cli_version':subprocess.check_output(['codex','--version'],text=True).strip(),'seed':20261018,
       'rubric':grading.RUBRIC,'axes':grading.AXES,'timeout_seconds':480,'automatic_retries':0,
       'grader':'Separate anonymous sessions of the same model; no independent human raters',
       'selection':'No increase in critical meaning errors/requester residue; no loss of explanation depth, naturalness or efficiency. Prefer smaller instructions in a tie.',
       'temperature':'not controlled by CLI','files':{}}
    for p in sorted(out.rglob('*')):
        if p.is_file():c['files'][p.relative_to(out).as_posix()]=base.sha(p.read_bytes())
    save(out/'contract.json',c)
    save(out/'locations.private.json',{'disabled':base.globals_to_disable()})
    jobs=[{'task':t['id'],'arm':a,'repeat':r} for t in tasks for a in ARMS for r in (1,2)]
    random.Random(c['seed']).shuffle(jobs);save(out/'jobs.json',jobs)
    shutil.copy2(__file__,out/'method.py')


def guide(out,arm,task):
    snapshot=out/'snapshots'/('baseline' if arm=='stacked' else arm)
    if arm in ('baseline','stacked'):
        paths=[p for p in sorted(snapshot.rglob('*.md')) if p.name not in ('sources.md','AGENTS_APPEND.md')
               and (p.name!='explanation.md' or task['explanation'])]
        paths += [out/'upstream/SKILL.upstream.md',out/'upstream/references/slop-catalog.md',
                  out/'upstream/references/gemini-syntax.md',out/'upstream/references/domains/tech.md']
        if arm=='stacked':paths=[out/'snapshots/kotonoha/meiseki-upstream/SKILL.md',out/'snapshots/kotonoha/meiseki-upstream/references/patterns.md']+paths
    else:
        paths=[snapshot/'kotonoha/SKILL.md',*[snapshot/'references'/name for name in
            ('workflow.md','audience.md','clarity.md','finish.md','review.md')],snapshot/'paragraph-writing/SKILL.md',snapshot/'japanese-direct-writing/SKILL.md']
        if task['explanation']:paths.append(snapshot/'references/explanation.md')
    return '\n\n'.join(p.read_text(encoding='utf-8') for p in paths)


def verify(out,c):
    for name,digest in c['files'].items():
        if base.sha((out/name).read_bytes())!=digest:raise ValueError('Frozen input changed: '+name)


def write_one(out,job,c,disabled):
    dest=out/'writing'/f"{job['task']}-{job['arm']}-{job['repeat']}.json"
    if dest.exists():return dest.stem,'retained'
    task=next(t for t in c['tasks'] if t['id']==job['task'])
    prompt=('文章規範は展開済みです。ツールや他のSkillを使わず、完成稿だけ返してください。\n'+guide(out,job['arm'],task)
            +'\n【依頼】\n'+task['instruction']+'\n【素材】\n'+task['input'])
    with tempfile.TemporaryDirectory(prefix='kotonoha-writing-') as td:r=base.execute(prompt,Path(td),c,disabled)
    save(dest,{**r,**job,'guide_characters':len(guide(out,job['arm'],task))})
    return dest.stem,r['status']


def grade_one(out,index,labels,mapping,c,disabled):
    path=out/'grades'/f'B{index:02}.json'
    if path.exists():return path.stem,'retained'
    rows=[]
    for label in labels:
        row=json.loads((out/'writing'/mapping[label]).read_text(encoding='utf-8'))
        task=next(t for t in c['tasks'] if t['id']==row['task'])
        rows.append({'id':label,'instruction':task['instruction'],'material':task['input'],
            'requirements':task['requirements'],'text':row['output']})
    with tempfile.TemporaryDirectory(prefix='kotonoha-grade-') as td:
        r=base.execute(c['rubric']+'\n'+json.dumps(rows,ensure_ascii=False),Path(td),c,disabled,schema=grading.schema())
    ratings=[]
    if r['status']=='completed':
        try:ratings=json.loads(r['output'])['ratings'];grading.validate_ratings(ratings,labels)
        except (ValueError,KeyError,TypeError):r['status']='invalid_rating'
    save(path,{**r,'labels':labels,'ratings':ratings})
    return path.stem,r['status']


def report(out,c):
    mapping=json.loads((out/'blind.private.json').read_text(encoding='utf-8'))
    rows={p.name:json.loads(p.read_text(encoding='utf-8')) for p in (out/'writing').glob('*.json')}
    ratings={mapping[r['id']]:r for p in (out/'grades').glob('*.json') for r in json.loads(p.read_text())['ratings']}
    results={}
    mean=lambda xs:sum(xs)/len(xs) if xs else None
    for arm in ARMS:
        written=[r for r in rows.values() if r['arm']==arm];scored=[ratings[n] for n,r in rows.items() if r['arm']==arm and n in ratings]
        results[arm]={'attempted':len(written),'completed':sum(r['status']=='completed' for r in written),'rated':len(scored),
            'axes':{a:mean([r[a] for r in scored]) for a in grading.AXES},
            'meaning_error_outputs':sum(bool(r['meaning_errors']) for r in scored),'requester_residue_outputs':sum(bool(r['requester_residue']) for r in scored),
            'mean_guide_characters':mean([r['guide_characters'] for r in written]),
            'mean_input_tokens':mean([r['usage']['input_tokens'] for r in written if r.get('usage')]),
            'mean_output_characters':mean([len(r.get('output') or '') for r in written if r['status']=='completed'])}
    save(out/'summary.json',{'expected':len(c['tasks'])*len(ARMS)*2,'conditions':results})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('prepare','writing','grade','report'));p.add_argument('--out',type=Path,required=True);p.add_argument('--baseline',type=Path);p.add_argument('--limit',type=int);p.add_argument('--holdout-from',type=Path)
    a=p.parse_args();out=a.out
    if a.phase=='prepare':prepare(out,a.baseline,a.holdout_from);return
    c=json.loads((out/'contract.json').read_text());
    global ARMS
    ARMS=tuple(c['arms']);verify(out,c);disabled=json.loads((out/'locations.private.json').read_text())['disabled']
    if a.phase=='writing':
        jobs=json.loads((out/'jobs.json').read_text())
        if a.limit:jobs=jobs[:a.limit]
        with ThreadPoolExecutor(max_workers=2) as pool:
            for result in pool.map(lambda j:write_one(out,j,c,disabled),jobs):print(result,flush=True)
    elif a.phase=='grade':
        mapping_path=out/'blind.private.json'
        if mapping_path.exists():mapping=json.loads(mapping_path.read_text())
        else:
            names=[p.name for p in sorted((out/'writing').glob('*.json')) if json.loads(p.read_text())['status']=='completed']
            random.Random(c['seed']+1).shuffle(names);mapping={f'O{i+1:03}':name for i,name in enumerate(names)};save(mapping_path,mapping)
        labels=list(mapping);batches=[labels[i:i+4] for i in range(0,len(labels),4)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            for result in pool.map(lambda item:grade_one(out,item[0],item[1],mapping,c,disabled),enumerate(batches)):print(result,flush=True)
    else:report(out,c)

if __name__=='__main__':main()
