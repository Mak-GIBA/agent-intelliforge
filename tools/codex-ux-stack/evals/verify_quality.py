#!/usr/bin/env python3
"""Verify published benchmark files and reproduce image ratings/check counts offline."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def verify(root):
    root = root.resolve()
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        path = root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Unsafe evidence path: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Evidence hash mismatch: ' + name)
    mapping = json.loads((root/'blind-map.json').read_text(encoding='utf-8'))
    results = json.loads((root/'results.json').read_text(encoding='utf-8'))
    for row in results['rows']:
        candidate = row['candidate']
        operations = json.loads((root/f'operations-{candidate}.json').read_text(encoding='utf-8'))
        checks = [check for entry in operations for check in entry['checks']]
        assert row['operation_checks']['raw_passed'] == sum(c['passed'] for c in checks)
        assert row['operation_checks']['total'] == len(checks)
        for entry in operations:
            for evidence in entry['evidence']:
                assert hashlib.sha256((root/evidence['file']).read_bytes()).hexdigest() == evidence['sha256']
        for task, expected in row['case_means'].items():
            label = next(key for key, value in mapping[task].items() if value == candidate)
            ratings = json.loads((root/'ratings'/f'{task}.json').read_text(encoding='utf-8'))['ratings']
            values = next(item for item in ratings if item['id'] == label)
            actual = statistics.mean(values[key] for key in ('hierarchy','readability','simplicity','consistency','fidelity'))
            assert actual == expected
    return results['rows']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    rows = verify(args.evidence)
    for row in rows:
        print(row['candidate'], json.dumps(row['case_means'], ensure_ascii=False), row['operation_checks'])
    print('Hashes, operation evidence and rating aggregates verified; this does not certify human usability.')


if __name__ == '__main__':
    main()
