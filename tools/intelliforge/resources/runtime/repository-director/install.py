#!/usr/bin/env python3
"""Offline installer for Repository Director. No arguments only previews."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tempfile
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


repo = load(ROOT/'skill/scripts/repository.py', 'repository_director_project')
legacy = load(ROOT/'migration.py', 'repository_director_legacy')
VERSION = repo.VERSION


def digest(data): return hashlib.sha256(data).hexdigest()


def location(name, default):
    value = Path(os.environ.get(name, str(default))).expanduser()
    if not value.is_absolute(): raise ValueError(name + ' must be absolute')
    return repo.safe(value)


def locations():
    home = Path.home()
    return {'data': location('RD_DATA_HOME', Path(os.environ.get('XDG_DATA_HOME', str(home/'.local/share')))/'repository-director'),
            'skills': location('RD_SKILLS_DIR', home/'.agents/skills'),
            'bin': location('RD_BIN_DIR', home/'.local/bin'),
            'codex': location('CODEX_HOME', home/'.codex')}


def payload(loc):
    result = {}
    for path in sorted((ROOT/'skill').rglob('*')):
        repo.safe(path)
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            result[loc['skills']/'repository-director'/path.relative_to(ROOT/'skill')] = path.read_bytes()
    launch = '#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(loc['skills']/'repository-director/scripts/repository.py')) + ' "$@"\n'
    result[loc['bin']/'repository-director'] = launch.encode()
    return result


def guide(loc):
    path = json.dumps(str(loc['skills']/'repository-director/SKILL.md'), ensure_ascii=False)
    return (repo.BEGIN + '\n'
            'リポジトリ方針・上流文書・AGENTS/READMEの整備、GitHub/GitLabの管理依頼では、\n'
            'repository-directorを読み、今回必要な手順だけ適用してください。\n'
            '既存コードからの文書整備にも使います。投稿・commit・push等は依頼と合意済み運用の範囲に従います。\n'
            'Skill file (JSON-quoted absolute path): ' + path + '\n' + repo.END + '\n').encode()


def guidance(raw, old, loc, remove=False):
    begin = repo.BEGIN.encode(); end = repo.END.encode()
    counts = raw.count(begin), raw.count(end)
    if counts == (0,0):
        if old: raise ValueError('Owned global guidance is missing; restore or merge it first')
        if remove: return raw
        return raw + (b'\n' if raw and not raw.endswith(b'\n') else b'') + guide(loc)
    if counts != (1,1) or raw.index(begin) > raw.index(end): raise ValueError('Malformed global guidance markers')
    start = raw.index(begin); finish = raw.index(end) + len(end)
    if raw[finish:finish+1] == b'\n': finish += 1
    if not old or digest(raw[start:finish]) != old.get('sha256'):
        raise ValueError('Edited/unowned global guidance is preserved')
    return raw[:start] + (b'' if remove else guide(loc)) + raw[finish:]


def legacy_present(loc):
    return any((root/name).exists() or (root/name).is_symlink()
               for root in {loc['skills'], loc['codex']/'skills'} for name in legacy.OLD_SKILLS) or (
        Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config')))/'speckit-workbench/install.json').exists() or any(
        p.exists() and b'<!-- github-project-director:begin -->' in p.read_bytes()
        for p in (loc['codex']/'AGENTS.md', loc['codex']/'AGENTS.override.md'))


def make_plan(loc, update=False, uninstall=False, migrate=False):
    if not uninstall:
        default_state=(Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'AgentIntelliforge' if os.name=='nt'
                       else Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'agent-intelliforge')
        state=location('INTELLIFORGE_STATE_DIR',default_state)
        for identity in ('speckit','github-pm','repository-director'):
            settings=repo.safe(state/'codex'/identity/'settings.json')
            if settings.is_file() and json.loads(settings.read_text(encoding='utf-8')).get('installed',True):
                raise ValueError('Portable/Plugin legacy runtime detected. Use intelliforge install --only repository-director --migrate-legacy --apply to retire its host registration first.')
    path = repo.safe(loc['data']/'install.json')
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if old and (old.get('name') != 'repository-director' or not isinstance(old.get('files'),dict)):
        raise ValueError('Invalid Repository Director ownership manifest')
    desired = payload(loc); changes = {}
    if uninstall and not old: raise ValueError('No owned Repository Director installation')
    if not uninstall and legacy_present(loc):
        if not migrate: raise ValueError('Legacy installation detected. Preview with --migrate-legacy; apply with --migrate-legacy --apply')
        changes.update(legacy.plan(loc['skills'], loc['codex'], loc['bin'], repo.safe))
    elif migrate and not uninstall:
        changes.update(legacy.plan(loc['skills'], loc['codex'], loc['bin'], repo.safe))
    target = loc['skills']/'repository-director'
    if target.exists():
        for p in target.rglob('*'):
            repo.safe(p)
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and str(p) not in old.get('files',{}):
                raise ValueError('Unowned/user-added Skill file preserved: ' + str(p))
    for name, sha in old.get('files',{}).items():
        p = Path(name)
        if not p.is_absolute() or '..' in p.parts or not (p.is_relative_to(target) or p == loc['bin']/'repository-director'):
            raise ValueError('Unsafe ownership manifest path')
        repo.safe(p)
        if not p.is_file() or digest(p.read_bytes()) != sha: raise ValueError('Edited/missing managed file preserved: ' + str(p))
        if uninstall or p not in desired: changes[p] = None
    if not uninstall:
        for p, data in desired.items():
            repo.safe(p)
            if p.exists() and p.read_bytes() != data and (not update or str(p) not in old.get('files',{})):
                raise ValueError('Existing file preserved; managed updates require --update: ' + str(p))
            if p.exists() and str(p) not in old.get('files',{}):
                raise ValueError('Unmanaged destination preserved: ' + str(p))
            changes[p] = data
    prior = old.get('guidance')
    override = loc['codex']/'AGENTS.override.md'
    repo.safe(override)
    selected = override if override.is_file() and override.read_bytes().strip() else loc['codex']/'AGENTS.md'
    if prior and Path(prior.get('path','')) != selected: raise ValueError('Global guidance path changed/shadowed; resolve before update')
    repo.safe(selected)
    raw = changes.get(selected, selected.read_bytes() if selected.exists() else b'') or b''
    raw.decode('utf-8')
    changes[selected] = guidance(raw, prior, loc, uninstall)
    if not uninstall:
        record = {'name':'repository-director','version':VERSION,'files':{str(p):digest(data) for p,data in desired.items()},
                  'guidance':{'path':str(selected),'sha256':digest(guide(loc))}}
        changes[path] = (json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode()
    else: changes[path] = None
    return {p:data for p,data in changes.items() if (p.read_bytes() if p.exists() else None) != data}


@contextmanager
def lock(loc):
    loc['data'].mkdir(parents=True, exist_ok=True)
    p = loc['data']/'.install.lock'
    try: fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError: raise ValueError('Another install or stale lock exists: ' + str(p))
    try:
        os.write(fd, str(os.getpid()).encode()); os.close(fd); yield
    finally: p.unlink(missing_ok=True)


def apply_changes(loc, changes):
    # Backups stay outside every Skill discovery root and are not executable Skills.
    present = [p for p in changes if p.is_file()]
    if present:
        backup = repo.safe(loc['data']/'backups'/('before-'+uuid.uuid4().hex+'.zip'))
        backup.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as archive:
            for n,p in enumerate(present): archive.writestr(f'{n:04d}-{p.name}',p.read_bytes())
            archive.writestr('paths.json',json.dumps({f'{n:04d}-{p.name}':str(p) for n,p in enumerate(present)},indent=2))
        backup.chmod(0o600)
    repo.transaction(changes)
    launcher = loc['bin']/'repository-director'
    if launcher.is_file(): launcher.chmod(0o755)
    # Empty retired directories are harmless but remove them so old discovery is unambiguous.
    for root in (loc['skills']/'repository-director', *(loc['skills']/n for n in legacy.OLD_SKILLS)):
        if not root.exists(): continue
        for p in sorted(root.rglob('*'), key=lambda p:len(p.parts), reverse=True):
            if p.is_dir():
                try:p.rmdir()
                except OSError:pass
        try:root.rmdir()
        except OSError:pass


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', action='version', version=VERSION)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--apply',action='store_true');mode.add_argument('--dry-run',action='store_true')
    op=p.add_mutually_exclusive_group();op.add_argument('--doctor',action='store_true');op.add_argument('--uninstall',action='store_true');op.add_argument('--self-test',action='store_true');op.add_argument('--extract',type=Path)
    p.add_argument('--update',action='store_true');p.add_argument('--migrate-legacy',action='store_true')
    a=p.parse_args(argv)
    try:
        if (a.doctor or a.self_test or a.extract) and (a.apply or a.dry_run or a.update or a.migrate_legacy):
            raise ValueError('Use diagnosis/tests/extraction separately from mutations')
        if a.uninstall and (a.update or a.migrate_legacy):raise ValueError('Use uninstall separately from update/migration')
        if a.self_test:
            return subprocess.call([sys.executable,'-B','-m','unittest','discover','-s',str(ROOT/'tests'),'-v'])
        if a.extract:
            dst=repo.safe(a.extract)
            if dst.exists() and any(dst.iterdir()):raise ValueError('Extraction destination must be empty')
            shutil.copytree(ROOT,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            print(dst);return 0
        loc=locations()
        if a.doctor:
            changes=make_plan(loc,update=True)
            missing=not (loc['data']/'install.json').is_file()
            print(json.dumps({'installed':not missing,'version':VERSION,'drift':bool(changes),'gh':bool(shutil.which('gh')),'glab':bool(shutil.which('glab')),'note':'No authentication, remote access or model execution performed.'},indent=2))
            return int(missing or bool(changes))
        changes=make_plan(loc,a.update,a.uninstall,a.migrate_legacy)
        print(json.dumps({'apply':a.apply,'changes':[{'path':str(path),'action':'remove' if data is None else 'write'} for path,data in changes.items()]},ensure_ascii=False,indent=2))
        if a.apply:
            with lock(loc):
                again=make_plan(loc,a.update,a.uninstall,a.migrate_legacy)
                if again!=changes:raise ValueError('Installation state changed since preflight; retry the preview')
                apply_changes(loc,changes)
        return 0
    except (ValueError,OSError,UnicodeError) as e:
        print('repository-director: '+str(e),file=sys.stderr);return 2



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':raise SystemExit(main())
