#!/usr/bin/env python3
"""Compute the predeclared metrics from model outputs and anonymous ratings."""
import argparse
import json
from pathlib import Path
import statistics

ARMS=('baseline','a','b','c')

def summarize(root, phase='writing'):
    outputs={p.name:json.loads(p.read_text()) for p in (root/phase).glob('*.json')}
    ratings={}
    for path in sorted((root/(phase+'-grades')).glob('*.json')):
        result=json.loads(path.read_text())
        if result['status']=='completed':
            for row in result['ratings']:
                if row['output_file'] in ratings:raise ValueError('Duplicate anonymous rating')
                ratings[row['output_file']]=row
    adjudications=root/(phase+'-adjudications.json')
    if adjudications.exists():
        for row in json.loads(adjudications.read_text()):
            if row['output_file'] not in ratings:raise ValueError('Adjudication without a rating')
            ratings[row['output_file']].update(row['replacement'])
    results={}
    for arm in ARMS:
        rows=[(name,row) for name,row in outputs.items() if row['arm']==arm]
        if not rows:continue
        judged=[ratings[name] for name,_ in rows if name in ratings]
        native=[json.loads(p.read_text()) for p in (root/'native').glob('*.json') if ('-'+arm+'-') in p.name]
        passed=[r for r in judged if not r['meaning_errors'] and not r['requester_residue'] and min(r['paragraph'],r['naturalness'],r['reader_fit'])>=3]
        completed=[r for _,r in rows if r['status']=='completed']
        results[arm]={'trials':len(rows),'completed':len(completed),'graded':len(judged),'primary_passes':len(passed),
            'primary_fraction':len(passed)/len(completed) if completed else None,
            'delivered_pass_fraction':len(passed)/len(rows),
            'meaning_error_outputs':sum(bool(r['meaning_errors']) for r in judged),
            'requester_residue_outputs':sum(bool(r['requester_residue']) for r in judged),
            'quality_mean':statistics.mean((r['paragraph']+r['naturalness']+r['reader_fit'])/3 for r in judged) if judged else None,
            'mean_elapsed_seconds':statistics.mean(r['elapsed_seconds'] for _,r in rows),
            'mean_completed_elapsed_seconds':statistics.mean(r['elapsed_seconds'] for r in completed) if completed else None,
            'mean_reported_total_tokens':statistics.mean(r['usage']['input_tokens']+r['usage']['output_tokens'] for r in completed if r['usage']) if completed else None,
            'native_trials':len(native),'native_route_passes':sum(r.get('route_pass',False) for r in native),
            'native_completion_failures':sum(r['status']!='completed' for r in native)}
    eligible=[a for a in ARMS[1:] if a in results and results[a]['trials']==24 and results[a]['graded']==24
        and results[a]['completed']==24 and results[a]['meaning_error_outputs']==0
        and results[a]['native_trials']==8 and results[a]['native_route_passes']==8]
    def rank(a):
        r=results[a]
        return (-r['primary_fraction'],r['requester_residue_outputs'],-r['quality_mean'],r['mean_elapsed_seconds'],r['mean_reported_total_tokens'])
    completed_count=sum(r['status']=='completed' for r in outputs.values())
    return {'phase':phase,'conditions':results,'eligible':eligible,'selected':min(eligible,key=rank) if eligible else None,
        'selection_policy':'The implementation gate requires all 24 outputs available and graded and all eight native routes passing. This completeness condition is stricter than contract.json\'s completed-output quality metric and selection text; it is a conservative adoption condition, not evidence of linguistic superiority.',
        'ratings_complete':len(ratings)==completed_count,'generation_complete':completed_count==len(outputs),
        'unavailable_outputs':[name for name,r in outputs.items() if r['status']!='completed'],
        'limitations':'Small fixed synthetic sample and same-model automatic grading. Each phase used two workers and phases overlapped (up to six requests); elapsed times are not a controlled speed comparison. No authorship detection or population inference. Operational failures are not semantic-quality failures.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--phase',default='writing',choices=['writing','holdout'])
    args=parser.parse_args();result=summarize(args.out,args.phase)
    (args.out/(args.phase+'-summary.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
