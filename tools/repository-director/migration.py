"""Inspect legacy ownership before retiring any discoverable entrypoint."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re

OLD_SKILLS = ('github-project-director', 'speckit-workbench', 'upstream-new', 'upstream-existing',
              'upstream-change', 'upstream-bug', 'upstream-refactor', 'upstream-check', 'upstream-review', 'upstream-approve')


def digest(data): return hashlib.sha256(data).hexdigest()


def remove_guide(raw: bytes, record: dict, skill: Path):
    begin = b'<!-- github-project-director:begin -->'; end = b'<!-- github-project-director:end -->'
    if raw.count(begin) != 1 or raw.count(end) != 1:
        raise ValueError('Legacy global guidance missing/duplicated; preserve and repair it first')
    start = raw.index(begin); finish = raw.index(end) + len(end)
    if finish <= start: raise ValueError('Invalid legacy guidance markers')
    if raw[finish:finish+1] == b'\n': finish += 1
    block = raw[start:finish]
    owner = b'<!-- owner: ' + digest(str(skill).encode()).encode() + b' -->'
    if digest(block) != record.get('sha256') or block.count(owner) != 1:
        raise ValueError('Edited or foreign legacy guidance; preserve and merge manually')
    if record.get('prefix') == '\n' and raw[max(0,start-1):start] == b'\n': start -= 1
    return raw[:start] + raw[finish:]


def plan(skills: Path, codex: Path, bin_dir: Path, safe, ignored=()) -> dict[Path, bytes | None]:
    """No mutation. Project documents, specify, venvs and historical data are retained."""
    changes = {}; claimed = set(ignored)
    github = skills / 'github-project-director'; manifest = github / '.github-pm-install.json'
    if github not in claimed and github.exists() and (manifest.exists() or (github/'SKILL.md').exists()):
        safe(manifest)
        if not manifest.is_file(): raise ValueError('Unowned github-project-director; export/resolve it before migration')
        value = json.loads(manifest.read_text(encoding='utf-8'))
        if value.get('name') != 'github-project-director' or not isinstance(value.get('files'), dict):
            raise ValueError('Invalid legacy GitHub manifest')
        expected = set()
        for name, sha in value['files'].items():
            rel = Path(name)
            if rel.is_absolute() or '..' in rel.parts or '\\' in name or not re.fullmatch('[0-9a-f]{64}', str(sha)):
                raise ValueError('Unsafe legacy GitHub manifest')
            p = safe(github / rel); expected.add(p)
            if not p.is_file() or digest(p.read_bytes()) != sha: raise ValueError('Edited/missing legacy Skill: ' + str(p))
            changes[p] = None
        actual = {safe(p) for p in github.rglob('*') if p.is_file() and p.name != manifest.name and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        if actual != expected: raise ValueError('User-added legacy Skill files are preserved; resolve them first')
        guidance = value.get('guidance')
        if guidance:
            if Path(guidance.get('home','')) != codex or guidance.get('file') not in ('AGENTS.md','AGENTS.override.md'):
                raise ValueError('Legacy guidance belongs to a different Codex home')
            p = safe(codex / guidance['file'])
            changes[p] = remove_guide(p.read_bytes(), guidance, github)
        changes[manifest] = None; claimed.add(github)
    conf = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home()/'.config'))) / 'speckit-workbench/install.json'
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share'))) / 'speckit-workbench'
    swb_skill = Path(os.environ.get('SWB_SKILL_DIR', str(skills/'speckit-workbench')))
    swb_bin = Path(os.environ.get('SWB_BIN_DIR', str(bin_dir))) / 'speckit-workbench'
    skill_dirs = [swb_skill, *(swb_skill.parent / n for n in OLD_SKILLS if n.startswith('upstream-'))]
    if conf.exists():
        safe(conf); value = json.loads(conf.read_text(encoding='utf-8'))
        managed = value.get('managed')
        if not isinstance(managed, dict) or not managed: raise ValueError('Invalid legacy Workbench manifest')
        for name, sha in managed.items():
            p = Path(name)
            if not p.is_absolute() or '..' in p.parts or not re.fullmatch('[0-9a-f]{64}', str(sha)):
                raise ValueError('Unsafe legacy Workbench manifest')
            if not (p == swb_bin or p.is_relative_to(data/'releases') or any(p.is_relative_to(d) for d in skill_dirs)):
                raise ValueError('Out-of-scope legacy manifest path: ' + name)
            safe(p)
            if not p.is_file() or digest(p.read_bytes()) != sha:
                raise ValueError('Edited/missing legacy Workbench file: ' + name)
            changes[p] = None
        for folder in skill_dirs:
            safe(folder)
            for p in folder.rglob('*') if folder.exists() else []:
                safe(p)
                if p.is_file() and p not in changes and '__pycache__' not in p.parts and p.suffix != '.pyc':
                    raise ValueError('User-added legacy Workbench files are preserved: ' + str(p))
            claimed.add(folder)
        changes[conf] = None
    roots = {skills, swb_skill.parent, codex/'skills'}
    for root in roots:
        for name in OLD_SKILLS:
            folder = safe(root / name)
            if (folder/'SKILL.md').exists() and folder not in claimed:
                raise ValueError('Unowned legacy Skill remains discoverable: ' + str(folder))
    for path in (codex/'AGENTS.md', codex/'AGENTS.override.md'):
        safe(path)
        raw = changes.get(path, path.read_bytes() if path.exists() else b'') or b''
        if b'<!-- github-project-director:begin -->' in raw:
            raise ValueError('Unowned legacy global guidance remains; resolve it before migration')
    return changes
