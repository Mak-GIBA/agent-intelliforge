"""Inspectable, additive installer; Linux Codex defaults to the existing scripts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from . import __version__
from .catalog import ForgeError, definitions, distribution_root, selection


def state_root() -> Path:
    if os.environ.get("INTELLIFORGE_STATE_DIR"):
        return Path(os.environ["INTELLIFORGE_STATE_DIR"]).expanduser().absolute()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "AgentIntelliforge"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "agent-intelliforge"


def inspect_plan(kits: list[dict], agent: str, plugin: bool, state: Path) -> dict:
    hosts = ["codex", "claude"] if agent == "both" else [agent]
    operations = []
    for host in hosts:
        for kit in kits:
            method = "plugin" if plugin or host == "claude" or os.name == "nt" else "legacy"
            if kit['id'] == 'herdr' and method == 'plugin': method = 'native'
            if kit['id']=='kotonoha':
                from .kotonoha_migration import describe
                migration=describe(state,host)
                if migration: method=migration['method']
            else: migration=None
            target_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) if host == "codex" else Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
            places = {"agent_home": str(target_home), "skills_home": str(Path.home() / (".agents/skills" if host == "codex" else ".claude/skills")),
                      "data_home": str(state), "bin_home": str(Path.home() / ".local/bin")}
            entry = {"kit": kit["id"], "agent": host, "method": method,
                     "skills": [item["name"] for item in kit["skills"]],
                     "sources": kit["sources"], "dependencies": kit["dependencies"],
                     "destinations": [item.format(**places) for item in kit["destinations"]],
                     "settings": kit["settings"], "definition": kit["definition"],
                     "editable_sources": kit["editable_sources"],
                     "runtime": str(state / host / kit["id"]),
                     "status": "experimental" if host == "claude" else "existing" if method == "legacy" else "additional distribution",
                     "legacy_script": kit["legacy"]["script"]}
            if method != "legacy":
                entry["destinations"] = [str(state / host / kit["id"])] + (
                    ["native " + host + " plugin manager cache"] if method == "plugin" and kit["plugin"]["enabled"]
                    else [str(Path(places["skills_home"]) / item["name"]) for item in kit["skills"]])
                entry["settings"] = ["selected plugin registrations" if method == "plugin" else "owned Skill directories", "kit runtime settings"]
            if migration: entry['migration']=migration
            operations.append(entry)
    return {"schema_version": 1, "default_agent": "codex", "operations": operations,
            "unresolved": "Latest upstream/plugin versions are resolved only during an explicit install/update."}


def show_plan(value: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2)); return
    for item in value["operations"]:
        print(f"{item['kit']} / {item['agent']} / {item['method']} ({item['status']})")
        for key in ("skills", "destinations", "settings", "editable_sources"):
            print(f"  {key}: " + ("; ".join(item[key]) or "none"))
        for source in item["sources"]:
            print(f"  source: {source['url']} — {source['revision']}")
        for dependency in item["dependencies"]:
            print(f"  dependency: {dependency['name']} — {dependency['condition']}")
        print("  definition: " + item["definition"])
    print(value["unresolved"])


def legacy_action(root: Path, kits: list[dict], action: str) -> int:
    if not shutil.which("bash"):
        raise ForgeError("The existing installer requires Bash; native Windows uses the portable path.")
    if action == "install":
        return subprocess.call(["bash", str(root / "install_all.sh"), "--only",
                                ",".join(kit["id"] for kit in kits), "--apply"])
    from .runtime import diagnose
    results = []
    for kit in kits:
        args = kit["legacy"]["actions"].get(action)
        if args is None:
            if action == "doctor":
                results.append(diagnose(kit, "codex", state_root(), legacy=True)); continue
            raise ForgeError(f"{kit['id']} has no existing {action} action; use its documented procedure. No replacement behavior was invented.")
        code = subprocess.call(["bash", str(root / kit["legacy"]["script"]), *args])
        if code in (130, 143):
            return code
        results.append({"kit": kit["id"], "exit_code": code})
    print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    return 1 if any(item.get("exit_code", 0) for item in results) else 0


def main(argv=None) -> int:
    if os.name == 'nt':
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("list", "inspect", "install", "update", "doctor", "uninstall", "locate"):
        command = commands.add_parser(action)
        command.add_argument("--only", action="append", help="kit IDs, comma-separated; repeatable")
        command.add_argument("--agent", choices=("codex", "claude", "both"), default="codex")
        command.add_argument("--plugin", action="store_true", help="opt into the official plugin distribution")
        command.add_argument("--json", action="store_true")
        command.add_argument("--state-dir", type=Path)
        command.add_argument("--skills-dir", type=Path, help="portable native Skill destination override")
        if action in ("install", "update", "uninstall"):
            mode = command.add_mutually_exclusive_group()
            mode.add_argument("--apply", action="store_true")
            mode.add_argument("--dry-run", action="store_true")
            command.add_argument("--upstream-only", action="store_true", help="kotonoha upstream check only")
            command.add_argument("--mode", choices=("auto", "explicit"))
        if action == "locate":
            command.add_argument("--upstream", action="store_true")
        if action == 'doctor': command.add_argument('--isolation-smoke', action='store_true', help='probe a temporary read-only boundary; no model calls')
    run = commands.add_parser("kit-run")
    run.add_argument("kit"); run.add_argument("--agent", choices=("codex", "claude"), default="codex")
    run.add_argument('--tool')
    hook = commands.add_parser("hook")
    hook.add_argument("--agent", choices=("codex", "claude"), default="codex")
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw[:1] in (['kit-run'], ['hook']):
        boundary = raw.index('--') if '--' in raw else len(raw)
        args, extra = parser.parse_known_args(raw[:boundary])
        args.args = extra + raw[boundary + 1:]
        if getattr(args, 'tool', None): args.args = ['--tool', args.tool, '--', *args.args]
    else:
        args = parser.parse_args(raw)
    try:
        from .runtime import kit_run, hook_run
        if args.action == "kit-run":
            return kit_run(args.kit, args.agent, args.args, state_root())
        if args.action == "hook":
            return hook_run(args.agent, args.args, state_root())
        root = distribution_root(); catalog = definitions(root)
        kits = selection(args.only, catalog); state = (args.state_dir or state_root()).absolute()
        if args.action == "list":
            if args.json:
                print(json.dumps(kits, ensure_ascii=False, indent=2))
            else:
                for kit in kits:
                    print(f"{kit['id']:<16} {kit['name']} — edit {kit['definition']}")
            return 0
        plan = inspect_plan(kits, args.agent, args.plugin, state)
        if args.action == "locate":
            if len(kits) != 1 or args.agent == "both":
                raise ForgeError("locate requires one --only kit and one agent")
            path = state / args.agent / kits[0]["id"] / ("upstream" if args.upstream else "bundle")
            print(path); return 0
        if getattr(args, "upstream_only", False) and (args.action != "update" or [kit["id"] for kit in kits] != ["kotonoha"] or args.mode):
            raise ForgeError("--upstream-only requires update --only kotonoha without --mode")
        if getattr(args, 'mode', None) and [kit['id'] for kit in kits] != ['kotonoha']:
            raise ForgeError('--mode requires --only kotonoha')
        if getattr(args, 'mode', None) and args.action not in ('install','update'):
            raise ForgeError('--mode applies to install/update only')
        if any(item['method']=='legacy' for item in plan['operations']) and (args.skills_dir or args.state_dir):
            raise ForgeError('--skills-dir/--state-dir apply to the additional Plugin/portable path. Use --plugin or the existing installer\'s documented destination flags.')
        if getattr(args, 'isolation_smoke', False):
            from .isolation import smoke
            value = [smoke(host,state) for host in (['codex','claude'] if args.agent=='both' else [args.agent])]
            print(json.dumps({'isolation':value},ensure_ascii=False,indent=2))
            return int(not all(item['isolation_ready'] for item in value))
        if args.action == "inspect" or (args.action != "doctor" and not args.apply):
            show_plan(plan, args.json); return 0
        if all(item["method"] == "legacy" for item in plan["operations"]):
            if getattr(args, "upstream_only", False) or getattr(args, "mode", None):
                if len(kits) != 1 or kits[0]["id"] != "kotonoha":
                    raise ForgeError("Writing mode options require --only kotonoha")
                command = ["bash", str(root / kits[0]["legacy"]["script"]), "--apply"]
                if args.action == "update": command.append("--update")
                if args.upstream_only: command.append("--upstream-only")
                if args.mode: command += ["--mode", args.mode]
                return subprocess.call(command)
            return legacy_action(root, kits, args.action)
        from .runtime import portable_action
        return portable_action(root, kits, plan, args, state)
    except (ForgeError, OSError, ValueError, subprocess.SubprocessError) as error:
        print("intelliforge: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
