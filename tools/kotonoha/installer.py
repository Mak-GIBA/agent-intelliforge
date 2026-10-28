#!/usr/bin/env python3
"""kotonoha writing integration 5.0.0, engine Python 3.10+; managed runtime >=3.11.
Based on basic-memory-workgraph installer 1.3.0's CLI, ownership contract,
path checks, staged directory replacement and backup strategy.
User-local Node/npm lint dependencies; no hooks, AGENTS edits, credentials, or document upload.
"""
from __future__ import annotations
import argparse
import ast
import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
import zlib

VERSION = '5.0.0'
REPO = 'nanaism/yomiyasu'
BASE_REPO_COMMIT = 'f0efd23a53c1c1cd028775aa415cc3f34ca5661a'
LEGACY_COMPONENTS = ('yomiyasu', 'kotonoha', 'paragraph-writing', 'japanese-direct-writing')
COMPONENTS = ('kotonoha',)
OWNERS = {'kotonoha': 'basic-memory-workgraph/kotonoha', 'yomiyasu': 'basic-memory-workgraph/codex-yomiyasu',
          'paragraph-writing': 'basic-memory-workgraph/paragraph-writing',
          'japanese-direct-writing': 'basic-memory-workgraph/japanese-direct-writing'}
MANIFEST = '.installer.json'
MAX_FILE = 2_000_000
MAX_TOTAL = 20_000_000
MAX_COUNT = 200
KNOWN_STYLERS = {'natural-japanese', 'japanese-humanizer', 'stop-ai-slop-jp',
                 'humanizer', 'humanizer-ja', 'humanizer-jp', 'stop-slop', 'meiseki', 'audience-boundary'}
LEGACY_TAG = 'v1.0.4'
LEGACY_COMMIT = '8d5abeebe2dd20c2db005deaddcc50be43c59c0a'
PINS = {
    'SKILL.md': ('df3412cd46066a03a6f000a66af19d079ad6a4f8', 30291),
    'LICENSE': ('f0d06f87f9b209d47c7f7963321ff71bab68c1e8', 1064),
    'README.md': ('31d7e00c2297d6b85b382dc05a2d3663c1534908', 22888),
    'references/domains/business.md': ('a4a0c492d95df742a275202ac80148c6b08abe0b', 3719),
    'references/domains/essay.md': ('36919c63949102934c414bbe8a8f700a5ed1a971', 2216),
    'references/domains/tech.md': ('1394795ff9e3d43004330b3abc93a83527babae7', 3379),
    'references/gemini-syntax.md': ('f06c2bb457d582b890f9581047fac33c4716ef83', 26466),
    'references/slop-catalog.md': ('c4ad42f1ac4a3ab8255f1d35438806fe40a58b42', 10668),
    'scripts/yomiyasu_lint.py': ('cd5e05a82d7cadcab43cd8e7acf6516716682b28', 27280),
    'scripts/yomiyasu_diff.py': ('ccc1c6a553bcc6b1a30578a1d20e697891f51089', 26801),
}
ASSET_B64 = '@ASSET_B64@'
ASSET_SHA256 = '377c0ffe4088c6e77e0da9e3bda77eeedf1913640eb3edcbdaab9ca1437200b7'
SELF_SCRIPT = None


class InstallError(RuntimeError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def abs_path(value: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(value))))


def linked(path: Path) -> bool:
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)
    except FileNotFoundError:
        return False


def safe_path(path: Path) -> None:
    for p in [path, *path.parents]:
        if linked(p):
            raise InstallError('symlink経由の管理先は変更しません: '+str(p))
        if p.exists() and p != path and not p.is_dir():
            raise InstallError('親パスがディレクトリではありません: '+str(p))


def safe_rel(value: str) -> str:
    if not isinstance(value, str):
        raise InstallError('管理パスは文字列でなければなりません。')
    path = PurePosixPath(value)
    if (not value or value == '.' or value != path.as_posix() or path.is_absolute() or '..' in path.parts
        or '\\' in value or ':' in value or any(ord(c) < 32 for c in value)):
        raise InstallError('不正な相対パスです: '+repr(value))
    return value


def emit(out: dict) -> None:
    print(json.dumps(out, ensure_ascii=False, indent=2))


def asset_aliases(out):
    # Legacy helpers/tests address these bytes; the on-disk source has one owner.
    out = dict(out)
    for key, raw in list(out.items()):
        if key.startswith("kotonoha/"):
            out.setdefault(key.removeprefix("kotonoha/"), raw)
    return out


