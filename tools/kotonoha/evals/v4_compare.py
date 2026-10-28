#!/usr/bin/env python3
"""Bounded paired capability checks. Explicit model use; no personal installation."""
from __future__ import annotations
import argparse
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tomllib

HERE=Path(__file__).resolve().parent


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def object_schema(fields):return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
STR={'type':'string'};LIST={'type':'array','items':STR}
WRITING=object_schema({'cases':{'type':'array','items':object_schema({'id':STR,'text':STR})}})
REVIEW=object_schema({'cases':{'type':'array','items':object_schema({'id':STR,'critical_errors':LIST,'regressions':LIST,'evidence':STR})}})


def invoke(prompt,schema,deadline,config):
    with tempfile.TemporaryDirectory(prefix='kotonoha-v4-model-') as tmp:
        cwd=Path(tmp);out=cwd/'output.json';structure=cwd/'schema.json';save(structure,schema)
        paths=sorted({str(p.resolve()) for root in (Path.home()/'.agents/skills',Path.home()/'.codex/skills')
                      if root.is_dir() for p in root.rglob('SKILL.md')})
        disabled=','.join('{path='+json.dumps(p)+',enabled=false}' for p in paths)
        args=['codex','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check',
              '--sandbox','read-only','--model',config['model'],'-c','model_reasoning_effort='+json.dumps(config.get('model_reasoning_effort','medium')),
              '-c','project_doc_max_bytes=0','-c','skills.config=['+disabled+']','-c','web_search="disabled"',
              '--json','--output-schema',str(structure),'--output-last-message',str(out),'-']
        remaining=min(180,deadline-time.monotonic())
        if remaining<=0:raise RuntimeError('Overall 30 minute model budget exhausted')
        start=time.monotonic()
        try:r=subprocess.run(args,input=prompt,cwd=cwd,text=True,capture_output=True,timeout=remaining)
        except subprocess.TimeoutExpired:raise RuntimeError('Model timeout; trial held without automatic replay')
        events=[]
        for line in r.stdout.splitlines():
            try:events.append(json.loads(line))
            except ValueError:pass
        tools=[e['item'].get('type') for e in events if e.get('type')=='item.completed'
               and e.get('item',{}).get('type') not in ('agent_message','reasoning')]
        if r.returncode or tools or not out.is_file():raise RuntimeError('No valid isolated model completion: '+str(r.returncode))
        value=json.loads(out.read_text('utf-8'))
        usage=next((e.get('usage') for e in reversed(events) if e.get('type')=='turn.completed'),None)
        return value,{'elapsed_seconds':round(time.monotonic()-start,2),'usage':usage,
                      'prompt_sha256':sha(prompt.encode()),'tools':tools}


