#!/usr/bin/env python3
"""Four paired native uses for the 4.1.1 editorial revision; at most ten minutes.

This is separate evidence, never a substitute for update_upstreams' 24-use gate.
"""
import argparse
import json
from pathlib import Path
import tempfile
import time
import tomllib

import flow_native as F


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    config = tomllib.loads((Path.home()/'.codex/config.toml').read_text())
    tasks = [t for t in json.loads((F.HERE/'flow-tasks.json').read_text())['tasks']
             if t['id'] in {'W01', 'W10', 'W17', 'W24'}]
    contract = {'protocol': 'editorial-native-v411', 'model': config['model'],
                'effort': config.get('model_reasoning_effort', 'medium'),
                'budget_seconds': 600, 'timeout_per_call': 180, 'automatic_retries': 0,
                'tasks': tasks, 'baseline_version': '4.1.0', 'candidate_version': '4.1.1',
                'baseline_sha256': F.inventory(a.baseline),
                'candidate_sha256': F.inventory(a.candidate),
                'runtime_settings_sha256': F.sha((a.runtime/'settings.json').read_bytes())}
    for name, path in [('runner.py', Path(__file__)), ('flow_native.py', F.HERE/'flow_native.py')]:
        raw = path.read_bytes()
        (a.output/name).write_bytes(raw)
        contract[name+'_sha256'] = F.sha(raw)
    contract['started_epoch'] = time.time()
    deadline = contract['started_epoch']+600
    F.save(a.output/'contract.json', contract)
    report = {'protocol': contract['protocol'], 'status': 'held', 'completed_pairs': 0,
              'case_ids': [t['id'] for t in tasks], 'critical_errors': [],
              'unresolved_regressions': [], 'route_failures': [],
              'scope': 'Four paired native uses and one separate blinded-label same-model review; not full 24-use validation'}
    try:
        for i, task in enumerate(tasks):
            for arm in (('baseline', 'candidate') if i % 2 == 0 else ('candidate', 'baseline')):
                source = a.baseline if arm == 'baseline' else a.candidate
                record = F.native(task, arm, source, a.runtime, contract, deadline)
                F.save(a.output/(task['id']+'-'+arm+'.json'), record)
                print(task['id'], arm, record['status'], flush=True)
            candidate = json.loads((a.output/(task['id']+'-candidate.json')).read_text())
            report['route_failures'].extend(task['id']+': '+x for x in F.route_errors(task, candidate))
            baseline = json.loads((a.output/(task['id']+'-baseline.json')).read_text())
            if baseline['status'] != 'completed' or not baseline.get('text'):
                raise ValueError('Incomplete baseline: '+task['id'])
            report['completed_pairs'] += 1
            if F.inventory(a.candidate) != contract['candidate_sha256'] or F.inventory(a.baseline) != contract['baseline_sha256']:
                raise ValueError('Comparison source changed')
        pairs, labels = [], {}
        for i, task in enumerate(tasks):
            order = ('baseline', 'candidate') if i % 2 == 0 else ('candidate', 'baseline')
            labels[task['id']] = 'Y' if i % 2 == 0 else 'X'
            pairs.append({**{k: task[k] for k in ('id', 'instruction', 'input', 'requirements')},
                          'versions': {label: json.loads((a.output/(task['id']+'-'+arm+'.json')).read_text())['text']
                                       for label, arm in zip(('X', 'Y'), order)}})
        prompt = ('依頼・原文・要件と出力X/Yを比較してください。版の出自は不明です。意味・事実・数値・否定・条件・確信度・範囲の変更や脱落、捏造を各版のerrorsへ記録してください。'
                  '相手版より説明の深さ、段落、自然さ、情報効率が具体的に悪い点だけをregressionsへ記録します。文体の好みや短さだけは劣化ではありません。'
                  '診断依頼は指摘として評価し、完成稿を要求しません。実際の文に基づくevidenceを付け、問題がなければ空配列にします。道具を使わずJSONだけ返してください。\n'
                  +json.dumps(pairs, ensure_ascii=False))
        with tempfile.TemporaryDirectory(prefix='kotonoha-editorial-review-') as td:
            receipt = F.invoke(prompt, Path(td), contract, deadline, schema=F.REVIEW)
            if receipt['status'] != 'completed' or receipt['tools']:
                raise ValueError('Review did not complete without tools')
            graded = json.loads(receipt['output'])
            F.save(a.output/'review.json', {'pairs': pairs, 'result': graded, 'receipt': F.clean(receipt, Path(td))})
        if len(graded['cases']) != 4 or {r['id'] for r in graded['cases']} != set(labels):
            raise ValueError('Incomplete review')
        for row in graded['cases']:
            label = labels[row['id']]
            report['critical_errors'].extend(row['id']+': '+x for x in row[label+'_errors'])
            report['unresolved_regressions'].extend(row['id']+': '+x for x in row['regressions_'+label])
        if not any(report[k] for k in ('critical_errors', 'unresolved_regressions', 'route_failures')):
            report['status'] = 'passed'
    except (OSError, ValueError, RuntimeError) as exc:
        report['error'] = str(exc)
    report['elapsed_seconds'] = round(time.time()-contract['started_epoch'], 2)
    report['artifacts'] = {p.name: F.sha(p.read_bytes()) for p in sorted(a.output.iterdir()) if p.is_file()}
    F.save(a.output/'quality.json', report)
    print(json.dumps({k: v for k, v in report.items() if k != 'artifacts'}, ensure_ascii=False), flush=True)
    return 0 if report['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
