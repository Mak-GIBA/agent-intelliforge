"""Transactional retirement of the former kit identity; upstream OSS stays named yomiyasu."""
from __future__ import annotations
from contextlib import contextmanager
import json
from contextlib import ExitStack
from pathlib import Path
import shutil
import tempfile
import uuid

from .catalog import ForgeError, MARKETPLACE
from .ownership import atomic_write, check_path, verify
from .portable import file_lock
from . import plugins

OLD='yomiyasu'
NEW='kotonoha'


def read(path):
    check_path(path)
    return json.loads(path.read_text(encoding='utf-8'))


def describe(state,agent):
    old=state/agent/OLD;new=state/agent/NEW
    check_path(old);check_path(new)
    if not old.exists():return None
    if new.exists():raise ForgeError('Both old and new writing runtimes exist; preserve and resolve them before migration')
    config=read(old/'settings.json')
    if config.get('owner')!=f'agent-intelliforge/{agent}/{OLD}' or config.get('method') not in ('native','plugin'):
        raise ForgeError('Unowned old writing runtime; preserving '+str(old))
    verify(old/'bundle',config['owner'])
    if (old/'upstream').exists():verify(old/'upstream',f'agent-intelliforge/{agent}/yomiyasu-upstream')
    for path in config.get('skills',[]):verify(Path(path),f'agent-intelliforge/{agent}/{Path(path).name}')
    return {'from':OLD,'to':NEW,'method':config['method'],'old_runtime':str(old),'runtime':str(new),
            'apply_required':True,'preserves':'mode, user configuration, upstream snapshots; dependencies rebuilt at the new absolute path'}


def plugin_rows(agent):
    value=json.loads(plugins.checked([agent,'plugin','list','--json']))
    if isinstance(value,dict) and 'installed' in value:value=value['installed']
    if isinstance(value,dict):
        value=[dict(row,id=identity) for identity,rows in value.items() for row in (rows if isinstance(rows,list) else [rows])]
    if not isinstance(value,list):raise ForgeError('Unknown plugin state protocol; old registration is preserved')
    return {row.get('pluginId',row.get('id',row.get('name'))):row for row in value}


def host_remove(agent,identity):
    argv=[agent,'plugin','remove' if agent=='codex' else 'uninstall',identity]
    if agent=='claude':argv.append('--keep-data')
    plugins.checked(argv)


