"""Readable per-kit installation and execution bindings for the additive path.

Legacy installers never import this module. Mutable settings and dependency
environments live outside hash-owned source bundles. No personal environment
is touched by previews, builds, or tests.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv

from .catalog import ForgeError, definitions, distribution_root
from .ownership import atomic_write, check_path, inventory, replace_tree, remove_tree, verify
from .portable import file_lock
from . import plugins


def owner(kit, agent):
    return f"agent-intelliforge/{agent}/{kit}"


def files(directory):
    check_path(directory)
    if not directory.is_dir():
        raise ForgeError(f"Missing generated resources: {directory}. Run tools/intelliforge/build.py first.")
    result = {}
    for path in sorted(directory.rglob('*')):
        check_path(path)
        if path.is_file() and path.name != '.intelliforge.json' and '__pycache__' not in path.parts:
            result[path.relative_to(directory).as_posix()] = path.read_bytes()
    return result


def load(path, name):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        specification.loader.exec_module(module)
    finally: sys.dont_write_bytecode = previous
    return module


def settings(home):
    path = home / 'settings.json'; check_path(path)
    value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if value and value.get('owner') != owner(home.name, home.parent.name):
        raise ForgeError(f"Unowned settings: {path}")
    return value


def checked(argv, *, cwd=None, env=None, timeout=120):
    from .subprocess_bridge import adapt
    result = subprocess.run(adapt(argv), cwd=cwd, env=env, timeout=timeout,
                            text=True, encoding='utf-8', capture_output=True)
    if result.returncode:
        # Do not persist the complete command/environment or credentials.
        raise ForgeError(f"{Path(argv[0]).name} failed ({result.returncode}): {result.stderr[-1200:]}")
    return result.stdout


def npm_command(*args):
    node = shutil.which('node'); npm = shutil.which('npm')
    if not node or not npm:
        raise ForgeError('Install the official Node.js runtime first; npm is required by this selected kit.')
    if os.name == 'nt':
        cli = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js'
        if not cli.is_file(): raise ForgeError('Cannot locate npm-cli.js next to Node.js; batch shims are not executed.')
        return [node, str(cli), *args]
    return [npm, *args]


def python_in(directory):
    return directory / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def environment(home, agent, state):
    value = {**os.environ, 'INTELLIFORGE_AGENT': agent, 'INTELLIFORGE_STATE_DIR': str(state),
             'INTELLIFORGE_KIT_HOME': str(home), 'PYTHONDONTWRITEBYTECODE': '1',
             'PYTHONUTF8': '1',
             'PYTHONPATH': os.pathsep.join([str(Path(__file__).resolve().parent.parent), os.environ.get('PYTHONPATH', '')])}
    config = settings(home)
    if config.get('writing_runtime'):
        value['KOTONOHA_RUNTIME_DIR'] = config['writing_runtime']
    if config.get('browser'):
        value['UX_GAN_RUNTIME'] = config['browser']
        value['PLAYWRIGHT_BROWSERS_PATH'] = str(Path(config['browser']) / 'browsers')
    if config.get('specify'):
        value['PATH'] = str(Path(config['specify']).parent) + os.pathsep + value.get('PATH', '')
    return value


def dependency_directory(home, label):
    parent = home / 'dependencies'; check_path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=label + '-', dir=parent))


def prepare_dependencies(kit, agent, home, bundle, config, state):
    """Explicit dependency policies, kept here instead of opaque shell payloads."""
    identity = kit['id']
    if identity == 'yomiyasu':
        helper = load(bundle / 'assets/kotonoha/scripts/writing_runtime.py', '_kotonoha_runtime')
        try: writing = helper.prepare(home / 'dependencies/kotonoha')
        except RuntimeError as error: raise ForgeError(str(error)) from error
        config['writing_runtime'] = str(home / 'dependencies/kotonoha')
        config['python'] = writing['python']
    if identity == 'ecc':
        from .ecc_port import prepare
        prepare(home, agent)
    if agent == 'claude' and identity in ('ux-stack', 'design-research'):
        sdk = state / 'claude/dependencies/mxc'
        if not sdk.exists():
            node = shutil.which('node')
            if not node or int(checked([node, '--version']).strip().lstrip('v').split('.')[0]) < 24:
                raise ForgeError('Claude experiment isolation requires Node.js >=24 and the MXC SDK.')
            # npm package-lock records exact tarball integrity; lifecycle scripts are disabled.
            sdk.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix='mxc-', dir=sdk.parent))
            try:
                (stage / 'package.json').write_text('{"private":true,"dependencies":{"@microsoft/mxc-sdk":"1.0.0"}}\n',encoding='utf-8',newline='\n')
                checked(npm_command('install', '--ignore-scripts', '--no-audit', '--no-fund'), cwd=stage, timeout=300)
                replace_tree(sdk, owner('mxc', agent), files(stage))
            finally: shutil.rmtree(stage)
        else: verify(sdk, owner('mxc', agent))
    if identity == 'ux-stack' and not config.get('browser'):
        directory = dependency_directory(home, 'browser')
        for name in ('package.json', 'package-lock.json'):
            shutil.copy2(bundle / 'browser' / name, directory / name)
        checked(npm_command('ci', '--ignore-scripts', '--no-audit', '--no-fund'), cwd=directory, timeout=300)
        env = {**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': str(directory / 'browsers')}
        checked(['node', str(directory / 'node_modules/playwright/cli.js'), 'install', 'chromium'], env=env, timeout=600)
        config['browser'] = str(directory)
    if identity == 'speckit' and not config.get('specify'):
        found = shutil.which('specify')
        if found:
            checked([found, 'version']); config['specify'] = found
        else:
            directory = dependency_directory(home, 'specify-1.0.8')
            venv.EnvBuilder(with_pip=True).create(directory)
            checked([str(python_in(directory)), '-m', 'pip', 'install', '--disable-pip-version-check', 'specify-cli==1.0.8'], timeout=600)
            config['specify'] = str(directory / ('Scripts/specify.exe' if os.name == 'nt' else 'bin/specify'))
    if identity == 'office' and not config.get('python'):
        from .office_port import prepare
        config.update(prepare(bundle, home))
    if identity == 'herdr' and not config.get('binary'):
        found = shutil.which('herdr')
        if not found:
            if os.name != 'nt': raise ForgeError('Install Herdr using its official installer first; the legacy Codex path also provides automatic installation.')
            import platform, zipfile
            if platform.machine().lower() not in ('amd64','x86_64'): raise ForgeError('The pinned Herdr release has no verified native Windows ARM64 asset.')
            source = kit['native_windows_asset']; directory = dependency_directory(home,'herdr-0.9.3')
            # Release digest was checked against GitHub metadata. No remote script is evaluated.
            with urllib.request.urlopen(source['url'], timeout=30) as response: raw = response.read(100_000_001)
            if len(raw)>100_000_000 or hashlib.sha256(raw).hexdigest()!=source['sha256']:
                raise ForgeError('Herdr release asset hash/size mismatch')
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                entries=[entry for entry in archive.infolist() if Path(entry.filename).name=='herdr.exe']
                if len(entries)!=1 or entries[0].file_size>100_000_000: raise ForgeError('Invalid Herdr native archive')
                executable=directory/'herdr.exe'; atomic_write(executable,archive.read(entries[0]));found=str(executable)
        checked([found, '--version'])
        config['binary'] = found
        config['binary_sha256'] = hashlib.sha256(Path(found).read_bytes()).hexdigest()
    if identity == 'github-pm' and not shutil.which('gh'):
        raise ForgeError('GitHub management requires the official GitHub CLI (gh). Install it and authenticate first.')
    if identity == 'workgraph':
        if not config.get('python'):
            directory = dependency_directory(home, 'workgraph-python')
            venv.EnvBuilder(with_pip=True).create(directory)
            executable = python_in(directory)
            checked([str(executable), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(bundle / 'requirements-export.txt')], timeout=300)
            config['python'] = str(executable)
        policy = home / 'policy'; policy.mkdir(parents=True, exist_ok=True)
        replace_tree(policy / 'assets', owner('workgraph-policy', agent), {
            name: data for name, data in files(bundle).items()
            if name == 'memory-policy.md' or name.startswith('templates/')})
        path = policy / 'config.json'; check_path(path)
        if not path.exists():
            atomic_write(path, b'{"mode":"smart","caseMode":"progressive","skillMode":"review","correctionMode":"scoped"}\n')
        config['policy'] = str(policy)
        # Only host-manager commands register the upstream plugin/MCP.
        # Existing Basic Memory projects, schemas and sharing permissions are not replaced.
        config['basic_memory_setup'] = 'Use bm install ' + ('claude-code' if agent == 'claude' else 'codex') + ' if the upstream integration is not already connected.'


def meiseki_assets(bundle):
    # Reviewed originals are part of the canonical payload; install never adopts an unreviewed release.
    return {}


def upstream_update(bundle, home, agent):
    engine = load(bundle / 'installer.py', '_intelliforge_yomiyasu')
    data = {name.removeprefix('upstream/'):raw for name,raw in engine.own_bundle('kotonoha','auto').items()
            if name.startswith('upstream/')}
    data['UPSTREAM.json'] = engine.own_bundle('kotonoha','auto')['UPSTREAM.json']
    return replace_tree(home / 'upstream', owner('yomiyasu-upstream', agent), data)


def marketplace(root, kit, agent, state, mode):
    """Owned local marketplace survives wheel upgrades; native managers own caches."""
    target = state / agent / 'marketplace'
    data = files(target) if target.exists() else {}
    prefix = 'plugins/' + kit['id'] + '/'
    data = {name: raw for name, raw in data.items() if not name.startswith(prefix)}
    for name, raw in files(root / 'plugins' / agent / kit['id']).items():
        if kit['id'] == 'yomiyasu' and name.startswith('skills/yomiyasu/meiseki-upstream/'):
            relative = name.removeprefix('skills/yomiyasu/')
            raw = (state / agent / kit['id'] / 'bundle/assets' / relative).read_bytes()
        if kit['id'] == 'yomiyasu' and name.endswith('agents/openai.yaml'):
            implicit = mode != 'explicit' and '/skills/yomiyasu/' not in '/' + name
            raw = f'policy:\n  allow_implicit_invocation: {str(implicit).lower()}\n'.encode()
        if agent == 'claude' and kit['id'] == 'yomiyasu' and name.endswith('SKILL.md') and mode == 'explicit':
            text = raw.decode(); split = text.split('---', 2)
            if len(split) != 3 or split[0].strip(): raise ForgeError('Missing Skill frontmatter')
            if 'disable-model-invocation:' not in split[1]:
                raw = ('---' + split[1] + 'disable-model-invocation: true\n---' + split[2]).encode()
        data[prefix + name] = raw
    identities = sorted({name.split('/')[1] for name in data if name.startswith('plugins/')})
    entries = [{'name': name, 'source': {'source': 'local', 'path': './plugins/' + name} if agent == 'codex' else './plugins/' + name} for name in identities]
    catalog = {'name': 'agent-intelliforge', 'owner': {'name': 'Mak-GIBA'}, 'plugins': entries}
    path = '.agents/plugins/marketplace.json' if agent == 'codex' else '.claude-plugin/marketplace.json'
    data[path] = (json.dumps(catalog, indent=2) + '\n').encode()
    backup = replace_tree(target, owner('marketplace', agent), data)
    return target, backup


def skill_roots(root, kit, agent):
    plugin = root / 'plugins' / agent / kit['id'] / 'skills'
    return {item.name: files(item) for item in sorted(plugin.iterdir()) if item.is_dir()} if plugin.exists() else {}


def diagnose(kit, agent, state, legacy=False):
    home = state / agent / kit['id']
    result = {'kit': kit['id'], 'agent': agent, 'legacy': legacy, 'runtime': str(home), 'exit_code': 0}
    if legacy:
        result['status'] = 'Existing installer has no doctor command; use its documented checks.'
        return result
    try:
        verify(home / 'bundle', owner(kit['id'], agent)); config = settings(home)
        result.update(installed=True, version=config.get('version'), method=config.get('method'))
        missing = []
        for key in ('python', 'binary', 'specify'):
            if config.get(key) and not Path(config[key]).is_file(): missing.append(key)
        if config.get('writing_runtime'):
            helper=load(home/'bundle/assets/kotonoha/scripts/writing_runtime.py','_kotonoha_health')
            result['writing_runtime']=helper.diagnose(Path(config['writing_runtime']))
            if result['writing_runtime']['status']!='READY':missing.append('writing runtime')
        for key in ('browser',):
            if config.get(key) and not Path(config[key]).is_dir(): missing.append(key)
        if kit['id'] == 'yomiyasu': verify(home / 'upstream', owner('yomiyasu-upstream', agent))
        if config.get('method') == 'plugin':
            result['host_cli'] = bool(shutil.which(agent))
            if not result['host_cli']: missing.append('host plugin manager')
            elif kit['plugin']['enabled']:
                identity = kit['id']+'@agent-intelliforge'
                result['plugin_registered'] = identity in plugins.installed(agent)
                if not result['plugin_registered']: missing.append('plugin registration')
        if kit['id'] in ('ux-stack', 'design-research'):
            result['model_execution'] = 'not performed by doctor'
            if agent == 'claude':
                from .provider import capabilities
                result['capabilities'] = capabilities()
                if not result['capabilities']['ready']: missing.append('claude role protocol')
            elif not shutil.which('codex'): missing.append('codex CLI')
        result['missing'] = missing
        result['exit_code'] = int(bool(missing))
    except (ForgeError, OSError, ValueError) as error:
        result.update(installed=False, error=str(error), exit_code=1)
    return result


def portable_action(root, kits, plan, args, state):
    catalog = {kit['id']: kit for kit in kits}; results = []
    # Complete preflight before the first dependency/network or mutation.
    for item in plan['operations']:
        kit = catalog[item['kit']]; home = state / item['agent'] / item['kit']
        if item['method'] == 'legacy': continue
        if (home / 'bundle').exists(): verify(home / 'bundle', owner(item['kit'], item['agent']))
        settings(home)
        if args.action in ('install', 'update'):
            files(root / 'tools/intelliforge/resources/runtime' / item['kit'])
            if item['method'] == 'plugin':
                plugins.conflict_skills(kit, item['agent'], args.skills_dir)
                plugins.preflight(kit, item['agent'], args.action, state)
                destination = state / item['agent'] / 'marketplace'
                if destination.exists(): verify(destination, owner('marketplace', item['agent']))
            else:
                destination = args.skills_dir or Path.home() / '.agents/skills'
                for name in (set(skill_roots(root, kit, item['agent'])) | ({'yomiyasu','paragraph-writing','japanese-direct-writing'} if kit['id']=='yomiyasu' else set())):
                    if (destination / name).exists(): verify(destination / name, owner(name, item['agent']))
    for item in plan['operations']:
        kit = catalog[item['kit']]; agent = item['agent']; home = state / agent / item['kit']
        if item['method'] == 'legacy':
            from .cli import legacy_action
            results.append({'kit': kit['id'], 'agent': agent, 'exit_code': legacy_action(root, [kit], args.action)}); continue
        if args.action == 'doctor': results.append(diagnose(kit, agent, state)); continue
        home.mkdir(parents=True, exist_ok=True)
        with file_lock(home / '.operation.lock'):
            config = settings(home)
            if args.action == 'uninstall':
                if not config: raise ForgeError('No owned installation to uninstall: ' + str(home))
                if config['method'] == 'plugin': plugins.manage(root, kit, agent, 'uninstall', state)
                else:
                    for target in config.get('skills', []): remove_tree(Path(target), owner(Path(target).name, agent))
                remove_tree(home / 'bundle', owner(kit['id'], agent))
                # Backups, upstream originals, dependencies and mutable settings remain recoverable.
                config['installed'] = False
                atomic_write(home / 'settings.json', (json.dumps(config, indent=2) + '\n').encode())
                results.append({'kit': kit['id'], 'agent': agent, 'uninstalled': True, 'retained': 'settings, backups, dependency environments, upstream originals'}); continue
            bundle = home / 'bundle'
            if getattr(args, 'upstream_only', False):
                verify(bundle, owner(kit['id'], agent))
                engine = load(bundle / 'installer.py', '_kotonoha_check_update')
                checked = engine.check_updates(Path('/nonexistent-kotonoha-preview'))
                results.append({'kit':kit['id'],'agent':agent,'upstream_only':True,'applied':False,**checked}); continue
            bundle_data = files(root / 'tools/intelliforge/resources/runtime' / kit['id'])
            if kit['id'] == 'yomiyasu':
                bundle_data.update(meiseki_assets(root / 'tools/intelliforge/resources/runtime/yomiyasu'))
            if kit['id']=='yomiyasu':
                lock_data=json.loads(bundle_data['assets/kotonoha/UPSTREAMS.json'])
                if lock_data['integration']['status']!='verified':raise ForgeError('Upstream integration is pending verification')
            backup = replace_tree(bundle, owner(kit['id'], agent), bundle_data)
            skill_backups = []; upstream_backup = None; upstream_changed = False; market_backup = None; market_target = None
            retired_backups = []
            old_config = (home / 'settings.json').read_bytes() if (home / 'settings.json').exists() else None
            try:
                config.update(owner=owner(kit['id'], agent), version=kit['version'], method=item['method'], installed=True)
                if getattr(args, 'mode', None): config['mode'] = args.mode
                prepare_dependencies(kit, agent, home, bundle, config, state)
                if kit['id'] == 'yomiyasu' and (args.action == 'update' or not (home / 'upstream').exists()):
                    upstream_backup = upstream_update(bundle, home, agent); upstream_changed = True
                if item['method'] == 'native':
                    destination = args.skills_dir or Path.home() / '.agents/skills'
                    if kit['id']=='yomiyasu':
                        for legacy_name in ('yomiyasu','paragraph-writing','japanese-direct-writing'):
                            old=destination/legacy_name
                            if old.exists():
                                verify(old,owner(legacy_name,agent))
                                saved=home/'backups'/(legacy_name+'-'+__import__('uuid').uuid4().hex)
                                saved.parent.mkdir(parents=True,exist_ok=True)
                                shutil.copytree(old,saved);verify(saved,owner(legacy_name,agent))
                                retired_backups.append((old,saved))
                                remove_tree(old,owner(legacy_name,agent))
                    config['skills'] = []
                    for name, data in skill_roots(root, kit, agent).items():
                        target = destination / name
                        if kit['id'] == 'yomiyasu':
                            mode = config.get('mode', 'auto')
                            data['agents/openai.yaml'] = f'policy:\n  allow_implicit_invocation: {str(mode == "auto" and name != "yomiyasu").lower()}\n'.encode()
                        skill_backups.append((target, replace_tree(target, owner(name, agent), data)))
                        config['skills'].append(str(target))
                atomic_write(home / 'settings.json', (json.dumps(config, ensure_ascii=False, indent=2) + '\n').encode())
                if item['method'] == 'plugin':
                    market_target, market_backup = marketplace(root, kit, agent, state, config.get('mode', 'auto'))
                    plugins.manage(market_target, kit, agent, 'update' if args.action == 'update' else 'install', state, args.skills_dir)
                for index,(target,saved) in enumerate(skill_backups):
                    if saved and kit['id']=='yomiyasu':
                        archive=home/'backups'/saved.name;archive.parent.mkdir(parents=True,exist_ok=True)
                        shutil.move(str(saved),str(archive))
                        skill_backups[index]=(target,archive)
            except BaseException:
                if market_target:
                    remove_tree(market_target, owner('marketplace', agent))
                    if market_backup: market_backup.rename(market_target)
                if upstream_changed:
                    remove_tree(home / 'upstream', owner('yomiyasu-upstream', agent))
                    if upstream_backup: upstream_backup.rename(home / 'upstream')
                for target, saved in reversed(skill_backups):
                    remove_tree(target, owner(target.name, agent))
                    if saved:
                        if kit['id']=='yomiyasu':
                            shutil.copytree(saved,target)
                            if saved.parent==target.parent:remove_tree(saved,owner(target.name,agent))
                        else:saved.rename(target)
                for old,saved in reversed(retired_backups):
                    if not old.exists():shutil.copytree(saved,old)
                remove_tree(bundle, owner(kit['id'], agent))
                if backup: backup.rename(bundle)
                if old_config is None: (home / 'settings.json').unlink(missing_ok=True)
                else: atomic_write(home / 'settings.json', old_config)
                raise
            results.append({'kit': kit['id'], 'agent': agent, 'version': kit['version'], 'method': item['method'], 'runtime': str(home)})
    print(json.dumps({'results': results}, ensure_ascii=False, indent=2))
    return int(any(value.get('exit_code', 0) for value in results))


ENTRIES = {'ux-stack': 'skill/scripts/harness.py', 'design-research': 'skill/scripts/harness.py',
           'speckit': 'swb.py', 'github-pm': 'skills/github-project-director/scripts/github_inspect.py',
           'office': 'office.py', 'yomiyasu': 'assets/kotonoha/scripts/check.py'}


def kit_run(identity, agent, arguments, state):
    identity = 'yomiyasu' if identity == 'kotonoha' else identity
    kit = definitions(distribution_root()).get(identity)
    if not kit: raise ForgeError('Unknown kit: ' + identity)
    home = state / agent / identity; bundle = home / 'bundle'
    verify(bundle, owner(identity, agent)); config = settings(home)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--tool'); parser.add_argument('arguments', nargs=argparse.REMAINDER)
    options = parser.parse_args(arguments if arguments[:1] == ['--tool'] else ['--', *arguments]); tail = options.arguments
    if tail[:1] == ['--']: tail = tail[1:]
    if identity == 'workgraph' and not options.tool: return hook_run(agent, tail, state)
    if identity == 'ecc':
        from .ecc_port import main
        return main(bundle, agent, tail)
    if identity == 'herdr':
        if hashlib.sha256(Path(config['binary']).read_bytes()).hexdigest()!=config.get('binary_sha256'):
            raise ForgeError('Herdr executable changed; revalidate it before running the workspace wrapper.')
        wrapper = load(bundle / 'install.py', '_intelliforge_herdr').RUNTIME
        wrapper = wrapper.replace("BINARY = str(Path.home() / '.local/bin/herdr')", 'BINARY = ' + repr(config['binary']))
        # Generated runtime contains a nested source string; port it at execution without editing the original.
        wrapper = wrapper.replace('import fcntl', 'from agent_intelliforge import fcntl_compat as fcntl')
        wrapper = wrapper.replace('import subprocess', 'from agent_intelliforge import subprocess_bridge as subprocess')
        temporary = home / 'herdr-open.py'; atomic_write(temporary, wrapper.encode())
        return subprocess.call([sys.executable, str(temporary), *tail], env=environment(home, agent, state))
    selected = ENTRIES.get(identity)
    if options.tool:
        if Path(options.tool).name != options.tool or not options.tool.endswith('.py'):
            raise ForgeError('--tool must be a Python helper filename')
        matches = [p for p in bundle.rglob(options.tool) if 'tests' not in p.parts and p.is_file()]
        if len(matches) != 1: raise ForgeError('Helper not found or ambiguous: ' + options.tool)
        allowed = {'workgraph': {'workgraph_tools.py','workgraph_github.py','install_schemas.py'},
                   'office': {'office.py'}, 'yomiyasu': {'check.py','writing_lint.py'}, 'github-pm': {'github_inspect.py'},
                   'speckit': {'swb.py'}, 'ux-stack': {'harness.py'}}
        if identity in allowed and options.tool not in allowed[identity]:
            raise ForgeError('Installer/configuration helpers are not executable through the portable Skill entry')
        if identity == 'design-research' and matches[0].parent != bundle / 'skill/scripts':
            raise ForgeError('Only the research workflow helpers are executable')
        selected = matches[0].relative_to(bundle).as_posix()
    if not selected: raise ForgeError('This kit has no generic executable entry')
    if identity == 'office' and tail[:1] == ['mcp-config']:
        raise ForgeError('Optional MCP registration uses the selected host manager; configure it explicitly.')
    executable = config.get('python', sys.executable)
    return subprocess.call([executable, '-B', str(bundle / selected), *tail], env=environment(home, agent, state))


def hook_run(agent, arguments, state):
    if os.environ.get('DR_GAN_CHILD') or os.environ.get('UX_GAN_CHILD'): return 0
    home = state / agent / 'workgraph'; verify(home / 'bundle', owner('workgraph', agent))
    module = load(home / 'bundle/hooks/basic_memory_workgraph.py', '_intelliforge_hook')
    policy = Path(settings(home)['policy']); module.ROOT = policy
    # Templates/policy remain hash-bound; configuration is intentionally editable.
    verify(policy / 'assets', owner('workgraph-policy', agent))
    def runtime():
        settings_value = module.read_object(policy / 'config.json')
        policy_text = (policy / 'assets/memory-policy.md').read_text(encoding='utf-8').strip()
        # Validate the same supported modes by calling the original with the assets view.
        for key, allowed, default in [('mode', ('smart','always','off'), 'smart'), ('caseMode', ('off','reusable','progressive'), 'off'), ('skillMode', ('off','review','auto'), 'review'), ('correctionMode', ('off','scoped'), 'off')]:
            settings_value[key] = settings_value.get(key, default)
            if settings_value[key] not in allowed: raise ValueError('Invalid mode')
        if not policy_text: raise ValueError('Missing policy')
        return settings_value, policy_text
    module.runtime = runtime
    if arguments[:1] == ['arm']:
        parser = argparse.ArgumentParser(); parser.add_argument('action'); parser.add_argument('--ticket', required=True)
        parser.add_argument('--token', required=True); parser.add_argument('--mode', required=True); parser.add_argument('--candidate', action='store_true')
        args = parser.parse_args(arguments)
        module.arm(args.ticket, args.token, args.mode, args.candidate); return 0
    event = json.load(sys.stdin)
    action = arguments[0] if arguments else 'recall'
    if action not in ('recall', 'save'): raise ForgeError('Unknown hook action')
    if agent == 'claude':
        identity = event.get('session_id')
        if isinstance(identity, str) and identity:
            turns = policy / 'turns'; turns.mkdir(exist_ok=True)
            path = turns / (hashlib.sha256(identity.encode()).hexdigest() + '.json')
            with file_lock(turns / '.lock'):
                if action == 'recall': atomic_write(path, json.dumps({'turn_id': secrets.token_hex(32)}).encode())
                event['turn_id'] = json.loads(path.read_text(encoding='utf-8')).get('turn_id') if path.exists() else None
                if action == 'save': path.unlink(missing_ok=True)
    value = module.evaluate(event, action)
    context = value.get('hookSpecificOutput', {}).get('additionalContext')
    if context:
        # Replace only the issued arm command, never reconstruct private reasoning.
        command = re.compile(r'^.*basic_memory_workgraph\.py[\'\"]? arm (.*)$', re.M)
        context = command.sub(lambda match: f'intelliforge hook --agent {agent} arm ' + match[1], context)
        context = context.replace(str(policy / 'templates'), str(policy / 'assets/templates'))
        value['hookSpecificOutput']['additionalContext'] = context
    if 'reason' in value: value['reason'] = value['reason'].replace(str(policy / 'templates'), str(policy / 'assets/templates'))
    if value: print(json.dumps(value, ensure_ascii=False))
    return 0