def assets() -> dict[str, bytes]:
    if ASSET_B64 == '@ASSET_B64@':
        root = Path(__file__).parent
        out = {}
        for prefix, directory in [('', root/'assets'), ('tests/', root/'tests'), ('evals/', root/'evals'), ('engine/', root/'engine')]:
            if not directory.is_dir():
                continue
            for p in sorted(directory.rglob('*')):
                if '__pycache__' in p.parts:
                    continue
                if linked(p):
                    raise InstallError('同梱資材のsymlinkを拒否しました。')
                if p.is_file():
                    out[safe_rel(prefix+p.relative_to(directory).as_posix())] = p.read_bytes()
        out['engine/update_upstreams.py'] = (root/'update_upstreams.py').read_bytes()
        return asset_aliases(out)
    raw = base64.b64decode(ASSET_B64, validate=True)
    if sha(raw) != ASSET_SHA256:
        raise InstallError('同梱資材のhashが一致しません。')
    decompressor = zlib.decompressobj()
    decoded = decompressor.decompress(raw, MAX_TOTAL+1)
    if len(decoded) > MAX_TOTAL or not decompressor.eof or decompressor.unused_data:
        raise InstallError('同梱資材の展開サイズ/終端が不正です。')
    data = json.loads(decoded)
    if not isinstance(data, dict) or len(data) > 1000:
        raise InstallError('同梱資材の形式が不正です。')
    out = {}
    for key, value in data.items():
        if isinstance(value, str): raw = value.encode("utf-8")
        elif isinstance(value, dict) and set(value) == {"base64"}: raw = base64.b64decode(value["base64"], validate=True)
        else: raise InstallError("Invalid bundled file encoding")
        out[safe_rel(key)] = raw
    return asset_aliases(out)


def inventory(directory: Path) -> dict[str, bytes]:
    safe_path(directory)
    if not directory.is_dir():
        raise InstallError('管理先がディレクトリではありません: '+str(directory))
    out = {}
    total = 0
    for parent, dirs, files in os.walk(directory, followlinks=False):
        for d in dirs:
            if linked(Path(parent)/d):
                raise InstallError('管理先内のsymlinkを拒否しました。')
        for name in files:
            p = Path(parent)/name
            if not stat.S_ISREG(p.lstat().st_mode):
                raise InstallError('通常ファイル以外を拒否しました。')
            total += p.stat().st_size
            if p.stat().st_size > MAX_FILE or total > MAX_TOTAL or len(out) >= 1000:
                raise InstallError('管理先の検査サイズを超えました。')
            out[safe_rel(p.relative_to(directory).as_posix())] = p.read_bytes()
    return out


def manifest_for(files: dict[str, bytes], component: str = 'yomiyasu') -> dict:
    if MANIFEST not in files:
        raise InstallError('別方式で導入された同名Skillは上書きしません。')
    marker = json.loads(files[MANIFEST])
    if not isinstance(marker, dict) or marker.get('schema') != 1 or marker.get('owner') != OWNERS[component]:
        raise InstallError('このインストーラーの管理対象ではありません。')
    tracked = marker.get('files')
    if not isinstance(tracked, dict) or not tracked or MANIFEST in tracked:
        raise InstallError('管理ファイル一覧が不正です。')
    for name, digest in tracked.items():
        safe_rel(name)
        if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise InstallError('管理hashが不正です。')
    if marker.get('mode') not in ('auto', 'explicit'):
        raise InstallError('保存済みの発動設定が不正です。')
    return marker


def edited(files: dict[str, bytes], marker: dict) -> list[str]:
    return [k for k, v in marker['files'].items() if k not in files or sha(files[k]) != v]


def conflict_scan(target: Path, cwd: Path | None = None) -> dict:
    home = abs_path(Path.home())
    codex = abs_path(os.environ.get('CODEX_HOME', str(home/'.codex')))
    cwd = abs_path(cwd or Path.cwd())
    roots = {target.parent, home/'.agents/skills', codex/'skills', Path('/etc/codex/skills')}
    for parent in [cwd, *cwd.parents]:
        roots.update({parent/'.agents/skills', parent/'.codex/skills'})
        if (parent/'.git').exists() or parent == home:
            break
    duplicates, stylers = [], []
    for root in sorted(roots, key=str):
        for name in sorted(KNOWN_STYLERS | set(COMPONENTS)):
            p = root/name
            if p == target or not (p/'SKILL.md').is_file():
                continue
            if name == target.name:
                duplicates.append(str(p))
            elif name in KNOWN_STYLERS:
                stylers.append(str(p))
    return {'duplicate_skill': duplicates, 'other_style_skills': stylers,
            'scope': 'ユーザー・管理者・現在プロジェクトの既知パス。全plugin cacheや別プロジェクトは対象外。'}


class LockedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_url(url: str) -> None:
    u = urllib.parse.urlparse(url)
    prefixes = {'api.github.com': ('/repos/'+REPO+'/', '/repos/bamboo-nova/meiseki/'),
                'raw.githubusercontent.com': ('/'+REPO+'/', '/bamboo-nova/meiseki/')}
    if (u.scheme != 'https' or u.hostname not in prefixes or u.username or u.password
        or u.port not in (None, 443) or not u.path.startswith(prefixes[u.hostname])):
        raise InstallError('許可されていない取得先です。')


