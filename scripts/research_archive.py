#!/usr/bin/env python3
"""Build, verify and restore published research records without running models.

Restoration always targets a new directory. Installation never calls this tool.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT/'docs/research-archives.json'
REPOSITORY = 'Mak-GIBA/agent-intelliforge'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+'\n').encode()


def relative(name):
    p = PurePosixPath(name)
    if (not name or not p.parts or p.is_absolute() or '..' in p.parts or p.as_posix() != name
            or '\\' in name or ':' in name or any(ord(c) < 32 for c in name)):
        raise ValueError('Unsafe archive path: '+repr(name))
    return p


def group(name):
    parts = PurePosixPath(name).parts
    if name.startswith('docs/design-research/') and len(parts) > 3:
        return 'research-history'
    if name.startswith('docs/codex-yomiyasu/evidence/'):
        return 'writing-evidence'
    if name.startswith('tools/codex-yomiyasu/evaluation'):
        return 'legacy-writing-studies'
    return None


def remove_from_tree(name):
    parts = PurePosixPath(name).parts
    kind = group(name)
    if kind == 'research-history':
        return 'runs' in parts
    if kind == 'writing-evidence':
        if len(parts) <= 5:
            return parts[-1].startswith(('W0', 'W1', 'W2')) or parts[-1] in {'runner.py', 'flow_native.py'}
        return not ('research-figures' in parts or 'public-source-licenses' in parts
                    or 'LICENSE' in parts[-1].upper() or parts[-1].upper().startswith('COPYING'))
    if kind == 'legacy-writing-studies':
        return not (len(parts) == 4 and parts[-1].lower().startswith('readme'))
    return False


def git_files(repo, commit):
    raw = subprocess.check_output(['git', 'ls-tree', '-rz', '--full-tree', commit], cwd=repo)
    result = {}
    for row in raw.split(b'\0'):
        if not row:
            continue
        head, path = row.split(b'\t', 1)
        mode, kind, oid = head.decode().split()
        name = path.decode('utf-8')
        relative(name)
        if kind != 'blob' or mode not in {'100644', '100755'}:
            raise ValueError('Unsupported tracked file: '+name)
        result[name] = {'mode': int(mode, 8) & 0o777, 'oid': oid}
    return result


def ignored_paths(all_names, removed):
    """Collapse only directories whose tracked descendants are all archived."""
    children = {}
    for name in all_names:
        parts = PurePosixPath(name).parts
        for i in range(1, len(parts)):
            children.setdefault('/'.join(parts[:i]), set()).add(name)
    selected = []
    for name in sorted(removed):
        parts = PurePosixPath(name).parts
        prefix = next(('/'.join(parts[:i])+'/' for i in range(1, len(parts))
                       if children['/'.join(parts[:i])] <= removed), name)
        if prefix not in selected:
            selected.append(prefix)
    return sorted(selected)


def build(repo, commit, output, archive_id):
    commit = subprocess.check_output(['git', 'rev-parse', commit+'^{commit}'], cwd=repo, text=True).strip()
    all_files = git_files(repo, commit)
    selected = {n: v for n, v in all_files.items() if group(n)}
    if not selected:
        raise ValueError('No research records at source commit')
    output.mkdir(parents=True, exist_ok=False)
    inventory = {'schema_version': 1, 'source_commit': commit, 'files': {}}
    archive = output/(archive_id+'.tar.gz')
    proc = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        with archive.open('xb') as target, gzip.GzipFile(fileobj=target, mode='wb', mtime=0, filename='') as gz:
            with tarfile.open(fileobj=gz, mode='w|', format=tarfile.PAX_FORMAT) as tar:
                for name, spec in sorted(selected.items()):
                    proc.stdin.write((spec['oid']+'\n').encode()); proc.stdin.flush()
                    _, kind, size = proc.stdout.readline().decode().split()
                    if kind != 'blob':
                        raise ValueError('Missing Git blob')
                    raw = proc.stdout.read(int(size))
                    if len(raw) != int(size) or proc.stdout.read(1) != b'\n':
                        raise ValueError('Truncated Git blob')
                    inventory['files'][name] = {'sha256': sha(raw), 'bytes': len(raw), 'mode': spec['mode'],
                                                'group': group(name), 'removed': remove_from_tree(name)}
                    info = tarfile.TarInfo('records/'+name); info.size = len(raw); info.mode = spec['mode']
                    tar.addfile(info, io.BytesIO(raw))
                raw = encoded(inventory)
                info = tarfile.TarInfo('inventory.json'); info.size = len(raw); info.mode = 0o644
                tar.addfile(info, io.BytesIO(raw))
    finally:
        proc.stdin.close(); proc.stdout.close()
        if proc.wait() != 0:
            raise ValueError('Git blob reader failed')
    removed = {n for n, row in inventory['files'].items() if row['removed']}
    entry = {'id': archive_id, 'source_commit': commit,
             'url': f'https://github.com/{REPOSITORY}/releases/download/{archive_id}/{archive.name}',
             'sha256': sha(archive.read_bytes()), 'archive_bytes': archive.stat().st_size,
             'inventory_sha256': sha(encoded(inventory)), 'file_count': len(selected),
             'original_bytes': sum(r['bytes'] for r in inventory['files'].values()),
             'removed_file_count': len(removed),
             'removed_bytes': sum(inventory['files'][n]['bytes'] for n in removed),
             'ignored_paths': ignored_paths(all_files, removed)}
    (output/'inventory.json').write_bytes(encoded(inventory))
    (output/'registry.json').write_bytes(encoded({'schema_version': 1, 'archives': [entry]}))
    (output/'SHA256SUMS').write_text(entry['sha256']+'  '+archive.name+'\n', encoding='utf-8')
    return entry


def entry_for(registry, archive_id):
    data = json.loads(registry.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported archive registry')
    entries = data['archives']
    if archive_id is None:
        if len(entries) != 1:
            raise ValueError('Select an archive with --id')
        return entries[0]
    for entry in entries:
        if entry['id'] == archive_id:
            return entry
    raise ValueError('Unknown archive: '+archive_id)


@contextmanager
def archive_file(entry, local=None):
    if local is not None:
        yield local
        return
    if not entry['url'].startswith('https://'):
        raise ValueError('Archive download requires HTTPS')
    with tempfile.TemporaryDirectory(prefix='research-archive-download-') as td:
        dest = Path(td)/'archive.tar.gz'
        with urllib.request.urlopen(entry['url'], timeout=60) as response, dest.open('xb') as out:
            remaining = entry['archive_bytes']
            while remaining > 0:
                block = response.read(min(1048576, remaining))
                if not block:
                    break
                out.write(block); remaining -= len(block)
            if remaining or response.read(1):
                raise ValueError('Archive download size differs')
        yield dest


@contextmanager
def validated(entry, path):
    if path.stat().st_size != entry['archive_bytes'] or sha(path.read_bytes()) != entry['sha256']:
        raise ValueError('Archive checksum or size differs')
    with tarfile.open(path, 'r:gz') as tar:
        members = tar.getmembers(); names = [m.name for m in members]
        if len(set(names)) != len(names) or any(not m.isfile() for m in members):
            raise ValueError('Duplicate or non-regular archive member')
        for name in names:
            relative(name)
        raw = tar.extractfile('inventory.json').read()
        if sha(raw) != entry['inventory_sha256']:
            raise ValueError('Inventory checksum differs')
        inventory = json.loads(raw)
        if inventory['schema_version'] != 1 or inventory['source_commit'] != entry['source_commit']:
            raise ValueError('Inventory source differs')
        files = inventory['files']
        if len(files) != entry['file_count'] or set(names) != {'inventory.json', *('records/'+n for n in files)}:
            raise ValueError('Archive file set differs')
        if sum(r['bytes'] for r in files.values()) != entry['original_bytes']:
            raise ValueError('Archive expanded size differs')
        for name, row in files.items():
            relative(name)
            member = tar.getmember('records/'+name)
            if member.size != row['bytes'] or sha(tar.extractfile(member).read()) != row['sha256']:
                raise ValueError('Archived file differs: '+name)
        yield tar, inventory


def verify(entry, path):
    with validated(entry, path) as (_, inventory):
        return {'status': 'verified', 'id': entry['id'], 'files': len(inventory['files']), 'sha256': entry['sha256']}


def restore(entry, path, destination):
    if destination.exists() or destination.is_symlink():
        raise ValueError('Restore destination must not exist; existing files are never overwritten')
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.research-archive-', dir=destination.parent))
    try:
        with validated(entry, path) as (tar, inventory):
            for name, row in inventory['files'].items():
                target = stage/relative(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile('records/'+name) as source, target.open('xb') as out:
                    shutil.copyfileobj(source, out)
                target.chmod(row['mode'] & 0o777)
                if sha(target.read_bytes()) != row['sha256']:
                    raise ValueError('Restored file differs: '+name)
        if destination.exists() or destination.is_symlink():
            raise ValueError('Restore destination appeared during extraction')
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {'status': 'restored', 'id': entry['id'], 'files': entry['file_count'], 'destination': str(destination)}


def check_tree(root, registry):
    data = json.loads(registry.read_text(encoding='utf-8'))
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    raw = [n for n in files if n.startswith('.artifacts/') or
           (n.startswith('docs/design-research/') and 'runs' in PurePosixPath(n).parts)]
    if raw:
        raise ValueError('Raw run records must not be tracked: '+', '.join(raw[:5]))
    prefixes = [p for entry in data['archives'] for p in entry['ignored_paths']]
    found = [n for n in files if n and any(n.startswith(p) if p.endswith('/') else n == p for p in prefixes)]
    if found:
        raise ValueError('Archived records are tracked again: '+', '.join(found[:5]))
    return {'status': 'passed', 'archives': len(data['archives'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    sub = parser.add_subparsers(dest='command', required=True)
    make = sub.add_parser('build', help='Maintainer: freeze committed research records into a new output directory')
    make.add_argument('--source-commit', required=True); make.add_argument('--output', type=Path, required=True)
    make.add_argument('--id', required=True)
    sub.add_parser('check-tree', help='Offline CI: reject reintroduction of archived records')
    for name in ('verify', 'restore'):
        command = sub.add_parser(name); command.add_argument('--id')
        command.add_argument('--archive', type=Path, help='Use a local archive instead of downloading')
        if name == 'restore':
            command.add_argument('--destination', type=Path, required=True)
    a = parser.parse_args()
    try:
        if a.command == 'build':
            result = build(ROOT, a.source_commit, a.output, a.id)
        elif a.command == 'check-tree':
            result = check_tree(ROOT, a.registry)
        else:
            entry = entry_for(a.registry, a.id)
            with archive_file(entry, a.archive) as path:
                result = verify(entry, path) if a.command == 'verify' else restore(entry, path, a.destination)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, tarfile.TarError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
