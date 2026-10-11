#!/usr/bin/env python3
"""Verify saved study inputs and receipts without running models or installation."""
import argparse
from collections import Counter
import json
from pathlib import Path

import run_study as study
import summarize_study
import verify_native


def audit(root, sources, upstream, final_assets_dir=None):
    contract = json.loads((root / 'contract.json').read_text())
    study.check_sources(contract, {'sources': str(sources), 'upstream': str(upstream)})
    verified = {}
    for phase, expected_count in [('writing', 96), ('holdout', 12)]:
        tasks = contract['tasks'] if phase == 'writing' else json.loads((root / 'holdout-tasks.json').read_text())
        by_id = {task['id']: task for task in tasks}
        jobs = json.loads((root / (phase + '-jobs.json')).read_text())
        expected = {f"{job['task']}-{job['arm']}-{job.get('repeat', 1)}.json" for job in jobs}
        receipts = list((root / phase).glob('*.json'))
        if len(expected) != expected_count or {p.name for p in receipts} != expected:
            raise ValueError('Incomplete or duplicate trial matrix: ' + phase)
        for path in receipts:
            row = json.loads(path.read_text())
            task = by_id[row['task']]
            prompt = ('この比較は文章生成のみ。必要な規則と参照資料は展開済みなので、ツール・ファイル・検索・他のスキルを使わず、完成稿だけ返してください。\n\n'
                      + study.guides(sources, upstream, row['arm'])
                      + '\n\n【執筆課題】\n' + task['instruction'] + '\n' + task['input'])
            if study.sha(prompt.encode()) != row['prompt_sha256']:
                raise ValueError('Generation prompt changed: ' + path.name)
            if row['status'] == 'completed' and (not row['output'] or row['tools']):
                raise ValueError('Missing final output or unexpected tools: ' + path.name)
        summary = summarize_study.summarize(root, phase)
        saved = json.loads((root / (phase + '-summary.json')).read_text())
        if summary != saved or not summary['ratings_complete']:
            raise ValueError('Summary does not match saved receipts and ratings: ' + phase)
        verified[phase] = {
            'trials': len(receipts),
            'statuses': dict(Counter(json.loads(p.read_text())['status'] for p in receipts)),
            'prompts_verified': len(receipts),
            'ratings_complete': True,
            'summary_sha256': study.sha((root / (phase + '-summary.json')).read_bytes()),
        }
    native = verify_native.verify(root, sources)
    verified['native'] = {'trials': len(native), 'routes_passed': sum(r['route_pass'] for r in native.values())}
    candidate_files = [p for p in (sources / 'c/assets').rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    metadata_updates = {}
    for source in candidate_files:
        relative = source.relative_to(sources / 'c/assets')
        deployed = (final_assets_dir or study.ROOT / 'assets') / relative
        if relative.as_posix() in {'paragraph-writing/UPSTREAM.json', 'japanese-direct-writing/SOURCE.json'}:
            before = json.loads(source.read_text())
            after = json.loads(deployed.read_text())
            expected = dict(before, revision='2.0.0-proposal.2', files={'SKILL.md': study.sha((deployed.parent / 'SKILL.md').read_bytes())})
            if after != expected:
                raise ValueError('Unexpected provenance change: ' + str(relative))
            metadata_updates[str(relative)] = 'Release revision and actual unchanged SKILL body digest'
            continue
        if relative.as_posix() == 'references/sources.md':
            if not deployed.read_text().startswith(source.read_text()):
                raise ValueError('Existing source attribution changed')
            metadata_updates[str(relative)] = 'Appended source attribution; excluded from generation guides'
            continue
        if source.read_bytes() != deployed.read_bytes():
            raise ValueError('Final install asset differs from tested C: ' + str(relative))
    verified['final_assets'] = {'candidate': 'c', 'identical_files': len(candidate_files) - len(metadata_updates),
                                'metadata_updates': metadata_updates}
    verified['contract_sha256'] = study.sha((root / 'contract.json').read_bytes())
    verified['evidence_files'] = {
        p.relative_to(root).as_posix(): study.sha(p.read_bytes()) for p in sorted(root.rglob('*'))
        if p.is_file() and not p.name.endswith('.private.json') and p.name != 'audit.json'
    }
    return verified


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--upstream-dir', type=Path, required=True)
    parser.add_argument('--final-assets-dir', type=Path, help='Historical release assets when the current rules have changed')
    args = parser.parse_args()
    result = audit(args.out, args.sources, args.upstream_dir, args.final_assets_dir)
    study.save(args.out / 'audit.json', result)
    print(json.dumps({key: value for key, value in result.items() if key != 'evidence_files'}, ensure_ascii=False, indent=2))
