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

VERSION = '1.0.0'
BEGIN = '<!-- repository-director:begin -->'
END = '<!-- repository-director:end -->'
EXCLUDED = {'.git', '.env', '.venv', 'venv', 'node_modules', 'vendor', 'dist', 'build',
            '__pycache__', '.next', '.cache', '.workgraph-recall'}
ROLES = {
    'purpose': ('purpose.md', ['purpose', 'overview', '目的', '背景']),
    'policy': ('repository-policy.md', ['repository-policy', '運営方針', '開発方針']),
    'requirements': ('requirements.md', ['requirements', '機能仕様', '要件', '要件定義']),
    'architecture': ('architecture.md', ['architecture', '構成・開発・運用', '全体設計']),
    'core': ('core-logic.md', ['core-logic', 'コアロジック']),
    'verification': ('verification.md', ['verification', 'テスト仕様', '検証']),
}
TITLES = {'purpose': '目的・背景', 'policy': 'リポジトリ運営方針', 'requirements': '要件・機能仕様',
          'architecture': '全体設計', 'core': 'コアロジック', 'verification': '検証・運用'}


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
    roles = {}
    for role, (_, aliases) in ROLES.items():
        matches = [f for f in docs if Path(f).stem.casefold() in [a.casefold() for a in aliases]]
        if indexes:
            index=root/indexes[0]
            safe(index)
            text=index.read_text(encoding='utf-8')
            link=re.search(r'\['+re.escape(TITLES[role])+r'\]\(([^)]+)\)',text)
            if link:
                target=Path(os.path.abspath(index.parent/unquote(link[1])))
                if target.is_relative_to(root) and target.relative_to(root).as_posix() in docs:
                    matches=[target.relative_to(root).as_posix()]
        roles[role] = matches
    return {'schema_version': 1, 'mode': 'existing' if sources else 'new',
            'revision': (git(root, 'rev-parse', 'HEAD') or '').strip() or None,
            'index': indexes[0] if indexes else 'docs/INDEX.md', 'documents': docs,
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
    heading = '# ' + TITLES[role] + '\n\n'
    status = '文書状態：調査用の下書き。内容の策定・業務上の合意・動作検証は未完了です。\n\n'
    sections = {
        'purpose': '## 事業目的・開発目的\n\n未確認。依頼者の説明や既存資料から確認します。\n\n## 利用者・適用価値・対象範囲\n\n未確認。\n\n## 依頼者のコメント\n\n要望・背景・理由・採否／保留・関連要件と出典を整理します。未収集です。\n',
        'policy': '## 方針の決め方\n\n' + ('対話で重要な未決事項を確認します。' if approach == 'dialogue' else 'お任せモード。以下はエージェントが選んだ開発上の既定方針です。事業上の合意を意味しません。') + '\n\n## 開発・検証・文書更新\n\n変更前に関連仕様と実装を確認し、変更と関連テスト・文書を一緒に更新します。既存の実行手順を優先し、未実施の確認を成功と記載しません。\n\n## Git・レビュー\n\n既存のブランチ規則とテンプレートを優先します。新たな共有開発では短命の作業ブランチとPR/MRでレビューします。コミットは一つの目的にまとめ、目的・変更・確認結果・残件を説明します。\n\n## 自動判断と相談\n\n依頼範囲の可逆な実装・検証・文書更新は進めます。事業要件の不明点、互換性や公開範囲を変える判断は確認します。commit・push・投稿・merge・本番操作は実際の依頼と合意済み運用の範囲に従います。この文書だけでは新しい操作権限を与えません。\n',
        'requirements': '## 実装から確認した現状\n\n機能・権限・入出力・制約をコード／テストの参照とともに調査します。未調査です。\n\n## 合意済み要件・受入条件\n\n未確認。現状動作をそのまま正式な要件とは扱いません。\n\n## 不一致・未実装・確認事項\n\n既存文書と実装の差、期待と現状の差を分けます。未調査です。\n',
        'architecture': '## 全体構成と責務\n\n主要モジュール・外部依存・データ境界を根拠付きで整理します。未調査です。\n\n## 代表的な処理とデータの流れ\n\n未調査。必要な図と関連する詳細仕様へのリンクを追加します。\n',
        'core': '## 主要処理・方式\n\n入力 → 処理段階 → 出力、担当モジュール、状態とデータの関係を調査します。未調査です。\n\n## 選定理由・成立条件・限界\n\n実装上の事実、出典のある採用理由、今後の提案を区別します。未確認です。\n',
        'verification': '## 検証方法・受入条件\n\n既存テストと実行手順を確認し、どの条件を確認するか対応付けます。未調査です。\n\n## 確認結果\n\nテストは未実行です。テストファイルの存在は動作確認を意味しません。\n\n## 開発・運用上の制約\n\n実行環境・CI・リリース・監視の条件を確認します。本番環境は未確認です。\n',
    }
    return heading + status + sections[role]


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
    links = []
    for role, (filename, _) in ROLES.items():
        existing = facts['roles'][role]
        target = existing[0] if existing else 'docs/' + filename
        links.append(f'| [{TITLES[role]}]({os.path.relpath(root / target, (root / facts["index"]).parent).replace(os.sep, "/")}) | {TITLES[role]}の正本・調査結果 |')
        if not existing:
            path = safe(root / target)
            if path.exists(): raise ValueError(f'Unclassified existing document: {target}')
            changes[path] = draft(role, facts, approach).encode()
    nav = '## 文書一覧\n\n| 文書 | 内容 |\n| --- | --- |\n' + '\n'.join(links) + '\n\n'
    # Keep existing named specs visible, even when they do not match a standard role.
    extra = [f for f in facts['documents'] if f.startswith('docs/') and f != facts['index']
             and f not in {v for values in facts['roles'].values() for v in values}]
    if extra:
        nav += '## 既存の詳細資料\n\n' + ''.join(f'- [{Path(f).stem}]({os.path.relpath(root / f, (root / facts["index"]).parent).replace(os.sep, "/")})\n' for f in extra) + '\n'
    index = safe(root / facts['index'])
    old = index.read_text(encoding='utf-8') if index.exists() else '# ドキュメント\n\n実装上の現状、合意済み要件、変更案、未確認事項を区別します。\n'
    changes[index] = block(old, nav).encode()
    for filename, text in {
        'README.md': '## 開発とドキュメント\n\n[文書索引](' + facts['index'] + ')、[開発ガイド](AGENTS.md)から関連する仕様・方針を確認してください。\n',
        'AGENTS.md': '## 変更前と完了前の確認\n\n- [文書索引](' + facts['index'] + ')から運営方針と関連する要件・設計・検証資料を読んでください。\n- 実装・テストの現状と正式な要件を区別し、重要な不明点を確認してください。\n- 依頼範囲の変更・関連テスト・文書を一緒に更新し、差分と説明を照合してください。\n- 文書整備だけの依頼ではアプリのソース・依存・DBを変更しないでください。\n- 未実施の確認は明示し、コミット・PR/MR・コメントでは目的・変更・確認結果・残件を伝えてください。\n',
        **({'CLAUDE.md': '開発の共通方針は [AGENTS.md](AGENTS.md) を参照してください。\n'} if agent == 'claude' or (root / 'CLAUDE.md').exists() else {}),
    }.items():
        path = safe(root / filename)
        content = path.read_text(encoding='utf-8') if path.exists() else '# ' + ('開発ガイド' if filename == 'AGENTS.md' else root.name) + '\n'
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
        if '文書状態：調査用の下書き。' in text: warnings.append('Draft content needs investigation: ' + rel)
        # Local Markdown links/images and reference-style definitions. Code fences are excluded.
        text = re.sub(r'^(`{3,}|~{3,}).*?^\1[^\n]*$', '', text, flags=re.M | re.S)
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=VERSION)
    commands = parser.add_subparsers(dest='action', required=True)
    for name in ('inspect', 'init', 'check'):
        p = commands.add_parser(name); p.add_argument('--project', type=Path, default=Path.cwd())
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
        result = inspect(root) if args.action == 'inspect' else initialize(root, args.mode, args.approach, args.apply, args.agent, args.document, args.index) if args.action == 'init' else check(root, args.base, args.index)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(bool(result.get('errors')))
    except (OSError, ValueError, UnicodeError) as error:
        print('repository-director: ' + str(error), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