def guide(root,new,explanation):
    # Future updates compare against the integrated v4 bundle, not a v3-only layout.
    if not new:
        for candidate in (root,root/'kotonoha'):
            if (candidate/'capabilities.json').is_file() and (candidate/'references/long-form.md').is_file():
                root,new=candidate,True
                break
    if new:
        paths=[root/'SKILL.md']+([root/'references/long-form.md'] if explanation else [])
    else:
        paths=[root/'kotonoha/SKILL.md',*[root/'references'/n for n in ('workflow.md','audience.md','clarity.md','finish.md','review.md')],
               root/'paragraph-writing/SKILL.md',root/'japanese-direct-writing/SKILL.md']
        if explanation:paths.append(root/'references/explanation.md')
    return '\n\n'.join(p.read_text('utf-8') for p in paths)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--baseline-results',type=Path)
    p.add_argument('--budget-from',type=Path)
    a=p.parse_args()
    root=a.candidate.resolve();adapter=root/'adapter';baseline=a.baseline.resolve()
    if (adapter/'FLOW.json').is_file():
        p.error('Preserved-flow candidates require flow_native.py and actual reference receipts')
    config=tomllib.loads((Path.home()/'.codex/config.toml').read_text('utf-8'))
    tasks=json.loads((HERE/'explanation-tasks.json').read_text('utf-8'))['tasks']+json.loads((HERE/'kotonoha-holdout.json').read_text('utf-8'))['tasks']
    outputs=root/'model';outputs.mkdir(exist_ok=False)
    bound={p.relative_to(adapter).as_posix():sha(p.read_bytes()) for p in adapter.rglob('*') if p.is_file()
           and p.name not in ('UPSTREAMS.json','resources.json') and '__pycache__' not in p.parts}
    save(outputs/'contract.json',{'case_ids':[t['id'] for t in tasks],'tasks':tasks,'adapter_sha256':bound,
        'model':config['model'],'effort':config.get('model_reasoning_effort','medium'),
        'timeout_per_call':180,'deadline_seconds':1800,'automatic_retries':0})
    remaining=1800 if a.budget_from is None else 1800-(time.time()-a.budget_from.stat().st_mtime)
    deadline=time.monotonic()+remaining;errors=[];regressions=[]
    try:
        for batch in range(3):
            selected=tasks[batch*6:(batch+1)*6];variants={}
            for name,base,new in [('baseline',baseline,False),('candidate',adapter,True)]:
                rules=guide(base,new,any(t.get('explanation') for t in selected))
                prompt='以下の規範をこの入力で全て渡しています。他のSkill・ファイル・ツールを使わず、各依頼の完成稿をJSON casesへ返してください。\n'+rules+'\n【依頼と素材】\n'+json.dumps(selected,ensure_ascii=False)
                previous=a.baseline_results/f'baseline-{batch}.json' if a.baseline_results and not new else None
                if previous:
                    saved=json.loads(previous.read_text('utf-8'))
                    old_contract=json.loads((a.baseline_results/'contract.json').read_text('utf-8'))
                    if old_contract['model']!=config['model'] or old_contract['effort']!=config.get('model_reasoning_effort','medium'):
                        raise RuntimeError('Baseline model conditions changed')
                    value,receipt=saved['result'],saved['receipt']
                    if receipt['prompt_sha256']!=sha(prompt.encode()):raise RuntimeError('Baseline prompt changed')
                else:
                    value,receipt=invoke(prompt,WRITING,deadline,config)
                if {r['id'] for r in value['cases']}!={t['id'] for t in selected} or len(value['cases'])!=6:raise RuntimeError('Missing/duplicate cases')
                variants[name]=value['cases'];save(outputs/f'{name}-{batch}.json',{'result':value,'receipt':receipt,'guide_characters':len(rules)})
                print(name,batch,'completed',flush=True)
            pairs=[]
            for n,task in enumerate(selected):
                order=('baseline','candidate') if n%2==0 else ('candidate','baseline')
                pair={**task,'versions':{label:next(x['text'] for x in variants[name] if x['id']==task['id']) for label,name in zip(('X','Y'),order)},
                      'candidate_label':'Y' if n%2==0 else 'X'}
                pairs.append(pair)
            # The reviewer sees originals and anonymized outputs, not Skill names or guides.
            judge='原文と依頼・要件を基準に、二つの完成稿を独立に読んでください。版の名前や短さを品質と同一視しないでください。candidate_labelの版について、意味・数値・否定・条件・確信度・主体・内容の脱落や捏造をcritical_errorsへ、もう一方より説明の深さ・段落・自然さ・情報効率が具体的に悪くなった点をregressionsへ記録してください。好みの違いだけは回帰に数えません。問題がなければ空配列。evidenceに実際の文に基づく理由を書く。道具は使わず評価JSONだけ返す。\n'+json.dumps(pairs,ensure_ascii=False)
            judged,receipt=invoke(judge,REVIEW,deadline,config)
            if {r['id'] for r in judged['cases']}!={t['id'] for t in selected} or len(judged['cases'])!=6:raise RuntimeError('Missing/duplicate ratings')
            save(outputs/f'review-{batch}.json',{'result':judged,'receipt':receipt,'pairs':pairs})
            for row in judged['cases']:
                errors.extend(row['id']+': '+e for e in row['critical_errors'])
                regressions.extend(row['id']+': '+e for e in row['regressions'])
            print('review',batch,'completed',flush=True)
        status='passed' if not errors and not regressions else 'held'
        quality={'status':status,'case_ids':[t['id'] for t in tasks],'critical_errors':errors,
            'unresolved_regressions':regressions,'adapter_sha256':bound,
            'artifacts':{p.relative_to(root).as_posix():sha(p.read_bytes()) for p in outputs.glob('*.json')},
            'scope':'18 fixtures, one generation per variant, separate anonymous review; no universal quality proof'}
        save(root/'quality.json',quality);print(json.dumps({'status':status,'critical_errors':errors,'regressions':regressions},ensure_ascii=False),flush=True)
        return 0 if status=='passed' else 2
    except (OSError,ValueError,RuntimeError) as exc:
        save(root/'quality.json',{'status':'held','error':str(exc),'adapter_sha256':bound})
        print(str(exc),flush=True);return 2


if __name__=='__main__':raise SystemExit(main())
