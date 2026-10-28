#!/usr/bin/env python3
"""Read-only verification of public evidence without personal execution settings."""
import argparse
import json
from pathlib import Path
import explanation_study as study
import explanation_native as native
import explanation_holdout as holdout
import run_study as base

def verify(root):
    result=study.audit(root)
    assets=root/'snapshots/improved/assets'
    if (root/'holdout').is_dir():
        result['holdout']=holdout.audit(root/'holdout')
        assets=root/'holdout/snapshots/revised/assets'
    body_checks=0
    for path in assets.rglob('*'):
        if not path.is_file():continue
        rel=path.relative_to(assets);current=study.ROOT/'assets'/rel
        if rel.as_posix()=='references/sources.md':
            if not current.read_text().startswith(path.read_text()):raise ValueError('Attribution changed')
        elif current.read_bytes()!=path.read_bytes():raise ValueError('Current asset differs: '+str(rel))
        body_checks+=1
    result['current_assets_verified']=body_checks
    native_contract=root/'native-contract.json'
    if native_contract.exists():
        nc=json.loads(native_contract.read_text())
        if nc['source_asset_sha256']!=study.hashes(assets):raise ValueError('Native assets changed')
        if nc['native_script_sha256']!=base.sha(Path(native.__file__).read_bytes()):raise ValueError('Native verifier changed')
        rows={p.stem:json.loads(p.read_text()) for p in (root/'native').glob('*.json')}
        if set(rows)!={r['id'] for r in nc['tasks']}:raise ValueError('Incomplete native matrix')
        for task in nc['tasks']:
            row=rows[task['id']]
            if row['prompt_sha256']!=base.sha(task['prompt'].encode()):raise ValueError('Native prompt changed')
            reads=native.full_reads(row['tools'],assets/'references/explanation.md')
            if reads!=row['explanation_reads']:raise ValueError('Native read evidence changed')
            route=row['status']=='completed' and bool(reads)==task['read_explanation']
            if route!=row['reference_route_pass']:raise ValueError('Native route result changed')
        result['native_receipts_verified']=len(rows)
        result['native_reference_routes_passed']=sum(r['reference_route_pass'] for r in rows.values())
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.out.resolve()),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