def download(url: str) -> bytes:
    validate_url(url)
    request = urllib.request.Request(url, headers={'User-Agent': 'kotonoha/'+VERSION,
                                                  'Accept': 'application/vnd.github+json'})
    with urllib.request.build_opener(LockedRedirect()).open(request, timeout=25) as response:
        raw = response.read(MAX_FILE+1)
    if len(raw) > MAX_FILE:
        raise InstallError('上流ファイルの取得サイズを超えました。')
    return raw


def json_download(url: str) -> dict:
    try:
        raw = download(url)
    except urllib.error.HTTPError as exc:
        if exc.code not in (403, 429) or not shutil.which('gh') or not url.startswith('https://api.github.com/repos/'):
            raise
        validate_url(url)
        raw = subprocess.check_output(['gh', 'api', url.removeprefix('https://api.github.com/')], timeout=25)
        if len(raw) > MAX_FILE: raise InstallError('API response exceeds limit')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise InstallError('GitHubの応答形式が不正です。')
    return value


def tag_commit(tag: str) -> str:
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?', tag):
        raise InstallError('上流tagの形式が想定外です。')
    obj = json_download(f'https://api.github.com/repos/{REPO}/git/ref/tags/{urllib.parse.quote(tag, safe="")}').get('object')
    for _ in range(5):
        if not isinstance(obj, dict) or not re.fullmatch(r'[a-f0-9]{40}', str(obj.get('sha', ''))):
            raise InstallError('上流tagの参照先が不正です。')
        if obj.get('type') == 'commit':
            return obj['sha']
        if obj.get('type') != 'tag':
            raise InstallError('上流tagがcommitを指していません。')
        # Derive the endpoint; never trust a URL embedded in a remote response.
        obj = json_download(f'https://api.github.com/repos/{REPO}/git/tags/{obj["sha"]}').get('object')
    raise InstallError('上流tagの参照が深すぎます。')


def release_file_manifest(tree: dict) -> dict[str, dict]:
    if tree.get('truncated') or not isinstance(tree.get('tree'), list):
        raise InstallError('Git treeが不完全です。')
    rows = tree['tree']
    prefix = 'skills/yomiyasu/' if any(r.get('path') == 'skills/yomiyasu/SKILL.md' for r in rows if isinstance(r, dict)) else ''
    out = {}
    total = 0
    def license_name(s):
        return '/' not in s and bool(re.search(r'LICENSE|LICENCE|COPYING|NOTICE', s, re.I))
    for row in rows:
        if not isinstance(row, dict):
            raise InstallError('Git treeの項目が不正です。')
        path = str(row.get('path', ''))
        name = None
        if '/' not in path and (path == 'README.md' or license_name(path)):
            name = path
        elif path.startswith(prefix):
            rel = path[len(prefix):]
            if rel == 'SKILL.md' or rel.startswith(('references/', 'scripts/', 'assets/')) or license_name(rel):
                name = rel
        if name is None or row.get('type') == 'tree':
            continue
        safe_rel(name); safe_rel(path)
        if row.get('type') != 'blob' or row.get('mode') not in ('100644', '100755'):
            raise InstallError('配布対象に通常ファイル以外があります: '+path)
        if name != 'SKILL.md' and PurePosixPath(name).name == 'SKILL.md':
            raise InstallError('予期しない入れ子のSKILL.mdがあります。配置方式をレビューしてください。')
        size = row.get('size')
        digest = row.get('sha')
        if type(size) is not int or not 0 <= size <= MAX_FILE or not re.fullmatch(r'[a-f0-9]{40}', str(digest)):
            raise InstallError('上流ファイルのmetadataが不正です。')
        spec = {'repo_path': path, 'git_blob_sha1': digest, 'size': size}
        if name in out:
            if out[name]['git_blob_sha1'] != digest or out[name]['size'] != size:
                raise InstallError('上流の同名資材が一致しません: '+name)
            # Prefer the canonical skill subtree when duplicate license copies agree.
            if path.startswith('skills/yomiyasu/'):
                out[name] = spec
            continue
        total += size
        if total > MAX_TOTAL or len(out) >= MAX_COUNT:
            raise InstallError('上流配布サイズ/ファイル数の上限を超えました。')
        out[name] = spec
    required = {'SKILL.md', 'LICENSE', 'scripts/yomiyasu_lint.py', 'scripts/yomiyasu_diff.py'}
    if not required <= out.keys() or not any(k.startswith('references/') for k in out):
        raise InstallError('上流の必須資材がありません。構造変更をレビューしてください。')
    return out


