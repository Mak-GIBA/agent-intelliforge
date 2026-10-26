#!/usr/bin/env python3
"""One explicitly requested reader-review repair; retains rejected outputs and receipts."""
from pathlib import Path
import argparse,json,time,tomllib
import v4_compare as C


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--budget-from',type=Path,required=True);a=p.parse_args()
    root=a.candidate.resolve();quality=json.loads((root/'quality.json').read_text('utf-8'))
    if (root/'adapter/FLOW.json').is_file():
        raise ValueError('Native-flow outputs require a new Skill run; historical answer repair is unsupported')
    if quality.get('status')!='held' or quality.get('critical_errors') or not quality.get('unresolved_regressions'):
        raise ValueError('Repair requires only recorded reader regressions, not missing/critical evidence')
    directory=root/'reader-repair';directory.mkdir(exist_ok=False)
    contract=json.loads((root/'model/contract.json').read_text('utf-8'))
    config=tomllib.loads((Path.home()/'.codex/config.toml').read_text('utf-8'))
    if config['model']!=contract['model'] or config.get('model_reasoning_effort','medium')!=contract['effort']:
        raise ValueError('Model conditions changed')
    actual={p.relative_to(root/'adapter').as_posix():C.sha(p.read_bytes()) for p in (root/'adapter').rglob('*')
            if p.is_file() and p.name not in ('UPSTREAMS.json','resources.json') and '__pycache__' not in p.parts}
    if actual!=quality['adapter_sha256']:raise ValueError('Adapter changed; rerun its paired comparison')
    ids={text.split(':',1)[0] for text in quality['unresolved_regressions']}
    tasks=[t for t in contract['tasks'] if t['id'] in ids]
    rows=[]
    for t in tasks:
        versions={}
        for arm in ('baseline','candidate'):
            for file in (root/'model').glob(arm+'-*.json'):
                for c in json.loads(file.read_text())['result']['cases']:
                    if c['id']==t['id']:versions[arm]=c['text']
        rows.append({**t,'current':versions['candidate'],'baseline':versions['baseline'],
                     'issues':[x for x in quality['unresolved_regressions'] if x.startswith(t['id']+':')]})
    C.save(directory/'input.json',{'rows':rows,'guide_sha256':{n:actual[n] for n in ('SKILL.md','references/long-form.md')}})
    deadline=time.monotonic()+max(0,1800-(time.time()-a.budget_from.stat().st_mtime))
    rules=C.guide(root/'adapter',True,any(t.get('explanation') for t in tasks))
    prompt='次の規範を使い、読者レビューで指摘された箇所を一度だけ改稿してください。原文の条件・確信度・事実を守り、問題のない箇所は残します。baselineを模写する必要はありません。ツールを使わず完成稿をcasesに返してください。\n'+rules+'\n'+json.dumps(rows,ensure_ascii=False)
    value,receipt=C.invoke(prompt,C.WRITING,deadline,config)
    if {r['id'] for r in value['cases']}!=ids or len(value['cases'])!=len(ids):raise ValueError('Repair omitted cases')
    C.save(directory/'output.json',{'result':value,'receipt':receipt})
    pairs=[{**row,'versions':{'X':next(c['text'] for c in value['cases'] if c['id']==row['id']),'Y':row['baseline']},'candidate_label':'X'} for row in rows]
    for row in pairs:row.pop('current');row.pop('baseline');row.pop('issues')
    judge='原文・依頼・要件を基準に二つの版を独立に評価してください。版の名前や規範は不明です。candidate_labelの版で、重大な意味変更・脱落・捏造をcritical_errorsへ、もう一方より具体的に悪くなった説明・構成・自然さ・効率をregressionsへ記録します。好みだけは劣化と数えず、実際の文に基づく理由をevidenceへ書きます。問題がなければ空配列。ツールを使わずJSONだけ返してください。\n'+json.dumps(pairs,ensure_ascii=False)
    reviewed,receipt=C.invoke(judge,C.REVIEW,deadline,config)
    if {r['id'] for r in reviewed['cases']}!=ids or len(reviewed['cases'])!=len(ids):raise ValueError('Missing repair review')
    C.save(directory/'review.json',{'result':reviewed,'receipt':receipt,'pairs':pairs})
    issues=[x for row in reviewed['cases'] for x in row['critical_errors']+row['regressions']]
    if issues:
        C.save(directory/'result.json',{'status':'held','issues':issues});print(json.dumps(issues,ensure_ascii=False));return 2
    quality.update(status='passed',resolved_regressions=quality['unresolved_regressions'],unresolved_regressions=[],
                   repair='one explicit reader-review repair; original paired outputs retained')
    for file in directory.glob('*.json'):quality['artifacts'][file.relative_to(root).as_posix()]=C.sha(file.read_bytes())
    C.save(root/'quality.json',quality);print('Reader repair independently accepted; original failures retained.');return 0


if __name__=='__main__':raise SystemExit(main())
