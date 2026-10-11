#!/usr/bin/env python3
"""New, smaller review units for outputs without a completed rating.

Retains failed 12-output jobs and never resubmits their payloads or reviews an
already rated output. This is a disclosed change of review-unit size, not a
retry of a timed-out unit.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('study',ROOT/'run_study.py')
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=2,choices=[1,2]);args=parser.parse_args()
    root=args.out;contract=json.loads((root/'contract.json').read_text());locations=json.loads((root/'locations.private.json').read_text())
    manifest=root/'writing-smaller-review-units.json'
    if not manifest.exists():
        rated={r['output_file'] for p in (root/'writing-grades').glob('*.json')
               for d in [json.loads(p.read_text())] if d['status']=='completed' for r in d['ratings']}
        jobs=json.loads((root/'writing-jobs.json').read_text())
        names=[f"{j['task']}-{j['arm']}-{j['repeat']}.json" for j in jobs]
        remaining=[n for n in names if n not in rated]
        S.save(manifest,{'reason':'Two 12-output review units timed out; new units contain at most four previously unrated outputs. Completed reviews are not repeated.',
                        'units':[remaining[i:i+4] for i in range(0,len(remaining),4)]})
    units=json.loads(manifest.read_text())['units'];ready=[]
    for i,names in enumerate(units):
        files=[root/'writing'/n for n in names]
        if not all(p.exists() for p in files):continue
        completed=[p for p in files if json.loads(p.read_text())['status']=='completed']
        if completed:ready.append((completed,f'U{i+1:02}'))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(S.grade_batch,root,'writing',files,identifier,contract,locations) for files,identifier in ready]
        for f in as_completed(futures):print('smaller-review',*f.result(),flush=True)

if __name__=='__main__':main()
