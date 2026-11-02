#!/usr/bin/env python3
"""Read repository evidence, add navigation/drafts, and check local documentation.

No model, package scripts, imports from the target, network or application writes.
The Skill writes the substantive specification after inspecting the evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

VERSION = '1.3.0'
BEGIN = '<!-- repository-director:begin -->'
END = '<!-- repository-director:end -->'
DRAFT = '<!-- repository-director:draft -->'
EXCLUDED = {'.git', '.env', '.venv', 'venv', 'node_modules', 'vendor', 'dist', 'build',
            '__pycache__', '.next', '.cache', '.workgraph-recall'}
ROLES = {
    'purpose': ('purpose.md', ['purpose', 'overview', '目的', '背景']),
    'policy': ('repository-policy.md', ['repository-policy', 'development', '運営方針', '開発方針', '開発・運用']),
    'requirements': ('requirements.md', ['requirements', '機能仕様', '要件', '要件定義']),
    'architecture': ('architecture.md', ['architecture', '構成・開発・運用', '全体設計']),
    'core': ('core-logic.md', ['core-logic', 'コアロジック']),
    'verification': ('verification.md', ['verification', 'development', 'テスト仕様', '検証', '開発・運用']),
}
TITLES = {'purpose': '目的・背景', 'policy': 'リポジトリ運営方針', 'requirements': '要件・機能仕様',
          'architecture': '全体設計', 'core': 'コアロジック', 'verification': '検証・運用'}
GROUPS = {
    'purpose': ('purpose.md', ('purpose', 'requirements'), '目的・背景', '事業目的・背景と主要機能'),
    'architecture': ('architecture.md', ('architecture', 'core'), '全体設計', 'ファイル構成・入口・主要処理の流れ'),
    'development': ('development.md', ('policy', 'verification'), '開発・運用', '開発・テスト・変更と運用の手順'),
}
ROLE_GROUP = {role: group for group, (_, roles, _, _) in GROUPS.items() for role in roles}


def safe(path: Path) -> Path:
    path = Path(os.path.abspath(path.expanduser()))
    for part in (path, *path.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError(f'Linked path is preserved: {part}')
        if part.exists() and getattr(part.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
            raise ValueError(f'Reparse path is preserved: {part}')
        if part != path and part.exists() and not part.is_dir():
            raise ValueError(f'Non-directory parent: {part}')
    return path


def atomic(path: Path, data: bytes):
    safe(path)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.repository-director-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data); out.flush(); os.fsync(out.fileno())
        os.chmod(name,mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def transaction(changes: dict[Path, bytes | None]):
    """Validate the whole batch, detect intervening changes, restore on local failure."""
    before = {}
    for path in changes:
        safe(path)
        if path.exists() and not path.is_file():
            raise ValueError(f'Not a regular file: {path}')
        before[path] = path.read_bytes() if path.exists() else None
    written = []
    try:
        for path, data in changes.items():
            current = path.read_bytes() if path.exists() else None
            if current != before[path]:
                raise ValueError(f'Changed during operation: {path}')
            if current == data: continue
            if data is None: path.unlink(missing_ok=True)
            else: atomic(path, data)
            written.append(path)
    except BaseException:
        for path in reversed(written):
            if before[path] is None: path.unlink(missing_ok=True)
            else: atomic(path, before[path])
        raise


def git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=20)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def inventory(root: Path) -> list[str]:
    result = []
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and (not d.startswith('.') or d in {'.github','.gitlab'})
                         and not (Path(base) / d).is_symlink()
                         and not getattr(Path(base)/d,'is_junction',lambda:False)())
        for name in sorted(names):
            path = Path(base) / name
            if name.startswith('.') or path.is_symlink(): continue
            result.append(path.relative_to(root).as_posix())
    return result


def inspect(root: Path) -> dict:
    safe(root)
    if not root.is_dir(): raise ValueError('Choose an existing project directory')
    files = inventory(root)
    docs = [f for f in files if f.lower().endswith('.md') and
            (f.startswith(('docs/','specs/')) or Path(f).name.lower() in ('readme.md', 'agents.md', 'claude.md'))]
    sources = [f for f in files if Path(f).suffix.lower() in {'.py', '.ts', '.tsx', '.js', '.jsx', '.rs', '.go', '.java', '.cs', '.rb', '.cpp', '.c', '.sh'}]
    tests = [f for f in sources if 'test' in f.lower() or 'spec' in Path(f).stem.lower()]
    indexes = [f for f in ('docs/INDEX.md', 'docs/index.md', 'docs/README.md') if f in docs]
    if not indexes and (root/'README.md').is_file():
        safe(root/'README.md')
        text = (root/'README.md').read_text(encoding='utf-8')
        match = re.search(r'\[文書索引\]\(([^)]+)\)',text)
        if match and match[1] in docs: indexes.append(match[1])
    entry = indexes[0] if indexes else 'README.md'
    # A custom role mapping may be recorded in either an existing index or README.
    navigation = []
    for rel in dict.fromkeys((entry, 'README.md')):
        if rel in docs:
            navigation.append((root / rel, safe(root / rel).read_text(encoding='utf-8')))
    roles = {}
    for role, (_, aliases) in ROLES.items():
        matches = [f for f in docs if Path(f).stem.casefold() in [a.casefold() for a in aliases]]
        labels = [TITLES[role]]
        if role in ('policy', 'verification'): labels.append(GROUPS['development'][2])
        for label in labels:
            found = False
            for index, text in navigation:
                link=re.search(r'\['+re.escape(label)+r'\]\(([^)]+)\)',text)
                if link:
                    url=urlsplit(link[1])
                    if url.scheme or url.netloc: continue
                    target=Path(os.path.abspath(index.parent/unquote(url.path)))
                    if target.is_relative_to(root) and target.relative_to(root).as_posix() in docs:
                        matches=[target.relative_to(root).as_posix()]; found=True; break
            if found: break
        roles[role] = matches
    return {'schema_version': 1, 'mode': 'existing' if sources else 'new',
            'revision': (git(root, 'rev-parse', 'HEAD') or '').strip() or None,
            'index': entry, 'documents': docs,
            'sources': sources, 'tests': tests, 'roles': roles,
            'manifests': [f for f in files if Path(f).name in ('package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod', 'Makefile')],
            'note': 'File inventory is evidence to investigate, not approved requirements or executed tests.'}


def block(text: str, content: str) -> str:
    counts = text.count(BEGIN), text.count(END)
    if counts == (0, 0):
        return text + ('\n' if text and not text.endswith('\n') else '') + '\n' + BEGIN + '\n' + content + END + '\n'
    if counts != (1, 1) or text.index(BEGIN) > text.index(END):
        raise ValueError('Malformed repository-director markers; preserve and repair manually')
    # Project-owned text may have been edited. Reinitialization never replaces it.
    return text


def draft(role: str, facts: dict, approach: str) -> str:
    group = ROLE_GROUP.get(role, role)
    sections = {
        'purpose': ('事業目的・背景', ('事業目的と背景', '利用者と提供価値', '主要機能と対象範囲')),
        'architecture': ('全体設計', ('全体像', 'ファイル構成', 'エントリーポイント', '主要処理の流れ', '設計上の要点')),
        'development': ('開発・運用', ('開発環境と実行', 'テスト', '変更とレビュー', '運用')),
    }
    title, headings = sections[group]
    return '# ' + title + '\n\n' + DRAFT + '\n\n' + '\n\n'.join('## ' + heading for heading in headings) + '\n'


def initialize(root: Path, mode: str, approach: str, apply: bool, agent: str, documents=(), index_path=None) -> dict:
    facts = inspect(root)
    if index_path:
        selected = Path(index_path)
        if selected.is_absolute() or '..' in selected.parts or selected.suffix != '.md': raise ValueError('Index must be a relative Markdown file')
        safe(root / selected); facts['index'] = selected.as_posix()
    for entry in documents:
        role, sep, name = entry.partition('='); rel = Path(name)
        if not sep or role not in ROLES or rel.is_absolute() or '..' in rel.parts or rel.suffix != '.md':
            raise ValueError('Use --document role=relative.md')
        target = safe(root / rel)
        if not target.is_file(): raise ValueError('Mapped document must exist: ' + name)
        facts['roles'][role] = [rel.as_posix()]
    changes = {}
    for group, (filename, roles, _, _) in GROUPS.items():
        # Business purpose must not be inferred merely from a requirements file.
        anchors = roles[:1] if group == 'purpose' else roles
        anchor = next((facts['roles'][r][0] for r in anchors if facts['roles'][r]), 'docs/' + filename)
        for role in roles:
            if not facts['roles'][role]: facts['roles'][role] = [anchor]
        path = safe(root / anchor)
        if not path.exists(): changes[path] = draft(group, facts, approach).encode()
    targets = {}
    for role, names in facts['roles'].items():
        for name in names: targets.setdefault(name, []).append(role)
    links = []
    for target, roles in targets.items():
        relative = os.path.relpath(root / target, (root / facts['index']).parent).replace(os.sep, '/')
        labels = []; descriptions = []
        for group in dict.fromkeys(ROLE_GROUP[r] for r in roles):
            members = [r for r in roles if ROLE_GROUP[r] == group]
            title = GROUPS[group][2] if len(members) > 1 else TITLES[members[0]]
            labels.append(f'[{title}]({relative})')
            descriptions.append(GROUPS[group][3] if len(members) > 1 else title)
        links.append('| ' + ' / '.join(labels) + ' | ' + '、'.join(descriptions) + ' |')
    nav = '## 文書一覧\n\n| 文書 | 内容 |\n| --- | --- |\n' + '\n'.join(links) + '\n\n'
    # Keep existing named specs visible, even when they do not match a standard role.
    extra = [f for f in facts['documents'] if f.startswith('docs/') and f != facts['index']
             and f not in {v for values in facts['roles'].values() for v in values}]
    if extra:
        nav += '## 既存の詳細資料\n\n' + ''.join(f'- [{Path(f).stem}]({os.path.relpath(root / f, (root / facts["index"]).parent).replace(os.sep, "/")})\n' for f in extra) + '\n'
    index = safe(root / facts['index'])
    if facts['index'] != 'README.md':
        old = index.read_text(encoding='utf-8') if index.exists() else '# ドキュメント\n'
        changes[index] = block(old, nav).encode()
    readme_nav = nav if facts['index'] == 'README.md' else '## ドキュメント\n\n[文書索引](' + facts['index'] + ')\n'
    guides = {
        'README.md': readme_nav + '\n開発時のルールは[AGENTS](AGENTS.md)を参照してください。\n',
        'AGENTS.md': '## 変更前と完了前の確認\n\n- [文書案内](' + facts['index'] + ')から目的・設計・開発手順と関連仕様を読んでください。\n- 依頼範囲の変更・関連テスト・文書を一緒に更新し、差分と説明を照合してください。\n- 文書整備だけの依頼ではアプリのソース・依存・DBを変更しないでください。\n- 未実施の確認は明示し、コミット・PR/MRでは目的・変更・確認結果・残件を伝えてください。\n',
        **({'CLAUDE.md': '開発の共通方針は [AGENTS.md](AGENTS.md) を参照してください。\n'} if agent == 'claude' or (root / 'CLAUDE.md').exists() else {}),
    }
    for filename, text in guides.items():
        path = safe(root / filename)
        content = path.read_text(encoding='utf-8') if path.exists() else '# ' + ('開発ガイド' if filename == 'AGENTS.md' else root.name) + '\n'
        if filename == 'README.md' and not path.exists():
            content += '\n' + DRAFT + '\n\n## 概要\n\n## 導入\n\n## 使い方\n\n## 主なコマンド\n'
            if any((root / name).is_file() for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt')):
                content += '\n## ライセンス\n'
        changes[path] = block(content, text).encode()
    changed = {p: data for p, data in changes.items() if not p.exists() or p.read_bytes() != data}
    if apply: transaction(changed)
    return {'mode': facts['mode'] if mode == 'auto' else mode, 'approach': approach, 'applied': apply,
            'changes': [p.relative_to(root).as_posix() for p in changed], 'facts': facts,
            'next': 'Drafts/navigation only. Inspect relevant source and tests, discuss missing intent, then write substantive documentation. No tests executed.'}


def headings(path: Path) -> set[str]:
    text = path.read_text(encoding='utf-8')
    result = set(re.findall(r'(?:id|name)=["\']([^"\']+)["\']', text))
    counts = {}
    for line in text.splitlines():
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if not match: continue
        title = re.sub(r'[`*_~]', '', match[1]).lower()
        slug = re.sub(r'[^\w\-\s]', '', title).replace(' ', '-')
        count = counts.get(slug, 0); counts[slug] = count + 1
        result.add(slug + (f'-{count}' if count else ''))
    return result


def check(root: Path, base: str | None = None, index_path=None) -> dict:
    facts = inspect(root); errors = []; warnings = []; graph = {}
    if index_path:
        selected=Path(index_path)
        if selected.is_absolute() or '..' in selected.parts or selected.suffix!='.md':raise ValueError('Index must be a relative Markdown file')
        safe(root/selected);facts['index']=selected.as_posix()
    if facts['index'] not in facts['documents']: errors.append('Missing document index: ' + facts['index'])
    for rel in facts['documents']:
        graph[rel] = set()
        path = safe(root / rel); text = path.read_text(encoding='utf-8')
        # Local Markdown links/images and reference-style definitions. Code fences are excluded.
        text = re.sub(r'^(`{3,}|~{3,}).*?^\1[^\n]*$', '', text, flags=re.M | re.S)
        if re.search(r'^' + re.escape(DRAFT) + r'\s*$', text, re.M) or re.search(r'^文書状態：調査用の下書き。', text, re.M):
            warnings.append('Draft content needs completion: ' + rel)
        destinations = re.findall(r'\]\(\s*(<[^>]+>|[^\s)]+)', text)
        destinations += re.findall(r'^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)', text, re.M)
        for raw in destinations:
            raw = raw.strip('<>')
            url = urlsplit(raw)
            if url.scheme or url.netloc or not raw: continue
            target = Path(os.path.abspath(path.parent / unquote(url.path))) if url.path else path
            if not target.is_relative_to(root):
                warnings.append(f'Outside project: {rel} -> {raw}'); continue
            try: safe(target)
            except ValueError:
                errors.append(f'Linked reference: {rel} -> {raw}'); continue
            if not target.exists(): errors.append(f'Missing reference: {rel} -> {raw}')
            else:
                graph[rel].add(target.relative_to(root).as_posix())
                if url.fragment and target.suffix.lower() == '.md' and unquote(url.fragment) not in headings(target):
                    errors.append(f'Missing heading: {rel} -> {raw}')
    seen=set(); pending=[facts['index']]
    while pending:
        node=pending.pop()
        if node in seen:continue
        seen.add(node);pending.extend(graph.get(node,set())-seen)
    warnings.extend('Document not reachable from index: '+rel for rel in facts['documents'] if rel.startswith('docs/') and rel not in seen)
    changed = set()
    if base:
        if not re.fullmatch(r'[A-Za-z0-9_./~^{}@+\-]+', base) or base.startswith('-'):
            raise ValueError('Invalid base revision')
        resolved = git(root, 'rev-parse', '--verify', base + '^{commit}')
        if not resolved: raise ValueError('Cannot resolve base revision')
        output = git(root, 'diff', '--name-only', '-z', resolved.strip(), '--', '.')
        if output is None: raise ValueError('Cannot inspect changes from base')
        changed.update(filter(None, output.split('\0')))
    else:
        for args in (('diff', '--name-only', '-z', '--', '.'), ('diff', '--cached', '--name-only', '-z', '--', '.')):
            output = git(root, *args)
            if output: changed.update(filter(None, output.split('\0')))
    untracked = git(root, 'ls-files', '--full-name', '--others', '--exclude-standard', '-z', '--', '.')
    if untracked: changed.update(filter(None, untracked.split('\0')))
    # Git names are relative to the repository root, including in subdirectories.
    top = git(root, 'rev-parse', '--show-toplevel')
    if top:
        prefix = root.relative_to(Path(top.strip())).as_posix()
        if prefix != '.': changed = {f[len(prefix)+1:] for f in changed if f.startswith(prefix + '/')}
    changed = {f for f in changed if not any(p in EXCLUDED or p.startswith('.') for p in Path(f).parts)}
    return {'errors': errors, 'warnings': warnings, 'changed_files': sorted(changed),
            'note': 'Structural inspection only. Review specification meaning, test evidence and whether each change needs documentation.'}


def work_status(root: Path, base: str, compare=()) -> dict:
    """Collect local Git evidence; shared paths are candidates, never merge verdicts."""
    safe(root)
    warnings = []

    def run(*args, at=root, allow=(0,), options=()):
        try:
            result = subprocess.run(
                ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', *options, '-C', str(at), *args],
                capture_output=True, timeout=20,
                env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_NO_LAZY_FETCH': '1',
                     'GIT_ALLOW_PROTOCOL': '', 'GIT_TERMINAL_PROMPT': '0'})
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError('Cannot inspect Git repository: ' + args[0]) from error
        if result.returncode not in allow:
            # Do not expose configured URLs, credentials or arbitrary stderr.
            raise ValueError('Cannot inspect Git repository: ' + args[0])
        return result.returncode, result.stdout.decode('utf-8', errors='surrogateescape')

    def resolve(ref, optional=False):
        if not ref or ref.startswith('-') or '\0' in ref:
            raise ValueError('Invalid revision')
        code, text = run('rev-parse', '--verify', '--end-of-options', ref + '^{commit}', allow=(0, 128))
        if code and not optional: raise ValueError('Cannot resolve revision: ' + ref)
        return text.strip() if code == 0 else None

    top = Path(run('rev-parse', '--show-toplevel')[1].strip())
    base_sha = resolve(base)
    head = resolve('HEAD', optional=True)
    branch_code, branch_text = run('symbolic-ref', '--quiet', '--short', 'HEAD', allow=(0, 1))
    branch = branch_text.strip() if branch_code == 0 else None
    if head is None: warnings.append('HEAD has no resolvable commit; committed task changes are unknown.')

    filter_options = {}

    def changes(at):
        # Even status can execute a configured clean/process filter. Disable callbacks
        # per worktree and retain uncertainty about normalized working-file contents.
        if at not in filter_options:
            _, keys = run('config', '--null', '--name-only', '--get-regexp',
                          r'^filter\..*\.(clean|process)$', at=at, allow=(0, 1))
            overrides = {}
            for key in filter(None, keys.split('\0')):
                driver = key.rsplit('.', 1)[0]
                overrides.update({driver + '.clean': '', driver + '.process': '', driver + '.required': 'false'})
            filter_options[at] = [arg for key, value in overrides.items() for arg in ('-c', key + '=' + value)]
            if overrides:
                warnings.append('Clean/process filters disabled; unstaged paths are candidates: ' + str(at))
        raw = run('status', '--porcelain=v1', '-z', '--untracked-files=all',
                  '--ignore-submodules=dirty', at=at, options=filter_options[at])[1].split('\0')
        result = {'staged': [], 'unstaged': [], 'untracked': []}
        paths = set(); i = 0
        while i < len(raw):
            row = raw[i]; i += 1
            if not row: continue
            if len(row) < 4 or row[2] != ' ': raise ValueError('Cannot parse Git status')
            xy, path = row[:2], row[3:]
            entry = {'path': path}; paths.add(path)
            if 'R' in xy or 'C' in xy:
                if i >= len(raw) or not raw[i]: raise ValueError('Cannot parse Git rename')
                entry['original_path'] = raw[i]; paths.add(raw[i]); i += 1
            if xy == '??': result['untracked'].append(entry)
            else:
                for key, status in (('staged', xy[0]), ('unstaged', xy[1])):
                    if status != ' ': result[key].append({**entry, 'status': status})
        return result, paths, bool(filter_options[at])

    pending, pending_paths, filters_disabled = changes(top)

    def counts(left, right):
        text = run('rev-list', '--left-right', '--count', left + '...' + right)[1]
        behind, ahead = map(int, text.split())
        return {'ahead': ahead, 'behind': behind, 'contained_in_base': ahead == 0}

    def delta(sha):
        code, text = run('merge-base', '--all', base_sha, sha, allow=(0, 1))
        bases = text.split() if code == 0 else []
        if len(bases) != 1:
            warnings.append('No unique merge base for ' + sha + '; changed paths and overlap are unknown.')
            return None
        text = run('diff', '--no-ext-diff', '--no-textconv', '--ignore-submodules=none',
                   '--no-renames', '--name-only', '-z', bases[0], sha, '--')[1]
        return sorted(set(filter(None, text.split('\0'))))

    # NUL field separators preserve spaces/Unicode; Git ref names cannot contain newlines.
    branch_rows = run('for-each-ref', '--format=%(refname)%00%(objectname)%00%(upstream)', 'refs/heads/')[1]
    branches = []
    for row in branch_rows.splitlines():
        ref, sha, upstream = row.split('\0')
        tracking = None
        if upstream:
            upstream_sha = resolve(upstream, optional=True)
            tracking = {'ref': upstream, 'sha': upstream_sha,
                        'status': 'available' if upstream_sha else 'unavailable'}
            if upstream_sha:
                tracking.update({k: v for k, v in counts(upstream_sha, sha).items() if k != 'contained_in_base'})
            else: warnings.append('Upstream is unavailable for ' + ref + '.')
        branches.append({'name': ref.removeprefix('refs/heads/'), 'sha': sha,
                         **counts(base_sha, sha), 'upstream': tracking})

    # -z was added after Git 2.34. The legacy porcelain format covers ordinary paths;
    # ambiguous records are rejected instead of inventing a clean worktree.
    code, text = run('worktree', 'list', '--porcelain', '-z', allow=(0, 129))
    if code == 0:
        blocks = [b.split('\0') for b in text.rstrip('\0').split('\0\0') if b]
    else:
        text = run('worktree', 'list', '--porcelain')[1]
        blocks = [b.splitlines() for b in text.strip().split('\n\n') if b]
    worktrees = []
    for lines in blocks:
        fields = {}
        for line in lines:
            key, _, value = line.partition(' ')
            if key not in {'worktree', 'HEAD', 'branch', 'detached', 'bare', 'locked', 'prunable'} or key in fields:
                raise ValueError('Cannot parse Git worktree; status is unknown')
            fields[key] = value
        if not fields.get('worktree'): raise ValueError('Cannot parse Git worktree path')
        path = fields['worktree']
        dirty = None
        if 'bare' not in fields:
            try:
                safe(Path(path))
                work_pending, _, work_filters = changes(Path(path))
                dirty = None if work_filters else any(work_pending.values())
            except ValueError:
                warnings.append('Worktree status is unavailable: ' + path)
        worktrees.append({'path': path, 'branch': fields.get('branch', '').removeprefix('refs/heads/') or None,
                          'sha': fields.get('HEAD'), 'dirty': dirty,
                          'locked': 'locked' in fields, 'prunable': 'prunable' in fields})

    committed_paths = delta(head) if head else None
    task_paths = set(committed_paths) | pending_paths if committed_paths is not None else None
    comparisons = []
    for ref in dict.fromkeys(compare):
        sha = resolve(ref); paths = delta(sha)
        comparisons.append({'ref': ref, 'sha': sha, **counts(base_sha, sha), 'changed_paths': paths,
                            'overlap_paths': sorted(task_paths.intersection(paths))
                            if task_paths is not None and paths is not None else None})
    # Each diff used fixed SHAs. Detect changed inputs instead of presenting a mixed snapshot as current.
    inputs = [(base, base_sha), ('HEAD', head), *[('refs/heads/' + b['name'], b['sha']) for b in branches],
              *[(c['ref'], c['sha']) for c in comparisons]]
    consistent = all(resolve(ref, optional=True) == sha for ref, sha in inputs)
    if not consistent: warnings.append('Refs changed during inspection; inspect again before acting.')
    return {'schema_version': 1, 'repository': str(top), 'project': str(root),
            'base': {'ref': base, 'sha': base_sha},
            'current': {'branch': branch, 'sha': head, 'changed_paths': committed_paths},
            'changes': pending, 'changes_status': 'filter_callbacks_disabled' if filters_disabled else 'checked',
            'branches': branches, 'worktrees': worktrees, 'submodule_worktrees': 'not_checked',
            'comparisons': comparisons, 'refs_consistent': consistent,
            'remote_freshness': 'not_checked', 'conflicts': 'not_checked', 'warnings': warnings,
            'note': 'Local repository-wide evidence only. Overlap is shared paths, not a conflict verdict; '
                    'ancestry containment does not detect squash merges or authorize deletion. '
                    'Worktree state can change after inspection. Submodule working files are not inspected. '
                    'No fetch, merge, hooks or application code executed.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=VERSION)
    commands = parser.add_subparsers(dest='action', required=True)
    for name in ('inspect', 'init', 'check', 'work-status'):
        p = commands.add_parser(name); p.add_argument('--project', type=Path, default=Path.cwd())
        if name == 'work-status':
            p.add_argument('--base', required=True, help='Explicit integration revision')
            p.add_argument('--compare', action='append', default=[], help='Compare task paths with this revision (repeatable)')
            continue
        p.add_argument('--index',help='Use an existing/custom relative Markdown index')
        if name == 'init':
            p.add_argument('--mode', choices=('auto', 'new', 'existing'), default='auto')
            p.add_argument('--approach', choices=('dialogue', 'delegate'), default='dialogue')
            p.add_argument('--document', action='append', default=[], help='Reuse an existing role=relative.md (repeatable)')
            p.add_argument('--agent', choices=('codex', 'claude'), default=os.environ.get('INTELLIFORGE_AGENT', 'codex'))
            m = p.add_mutually_exclusive_group(); m.add_argument('--apply', action='store_true'); m.add_argument('--dry-run', action='store_true')
        if name == 'check': p.add_argument('--base')
    args = parser.parse_args(argv)
    try:
        root = safe(args.project)
        if args.action == 'work-status': result = work_status(root, args.base, args.compare)
        else: result = inspect(root) if args.action == 'inspect' else initialize(root, args.mode, args.approach, args.apply, args.agent, args.document, args.index) if args.action == 'init' else check(root, args.base, args.index)
        print(json.dumps(result, ensure_ascii=args.action == 'work-status', indent=2))
        return int(bool(result.get('errors')))
    except (OSError, ValueError, UnicodeError) as error:
        print('repository-director: ' + str(error), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
