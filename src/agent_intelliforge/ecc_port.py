"""On-demand ECC reader over an immutable upstream snapshot; no Codex required."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request

from .catalog import ForgeError
from .ownership import replace_tree, verify


def prepare(home, agent):
    from .runtime import checked, files, owner
    destination = home / 'upstream'
    if destination.exists():
        verify(destination, owner('ecc-upstream', agent)); return
    if not shutil.which('git'): raise ForgeError('The ECC source reader requires Git.')
    # Resolve a released version, then clone that tag. No branch-tip guess.
    with urllib.request.urlopen('https://api.github.com/repos/affaan-m/ECC/releases/latest', timeout=30) as stream:
        release = json.load(stream)
    tag = release.get('tag_name')
    if release.get('draft') or release.get('prerelease') or not isinstance(tag, str) or tag.startswith('-'):
        raise ForgeError('No supported stable ECC release found')
    with tempfile.TemporaryDirectory(prefix='intelliforge-ecc-') as temporary:
        source = Path(temporary) / 'source'
        checked(['git', 'clone', '--depth', '1', '--branch', tag, 'https://github.com/affaan-m/ECC.git', str(source)], timeout=180)
        commit = checked(['git', '-C', str(source), 'rev-parse', 'HEAD']).strip()
        if not (source/'skills/tdd-workflow/SKILL.md').is_file():
            raise ForgeError('ECC release is missing tdd-workflow; existing runtime is preserved')
        data = {name: raw for name, raw in files(source).items() if not name.startswith('.git/')}
        data['INTELLIFORGE_UPSTREAM.json'] = (json.dumps({'repository': 'affaan-m/ECC', 'tag': tag, 'commit': commit}, indent=2) + '\n').encode()
        replace_tree(destination, owner('ecc-upstream', agent), data)


def main(bundle, agent, arguments):
    from .runtime import load, owner
    upstream = bundle.parent / 'upstream'; verify(upstream, owner('ecc-upstream', agent))
    module = load(bundle / 'ecc_on_demand.py', '_intelliforge_ecc_reader')
    parser = argparse.ArgumentParser()
    parser.add_argument('--cwd', type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest='action', required=True)
    for action in ('search', 'resolve', 'doctor'):
        command = commands.add_parser(action); command.add_argument('--json', action='store_true')
        if action != 'doctor': command.add_argument('query')
        if action == 'search':
            command.add_argument('--limit', type=int, choices=range(1,6), default=5)
            command.add_argument('--language')
    args = parser.parse_args(arguments)
    skills = []
    for path in sorted((upstream / 'skills').glob('*/SKILL.md')):
        text = path.read_text(encoding='utf-8')
        description = next((line.removeprefix('description:').strip() for line in text.splitlines() if line.startswith('description:')), '')
        skills.append({'name': path.parent.name, 'description': description, 'path': str(path), 'skill_dir': str(path.parent), 'plugin_root': str(upstream)})
    required = {name for name in module.ENTRIES.values() if name}
    if required - {item['name'] for item in skills}: raise ForgeError('ECC snapshot is missing required originals')
    if args.action == 'search':
        try: value = {'matches': module.search_catalog(skills, args.query, args.cwd, args.limit, language=args.language)}
        except module.ManagementError as error: raise ForgeError(str(error)) from error
    elif args.action == 'resolve':
        found = [item for item in skills if item['name'] == args.query.removeprefix('ecc:')]
        if len(found) != 1: raise ForgeError('ECC skill is missing or ambiguous: ' + args.query)
        value = found[0]
    else: value = {'ready': True, 'source': str(upstream), 'originals': len(skills), 'mcp': 'explicit host registration; unchanged upstream definitions'}
    if args.action == 'resolve' and not args.json: print(value['path'])
    else: print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0
