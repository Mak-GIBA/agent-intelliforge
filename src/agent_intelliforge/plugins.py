"""Delegate plugin lifecycle to host CLIs; never edit their caches/settings files."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from .catalog import ForgeError, MARKETPLACE
from .ownership import atomic_write, check_path
from .portable import native_command


def installed(agent):
    value = json.loads(checked([agent, 'plugin', 'list', '--json']))
    if agent == 'codex':
        if not isinstance(value, dict) or not isinstance(value.get('installed'), list):
            raise ForgeError('Unsupported Codex plugin list protocol; no plugin registration changed.')
        return {item['pluginId'] for item in value['installed'] if item.get('installed')}
    if isinstance(value, dict):
        if 'installed' in value: value = value['installed']
        else: return set(value)
    if not isinstance(value, list): raise ForgeError('Unsupported Claude plugin list protocol')
    return {item.get('id', item.get('pluginId', item.get('name'))) for item in value}


def preflight(kit, agent, action, state):
    if not kit['plugin']['enabled']: return
    if not shutil.which('intelliforge'):
        raise ForgeError('Plugin helpers/hooks require intelliforge on PATH. Run uv tool install . before applying the Plugin route.')
    if not shutil.which(agent): raise ForgeError(f'Install and authenticate {agent} first.')
    registry = state / agent / 'plugin-registrations.json'; check_path(registry)
    prior = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else {}
    identity = kit['id'] + '@' + MARKETPLACE
    marketplaces = json.loads(checked([agent,'plugin','marketplace','list','--json']))
    rows = marketplaces.get('marketplaces', marketplaces) if isinstance(marketplaces,dict) else marketplaces
    if isinstance(rows,dict): rows = [dict(value,name=name) for name,value in rows.items()]
    if not isinstance(rows,list): raise ForgeError('Unsupported marketplace list protocol')
    target = (state/agent/'marketplace').absolute()
    for row in rows:
        if row.get('name') != MARKETPLACE: continue
        source = row.get('root') or row.get('installLocation') or row.get('path')
        if source is None or Path(source).absolute() != target:
            raise ForgeError('Existing marketplace uses another source; preserving '+ MARKETPLACE)
    if identity in installed(agent) and identity not in prior:
        raise ForgeError('Existing unowned plugin registration is preserved: ' + identity)
    if action in ('update', 'uninstall') and identity not in prior:
        raise ForgeError('No owned plugin registration: ' + identity)


def checked(argv: list[str], *, timeout=120) -> str:
    result = subprocess.run(native_command(argv), capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    if result.returncode:
        raise ForgeError(f"{argv[0]} {' '.join(argv[1:3])} failed ({result.returncode}): {result.stderr[-1200:]}")
    return result.stdout


def conflict_skills(kit: dict, agent: str, skills_dir: Path | None = None) -> None:
    if kit['id']=='workgraph' and agent=='codex' and skills_dir is None:
        import os
        home=Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))
        if (home/'hooks/basic_memory_workgraph.py').exists() or (home/'basic-memory-workgraph/config.json').exists():
            raise ForgeError('Existing Workgraph hooks are preserved. Use the legacy installer until explicitly migrating their registration.')
    roots = [skills_dir] if skills_dir else ([Path.home() / ".agents/skills", Path.home() / ".codex/skills"]
                                           if agent == "codex" else [Path.home() / ".claude/skills"])
    conflicts = [str(root / item["name"]) for root in roots for item in kit["skills"]
                 if (root / item["name"]).exists() or (root / item["name"]).is_symlink()]
    if conflicts:
        raise ForgeError("Standalone Skills conflict with the plugin. Preserve/edit/export them before an explicit migration: " + ", ".join(conflicts))


def manage(root: Path, kit: dict, agent: str, action: str, state: Path, skills_dir=None) -> None:
    if not kit["plugin"]["enabled"]:
        return
    preflight(kit, agent, action, state)
    registry = state / agent / "plugin-registrations.json"
    check_path(registry)
    previous = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else {}
    identity = kit["id"] + "@" + MARKETPLACE
    if action == "install":
        conflict_skills(kit, agent, skills_dir)
        # A published git marketplace is stable across uv package upgrades; the
        # local checkout is useful while validating unpublished packages.
        source = str(root)
        if not previous:
            checked([agent, "plugin", "marketplace", "add", source])
        checked([agent, "plugin", "add" if agent == "codex" else "install", identity])
        previous[identity] = {"source": source, "agent": agent}
    elif action == "update":
        if identity not in previous:
            raise ForgeError(f"Plugin not installed by this CLI: {identity}; use its host manager.")
        # Codex's marketplace upgrade is Git-only. This installer deliberately
        # registers an owned local directory so wheel upgrades cannot invalidate
        # its path. plugin add installs/refetches that selected local plugin.
        if agent == 'claude': checked([agent, 'plugin', 'marketplace', 'update', MARKETPLACE])
        checked([agent, "plugin", "add" if agent == "codex" else "update", identity])
    elif action == "uninstall":
        if identity not in previous:
            raise ForgeError(f"Unowned plugin registration; preserving {identity}")
        command = [agent, "plugin", "remove" if agent == "codex" else "uninstall", identity]
        if agent == "claude": command.append("--keep-data")
        checked(command)
        previous.pop(identity)
    atomic_write(registry, (json.dumps(previous, ensure_ascii=False, indent=2) + "\n").encode())
