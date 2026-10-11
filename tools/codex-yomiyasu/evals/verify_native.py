#!/usr/bin/env python3
"""Recompute native route evidence from full tool output, frozen text and prompts.

This performs no model calls or installation. Reading a skill is observable;
the model's private reasoning and exact internal application count are not.
"""
import argparse
import json
from pathlib import Path
import tempfile

import run_study as study

def verify(root, sources):
    tasks={task['id']:task for task in study.native_tasks()}
    results={}
    with tempfile.TemporaryDirectory(prefix='yomiyasu-receipt-check-') as temp:
        skills=Path(temp)
        for receipt in sorted((root/'native').glob('*.json')):
            row=json.loads(receipt.read_text());task=tasks[row['task']]
            prompt=task['prompt']+'\n送信・インストール・ユーザー設定変更は不要です。完成稿だけを返してください。'
            if study.sha(prompt.encode())!=row['prompt_sha256']:
                raise ValueError('Prompt mismatch: '+receipt.name)
            if row['expected_reads']!=task['expected']:
                raise ValueError('Expected route mismatch: '+receipt.name)
            directory=sources/row['arm']/'assets'
            for name in ('yomiyasu','paragraph-writing','japanese-direct-writing'):
                source=directory/'SKILL.md' if name=='yomiyasu' else directory/name/'SKILL.md'
                target=skills/name/'SKILL.md';target.parent.mkdir(exist_ok=True)
                target.write_bytes(source.read_bytes())
            reads=study.read_receipts(row['tools'],skills)
            passed=(row['status']=='completed' and set(reads)==set(task['expected'])
                    and all(len(entries)==1 for entries in reads.values()))
            if passed!=row['route_pass']:
                raise ValueError('Saved route result mismatch: '+receipt.name)
            results[receipt.name]={'status':row['status'],'route_pass':passed,
                'prompt_verified':True,'expected_reads':task['expected'],'reads':reads,
                'full_skill_content_verified':bool(reads),
                'verification_method':'Successful actual read command must contain the complete frozen SKILL text in its tool output. Empty reads are legitimate for negative controls and are not full reads.',
                'internal_application_count':'not observable'}
    if len(results)!=32:
        raise ValueError('Expected all 32 native receipts')
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--sources',type=Path,required=True)
    args=parser.parse_args()
    result=verify(args.out,args.sources)
    study.save(args.out/'native-read-verification.json',result)
    print(json.dumps({'receipts_verified':len(result),'route_passes':sum(x['route_pass'] for x in result.values())}))