@contextmanager
def migrate(state,agent,method):
    info=describe(state,agent)
    if not info:yield;return
    old=state/agent/OLD;new=state/agent/NEW;market=state/agent/'marketplace'
    registry=state/agent/'plugin-registrations.json'
    old_id=OLD+'@'+MARKETPLACE;new_id=NEW+'@'+MARKETPLACE
    with file_lock(state/agent/'.kotonoha-migration.lock'), ExitStack() as locks:
        locks.enter_context(file_lock(old/'.operation.lock'))
        describe(state,agent)  # recheck after acquiring both locks
        config=read(old/'settings.json')
        if method!=config['method']:raise ForgeError('Migration preserves the existing installation method')
        registry_raw=registry.read_bytes() if registry.exists() else None
        prior=read(registry) if registry.exists() else {}
        enabled=True
        if method=='plugin':
            verify(market,f'agent-intelliforge/{agent}/marketplace')
            rows=plugin_rows(agent)
            if new_id in rows or new_id in prior:raise ForgeError('New plugin already exists; nothing migrated')
            if old_id not in prior or old_id not in rows or Path(prior[old_id]['source']).absolute()!=market.absolute():
                raise ForgeError('Old plugin registration is not owned by this runtime')
            enabled=rows[old_id].get('enabled')
            if not isinstance(enabled,bool):raise ForgeError('Cannot determine old plugin enabled state; preserving it')
            if not enabled and 'disable' not in plugins.checked([agent,'plugin','--help']).split():
                raise ForgeError('Host CLI cannot preserve a disabled plugin; old plugin remains unchanged. Use a host version with plugin disable support.')
        with tempfile.TemporaryDirectory(prefix='kotonoha-migration-') as td:
            snapshot=Path(td)
            if market.exists():shutil.copytree(market,snapshot/'marketplace')
            # The original old runtime stays untouched until all new resources succeed.
            skill_snapshots=[]
            for index,path in enumerate(config.get('skills',[])):
                target=Path(path);saved=snapshot/('skill-'+str(index));shutil.copytree(target,saved);skill_snapshots.append((target,saved))
            entered=False
            try:
                new.mkdir()
                shutil.copytree(old/'bundle',new/'bundle')
                marker=new/'bundle/.intelliforge.json';value=read(marker);value['owner']=f'agent-intelliforge/{agent}/{NEW}'
                atomic_write(marker,(json.dumps(value,indent=2)+'\n').encode())
                if (old/'upstream').exists():shutil.copytree(old/'upstream',new/'upstream')
                config['owner']=f'agent-intelliforge/{agent}/{NEW}'
                atomic_write(new/'settings.json',(json.dumps(config,indent=2)+'\n').encode())
                if method=='plugin':
                    prior[new_id]=dict(prior[old_id],migration_from=old_id);atomic_write(registry,(json.dumps(prior,indent=2)+'\n').encode())
                entered=True
                yield
                if method=='plugin':
                    rows=plugin_rows(agent)
                    if new_id not in rows:raise ForgeError('New plugin installation was not confirmed')
                    if not enabled:plugins.checked([agent,'plugin','disable',new_id])
                    if plugin_rows(agent).get(new_id,{}).get('enabled')!=enabled:
                        raise ForgeError('New plugin enabled state differs')
                    host_remove(agent,old_id)
                    if old_id in plugin_rows(agent):raise ForgeError('Old plugin retirement was not confirmed')
                    from .runtime import files
                    from .ownership import replace_tree
                    payload={k:v for k,v in files(market).items() if not k.startswith('plugins/'+OLD+'/')}
                    for name in ('.agents/plugins/marketplace.json','.claude-plugin/marketplace.json'):
                        if name in payload:
                            catalog=json.loads(payload[name]);catalog['plugins']=[p for p in catalog['plugins'] if p['name']!=OLD]
                            payload[name]=(json.dumps(catalog,indent=2)+'\n').encode()
                    replace_tree(market,f'agent-intelliforge/{agent}/marketplace',payload)
                    active=read(registry);active.pop(old_id,None)
                    atomic_write(registry,(json.dumps(active,indent=2)+'\n').encode())
                # Keep the untouched old environment as an explicitly labelled recovery backup.
                backup=state/agent/'migration-backups'/uuid.uuid4().hex;backup.parent.mkdir(exist_ok=True)
                check_path(backup)
                locks.close()
                old.rename(backup)
            except BaseException:
                recovery_error=None
                try:
                    if method=='plugin':
                        # Retain a source for reinstalling the old registration before restoring it.
                        if market.exists():shutil.rmtree(market)
                        shutil.copytree(snapshot/'marketplace',market)
                        rows=plugin_rows(agent)
                        if old_id not in rows:
                            plugins.checked([agent,'plugin','add' if agent=='codex' else 'install',old_id])
                            if not enabled:plugins.checked([agent,'plugin','disable',old_id])
                        if new_id in rows:host_remove(agent,new_id)
                except Exception as error:recovery_error=error
                if registry_raw is None:registry.unlink(missing_ok=True)
                else:atomic_write(registry,registry_raw)
                for target,saved in (skill_snapshots if entered else []):
                    if target.exists():shutil.rmtree(target)
                    shutil.copytree(saved,target)
                if new.exists() and recovery_error is None:shutil.rmtree(new)
                if recovery_error is not None:
                    raise ForgeError('Host rollback failed; both runtime copies are preserved. Repair plugin registrations before retrying: '+str(old)+' ; '+str(new)) from recovery_error
                raise
