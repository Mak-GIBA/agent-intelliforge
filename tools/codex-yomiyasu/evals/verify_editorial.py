#!/usr/bin/env python3
"""Offline verification of the exact 4.1.0 -> 4.1.1 editorial changes.

The full upstream update gate remains in update_upstreams.py.
"""
import argparse
import json
from pathlib import Path

import flow_native as F


def verify(baseline, candidate, native=None):
    manifest = json.loads((F.HERE/'editorial-v411.json').read_text())
    old, new = F.inventory(baseline), F.inventory(candidate)
    expected = set(manifest['changes']) | set(manifest['metadata'])
    if set(old) != set(new) or {n for n in old if old[n] != new[n]} != expected:
        raise ValueError('Changes exceed the reviewed editorial file set')
    for name, row in manifest['changes'].items():
        if old[name] != row['before_sha256'] or new[name] != row['after_sha256']:
            raise ValueError('Editorial file identity differs: '+name)
        text = (baseline/name).read_text()
        for before, after in row['replacements']:
            if text.count(before) != 1:
                raise ValueError('Ambiguous editorial transformation: '+name)
            text = text.replace(before, after)
        if text.encode() != (candidate/name).read_bytes():
            raise ValueError('Editorial changes differ: '+name)
    for name, row in manifest['metadata'].items():
        if old[name] != row['before_sha256'] or new[name] != row['after_sha256']:
            raise ValueError('Audit metadata differs: '+name)
    namespace = {}
    exec(compile((F.HERE.parent/'engine/flow_contract.py').read_bytes(), 'flow_contract.py', 'exec'), namespace)
    flow = namespace['verify_flow'](candidate, json.loads((F.HERE/'flow-v3-baseline.json').read_text()))
    result = {'status': 'passed', 'edited_documents': len(manifest['changes']),
              'preserved_resources': flow['preserved_resources'],
              'unchanged_files': len(old)-len(expected),
              'source_sha256': new, 'metadata_changes': sorted(manifest['metadata'])}
    if native is not None:
        contract = json.loads((native/'contract.json').read_text())
        quality = json.loads((native/'quality.json').read_text())
        for name, digest in quality['artifacts'].items():
            if Path(name).name != name or F.sha((native/name).read_bytes()) != digest:
                raise ValueError('Native evidence changed: '+name)
        if contract['baseline_sha256'] != old:
            raise ValueError('Native baseline differs')
        # Only the provenance annotation was added after native execution began.
        tested = dict(new, **{'UPSTREAMS.json': old['UPSTREAMS.json']})
        if contract['candidate_sha256'] != tested:
            raise ValueError('Native candidate differs beyond provenance metadata')
        ids = ['W01', 'W10', 'W17', 'W24']
        tasks = [t for t in json.loads((F.HERE/'flow-tasks.json').read_text())['tasks'] if t['id'] in ids]
        if contract['tasks'] != tasks or contract['budget_seconds'] != 600 or contract['automatic_retries'] != 0:
            raise ValueError('Native comparison conditions differ')
        for name in ('runner.py', 'flow_native.py'):
            if F.sha((native/name).read_bytes()) != contract[name+'_sha256']:
                raise ValueError('Native runner snapshot differs')
        pairs, critical, regressions, routes = [], [], [], []
        for i, task in enumerate(tasks):
            records = {arm: json.loads((native/(task['id']+'-'+arm+'.json')).read_text()) for arm in ('baseline', 'candidate')}
            for record in records.values():
                if record['status'] != 'completed' or not record.get('text') or not record['skills_unchanged'] or not record['draft_unchanged']:
                    raise ValueError('Incomplete or mutated native trial')
            record = records['candidate']
            # Recompute visibility from actual returned text, not the runner summary.
            record['full_reads'] = ['kotonoha/'+p for p in F.observed_reads(candidate, record['tools'])]
            routes.extend(task['id']+': '+x for x in F.route_errors(task, record))
            order = ('baseline', 'candidate') if i % 2 == 0 else ('candidate', 'baseline')
            pairs.append({**{k: task[k] for k in ('id', 'instruction', 'input', 'requirements')},
                          'versions': {label: records[arm]['text'] for label, arm in zip(('X', 'Y'), order)}})
        review = json.loads((native/'review.json').read_text())
        receipt, graded = review['receipt'], review['result']
        if review['pairs'] != pairs or receipt['status'] != 'completed' or receipt['tools'] or json.loads(receipt['output']) != graded:
            raise ValueError('Native review does not match actual outputs')
        if len(graded['cases']) != 4 or {r['id'] for r in graded['cases']} != set(ids):
            raise ValueError('Incomplete native review')
        for i, task in enumerate(tasks):
            row = next(r for r in graded['cases'] if r['id'] == task['id'])
            label = 'Y' if i % 2 == 0 else 'X'
            critical.extend(task['id']+': '+x for x in row[label+'_errors'])
            regressions.extend(task['id']+': '+x for x in row['regressions_'+label])
        if (quality['status'] != 'passed' or quality['completed_pairs'] != 4 or critical or regressions or routes
                or quality['critical_errors'] != critical or quality['unresolved_regressions'] != regressions
                or quality['route_failures'] != routes or quality['elapsed_seconds'] > 600):
            raise ValueError('Native evidence does not support the reported pass')
        result['native'] = {k: quality[k] for k in ('protocol', 'status', 'completed_pairs', 'elapsed_seconds')}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    result = verify(a.baseline, a.candidate, a.native)
    F.save(a.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
