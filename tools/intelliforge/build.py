#!/usr/bin/env python3
"""Build inspectable plugin/package resources without installing any kit.

Edit tools/<kit>/kit.json, the referenced source assets, and this small packaging
adapter. Design Research/Upstream use their verified assembly, never the old base
assets directly. No existing installer execution behavior is changed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from agent_intelliforge.catalog import definitions, source_path, summary

EXCLUDES = {"__pycache__", "node_modules", ".git", "evaluation", "evaluation-v200",
            "evaluation-v130", "evaluation-explanation", "evaluation-v200", "evaluation-v200-proposal", "evals"}


def files_under(root: Path, *, excludes=EXCLUDES) -> dict[str, bytes]:
    result = {}
    for path in sorted(root.rglob("*")):
        if any(part in excludes for part in path.relative_to(root).parts): continue
        if path.is_symlink(): raise ValueError("Linked source: " + str(path))
        if path.is_file() and path.suffix != ".pyc":
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def portable_python(data: bytes, relative: str) -> bytes:
    """Imports select adapters only in generated copies; original code stays intact."""
    text = data.decode("utf-8")
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines: offsets.append(offsets[-1] + len(line))
    def position(line, column):
        return offsets[line - 1] + len(lines[line - 1].encode()[:column].decode())
    replacements = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name in ("fcntl", "subprocess") for alias in node.names):
            rewritten = []
            for alias in node.names:
                if alias.name == "fcntl": rewritten.append(f"from agent_intelliforge import fcntl_compat as {alias.asname or 'fcntl'}")
                elif alias.name == "subprocess": rewritten.append(f"from agent_intelliforge import subprocess_bridge as {alias.asname or 'subprocess'}")
                else: rewritten.append(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
            replacements.append((position(node.lineno, node.col_offset),
                                 position(node.end_lineno, node.end_col_offset), "; ".join(rewritten)))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "symlink_to":
            destination = ast.get_source_segment(text, node.func.value)
            arguments = ", ".join(ast.get_source_segment(text, part) for part in node.args)
            keywords = ", ".join(keyword.arg + "=" + ast.get_source_segment(text, keyword.value) for keyword in node.keywords)
            rewritten = "_portable_link(" + destination + (", " + arguments if arguments else "") + (", " + keywords if keywords else "") + ")"
            replacements.append((position(node.lineno, node.col_offset),
                                 position(node.end_lineno, node.end_col_offset), rewritten))
    for start, end, value in sorted(replacements, reverse=True): text = text[:start] + value + text[end:]
    text = text.replace("os.O_NOFOLLOW", 'getattr(os, "O_NOFOLLOW", 0)')
    # Original sources use UTF-8 assets. Bind omitted Path text encodings in
    # distribution copies, without changing explicit encodings or **options.
    # Insert at closing parentheses so nested read/write calls do not overlap.
    lines = text.splitlines(keepends=True); offsets = [0]
    for line in lines: offsets.append(offsets[-1] + len(line))
    insertions = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute): continue
        method = node.func.attr
        if method not in ('read_text', 'write_text'): continue
        if len(node.args) != (1 if method == 'write_text' else 0): continue
        if any(isinstance(argument, ast.Starred) for argument in node.args): continue
        if any(keyword.arg in (None, 'encoding') for keyword in node.keywords): continue
        end = position(node.end_lineno, node.end_col_offset) - 1
        separator = '' if text[:end].rstrip().endswith(('(', ',')) else ', '
        addition = 'encoding="utf-8"'
        if method == 'write_text' and not any(keyword.arg == 'newline' for keyword in node.keywords):
            addition += ', newline="\\n"'
        insertions.append((end, separator + addition))
    for end, addition in sorted(insertions, reverse=True): text = text[:end] + addition + text[end:]
    patch = "\nfrom agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link\n_apply_ports(globals())\n"
    parsed = ast.parse(text); lines = text.splitlines(keepends=True)
    entries = [node for node in parsed.body if isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
               and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"]
    index = sum(len(line) for line in lines[:entries[-1].lineno - 1]) if entries else len(text)
    text = text[:index] + patch + text[index:]
    compile(text, relative, "exec")
    return text.encode()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def assembled_sources(explicit: Path | None) -> Path:
    if explicit:
        root = explicit / "sources" if (explicit / "sources/tools").exists() else explicit
        if not (root / "tools/design-research/skill/scripts/codex_interface.py").exists():
            raise ValueError("An assembled current source tree is required")
        return root
    temporary = Path(tempfile.mkdtemp(prefix="intelliforge-build-"))
    # The assembler verifies pinned base hashes and executes its existing tests.
    subprocess.run([sys.executable, "-B", str(ROOT / "tools/design-research-upgrade/build_installers.py"),
                    "--out", str(temporary / "assembly")], check=True)
    return temporary / "assembly/sources"


def render_skill(data: bytes, kit: dict, agent: str, name: str) -> bytes:
    text = data.decode("utf-8")
    if kit['id'] in ('ux-stack', 'design-research'):
        invocation = f'intelliforge kit-run {kit["id"]} --agent {agent} --'
        text = text.replace('bash <skill-dir>/scripts/gan-harness.sh', invocation)
        text = text.replace('the installed Bash harness', 'the installed harness').replace('the Bash entry point', 'the portable entry point')
        text = text.replace('the actual Bash script', 'the actual harness').replace('the real [gan-harness.sh](scripts/gan-harness.sh)', f'`{invocation}`')
        text = text.replace('existing Codex model/auth settings', 'existing selected-agent model/auth settings')
    if kit["id"] == "ecc":
        text = text.replace("python3 {{MANAGER}}", f"intelliforge kit-run ecc --agent {agent} --")
    if kit["id"] == "office":
        text = text.replace("{{LAUNCHER}}", f"intelliforge kit-run office --agent {agent} --")
        text = text.replace("{{RELEASE}}", f"<runtime shown by intelliforge locate --only office --agent {agent}>")
    if kit["id"] == "kotonoha" and name == "kotonoha":
        text = text.replace("`upstream/SKILL.upstream.md`", f"`intelliforge locate --only kotonoha --agent {agent} --upstream` が示すディレクトリの `SKILL.upstream.md`")
    # Keep facts/constraints in the original body. This is invocation binding,
    # not a second independently edited version of the writing/research rules.
    appendix = (f"\n\n## 配布環境の呼び出し\nこのPluginの管理ソースは `{kit['definition']}`。"
                f"導入先は `intelliforge locate --only {kit['id']} --agent {agent}` で確認する。"
                f"Pythonヘルパーは `intelliforge kit-run {kit['id']} --agent {agent} --tool <ファイル名> -- <引数>`、"
                f"研究・UXハーネスは `intelliforge kit-run {kit['id']} --agent {agent} -- <引数>` から実行する。"
                "Windowsではこの入口を使い、Bashやpython3という実行名を前提にしない。\n")
    if kit['id'] == 'kotonoha':
        appendix = (f"\n\n検査は `intelliforge kit-run kotonoha --agent {agent} --tool writing_lint.py -- <原稿> [--before <原稿>]`。"
                    "Python・Node.jsは導入時に準備した専用環境を使う。\n")
    if agent == "claude":
        # Namespacing is a host API detail; upstream originals stay unchanged.
        owners = {skill['name']: item['id'] for item in definitions(ROOT).values() for skill in item['skills']}
        text = re.sub(r"\$([a-z][a-z0-9-]+)", lambda m: "/" + owners[m[1]] + ":" + m[1] if m[1] in owners else m[0], text)
        appendix += "Claude Code対応は試験対応。実機未検証の機能を検証済みと扱わない。\n"
    return (text.rstrip() + appendix).encode()


def bundle_for(kit: dict, assembled: Path) -> dict[str, bytes]:
    directory = Path(kit["definition"]).parent
    source = assembled / directory if kit["id"] in ("speckit", "design-research") else ROOT / directory
    files = files_under(source)
    files["kit.json"] = (ROOT / kit["definition"]).read_bytes()
    return {name: portable_python(data, name) if name.endswith(".py") else data for name, data in files.items()}


def build_outputs(assembled: Path) -> dict[str, bytes]:
    catalog = definitions(ROOT); output = {}; exports = {"codex": [], "claude": []}
    for kit in catalog.values():
        bundle = bundle_for(kit, assembled)
        for name, data in bundle.items(): output[f"resources/runtime/{kit['id']}/{name}"] = data
        skills = list(kit["skills"])
        if kit["id"] == "speckit":
            common = load_module(assembled / "tools/speckit-upstream/workbench/command_skills.py", "intelliforge_command_skills")
            if {s['name'] for s in skills} != set(common.COMMANDS): raise ValueError('Upstream catalog differs from command_skills.py')
            kit = dict(kit, skills=skills)
        if not kit["plugin"]["enabled"]: continue
        for agent in ("codex", "claude"):
            prefix = f"plugins/{agent}/{kit['id']}"
            manifest = {"name": kit["id"], "version": kit["version"], "description": kit["name"],
                        "repository": "https://github.com/Mak-GIBA/agent-intelliforge"}
            if agent == "codex":
                manifest = {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", **manifest}
                output[prefix + "/plugin.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
            else:
                output[prefix + "/.claude-plugin/plugin.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
            for skill in skills:
                name = skill["name"]
                if skill.get('generated'):
                    body = common.render_skill(name, Path("__INTELLIFORGE_SWB__"), Path("__INTELLIFORGE_ASSETS__"))
                    body = body.replace("__INTELLIFORGE_SWB__", f"intelliforge kit-run speckit --agent {agent} --")
                    body = body.replace("__INTELLIFORGE_ASSETS__", "../../assets")
                    data = {"SKILL.md": body.encode(), "agents/openai.yaml": b"policy:\n  allow_implicit_invocation: false\n"}
                else:
                    base = assembled if skill.get("assembled") else ROOT
                    data = files_under(source_path(base, skill["source"]))
                    if kit["id"] == "kotonoha" and name == "kotonoha":
                        data = {key: value for key, value in data.items() if not key.startswith(("kotonoha/", "paragraph-writing/", "japanese-direct-writing/"))}
                if kit['id'] == 'kotonoha' and agent == 'codex':
                    data['agents/openai.yaml'] = ('policy:\n  allow_implicit_invocation: '+str(True).lower()+'\n').encode()
                for path, raw in data.items():
                    if path == "SKILL.md": raw = render_skill(raw, kit, agent, name)
                    # Original writing checkers are hash-bound resources. Port only
                    # our adapter; rewriting originals invalidates resources.json.
                    original = kit['id']=='kotonoha' and path.startswith(('upstream/','meiseki-upstream/'))
                    if path.endswith(".py") and not original: raw = portable_python(raw, path)
                    if agent == "claude" and path == "agents/openai.yaml": continue
                    if agent == "claude" and path == "SKILL.md" and (name.startswith("upstream-")):
                        parts = raw.decode().split('---', 2)
                        raw = ('---' + parts[1] + 'disable-model-invocation: true\n---' + parts[2]).encode()
                    output[prefix + f"/skills/{name}/{path}"] = raw
            if kit["id"] == "speckit":
                for name, raw in files_under(assembled / "tools/speckit-upstream/assets").items():
                    output[prefix + "/assets/" + name] = raw
            if kit["id"] == "workgraph":
                # Official hooks carry the existing policy; no new auto-save rules.
                hooks = {"hooks": {event: [{"hooks": [{"type": "command", "command": f"intelliforge hook --agent {agent} {action}"}]}]
                                   for event, action in (("UserPromptSubmit", "recall"), ("Stop", "save"))}}
                if agent == "claude":
                    for entries in hooks["hooks"].values():
                        # Exec form avoids shell-specific quoting on all hosts.
                        for item in entries[0]["hooks"]:
                            command = item.pop("command"); item["command"] = "intelliforge"; item["args"] = command.split()[1:]
                output[prefix + "/hooks/hooks.json"] = (json.dumps(hooks, indent=2) + "\n").encode()
                server = {'command': 'uvx', 'args': ['--from', 'basic-memory', 'basic-memory', 'mcp']}
                if agent == 'codex': server = dict(server, type='stdio')
                output[prefix + ('/mcp.json' if agent == 'codex' else '/.mcp.json')] = (json.dumps({'mcpServers': {'basic-memory': server}}, indent=2) + '\n').encode()
            output[prefix + "/INSTALLATION.json"] = (json.dumps(dict(kit, agent=agent), ensure_ascii=False, indent=2) + "\n").encode()
            exports[agent].append({"name": kit["id"], "source": "./" + prefix, "description": kit["name"]})
    for agent, target in (("codex", ".agents/plugins/marketplace.json"), ("claude", ".claude-plugin/marketplace.json")):
        value = {"name": "agent-intelliforge", "owner": {"name": "Mak-GIBA"}, "plugins": exports[agent]}
        if agent == "codex":
            for item in value["plugins"]: item["source"] = {"source": "local", "path": item["source"]}
        output[target] = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assembled-source", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--package-resources", action="store_true")
    args = parser.parse_args()
    assembled = assembled_sources(args.assembled_source)
    expected = build_outputs(assembled)
    block = '# intelliforge-manifest:begin\n' + '\n'.join(summary(kit) for kit in definitions(ROOT).values()) + '\n# intelliforge-manifest:end\n'
    for name in ('install_all.sh', 'install_all.ps1', 'intelliforge.py'):
        original = (ROOT / name).read_text(encoding='utf-8')
        original = re.sub(r'^# intelliforge-manifest:begin\n.*?^# intelliforge-manifest:end\n', '', original, flags=re.M | re.S)
        if original.startswith('#!'):
            first, rest = original.split('\n', 1); expected[name] = (first + '\n' + block + rest).encode()
        else: expected[name] = (block + original).encode()
    package = ROOT / "src/agent_intelliforge/resources"
    targets = {ROOT / key: value for key, value in expected.items() if not key.startswith("resources/")}
    for key, value in expected.items():
        if key.startswith("resources/"): targets[ROOT / "tools/intelliforge" / key] = value
    from source_manifest import snapshot
    targets[ROOT/'tools/intelliforge/source-manifest.json'] = (json.dumps({
        'schema_version':1, 'sources':snapshot(ROOT), 'outputs':{
            path.relative_to(ROOT).as_posix():hashlib.sha256(data).hexdigest() for path,data in targets.items()}},
        indent=2, sort_keys=True) + '\n').encode()
    for directory in (ROOT/'plugins', ROOT/'tools/intelliforge/resources/runtime'):
        for name in files_under(directory):
            if directory/name not in targets:
                raise SystemExit('Unexpected generated file; preserve/review it before rebuilding: '+str(directory/name))
    for path, data in targets.items():
        if args.check:
            if not path.is_file() or path.read_bytes() != data: raise SystemExit("Stale distribution: " + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    if args.package_resources:
        if package.exists(): shutil.rmtree(package)
        package.mkdir(parents=True)
        for pattern in ("install_*.sh", "install_*.ps1"):
            for script in ROOT.glob(pattern): shutil.copy2(script, package / script.name)
        for directory in ("tools", "plugins", ".agents", ".claude-plugin"):
            shutil.copytree(ROOT / directory, package / directory, ignore=shutil.ignore_patterns(
                "__pycache__", "node_modules", "*.pyc", "evaluation*", "evals", "evidence", "resources"))
        # Runtime resources were excluded from the source tree copy above.
        shutil.copytree(ROOT / "tools/intelliforge/resources", package / "tools/intelliforge/resources", dirs_exist_ok=True)
    print(f"{'Checked' if args.check else 'Built'} {len(targets)} distribution files; no kits installed.")


if __name__ == "__main__": main()
