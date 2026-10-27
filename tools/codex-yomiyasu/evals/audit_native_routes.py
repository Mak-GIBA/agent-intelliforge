#!/usr/bin/env python3
"""Offline visibility audit. Never changes Skill outputs, reviews or source rules."""
import argparse
import json
from pathlib import Path
import flow_native as N


def audit(candidate):
    adapter=candidate/'adapter'
    quality=json.loads((candidate/'quality.json').read_text(encoding='utf-8'))
    bound={k:v for k,v in N.inventory(adapter).items() if k not in {'UPSTREAMS.json','resources.json'}}
    if bound!=quality['adapter_sha256']:
        raise ValueError('Adapter differs from the evaluated source')
    contracts=[n for n in quality['artifacts'] if n.startswith(('native-r1/','native-r2/','native-r3/')) and n.endswith('/contract.json')]
    if len(contracts)!=1:raise ValueError('Missing native contract')
    directory=Path(contracts[0]).parent
    contract=json.loads((candidate/contracts[0]).read_text(encoding='utf-8'))
    before=candidate/'initial-route-quality.json'
    if before.exists():raise ValueError('Route audit already recorded')
    N.save(before,quality)
    rows=[];failures=[]
    for task in contract['tasks']:
        record=json.loads((candidate/directory/(task['id']+'-candidate.json')).read_text(encoding='utf-8'))
        observed=N.observed_reads(adapter,record['tools'])
        reassessed={**record,'full_reads':['kotonoha/'+name for name in observed]}
        errors=N.route_errors(task,reassessed)
        failures.extend(task['id']+': '+x for x in errors)
        matches=[]
        for name in observed:
            raw=(adapter/name).read_text(encoding='utf-8').strip()
            matches.append({'path':name,'sha256':N.sha((adapter/name).read_bytes()),
                'tool_indices':[i for i,t in enumerate(record['tools']) if raw in t.get('aggregated_output','')]})
        rows.append({'id':task['id'],'original_observation':record['full_reads'],
                     'observed_references':matches,'route_errors':errors})
    result={'reason':'Compound shell status does not erase successfully returned preceding file text. Full guide content must be present in immutable tool receipts; source/answers/ratings stay unchanged.',
            'adapter_sha256':bound,'cases':rows,'route_failures':failures}
    N.save(candidate/'route-audit.json',result)
    (candidate/'route-audit-method.py').write_bytes(Path(__file__).read_bytes())
    quality['route_failures']=failures
    quality['route_audit']='route-audit.json'
    quality['status']='passed' if not failures and not quality['critical_errors'] and not quality['unresolved_regressions'] else 'held'
    for name in ['initial-route-quality.json','route-audit.json','route-audit-method.py']:
        quality['artifacts'][name]=N.sha((candidate/name).read_bytes())
    N.save(candidate/'quality.json',quality)
    return {'status':quality['status'],'route_failures':failures,'cases':len(rows)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.candidate.resolve()),ensure_ascii=False,indent=2))
