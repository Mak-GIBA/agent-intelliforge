#!/usr/bin/env python3
"""Atomic role drafts and host-validated progress; no application writes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_json(path, limit=5_000_000):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Missing, linked or oversized checkpoint file')
    return json.loads(path.read_text(encoding='utf-8'))


def atomic(path, value):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Linked checkpoint refused')
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            os.chmod(temporary, 0o600)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save(directory, input_path, stage, remaining):
    directory = Path(directory).absolute()
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError('Linked role directory refused')
    source = Path(input_path)
    if not source.is_absolute():
        source = directory / source
    if not source.resolve().is_relative_to(directory.resolve()):
        raise ValueError('Draft must be inside the role directory')
    context = read_json(directory / 'checkpoint-context.json')
    result = read_json(source)
    if not isinstance(result, dict) or stage not in ('observing', 'reporting'):
        raise ValueError('Invalid draft/stage')
    if any(not isinstance(item, str) or not item.strip() for item in remaining):
        raise ValueError('Remaining work must be nonempty strings')
    value = {'version': 1, 'context': context, 'stage': stage,
             'remaining': remaining, 'result': result}
    request = {'request': uuid.uuid4().hex, 'checkpoint_sha256': checksum(value)}
    atomic(directory / 'checkpoint.json', value)
    atomic(directory / 'checkpoint-request.json', request)
    return {'saved': True, 'stage': stage, 'remaining': len(remaining), **request}


def validate_checkpoint(value, context, schema, validate, evidence_check):
    if (not isinstance(value, dict) or set(value) != {'version', 'context', 'stage', 'remaining', 'result'}
            or type(value['version']) is not int or value['version'] != 1 or value['context'] != context
            or value['stage'] not in ('observing', 'reporting')
            or not isinstance(value['remaining'], list)
            or any(not isinstance(x, str) or not x.strip() for x in value['remaining'])):
        raise ValueError('Checkpoint context/stage mismatch')
    result = value['result']
    if not isinstance(result, dict) or not set(result).issubset(schema['properties']):
        raise ValueError('Unknown partial result fields')
    for key, item in result.items():
        validate(item, schema['properties'][key], '$.' + key)
    if value['stage'] == 'reporting':
        validate(result, schema)
    evidence = evidence_check(result)
    ids = set(evidence)

    def references(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in ('evidence_ids', 'verified_after_ids') and not set(child).issubset(ids):
                    raise ValueError('Checkpoint refers to missing evidence')
                if key in ('before_evidence_id', 'after_evidence_id') and child not in ids:
                    raise ValueError('Checkpoint operation lacks evidence')
                references(child)
        elif isinstance(item, list):
            for child in item:
                references(child)
    references(result)
    return evidence


def result_progress(value, evidence):
    """Stable achievement keys; changing wording or timestamps is not progress."""
    result = value['result']
    keys = {'stage:' + value['stage']}
    for key, item in result.get('first_impression', {}).items():
        if item.strip():
            keys.add('impression:' + key)
    for name in ('screens', 'flows'):
        keys.update(name + ':' + row['id'] for row in result.get(name, []))
    keys.update('reference:' + row['url'] for row in result.get('apps', []) if row.get('evidence_ids'))
    keys.update('issue:' + row['id'] + ':' + row['status'] for row in result.get('issues', []))
    keys.update('screen:' + row['screen_id'] for row in result.get('screen_reviews', []))
    for row in result.get('coverage', []):
        if row['result'] != 'not_tested' and row['steps']:
            keys.add('coverage:' + checksum([row[k] for k in ('flow_id', 'viewport', 'state', 'perspective', 'result')]))
    # Evidence IDs can change on re-submission; actual image identities cannot.
    keys.update('image:' + checksum([row['sha256'], row['url'], row['viewport']]) for row in evidence.values())
    return keys


class Progress:
    def __init__(self, directory, context, schema, validate, evidence_check, receipt_check, record):
        self.directory = Path(directory)
        self.context, self.schema = context, schema
        self.validate, self.evidence_check = validate, evidence_check
        self.receipt_check, self.record = receipt_check, record
        self.seen = set(record.get('seen', []))
        self.last_digest = None
        self.latest = None
        self.invalid = ''
        self.image_cache = {}
        verified = self.directory / 'validated-checkpoint.json'
        if verified.exists():
            value = read_json(verified)
            if checksum(value) != record.get('checkpoint_sha256'):
                raise ValueError('Saved host checkpoint fingerprint changed')
            self.accept(value)

    def accept(self, value):
        evidence = validate_checkpoint(value, self.context, self.schema, self.validate, self.evidence_check)
        hashes = self.record.get('evidence_hashes', {})
        for key, picture in evidence.items():
            if key in hashes and hashes[key] != picture['sha256']:
                raise ValueError('Previously verified evidence bytes/hash changed')
        if self.latest:
            if self.latest['stage'] == 'reporting' and value['stage'] != 'reporting':
                raise ValueError('Reporting cannot restart browser observation')
            previous = self.latest['result']
            current = value['result']
            for section, fields in (('screens', ('id',)), ('flows', ('id',)), ('issues', ('id',)),
                                    ('apps', ('url',)), ('screen_reviews', ('screen_id',)),
                                    ('coverage', ('flow_id', 'viewport', 'state', 'perspective'))):
                old = {tuple(row[key] for key in fields) for row in previous.get(section, [])}
                new = {tuple(row[key] for key in fields) for row in current.get(section, [])}
                if not old.issubset(new):
                    raise ValueError('Checkpoint dropped earlier ' + section)
            images = {row['id']: row for row in current.get('evidence', [])}
            for row in previous.get('evidence', []):
                if row['id'] not in images or any(images[row['id']][key] != row[key] for key in
                        ('path', 'url', 'source', 'viewport', 'screen_id', 'flow_id')):
                    raise ValueError('Checkpoint dropped or changed earlier evidence identity')
        self.latest = value
        keys = result_progress(value, evidence)
        new = keys - self.seen
        self.seen.update(keys)
        self.record['seen'] = sorted(self.seen)
        self.record['evidence_hashes'] = {**hashes, **{key: row['sha256'] for key, row in evidence.items()}}
        atomic(self.directory / 'validated-checkpoint.json', value)
        self.record['checkpoint_sha256'] = checksum(value)
        return bool(new)

    def verify_latest(self):
        if not self.latest:
            raise ValueError('No verified checkpoint')
        value = read_json(self.directory / 'validated-checkpoint.json')
        if checksum(value) != self.record.get('checkpoint_sha256') or value != self.latest:
            raise ValueError('Saved host checkpoint fingerprint changed')
        evidence = validate_checkpoint(value, self.context, self.schema, self.validate, self.evidence_check)
        for key, picture in evidence.items():
            if self.record.get('evidence_hashes', {}).get(key) != picture['sha256']:
                raise ValueError('Previously verified evidence bytes/hash changed')
        return value

    def poll(self):
        progressed = False
        path = self.directory / 'checkpoint.json'
        if path.exists():
            request = None
            identity = None
            try:
                value = read_json(path)
                identity = checksum(value)
                request_path = self.directory / 'checkpoint-request.json'
                if request_path.exists():
                    candidate = read_json(request_path)
                    if not isinstance(candidate, dict) or not isinstance(candidate.get('request'), str):
                        raise ValueError('Invalid checkpoint validation request')
                    if candidate.get('checkpoint_sha256') == identity:
                        request = candidate.get('request')
                revision = (identity, request)
                if revision != self.last_digest:
                    self.last_digest = revision
                    progressed = self.accept(value)
                    self.invalid = ''
                    atomic(self.directory / 'checkpoint-validation.json', {
                        'request': request, 'checkpoint_sha256': identity, 'status': 'verified', 'reason': ''})
            except (OSError, ValueError) as error:
                # Keep the last verified draft. Never promote a corrupt later one.
                self.invalid = str(error)
                atomic(self.directory / 'checkpoint-validation.json', {
                    'request': request, 'checkpoint_sha256': identity, 'status': 'rejected', 'reason': self.invalid})
        if self.latest and self.latest['stage'] == 'reporting':
            return progressed
        # Local browser receipts are independent of model chatter. Repeating the
        # same operation or image does not keep a stuck role alive.
        frames = {}
        for file in (self.directory / 'screenshots').rglob('browser-receipts.jsonl'):
            if file.is_symlink():
                continue
            try:
                lines = file.read_text(encoding='utf-8').splitlines()
            except OSError:
                continue
            for line in lines:
                try:
                    receipt = json.loads(line)
                    if receipt.get('kind') == 'frame':
                        identity = checksum(receipt)
                        if identity not in self.image_cache:
                            self.image_cache[identity] = self.receipt_check(receipt)
                        if self.image_cache[identity]:
                            frames[receipt['id']] = receipt
                    elif receipt.get('kind') == 'action':
                        pictures = [frames[x] for x in receipt.get('frames', []) if x in frames]
                        if not pictures:
                            continue
                        operation = 'operation:' + checksum([receipt.get('tool'), receipt.get('args'),
                                                             receipt.get('url'), pictures[-1]['viewport']])
                        image = 'frame:' + pictures[-1]['sha256']
                        if operation not in self.seen and image not in self.seen:
                            progressed = True
                        self.seen.update((operation, image))
                except (ValueError, KeyError, TypeError, OSError):
                    continue
        self.record['seen'] = sorted(self.seen)
        return progressed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['save'])
    parser.add_argument('--directory', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--stage', choices=['observing', 'reporting'], default='observing')
    parser.add_argument('--remaining', action='append', default=[])
    args = parser.parse_args()
    saved = save(args.directory, args.input, args.stage, args.remaining)
    deadline = time.monotonic()+10
    path = Path(args.directory) / 'checkpoint-validation.json'
    while time.monotonic() < deadline:
        if path.exists():
            response = read_json(path)
            if not isinstance(response, dict):
                raise ValueError('Invalid host checkpoint acknowledgement')
            if response.get('request') == saved['request'] and response.get('checkpoint_sha256') == saved['checkpoint_sha256']:
                if response.get('status') != 'verified':
                    raise ValueError('Host rejected checkpoint: ' + response.get('reason', 'validation failed'))
                print(json.dumps({**saved, 'validation': 'verified'}))
                return
        time.sleep(.05)
    raise ValueError('Checkpoint saved, but host validation did not respond; do not claim completion')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