def resolve_release(tag: str | None = None) -> dict:
    release = json_download(f'https://api.github.com/repos/{REPO}/releases/latest' if tag is None
                            else f'https://api.github.com/repos/{REPO}/releases/tags/{urllib.parse.quote(tag, safe="")}')
    if release.get('draft') or release.get('prerelease'):
        raise InstallError('draft/prereleaseは自動採用しません。')
    resolved_tag = str(release.get('tag_name', ''))
    if tag is not None and resolved_tag != tag:
        raise InstallError('指定tagとreleaseが一致しません。')
    commit = tag_commit(resolved_tag)
    tree = json_download(f'https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1')
    return {'repository': REPO, 'tag': resolved_tag, 'commit': commit,
            'published_at': release.get('published_at'),
            'release_url': f'https://github.com/{REPO}/releases/tag/{resolved_tag}',
            'files': release_file_manifest(tree)}


def map_upstream(name: str) -> str:
    return 'upstream/'+('SKILL.upstream.md' if name == 'SKILL.md' else name)


def verify_file(name: str, data: bytes, spec: dict) -> bytes:
    if len(data) != spec['size'] or blob_sha(data) != spec['git_blob_sha1']:
        raise InstallError('上流のサイズ/blob hashが一致しません: '+name)
    if Path(name).suffix.lower() in ('.md', '.py', '.txt', '.json', '.yaml', '.yml', '.toml') or 'LICENSE' in name.upper():
        text = data.decode('utf-8')
        if '\x00' in text:
            raise InstallError('上流テキストにNULがあります。')
        if name.endswith('.py'):
            ast.parse(text, filename=name)
    return data


def upstream_contract(files: dict[str, bytes]) -> dict:
    required = {'upstream/SKILL.upstream.md', 'upstream/LICENSE',
                'upstream/scripts/yomiyasu_lint.py', 'upstream/scripts/yomiyasu_diff.py'}
    if not required <= files.keys():
        raise InstallError('上流資材が不完全です。--updateで再取得してください。')
    skill = files['upstream/SKILL.upstream.md'].decode('utf-8')
    if not re.search(r'^name:\s*[\'\"]?yomiyasu[\'\"]?\s*$', skill, re.M):
        raise InstallError('上流Skill名が変わっています。自動適用しません。')
    scripts = '\n'.join(v.decode('utf-8') for k, v in files.items() if k.startswith('upstream/scripts/') and k.endswith('.py'))
    if 'markdown_visibility' in scripts and 'upstream/scripts/markdown_visibility.py' not in files:
        raise InstallError('上流の補助moduleがありません。')
    if 'Unicode License' in scripts and 'upstream/UNICODE-LICENSE.txt' not in files:
        raise InstallError('上流のUnicodeライセンスがありません。--updateで再取得してください。')
    if '--json' not in scripts:
        raise InstallError('上流JSON CLIの構造が変わっています。アダプターをレビューしてください。')
    return {'status': 'STRUCTURAL_CHECKED', 'runtime_executed': False,
            'note': '静的構造の照合のみ。新しい上流scriptはインストール時に実行しません。'}


def fetch_release(meta: dict) -> dict[str, bytes]:
    out = {}
    for name, spec in sorted(meta['files'].items()):
        data = download(f'https://raw.githubusercontent.com/{REPO}/{meta["commit"]}/{spec["repo_path"]}')
        out[map_upstream(name)] = verify_file(name, data, spec)
    upstream_contract(out)
    return out


def source_upstream(source: Path) -> tuple[dict, dict[str, bytes]]:
    """Read-only local source: an installed snapshot, Git checkout, or legacy pin."""
    safe_path(source)
    if not source.is_dir():
        raise InstallError('--source-dirが存在しません。')
    if (source/'UPSTREAM.json').is_file() and (source/'upstream').is_dir():
        all_files = inventory(source)
        marker = manifest_for(all_files, json.loads(all_files[MANIFEST]).get('component','yomiyasu'))
        if edited(all_files, marker):
            raise InstallError('ローカルsnapshotが編集されています。')
        if any(k.startswith('upstream/') and k not in marker['files'] for k in all_files):
            raise InstallError('ローカルsnapshotの上流配下に未管理ファイルがあります。')
        meta = json.loads(all_files['UPSTREAM.json'])
        out = {k: v for k, v in all_files.items() if k.startswith('upstream/')}
        upstream_contract(out)
        return meta, out
    if (source/'.git').exists():
        git = shutil.which('git')
        if not git:
            raise InstallError('Git checkoutを使うにはgitが必要です。')
        def git_read(*args):
            return subprocess.check_output([git, '-C', str(source), *args], timeout=20)
        commit = git_read('rev-parse', 'HEAD').decode().strip()
        if not re.fullmatch(r'[a-f0-9]{40}', commit):
            raise InstallError('ローカルcommitが不正です。')
        rows = []
        for item in git_read('ls-tree', '-r', '-l', '-z', 'HEAD').split(b'\0'):
            if not item:
                continue
            metadata, path = item.decode('utf-8').split('\t', 1)
            mode, kind, digest, size = metadata.split()
            rows.append({'path': path, 'mode': mode, 'type': kind, 'sha': digest,
                         'size': int(size) if size != '-' else -1})
        specs = release_file_manifest({'tree': rows, 'truncated': False})
        meta = {'repository': REPO, 'tag': 'local-'+commit[:12], 'commit': commit,
                'files': specs, 'provenance': 'explicit local checkout; publisher identity not verified'}
    else:
        specs = {k: {'repo_path': k, 'git_blob_sha1': v[0], 'size': v[1]} for k, v in PINS.items()}
        meta = {'repository': REPO, 'tag': LEGACY_TAG, 'commit': LEGACY_COMMIT, 'files': specs}
    out = {}
    for name, spec in specs.items():
        p = source/safe_rel(spec['repo_path'])
        safe_path(p)
        if not p.is_file() or p.stat().st_size > MAX_FILE:
            raise InstallError('ローカル上流資材がない/大きすぎます: '+name)
        out[map_upstream(name)] = verify_file(name, p.read_bytes(), spec)
    upstream_contract(out)
    return meta, out



