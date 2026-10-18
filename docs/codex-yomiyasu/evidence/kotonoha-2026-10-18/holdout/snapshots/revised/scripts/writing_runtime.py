#!/usr/bin/env python3
"""User-local writing runtimes. No global installs, profile edits or document upload."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent


def checked(argv, **kwargs):
    result = subprocess.run([str(a) for a in argv], capture_output=True, text=True,
                            encoding='utf-8', timeout=kwargs.pop('timeout', 300), **kwargs)
    if result.returncode:
        raise RuntimeError('Runtime command failed: '+str(argv[0])+'\n'+result.stderr[-3000:])
    return result.stdout.strip()


def safe(directory):
    p = Path(os.path.abspath(directory))
    for item in (p, *p.parents):
        if item.is_symlink():
            raise RuntimeError('Linked runtime path refused: '+str(item))
    return p


def key():
    system = {'Windows':'win32','Darwin':'darwin','Linux':'linux'}.get(platform.system())
    arch = {'AMD64':'x64','x86_64':'x64','aarch64':'arm64','arm64':'arm64'}.get(platform.machine())
    result = str(system)+'-'+str(arch)
    if system == 'linux' and platform.libc_ver()[0] != 'glibc':
        raise RuntimeError('Automatic Node.js provisioning requires Linux glibc; provide a compatible runtime.')
    return result


def fetch(spec, destination):
    destination = safe(destination)
    if destination.exists():
        raise RuntimeError('Refusing to replace an existing runtime directory: '+str(destination))
    if not spec['url'].startswith(('https://nodejs.org/dist/', 'https://github.com/astral-sh/uv/releases/download/')):
        raise RuntimeError('Unapproved runtime source')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.runtime-', dir=destination.parent) as td:
        archive = Path(td)/('asset.zip' if spec['url'].endswith('.zip') else 'asset.tar.gz')
        digest = hashlib.sha256(); size = 0
        with urllib.request.urlopen(spec['url'], timeout=60) as source, archive.open('wb') as out:
            while chunk := source.read(1024*1024):
                size += len(chunk)
                if size > 250_000_000: raise RuntimeError('Runtime archive exceeds limit')
                digest.update(chunk);out.write(chunk)
        if digest.hexdigest() != spec['sha256']: raise RuntimeError('Runtime archive SHA-256 mismatch')
        stage = Path(td)/'files';stage.mkdir(); total = 0
        def copy(name, length, stream, executable=False):
            nonlocal total
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:
                raise RuntimeError('Unsafe runtime archive member')
            total += length
            if total > 1_000_000_000: raise RuntimeError('Runtime extraction exceeds limit')
            target = stage.joinpath(*rel.parts);target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as out: shutil.copyfileobj(stream, out)
            target.chmod(0o755 if executable else 0o644)
        if archive.suffix == '.zip':
            with zipfile.ZipFile(archive) as z:
                for item in z.infolist():
                    if item.is_dir(): continue
                    if (item.external_attr >> 16) & 0o170000 == 0o120000:
                        raise RuntimeError('Linked zip member refused')
                    with z.open(item) as stream:copy(item.filename,item.file_size,stream)
        else:
            with tarfile.open(archive) as z:
                for item in z:
                    # npm symlinks are not needed: invoke npm-cli.js directly.
                    if item.isdir() or item.issym() or item.islnk(): continue
                    if not item.isfile(): raise RuntimeError('Special runtime archive member refused')
                    with z.extractfile(item) as stream:copy(item.name,item.size,stream,bool(item.mode & 0o111))
        inventory = {p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in stage.rglob('*') if p.is_file()}
        (stage/'.runtime.json').write_text(json.dumps({'owner':'agent-intelliforge/kotonoha-runtime',
            'archive':spec,'files':inventory},indent=2)+'\n',encoding='utf-8')
        stage.rename(destination)
    return destination


def verify(directory):
    directory = safe(directory)
    marker = directory/'.runtime.json'
    if not marker.is_file(): raise RuntimeError('Unmanaged runtime directory: '+str(directory))
    data = json.loads(marker.read_text(encoding='utf-8'))
    if data.get('owner') != 'agent-intelliforge/kotonoha-runtime': raise RuntimeError('Runtime owner mismatch')
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p != marker}
    if actual != set(data['files']): raise RuntimeError('Runtime files changed')
    for name,digest in data['files'].items():
        p = safe(directory/name)
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest: raise RuntimeError('Runtime file modified: '+name)


def npm_path(node):
    base = Path(node).resolve().parent
    for p in (base/'node_modules/npm/bin/npm-cli.js',base.parent/'lib/node_modules/npm/bin/npm-cli.js'):
        if p.is_file(): return str(p)
    npm = shutil.which('npm')
    if npm:
        p = Path(npm).resolve()
        if p.name == 'npm-cli.js': return str(p)
    raise RuntimeError('Cannot locate npm-cli.js for selected Node.js')


def _prepare(directory):
    directory = safe(directory)
    settings = directory/'settings.json'
    if settings.exists():
        data = json.loads(settings.read_text(encoding='utf-8'))
        if data.get('owner') != 'agent-intelliforge/kotonoha': raise RuntimeError('Runtime settings owner mismatch')
        for item in data.get('archives',[]): verify(directory/item)
        checked([data['python'],'-c','import sys;assert sys.version_info >= (3,11)'])
        checked([data['node'],'--version'])
        expected = hashlib.sha256((HERE/'lint-runtime/package-lock.json').read_bytes()).hexdigest()
        if data.get('lint_lock_sha256') == expected:
            lint=Path(data['lint']);safe(lint)
            manifest=lint/'.lint-files.json'
            if not manifest.is_file():raise RuntimeError('Missing managed lint inventory')
            for name,digest in json.loads(manifest.read_text(encoding='utf-8')).items():
                target=safe(lint/name)
                if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('Lint runtime modified: '+name)
            return data
    elif directory.exists() and any(directory.iterdir()):
        marker=directory/'.owner.json'
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')).get('owner') != 'agent-intelliforge/kotonoha':
            raise RuntimeError('Unmanaged runtime state: '+str(directory))
    versions = json.loads((HERE/'runtime-versions.json').read_text(encoding='utf-8'))
    spec = versions['platforms'].get(key())
    if not spec: raise RuntimeError('No verified automatic runtime for '+key())
    directory.mkdir(parents=True,exist_ok=True)
    marker=directory/'.owner.json'
    if not marker.exists():
        with marker.open('x',encoding='utf-8') as stream:json.dump({'owner':'agent-intelliforge/kotonoha'},stream)
    data = {'owner':'agent-intelliforge/kotonoha','archives':[],'python':sys.executable}
    if sys.version_info < (3,11):
        uv = shutil.which('uv')
        if not uv:
            target = directory/('uv-'+versions['uv'])
            if target.exists(): verify(target)
            else: fetch(spec['uv'], target)
            uv = str(next(target.rglob('uv.exe' if os.name == 'nt' else 'uv')))
            data['archives'].append(target.name)
        env = {**os.environ,'UV_PYTHON_INSTALL_DIR':str(directory/'python'),'UV_CACHE_DIR':str(directory/'uv-cache'),
               'UV_PYTHON_BIN_DIR':str(directory/'python-bin'),'UV_NO_MODIFY_PATH':'1'}
        checked([uv,'python','install',versions['python']],env=env)
        data['python'] = checked([uv,'python','find',versions['python']],env=env)
    node = shutil.which('node')
    if node:
        try:
            if int(checked([node,'--version']).lstrip('v').split('.')[0]) != 24: node = None
        except (RuntimeError,ValueError): node = None
    if not node:
        target = directory/('node-'+versions['node'])
        if target.exists():verify(target)
        else:fetch(spec['node'],target)
        node = str(next(target.rglob('node.exe' if os.name == 'nt' else 'node')))
        data['archives'].append(target.name)
    data['node'] = str(Path(node).resolve());data['npm'] = npm_path(node)
    lock = (HERE/'lint-runtime/package-lock.json').read_bytes()
    lock_hash = hashlib.sha256(lock).hexdigest()
    lint = directory/('lint-'+lock_hash[:16])
    if not lint.exists():
        stage = Path(tempfile.mkdtemp(prefix='.lint-',dir=directory))
        try:
            for name in ('package.json','package-lock.json'): shutil.copy2(HERE/'lint-runtime'/name,stage/name)
            env = {**os.environ,'PATH':str(Path(node).parent)+os.pathsep+os.environ.get('PATH',''),
                   'npm_config_cache':str(directory/'npm-cache')}
            checked([node,data['npm'],'ci','--ignore-scripts','--no-audit','--no-fund'],cwd=stage,env=env,timeout=600)
            inventory={p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file() and not p.is_symlink()}
            (stage/'.lint-files.json').write_text(json.dumps(inventory,sort_keys=True),encoding='utf-8')
            stage.rename(lint)
        finally:
            if stage.exists():shutil.rmtree(stage)
    if not (lint/'.lint-files.json').is_file():raise RuntimeError('Unmanaged lint cache: '+str(lint))
    for name,digest in json.loads((lint/'.lint-files.json').read_text(encoding='utf-8')).items():
        if hashlib.sha256(safe(lint/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Lint runtime modified: '+name)
    data.update(lint=str(lint),lint_lock_sha256=lock_hash)
    # End-to-end availability, without touching a user document.
    with tempfile.TemporaryDirectory(prefix='.smoke-',dir=directory) as td:
        sample=Path(td)/'sample.md';sample.write_text('# 確認\n\n入力値を保存します。\n',encoding='utf-8')
        scope={'__file__':str(HERE/'writing_lint.py'),'__name__':'kotonoha_lint_probe'}
        exec(compile((HERE/'writing_lint.py').read_text(encoding='utf-8'),scope['__file__'],'exec'),scope)
        result=scope['lint'](sample,data)
        if result['status'] != 'checked':raise RuntimeError('Writing lint smoke failed: '+json.dumps(result,ensure_ascii=False))
    data['versions'] = {'node':checked([node,'--version']),'python':checked([data['python'],'--version'])}
    temporary = directory/'settings.tmp';temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(settings)
    return data


def prepare(directory):
    directory=safe(directory);directory.parent.mkdir(parents=True,exist_ok=True)
    lock=directory.with_name('.'+directory.name+'.lock')
    try:lock.mkdir()
    except FileExistsError:raise RuntimeError('Writing runtime is locked; inspect unfinished preparation: '+str(lock))
    try:return _prepare(directory)
    finally:lock.rmdir()


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    if args.prepare: print(json.dumps(prepare(Path(args.directory)),ensure_ascii=False,indent=2))
    else:
        path=safe(args.directory)/'settings.json'
        print(path.read_text(encoding='utf-8') if path.exists() else '{"installed":false}')
