#!/usr/bin/env python3
"""User-only Office Workbench installer. Network setup is opt-in (--apply)."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
import urllib.parse
import urllib.request
import uuid

from common import OfficeError, absolute, atomic_write, file_sha, json_bytes, load_json, lock, no_symlinks, office_env, paths, run, sha

ROOT = Path(__file__).resolve().parent
VERSIONS = load_json(ROOT / 'versions.json')
VERSION = VERSIONS['kit_version']
OWNER = 'codex-office-workbench'

class HTTPSOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urllib.parse.urlsplit(newurl)
        allowed = {'github.com', 'raw.githubusercontent.com', 'release-assets.githubusercontent.com',
                   'objects.githubusercontent.com', 'github-releases.githubusercontent.com'}
        if u.scheme != 'https' or u.hostname not in allowed or u.username or u.password:
            raise OfficeError('Rejected unexpected download redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch_checked(url: str, dest: Path, expected: str, algorithm='sha256', limit=100_000_000):
    no_symlinks(dest)
    if dest.exists(): raise OfficeError('Download destination exists')
    request = urllib.request.Request(url, headers={'User-Agent': 'codex-office-workbench/1.0'})
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.build_opener(HTTPSOnly()).open(request, timeout=60) as resp:
            if urllib.parse.urlsplit(resp.url).scheme != 'https': raise OfficeError('HTTPS required')
            total = 0
            with dest.open('xb') as f:
                while True:
                    buf = resp.read(1024 * 256)
                    if not buf: break
                    total += len(buf)
                    if total > limit: raise OfficeError('Download too large')
                    f.write(buf)
        content = dest.read_bytes()
        digest = sha(content) if algorithm == 'sha256' else hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        if digest != expected:
            raise OfficeError(f'Checksum mismatch: {dest.name}. No unverified execution allowed.')
    except BaseException:
        with contextlib.suppress(FileNotFoundError): dest.unlink()
        raise

def platform_key():
    system = platform.system()
    if system not in ('Linux', 'Darwin'):
        raise OfficeError('This installer supports Linux/WSL2 and macOS, not native Windows')
    machine = platform.machine().lower()
    arch = {'x86_64': 'x64', 'amd64': 'x64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(machine)
    if not arch: raise OfficeError(f'Unsupported CPU: {machine}')
    if system == 'Linux' and Path('/etc/alpine-release').exists():
        raise OfficeError('This bundle targets glibc Linux; Alpine/musl is not supported')
    return ('linux' if system == 'Linux' else 'mac') + '-' + arch

def files_under(root: Path) -> dict[str, str]:
    result = {}
    no_symlinks(root)
    if not root.exists(): return result
    for p in sorted(root.rglob('*')):
        no_symlinks(p)
        if p.is_file(): result[p.relative_to(root).as_posix()] = file_sha(p)
    return result

def existing_config(p):
    if not p['config'].exists():
        if p['skill'].exists() or p['launcher'].exists():
            raise OfficeError('Unmanaged office-workbench Skill/launcher exists. Not overwriting it.')
        return None
    d = load_json(p['config'])
    if d.get('owner') != OWNER or d.get('schema') != 1:
        raise OfficeError('Unrecognized install manifest; refusing to overwrite')
    if absolute(d.get('skill_path','')) != p['skill'] or absolute(d.get('launcher_path','')) != p['launcher']:
        raise OfficeError('Manifest paths do not match this user environment')
    release = absolute(d.get('release',''))
    if release.parent != p['data'] / 'releases':
        raise OfficeError('Unsafe release path in manifest')
    for rel, expected in d.get('release_files', {}).items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts: raise OfficeError('Invalid manifest member')
        f = release / rel
        no_symlinks(f)
        if not f.is_file() or file_sha(f) != expected:
            raise OfficeError(f'Managed runtime changed/missing; preserve your edits before updating: {f}')
    for rel, expected in d.get('skill_files', {}).items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts: raise OfficeError('Invalid Skill manifest member')
        f = p['skill'] / rel
        no_symlinks(f)
        if not f.is_file() or file_sha(f) != expected:
            raise OfficeError(f'Edited/missing managed Skill file (not overwritten even with --force): {f}')
    if p['launcher'].exists() and file_sha(p['launcher']) != d.get('launcher_sha256'):
        raise OfficeError('Launcher was edited; refusing to overwrite')
    return d

def install_dependencies(release: Path, docling: bool):
    venv = release / 'venv'
    run([sys.executable, '-m', 'venv', str(venv)], timeout=180)
    python = str(venv / 'bin/python')
    # Never install into the user's system/interpreter environment. No sdist build scripts.
    run([python, '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check',
         '--no-input', '--index-url', 'https://pypi.org/simple', '--only-binary=:all:',
         *VERSIONS['python_requirements']], timeout=1200)
    run([python, '-m', 'pip', 'check'], timeout=60)
    run([python, '-c', 'import markitdown,pypdf,pdfplumber,pypdfium2,docx,pptx,PIL,defusedxml'], timeout=90)
    frozen = run([python, '-m', 'pip', 'freeze'], timeout=60).stdout
    atomic_write(release / 'pip-freeze.txt', frozen.encode())
    if docling:
        dv = release / 'docling-venv'
        run([sys.executable, '-m', 'venv', str(dv)], timeout=180)
        dp = str(dv / 'bin/python')
        run([dp, '-m', 'pip', '--isolated', 'install', '--disable-pip-version-check',
             '--no-input', '--index-url', 'https://pypi.org/simple', '--only-binary=:all:',
             *VERSIONS['docling_requirements']], timeout=1800)
        run([dp, '-m', 'pip', 'check'], timeout=60)
        if not (dv / 'bin/docling').is_file(): raise OfficeError('Docling CLI missing after installation')
        atomic_write(release / 'docling-pip-freeze.txt', run([dp,'-m','pip','freeze']).stdout.encode())
    return python

def setup_office(release: Path, supplied: str | None):
    key = platform_key()
    if supplied:
        binary = absolute(supplied)
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise OfficeError('--officecli must name an executable you trust')
        # Explicitly selected external file is reused, never overwritten or deleted.
        result = run([str(binary), '--version'], timeout=30, env=office_env())
        return {'path': str(binary), 'managed': False, 'sha256': file_sha(binary),
                'version_output': result.stdout.strip(), 'pinned': False}
    binary = release / 'bin/officecli'
    url = f"https://github.com/iOfficeAI/OfficeCLI/releases/download/v{VERSIONS['officecli_version']}/officecli-{key}"
    fetch_checked(url, binary, VERSIONS['officecli_assets'][key])
    binary.chmod(0o700)
    for name, digest in VERSIONS['officecli_references'].items():
        fetch_checked(f"https://raw.githubusercontent.com/iOfficeAI/OfficeCLI/v{VERSIONS['officecli_version']}/{name}",
                      release / 'references/officecli-upstream' / name, digest, 'git-blob', 2_000_000)
    result = run([str(binary), '--version'], timeout=30, env=office_env())
    if VERSIONS['officecli_version'] not in result.stdout + result.stderr:
        raise OfficeError('Downloaded OfficeCLI did not report the pinned version')
    return {'path': str(binary), 'managed': True, 'sha256': file_sha(binary),
            'version_output': result.stdout.strip(), 'pinned': True}

def system_packages(apply: bool):
    cmd = ['apt-get', 'install', '--no-install-recommends', 'libreoffice-writer',
           'libreoffice-impress', 'poppler-utils', 'fontconfig', 'fonts-noto-cjk']
    if platform.system() != 'Linux' or not shutil.which('apt-get'):
        if apply: raise OfficeError('Automatic OS packages: Debian/Ubuntu only. Install a renderer using your OS tools.')
        return {'automatic': False, 'need': ['LibreOffice Writer/Impress', 'Japanese fonts', 'fontconfig']}
    if os.geteuid() != 0: cmd.insert(0, 'sudo')
    print('Explicit OS-level action (not rolled back by this installer):', ' '.join(cmd))
    if apply:
        # Inherit terminal for sudo authentication. No credentials in args/env.
        from agent_intelliforge import subprocess_bridge as subprocess
        subprocess.run(cmd, check=True)
    return {'command': cmd, 'executed': apply}

def apply_install(args, p, old):
    p['data'].mkdir(parents=True, exist_ok=True)
    with lock(p['data'] / '.install.lock'):
        old = existing_config(p)
        features = {'docling': bool(args.with_docling), 'assets_only': bool(args.assets_only)}
        if old and not args.force:
            if old.get('features') != features:
                raise OfficeError('Feature set differs. Re-run --apply --force with desired options.')
            print('SKIP: already installed; use --force to update managed files.')
            return old
        token = time.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
        release = p['data'] / 'releases' / f'{VERSION}-{token}'
        release.mkdir(parents=True)
        changed: list[tuple[Path, bytes | None, int]] = []
        installed = False
        try:
            for name in ('common.py','office.py','install.py','versions.json','README_JA.md','SOURCES.md','LICENSE'):
                shutil.copyfile(ROOT / name, release / name)
            shutil.copytree(ROOT / 'skills', release / 'skills')
            shutil.copytree(ROOT / 'tests', release / 'tests')
            if args.assets_only:
                python = sys.executable
                office = {'path': None, 'managed': False, 'pinned': False}
            else:
                python = install_dependencies(release, args.with_docling)
                office = setup_office(release, args.officecli)
            launcher = ("#!/bin/sh\n# Managed by codex-office-workbench.\n" +
                        'exec ' + __import__('shlex').quote(python) + ' ' +
                        __import__('shlex').quote(str(release / 'office.py')) + ' "$@"\n').encode()
            # Stage all downloads/venvs first. Existing active assets have not changed yet.
            targets = {p['launcher']: (launcher,0o700)}
            skill_template = release / 'skills/office-workbench'
            for f in skill_template.rglob('*'):
                if f.is_file():
                    content = f.read_bytes().replace(b'{{LAUNCHER}}', str(p['launcher']).encode()).replace(b'{{RELEASE}}', str(release).encode())
                    targets[p['skill'] / f.relative_to(skill_template)] = (content,0o600)
            config = {
                'schema':1, 'owner':OWNER, 'kit_version':VERSION, 'release':str(release),
                'python':python, 'officecli':office, 'features':features,
                'skill_path':str(p['skill']), 'launcher_path':str(p['launcher']),
                'launcher_sha256':sha(launcher), 'codex_home':str(p['codex']),
                'skill_files':{x.relative_to(p['skill']).as_posix():sha(b) for x,(b,m) in targets.items() if x!=p['launcher']},
                'release_files':{}, 'installed_at':token,
            }
            for f in release.rglob('*'):
                if f.is_file() and not any(v in f.relative_to(release).parts for v in ('venv','docling-venv','__pycache__')):
                    config['release_files'][f.relative_to(release).as_posix()] = file_sha(f)
            targets[p['config']] = (json_bytes(config),0o600)
            backups = p['data'] / 'backups' / token
            for dest, (data, mode) in targets.items():
                no_symlinks(dest)
                if dest.exists():
                    allowed = dest in (p['launcher'],p['config']) or (old and dest.relative_to(p['skill']).as_posix() in old.get('skill_files',{}))
                    if not old or not allowed: raise OfficeError(f'Unmanaged file conflict: {dest}')
            for n,(dest,(data,mode)) in enumerate(targets.items()):
                prior = dest.read_bytes() if dest.exists() else None
                perm = dest.stat().st_mode & 0o777 if dest.exists() else mode
                if prior is not None:
                    atomic_write(backups / f'{n:04d}.bin', prior)
                changed.append((dest,prior,perm))
                atomic_write(dest,data,mode)
            if changed:
                atomic_write(backups / 'index.json', json_bytes({'files':[{'path':str(d),'backup':f'{i:04d}.bin' if b is not None else None} for i,(d,b,m) in enumerate(changed)]}))
            installed = True
            print(json.dumps({'installed':True, 'version':VERSION, 'skill':str(p['skill']),
                  'launcher':str(p['launcher']), 'assets_only':args.assets_only,
                  'notice':'Tool installation is not visual quality certification. Run doctor and smoke-test.'}, ensure_ascii=False,indent=2))
            return config
        except BaseException:
            for dest, prior, mode in reversed(changed):
                if prior is None:
                    with contextlib.suppress(FileNotFoundError):dest.unlink()
                else: atomic_write(dest,prior,mode)
            raise
        finally:
            if not installed:
                shutil.rmtree(release, ignore_errors=True)

def uninstall(p, apply):
    d = existing_config(p)
    if not d: print('SKIP: not installed'); return
    # MCP is managed separately to avoid deleting an active server's executable.
    config_toml = p['codex'] / 'config.toml'
    if config_toml.exists():
        import tomllib
        try: servers=tomllib.loads(config_toml.read_text(encoding="utf-8")).get('mcp_servers',{})
        except ValueError as e: raise OfficeError('Invalid Codex config.toml; refusing uninstall') from e
        if 'codex-office-workbench' in servers:
            raise OfficeError('Run office-workbench mcp-disable --apply before uninstalling')
    targets=[p['skill']/r for r in d['skill_files']]+[p['launcher'],p['config']]
    print(json.dumps({'remove':[str(x) for x in targets],
                      'preserve':['documents','other tools/configs','downloaded releases and backups'], 'apply':apply},indent=2))
    if not apply:return
    with lock(p['data']/'.install.lock'):
        existing_config(p)
        for f in targets:
            if f.exists(): f.unlink()
        for directory in sorted(p['skill'].rglob('*'),key=lambda x:len(x.parts),reverse=True):
            if directory.is_dir():
                with contextlib.suppress(OSError):directory.rmdir()
        with contextlib.suppress(OSError): p['skill'].rmdir()
    print('Uninstalled owned entry points only. Releases/backups retained; no user documents removed.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    a=parser.add_mutually_exclusive_group()
    a.add_argument('--apply',action='store_true');a.add_argument('--dry-run',action='store_true')
    parser.add_argument('--force',action='store_true',help='update only unedited owned files; preserve old release')
    parser.add_argument('--doctor',action='store_true')
    parser.add_argument('--uninstall',action='store_true')
    parser.add_argument('--with-mcp',action='store_true',help='opt-in OfficeCLI stdio server registration')
    parser.add_argument('--with-docling',action='store_true',help='large local Docling environment; model download is separate')
    parser.add_argument('--officecli',help='explicit existing trusted binary to reuse; never modify it')
    parser.add_argument('--assets-only',action='store_true',help='offline/incomplete kit only; no editing tools installed')
    parser.add_argument('--system-deps',action='store_true',help='show OS renderer/font package command')
    parser.add_argument('--install-system-deps',action='store_true',help='with --apply, explicitly invoke apt/sudo for rendering')
    args=parser.parse_args()
    p=paths()
    for x in p.values():no_symlinks(x)
    if args.doctor:
        from office import doctor
        return doctor(p, strict=False)
    if args.uninstall:
        uninstall(p,args.apply);return 0
    if args.system_deps or args.install_system_deps:
        system_packages(args.install_system_deps and args.apply)
        return 0
    if args.assets_only and (args.with_docling or args.with_mcp):
        raise OfficeError('--assets-only cannot enable MCP/Docling')
    old=existing_config(p)
    print(json.dumps({'action':'update' if old and args.force else ('skip' if old else 'install'),
          'version':VERSION,'paths':{k:str(v) for k,v in p.items()},
          'dependencies':VERSIONS['python_requirements'], 'mcp_opt_in':args.with_mcp,
          'writes':bool(args.apply),'existing_settings':'not modified (except explicit MCP opt-in)'},indent=2,ensure_ascii=False))
    if not args.apply:return 0
    if not args.assets_only and not shutil.which('codex'):
        raise OfficeError('Install Codex first (or use --assets-only for inspection/testing)')
    d=apply_install(args,p,old)
    if args.with_mcp:
        result=run([d['python'],str(Path(d['release'])/'office.py'),'mcp-enable','--apply'],check=False)
        print(result.stdout)
        if result.returncode:
            print('Core install succeeded; MCP registration failed: '+result.stderr,file=sys.stderr)
            return result.returncode
    return 0


from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':
    try:sys.exit(main())
    except (OfficeError,OSError,ValueError) as e:
        print('ERROR: '+str(e),file=sys.stderr);sys.exit(2)