def fetch_meiseki() -> tuple[dict, dict[str, bytes]]:
    """Resolve latest stable; never silently adopt unreviewed normative changes."""
    bundled = {k.removeprefix('meiseki-upstream/'):v for k,v in assets().items() if k.startswith('meiseki-upstream/')}
    reviewed = json.loads(bundled['UPSTREAM.json'])
    repo = 'bamboo-nova/meiseki'
    release = json_download(f'https://api.github.com/repos/{repo}/releases/latest')
    if release.get('draft') or release.get('prerelease'): raise InstallError('meiseki must be a stable release')
    tag = str(release['tag_name'])
    commit = json_download(f'https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(tag, safe="")}')['sha']
    if not re.fullmatch('[a-f0-9]{40}', commit): raise InstallError('Invalid meiseki commit')
    files = {}
    for name,digest in reviewed['files'].items():
        remote = 'LICENSE' if name == 'LICENSE' else '.agents/skills/meiseki/'+name
        raw = download(f'https://raw.githubusercontent.com/{repo}/{commit}/{remote}')
        if sha(raw) != digest:
            raise InstallError('meiseki '+tag+' has unreviewed normative changes: '+name+'; existing installation retained')
        local_name = 'SKILL.upstream.md' if name == 'SKILL.md' else name
        files['meiseki-upstream/'+local_name] = raw
    meta = {**reviewed, 'tag':tag, 'commit':commit, 'latest_stable_checked':True}
    files['meiseki-upstream/UPSTREAM.json'] = (json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    return meta, files


def prepare_writing_runtime(root: Path) -> dict:
    """Prepare dependencies before replacing any owned Skill."""
    bundle = assets()
    with tempfile.TemporaryDirectory(prefix='kotonoha-runtime-source-') as td:
        base = Path(td)
        for name,raw in bundle.items():
            if name.startswith('scripts/') or name.startswith('meiseki-upstream/'):
                target = base/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        scope = {'__name__':'kotonoha_runtime','__file__':str(base/'scripts/writing_runtime.py')}
        exec(compile(bundle['scripts/writing_runtime.py'],scope['__file__'],'exec'),scope)
        return scope['prepare'](root.parent/'.kotonoha-runtime')


def agent_yaml(name: str, mode: str) -> bytes:
    titles = {'kotonoha': 'kotonoha 日本語執筆・推敲', 'yomiyasu': 'yomiyasu 日本語執筆・推敲', 'paragraph-writing': 'paragraph-writing 段落構成',
              'japanese-direct-writing': 'japanese-direct-writing 留保の整理'}
    summary = {'kotonoha': '明晰さ・段落・説明の深さ・自然さを統合する', 'yomiyasu': '読者に向けた自然な日本語を段落から組み立てる',
               'paragraph-writing': '事実と意味を保って段落の論旨を整える',
               'japanese-direct-writing': '確信度を変えず不要な予防線だけを減らす'}
    prompt = '$'+name+'を使い、原文の意味・情報量を保って日本語の完成稿を仕上げてください。'
    return ('interface:\n  display_name: '+json.dumps(titles[name], ensure_ascii=False)+
            '\n  short_description: '+json.dumps(summary[name], ensure_ascii=False)+
            '\n  default_prompt: '+json.dumps(prompt, ensure_ascii=False)+
            '\npolicy:\n  products:\n    - "CODEX"\n  allow_implicit_invocation: '+str(mode == 'auto' and name != 'yomiyasu').lower()+'\n').encode('utf-8')


def own_bundle(component: str, mode: str) -> dict[str, bytes]:
    data = assets()
    if component == 'yomiyasu':
        out = {k: v for k, v in data.items() if k == 'SKILL.md' or k.startswith(('references/', 'scripts/', 'meiseki-upstream/'))}
    else:
        prefix = component+'/'
        out = {k[len(prefix):]: v for k, v in data.items() if k.startswith(prefix)}
    if 'SKILL.md' not in out:
        raise InstallError('同梱Skillがありません。')
    out['agents/openai.yaml'] = agent_yaml(component, mode)
    return out


@contextmanager
def lock(target: Path):
    path = target.parent/'.kotonoha-installer.lock'
    safe_path(path)
    try:
        fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise InstallError('別の処理のlockがあります。稼働状況を確認してください: '+str(path)) from exc
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'time': time.time()}))
        yield
    finally:
        path.unlink(missing_ok=True)


