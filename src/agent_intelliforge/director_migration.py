"""Explicit retirement of the former two kits, including host registrations."""
from __future__ import annotations
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from .catalog import ForgeError, MARKETPLACE
from .ownership import check_path, verify, atomic_write, inventory
from .portable import file_lock
from . import plugins

OLD = ('speckit', 'github-pm')


def describe(state, agent):
    result=[]
    for identity in OLD:
        home=state/agent/identity;check_path(home)
        path=home/'settings.json'
        if not path.exists():continue
        config=json.loads(path.read_text(encoding='utf-8'))
        if not config.get('installed',True):continue
        if config.get('owner')!=f'agent-intelliforge/{agent}/{identity}' or config.get('method') not in ('native','plugin'):
            raise ForgeError('Foreign legacy runtime preserved: '+str(home))
        verify(home/'bundle',config['owner'])
        result.append({'id':identity,'home':home,'config':config})
    return result


@contextmanager
def migrate(root, state, agent, enabled, skills_dir=None):
    from . import runtime
    old=describe(state,agent)
    engine=runtime.load(root/'tools/repository-director/install.py','_director_migration_engine')
    native_skills=skills_dir or Path(os.environ.get('RD_SKILLS_DIR',Path.home()/'.agents/skills'))
    if state.absolute().is_relative_to(native_skills.absolute()):
        raise ForgeError('Runtime and backups must be outside the Skill discovery directory')
    codex=Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))
    bin_dir=Path(os.environ.get('RD_BIN_DIR',Path.home()/'.local/bin'))
    standalone=agent=='codex' and engine.legacy_present({'skills':native_skills,'codex':codex,'bin':bin_dir})
    if not old and not standalone:
        yield;return
    if not enabled:raise ForgeError('Legacy repository kits detected; preview/install with --migrate-legacy --only repository-director')
    state.mkdir(parents=True,exist_ok=True)
    with file_lock(state/('.repository-director-migration-'+agent+'.lock')):
        old=describe(state,agent)
        retired=[];registrations=[];removed=[]
        registry=state/agent/'plugin-registrations.json';check_path(registry)
        registry_before=registry.read_bytes() if registry.exists() else None
        records=json.loads(registry_before) if registry_before else {}
        old_settings={item['home']/'settings.json':(item['home']/'settings.json').read_bytes() for item in old}
        market=state/agent/'marketplace';check_path(market)
        market_before=None
        if any(item['config']['method']=='plugin' for item in old):
            verify(market,f'agent-intelliforge/{agent}/marketplace')
            market_before=runtime.files(market)
            present=plugins.installed(agent)
            from .kotonoha_migration import plugin_rows
            rows=plugin_rows(agent)
            for item in old:
                identity=item['id']+'@'+MARKETPLACE
                if rows.get(identity,{}).get('enabled') is False:
                    raise ForgeError('Disabled legacy plugin preserved. Resolve its intended state through the host manager before migration: '+identity)
        for item in old:
            if item['config']['method']=='plugin':
                identity=item['id']+'@'+MARKETPLACE
                record=records.get(identity,{})
                if identity not in present or Path(record.get('source','')).absolute()!=market.absolute():
                    raise ForgeError('Unowned/missing legacy plugin registration: '+identity)
                registrations.append(identity)
            for name in item['config'].get('skills',[]):
                path=Path(name);check_path(path)
                permitted={Path.home()/'.agents/skills',Path.home()/'.claude/skills',codex/'skills',native_skills}
                if path.parent not in permitted or path.name not in engine.legacy.OLD_SKILLS:
                    raise ForgeError('Legacy Skill outside expected roots: '+name)
                verify(path,f'agent-intelliforge/{agent}/{path.name}')
                retired.append(path)
        # Standalone formats and portable formats have distinct manifests.
        changes={}
        if standalone:
            changes=engine.legacy.plan(native_skills,codex,bin_dir,engine.repo.safe,ignored=retired)
        backup=state/agent/'repository-director-migration-backups'/uuid.uuid4().hex
        backup.mkdir(parents=True)
        saved_files={p:p.read_bytes() for p in changes if p.exists()}
        file_keys={str(n):str(p) for n,p in enumerate(saved_files)}
        for n,(path,data) in enumerate(saved_files.items()):(backup/str(n)).write_bytes(data)
        (backup/'paths.json').write_text(json.dumps(file_keys,indent=2),encoding='utf-8')
        try:
            for n,path in enumerate(retired):
                dest=backup/('skill-'+str(n));shutil.copytree(path,dest);shutil.rmtree(path)
            if changes:engine.repo.transaction(changes)
            for identity in registrations:
                argv=[agent,'plugin','remove' if agent=='codex' else 'uninstall',identity]
                if agent=='claude':argv.append('--keep-data')
                plugins.checked(argv)
                if identity in plugins.installed(agent):raise ForgeError('Legacy plugin retirement could not be verified: '+identity)
                removed.append(identity);records.pop(identity,None)
            if market_before is not None:
                data={n:raw for n,raw in market_before.items() if not any(n.startswith('plugins/'+i+'/') for i in OLD)}
                catalog_path='.agents/plugins/marketplace.json' if agent=='codex' else '.claude-plugin/marketplace.json'
                value=json.loads(data[catalog_path]);value['plugins']=[row for row in value['plugins'] if row['name'] not in OLD]
                data[catalog_path]=(json.dumps(value,indent=2)+'\n').encode()
                from .ownership import replace_tree
                replace_tree(market,f'agent-intelliforge/{agent}/marketplace',data)
            if registry_before is not None:atomic_write(registry,(json.dumps(records,indent=2)+'\n').encode())
            engine.repo.transaction({item['home']/'settings.json':(json.dumps(dict(item['config'],installed=False,migrated_to='repository-director'),indent=2)+'\n').encode() for item in old})
            yield
        except BaseException:
            # Restore local resources before re-registering a previously removed host plugin.
            if changes:engine.repo.transaction({p:saved_files.get(p) for p in changes})
            for n,path in enumerate(retired):
                if not path.exists():shutil.copytree(backup/('skill-'+str(n)),path)
            if market_before is not None:
                from .ownership import replace_tree
                replace_tree(market,f'agent-intelliforge/{agent}/marketplace',market_before)
            if registry_before is None:registry.unlink(missing_ok=True)
            else:atomic_write(registry,registry_before)
            engine.repo.transaction(old_settings)
            for identity in removed:
                try:plugins.checked([agent,'plugin','add' if agent=='codex' else 'install',identity])
                except Exception as exc:raise ForgeError('Local rollback complete, but restore host plugin manually: '+identity) from exc
            raise