def backup(target: Path, files: dict[str, bytes]) -> Path:
    base = target.parent/'.kotonoha-installer-backups'
    safe_path(base); base.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive = base/(target.name+'-'+time.strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:10]+'.zip')
    fd = os.open(archive, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in sorted(files.items()):
                z.writestr(name, data)
    return archive


def replace_directories(stages: list[tuple[Path | None, Path]]) -> None:
    """Exception rollback. This is not a power-loss-atomic multi-dir transaction."""
    switched = []
    try:
        for stage, target in stages:
            retired = target.parent/('.'+target.name+'-retired-'+uuid.uuid4().hex)
            had = target.exists()
            if had:
                os.replace(target, retired)
            entry = {'target': target, 'retired': retired, 'had': had, 'placed': False}
            switched.append(entry)
            if stage is not None:
                os.replace(stage, target)
                entry['placed'] = True
    except BaseException:
        for entry in reversed(switched):
            try:
                if entry['placed']:
                    shutil.rmtree(entry['target'])
                if entry['had']:
                    os.replace(entry['retired'], entry['target'])
            except OSError as exc:
                raise InstallError('復元に失敗しました。原本は保持しています: '+str(entry['retired'])) from exc
        raise
    for entry in switched:
        if entry['had']:
            try:
                shutil.rmtree(entry['retired'])
            except OSError:
                print('WARN: 旧一時フォルダが残っています: '+str(entry['retired']), file=sys.stderr)


def summarize(results: dict) -> dict:
    if len(results) == 1:
        return next(iter(results.values()))
    return {'components': results, 'applied': any(r.get('applied') for r in results.values())}


def plan(target: Path, component: str, mode: str | None, refresh: bool,
         project: Path | None = None) -> tuple[dict, dict | None, dict[str, bytes]]:
    safe_path(target)
    files = inventory(target) if target.exists() else {}
    marker = manifest_for(files, component) if target.exists() else None
    if marker and edited(files, marker):
        raise InstallError('管理ファイルに編集・欠落があります。--forceでも消しません: '+', '.join(edited(files, marker)))
    effective = mode or (marker['mode'] if marker else 'auto')
    same = bool(marker and marker.get('version') == VERSION and marker['mode'] == effective)
    if marker and not same and not refresh:
        raise InstallError('既存版/設定の更新には --update または --force を指定してください。')
    result = {'action': 'skip' if same and not refresh else ('update' if marker else 'install'),
              'component': component, 'target': str(target), 'version': VERSION, 'mode': effective,
              'applied': False, 'network': False, 'conflicts': conflict_scan(target, project),
              'changes_other_settings': False,
              'note': 'autoは暗黙選択の許可です。毎回答への適用を保証するHookではありません。'}
    return result, marker, files



def install(target: Path, mode=None, force=False, apply=False, source=None, project=None, update=False) -> dict:
    return install_selected(target.parent, ('yomiyasu',), mode, force, apply, source, project, update)


def legacy_uninstall_selected(root: Path, names: tuple[str, ...], apply: bool) -> dict:
    states, results = {}, {}
    for name in names:
        target = root/name; safe_path(target)
        if not target.exists():
            results[name] = {'action': 'absent', 'component': name, 'applied': False}
            continue
        old = inventory(target); marker = manifest_for(old, name)
        if edited(old, marker):
            raise InstallError('編集済みの管理ファイルがあるため解除しません: '+name)
        if set(old) - set(marker['files']) - {MANIFEST}:
            raise InstallError('ユーザー追加ファイルがあるため解除しません: '+name)
        states[name] = old
        results[name] = {'action': 'uninstall', 'component': name, 'target': str(target), 'applied': False}
    if apply and states:
        with lock(root/next(iter(states))):
            for name, old in states.items():
                if inventory(root/name) != old:
                    raise InstallError('解除準備中に内容が変更されました。')
                results[name]['backup'] = str(backup(root/name, old))
            for name, old in states.items():
                if inventory(root/name) != old:
                    raise InstallError('バックアップ中に内容が変更されました。')
            replace_directories([(None, root/name) for name in states])
        for name in states:
            results[name]['applied'] = True
    return summarize(results)


def uninstall(target: Path, apply: bool) -> dict:
    return uninstall_selected(target.parent, ('yomiyasu',), apply)


def legacy_doctor(target: Path, project=None, component='yomiyasu') -> tuple[dict, int]:
    out = {'component': component, 'target': str(target), 'codex_on_path': bool(shutil.which('codex')),
           'python': sys.version.split()[0], 'conflicts': conflict_scan(target, project)}
    try:
        files = inventory(target); marker = manifest_for(files, component)
        changed = edited(files, marker)
        out.update(version=marker['version'], mode=marker['mode'], edited=changed,
                   implicit_invocation=b'allow_implicit_invocation: true' in files.get('agents/openai.yaml', b''))
        if component == 'yomiyasu':
            out['upstream_compatibility'] = upstream_contract(files)
            out.update(upstream_tag=marker.get('upstream_tag'), upstream_commit=marker.get('upstream_commit'))
            if 'meiseki-upstream/UPSTREAM.json' in files:
                out['meiseki'] = json.loads(files['meiseki-upstream/UPSTREAM.json'])
            runtime_path = target.parent.parent/'.kotonoha-runtime/settings.json'
            out['writing_runtime_configured'] = runtime_path.is_file()
            helper = target/'scripts/writing_runtime.py'
            if runtime_path.is_file() and helper.is_file() and not changed:
                scope={'__name__':'kotonoha_health','__file__':str(helper)}
                exec(compile(helper.read_text(encoding='utf-8'),str(helper),'exec'),scope)
                out['writing_runtime'] = scope['diagnose'](runtime_path.parent)
        unknown_upstream = [k for k in files if k.startswith('upstream/') and k not in marker['files']]
        out['untracked_upstream'] = unknown_upstream
        ok = not changed and not unknown_upstream and not out['conflicts']['duplicate_skill']
        out['status'] = 'READY_FILES' if ok else 'DAMAGED_OR_CONFLICTING'
        return out, 0 if ok else 2
    except (InstallError, OSError, ValueError, KeyError) as exc:
        out.update(status='NOT_READY', error=str(exc))
        return out, 2


def legacy_check_updates(root: Path, names: tuple[str, ...], ref=None) -> dict:
    results = {}
    for name in names:
        target = root/name; safe_path(target)
        old = inventory(target) if target.exists() else {}
        marker = manifest_for(old, name) if old else None
        row = {'action': 'check-update', 'component': name, 'applied': False,
               'installed_version': marker.get('version') if marker else None,
               'bundled_version': VERSION, 'wrapper_update_available': not marker or marker.get('version') != VERSION}
        if name == 'yomiyasu':
            latest = resolve_release(ref)
            meiseki, _ = fetch_meiseki()
            row['meiseki_latest'] = {k:v for k,v in meiseki.items() if k != 'files'}
            row.update(network=True, latest={k: v for k, v in latest.items() if k != 'files'},
                       installed_upstream_commit=marker.get('upstream_commit') if marker else None,
                       upstream_update_available=not marker or marker.get('upstream_commit') != latest['commit'])
        else:
            row['network'] = False
        results[name] = row
    return summarize(results)


def extract(destination: Path) -> dict:
    safe_path(destination)
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise InstallError('展開先は空または未作成のディレクトリにしてください。')
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in assets().items():
        if not name.startswith(('kotonoha/','tests/','evals/','engine/')): continue
        p = destination/safe_rel(name); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as stream:
            stream.write(data)
    if SELF_SCRIPT:
        shell = Path(SELF_SCRIPT).read_text(encoding='utf-8')
        if str(SELF_SCRIPT).endswith('.ps1'):
            match = re.search(r"\$payload = '([A-Za-z0-9+/=]+)'", shell)
            if not match: raise InstallError('PowerShell payload missing')
            source = base64.b64decode(match[1],validate=True).decode('utf-8')
        else:
            source = shell.split("<<'YOMI_INSTALL_PY'\n", 1)[1].rsplit('\nYOMI_INSTALL_PY', 1)[0]
        source = source.replace('    SELF_SCRIPT = abs_path(sys.argv[1])\n    raise SystemExit(main(sys.argv[2:]))',
                                '    raise SystemExit(main())')
        (destination/'installer.py').write_text(source, encoding='utf-8')
    else:
        source = Path(__file__).read_text(encoding='utf-8')
        raw = zlib.compress(json.dumps({k: {'base64':base64.b64encode(v).decode()} for k, v in assets().items() if k.startswith(('kotonoha/','tests/','evals/','engine/'))}, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'), 9)
        source = re.sub(r"^ASSET_B64 = .*$", 'ASSET_B64 = '+repr(base64.b64encode(raw).decode('ascii')), source, count=1, flags=re.M)
        source = re.sub(r"^ASSET_SHA256 = .*$", 'ASSET_SHA256 = '+repr(sha(raw)), source, count=1, flags=re.M)
        (destination/'installer.py').write_text(source, encoding='utf-8')
    return {'action': 'extract', 'path': str(destination), 'note': '独自資材の展開のみ。上流原本はインストール時に取得します。'}


def self_test() -> int:
    bundle = assets()
    suite = unittest.TestSuite()
    for path in sorted(k for k in bundle if k.startswith('tests/test_') and k.endswith('.py')):
        module = types.ModuleType('proposal_tests_'+Path(path).stem)
        module.I = sys.modules[__name__]
        module.A = bundle
        module.__file__ = str(Path(__file__).resolve().parent/path)
        sys.modules[module.__name__] = module
        exec(compile(bundle[path].decode('utf-8'), path, 'exec'), module.__dict__)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    print('Offline tests: simulated upstream, no Codex model invocation.', flush=True)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv: list[str] | None = None) -> int:
    if sys.version_info < (3, 10):
        print('Python 3.10+が必要です。', file=sys.stderr)
        return 2
    p = argparse.ArgumentParser(description=__doc__)
    apply_group = p.add_mutually_exclusive_group()
    apply_group.add_argument('--apply', action='store_true')
    apply_group.add_argument('--dry-run', action='store_true', help='既定。変更・通信なしの予定表示')
    p.add_argument('--force', action='store_true', help='同梱ルール/設定の更新。既存の上流版は維持')
    p.add_argument('--update', action='store_true', help='選択Skillを更新。yomiyasuの上流は最新安定releaseを取得')
    p.add_argument('--upstream-only', action='store_true', help='--update時、yomiyasuの上流だけを更新。独自ルールと版を維持')
    p.add_argument('--upstream-ref', metavar='TAG', help='--update/--check-updateの取得対象を安定releaseのtagに固定')
    p.add_argument('--mode', choices=('auto', 'explicit'))
    p.add_argument('--only', choices=('all', 'kotonoha'), default='all')
    actions = p.add_mutually_exclusive_group()
    actions.add_argument('--doctor', '--status', action='store_true')
    actions.add_argument('--check-update', action='store_true')
    actions.add_argument('--uninstall', action='store_true')
    actions.add_argument('--self-test', action='store_true')
    actions.add_argument('--extract', metavar='DIRECTORY')
    p.add_argument('--skills-dir', help='親ディレクトリ。既定 ~/.agents/skills')
    p.add_argument('--source-dir', help='ローカルGit checkout、管理済みsnapshot、旧v1.0.4固定版のフラット原本')
    p.add_argument('--project', help='競合診断するプロジェクト。設定は変更しない')
    args = p.parse_args(argv)
    try:
        special = args.doctor or args.self_test or args.extract or args.check_update
        if special and (args.apply or args.force or args.update or args.mode or args.source_dir or args.upstream_only):
            raise InstallError('診断・展開・テストと変更オプションは併用できません。')
        if args.upstream_ref and special and not args.check_update:
            raise InstallError('--upstream-refは--update/--check-update専用です。')
        if args.uninstall and (args.force or args.update or args.mode or args.source_dir or args.upstream_only or args.upstream_ref):
            raise InstallError('解除と更新のオプションは併用できません。')
        root = abs_path(args.skills_dir or Path.home()/'.agents/skills')
        names = COMPONENTS
        if args.upstream_only:
            if args.only not in ('all', 'yomiyasu', 'kotonoha'):
                raise InstallError('--upstream-onlyの対象はyomiyasuです。')
            names = COMPONENTS
        if args.upstream_ref and args.only not in ('all', 'yomiyasu', 'kotonoha'):
            raise InstallError('--upstream-refの対象はyomiyasuです。')
        project = abs_path(args.project) if args.project else None
        if args.self_test:
            if args.only != 'all':
                raise InstallError('--self-testでは--onlyを指定しません。')
            return self_test()
        if args.extract:
            if args.only != 'all':
                raise InstallError('--extractでは--onlyを指定しません。')
            emit(extract(abs_path(args.extract))); return 0
        if args.doctor:
            results = {n: doctor(root/n, project, n) for n in names}
            emit(summarize({n: v[0] for n, v in results.items()}))
            return max(v[1] for v in results.values())
        if args.check_update:
            result=check_updates(root, names, args.upstream_ref)
            emit(result); return 2 if any(v['status']=='check_failed' for v in result['upstreams'].values()) else 0
        if args.uninstall:
            emit(uninstall_selected(root, names, args.apply)); return 0
        result=install_selected(root, names, args.mode, args.force, args.apply,
                              abs_path(args.source_dir) if args.source_dir else None, project,
                              args.update, args.upstream_only, args.upstream_ref)
        emit(result)
        return 2 if result.get('status')=='UPSTREAM_REVIEW_REQUIRED' else 0
    except (RuntimeError, OSError, ValueError, KeyError, SyntaxError, subprocess.SubprocessError) as exc:
        emit({'status': 'ERROR', 'message': str(exc), 'note': '不明な状態で上書きせず停止しました。'})
        return 2

exec(compile(assets()['engine/layout_v4.py'], str(Path(__file__).parent/'engine/layout_v4.py'), 'exec'), globals())

if __name__ == '__main__':
    raise SystemExit(main())
