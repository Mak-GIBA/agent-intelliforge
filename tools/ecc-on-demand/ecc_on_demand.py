#!/usr/bin/env python3
"""Keep native ECC installed, exposing five small on-demand skill entrypoints.

Python 3.11+, standard library only. Native Codex owns ECC's cache and updates.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import subprocess
import sys
import tempfile
import time
import tomllib
from urllib.parse import urlparse

OWNER = "basic-memory-workgraph/ecc-on-demand"
PLUGIN = "ecc@ecc"
ENTRIES = {
    "ecc-tdd": "tdd-workflow",
    "ecc-python": "python-patterns",
    "ecc-errors": "error-handling",
    "ecc-security": "security-review",
    "ecc-library": None,
}
MANAGER_DIR = "ecc-on-demand"
MCP_SERVERS = {
    "firecrawl": {"url": "https://mcp.firecrawl.dev/v2/mcp", "startup_timeout_sec": 60},
    "context7": {"command": "npx", "args": ["-y", "@upstash/context7-mcp@4.3.0"], "startup_timeout_sec": 60},
    "parallel-search": {"url": "https://search.parallel.ai/mcp", "startup_timeout_sec": 60},
    "playwright": {"command": "npx", "args": ["-y", "@playwright/mcp@0.0.83", "--headless", "--isolated"], "startup_timeout_sec": 60},
    "chrome-devtools": {"command": "npx", "args": ["-y", "chrome-devtools-mcp@1.10.1", "--headless", "--isolated", "--no-usage-statistics", "--no-performance-crux"], "env_vars": ["HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"], "startup_timeout_sec": 60},
    # Retain legacy names for ownership validation/restoration and explicit use.
    "sequential-thinking": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@2026.8.31"], "env": {"DISABLE_THOUGHT_LOGGING": "true"}, "startup_timeout_sec": 60},
    "cloudflare-docs": {"url": "https://docs.mcp.cloudflare.com/mcp", "startup_timeout_sec": 60},
}
RECOMMENDED_MCPS = ("firecrawl", "chrome-devtools")
# Registration is a workflow choice. The paired trials did not establish a
# general accuracy gain; explicit-only tools must stay explicit-only.
MCP_SELECTION_BASIS = {
    "firecrawl": "keyless hosted connection: rate-limited search, scrape and parse; crawl/map require authentication; not evaluated in the paired workflow trials",
    "context7": "conditional: unknown-library discovery and documentation access; tested answers/code tied, citation defect observed",
    "playwright": "conditional: interactive browser work; tested final outcomes tied, lower observed model/tool time",
    "chrome-devtools": "browser diagnosis: console/network inspection; tested outcomes tied, not a general accuracy gain",
    "parallel-search": "optional: alternative public search; no observed answer gain in the fixed tasks",
    "cloudflare-docs": "optional: Cloudflare-specific documentation; no observed answer gain in the fixed tasks",
    "sequential-thinking": "explicit-only: tested reasoning tied; default adoption rule not met",
}
MCP_PRESETS = {
    "recommended": RECOMMENDED_MCPS,
    "research": ("context7", "parallel-search"),
    "browser": ("playwright", "chrome-devtools"),
    "cloudflare": ("context7", "cloudflare-docs"),
    "none": (),
}


def mcp_selection(value) -> tuple[str, ...]:
    """Validate selections before any native command or configuration mutation."""
    names = value.split(",") if isinstance(value, str) else value
    if not isinstance(names, (list, tuple)) or any(not isinstance(n, str) or not n.strip() for n in names):
        raise ManagementError("MCP selection must contain names/presets separated by commas")
    names = [n.strip() for n in names]
    if "none" in names and len(names) != 1:
        raise ManagementError("MCP preset none cannot be combined with other selections")
    result = []
    for name in names:
        if name in MCP_PRESETS:
            result.extend(MCP_PRESETS[name])
        elif name in MCP_SERVERS:
            result.append(name)
        else:
            raise ManagementError(f"Unknown MCP selection: {name}; available: {', '.join(MCP_PRESETS)}; {', '.join(MCP_SERVERS)}")
    return tuple(dict.fromkeys(result))


def check_mcps(text: str, owned: dict) -> None:
    servers = tomllib.loads(text).get("mcp_servers", {})
    for name, record in owned.items():
        if (name not in MCP_SERVERS or text.count(record["block"]) != 1
                or servers.get(name) != record["config"]):
            raise ManagementError(f"Managed MCP changed; preserving it: {name}")


def add_mcps(text: str, owned: dict, selected=RECOMMENDED_MCPS) -> tuple[str, dict, dict]:
    """Append missing servers; preserve existing commands, credentials and opt-outs."""
    check_mcps(text, owned)
    servers = tomllib.loads(text).get("mcp_servers", {})
    selected = mcp_selection(selected)
    records = dict(owned)
    report = {name: "managed_retained" for name in owned if name not in selected}
    for name in selected:
        config = MCP_SERVERS[name]
        # Older Context7 names must not create a second connection.
        alias = "context7-mcp" if name == "context7" else name
        if name in servers or alias in servers:
            existing = servers.get(name, servers.get(alias))
            report[name] = "managed" if name in owned else "existing_disabled" if existing.get("enabled") is False else "existing_preserved"
            continue
        block = f'\n# {OWNER}:mcp:{name}:begin\n[mcp_servers.{name}]\n'
        for key, value in config.items():
            literal = ('{ ' + ', '.join(f'{json.dumps(k)} = {json.dumps(v)}' for k, v in value.items()) + ' }'
                       if isinstance(value, dict) else json.dumps(value))
            block += f'{key} = {literal}\n'
        block += f'# {OWNER}:mcp:{name}:end\n'
        text += block
        records[name] = {"block": block, "config": config}
        report[name] = "added"
    check_mcps(text, records)
    return text, records, report


class ManagementError(Exception):
    pass


class CatalogError(ManagementError):
    def __init__(self, code, message, *, target=None):
        super().__init__(message)
        self.code, self.target = code, target

    def detail(self):
        return {"code": self.code, "message": str(self),
                **({"target": self.target} if self.target else {}),
                "recovery": "Use refresh --dry-run, then refresh; use install_ecc.sh --apply for managed installation changes"}


def official_source(source: dict) -> bool:
    if source.get("sourceType") != "git":
        return False
    value = str(source.get("source", "")).strip()
    if value.casefold() == "affaan-m/ecc":
        return True
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.split(":", 1)[1]
    url = urlparse(value)
    return (url.hostname == "github.com" and url.scheme in ("https", "ssh")
            and url.path.rstrip("/").removesuffix(".git").casefold() == "/affaan-m/ecc")


def source_bytes(path: Path, root: Path) -> bytes:
    """Preserve lexical paths until every ancestor has passed the link check."""
    if not path.is_absolute() or not root.is_absolute() or ".." in path.parts or ".." in root.parts:
        raise CatalogError("source_unsafe", "ECC source paths must be absolute and bounded")
    try:
        path.relative_to(root)
    except ValueError:
        raise CatalogError("source_unsafe", "ECC original escapes its registered root") from None
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CatalogError("source_unsafe", "ECC original contains a symbolic link")
    if not path.is_file():
        raise CatalogError("source_missing", "ECC original is missing")
    return path.read_bytes()


def original_issue(row):
    try:
        data = source_bytes(Path(row["path"]), Path(row["plugin_root"]))
        if row.get("verification_issue"):
            return row["verification_issue"]
        if digest(data) != row["sha256"]:
            raise CatalogError("source_modified", "ECC original changed or missing; refresh its verified catalog")
    except (OSError, CatalogError) as error:
        return CatalogError(getattr(error, "code", "source_unreadable"), str(error), target=row["name"]).detail()
    return None


def source_observation(row):
    """A retry trigger, never a trusted document checksum."""
    try:
        return digest(source_bytes(Path(row["path"]), Path(row["plugin_root"])))
    except (OSError, CatalogError) as error:
        return getattr(error, "code", "source_unreadable")


def git_read(root, *arguments, deadline=None):
    remaining = 10 if deadline is None else deadline - time.monotonic()
    if remaining <= 0:
        raise CatalogError("catalog_unavailable", "ECC catalog verification timed out")
    try:
        result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True,
                                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, timeout=remaining)
    except (OSError, subprocess.TimeoutExpired):
        raise CatalogError("source_unverified", "Cannot verify the native ECC Git revision") from None
    if result.returncode:
        raise CatalogError("source_unverified", "Cannot verify the native ECC Git revision")
    return result.stdout


def native_identity(root, *, deadline=None):
    marker = source_bytes(root / ".codex-marketplace-install.json", root)
    metadata = json.loads(marker)
    if not official_source({"sourceType": metadata.get("source_type"), "source": metadata.get("source")}):
        raise CatalogError("source_unverified", "Native ECC source is not the official repository")
    revision = metadata.get("revision", "")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40,64}", revision):
        raise CatalogError("source_unverified", "Native ECC revision is unavailable")
    if git_read(root, "rev-parse", "HEAD", deadline=deadline).decode().strip() != revision:
        raise CatalogError("source_unverified", "ECC Git HEAD differs from the native installation revision")
    origin = git_read(root, "config", "--get", "remote.origin.url", deadline=deadline).decode().strip()
    if not official_source({"sourceType": "git", "source": origin}):
        raise CatalogError("source_unverified", "ECC Git origin differs from the official repository")
    return {"revision": revision, "marker_sha256": digest(marker)}


def git_tree(root, deadline=None):
    result = {}
    for entry in git_read(root, "ls-tree", "-rz", "HEAD", deadline=deadline).split(b"\0"):
        if not entry:
            continue
        metadata, filename = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        if kind == "blob" and mode in ("100644", "100755"):
            result[filename.decode()] = oid
    return result


def matches_git(data, oid):
    if not oid:
        return False
    constructor = hashlib.sha256 if len(oid) == 64 else hashlib.sha1
    return constructor(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == oid


def frontmatter(text, keys=("name", "description")):
    """Scalar metadata needed for native command wrappers; reject unknown syntax."""
    if not text.startswith("---\n"):
        return {}, text.strip()
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        raise CatalogError("source_unverified", "Unrecognized ECC source frontmatter")
    values = {}
    for line in parts[0].splitlines()[1:]:
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if not match or match[1] not in keys:
            continue
        value = match[2].strip()
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except ValueError:
                raise CatalogError("source_unverified", "Unrecognized command metadata") from None
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        if not isinstance(value, str) or value in ("|", ">", "|-", ">-"):
            raise CatalogError("source_unverified", "Unsupported command metadata format")
        values[match[1]] = value
    return values, parts[1].strip()


def prove_original(row, tree):
    root = Path(row["plugin_root"])
    path = Path(row["path"])
    raw = source_bytes(path, root)
    relative = path.relative_to(root).as_posix()
    metadata, _ = frontmatter(raw.decode("utf-8"), keys=("name",))
    if metadata.get("name", path.parent.name) != row["name"]:
        raise CatalogError("source_unverified", "Native ECC name differs from its document", target=row["name"])
    if matches_git(raw, tree.get(relative)):
        return digest(raw)
    prefix = ".codex-plugin/migrated-command-skills/"
    name = row["name"]
    if relative == prefix + name + "/SKILL.md" and name.startswith("source-command-"):
        command = name.removeprefix("source-command-")
        if not re.fullmatch(r"[\w-]+", command):
            raise CatalogError("source_unverified", "Unsupported migrated command name", target=name)
        source = "commands/" + command + ".md"
        original = source_bytes(root / source, root)
        if matches_git(original, tree.get(source)):
            fields, body = frontmatter(original.decode("utf-8"))
            description = fields.get("description", "")
            expected = ("---\nname: " + json.dumps(name, ensure_ascii=False)
                        + "\ndescription: " + json.dumps(description, ensure_ascii=False) + "\n---\n\n# " + name
                        + "\n\nUse this skill when the user asks to run the migrated source command `" + command
                        + "`.\n\n## Command Template\n\n" + body + "\n")
            if raw.decode("utf-8") == expected:
                return digest(raw)
    raise CatalogError("source_modified", "ECC original differs from its official Git content", target=row["name"])


def cache_signature(roots):
    """Changes trigger native lookup; directory names never choose a plugin."""
    values = []
    for parent in sorted({Path(root).parent for root in roots}, key=str):
        if parent.is_symlink():
            values.append([str(parent), "symlink"])
            continue
        for entry in sorted(parent.iterdir(), key=lambda p: p.name) if parent.is_dir() else []:
            marker = entry / ".codex-marketplace-install.json"
            try:
                value = digest(source_bytes(marker, entry)) if marker.is_file() else None
            except (OSError, CatalogError):
                value = "unreadable"
            values.append([str(entry), value])
    return digest(json.dumps(values).encode())


def make_snapshot(originals, *, deadline=None, allow_partial=False):
    roots = {}
    for row in originals:
        root = Path(row["plugin_root"])
        if str(root) in roots:
            continue
        try:
            identity = native_identity(root, deadline=deadline)
        except (CatalogError, OSError, ValueError):
            raise CatalogError("source_unverified", "Cannot verify the native ECC installation") from None
        tree = git_tree(root, deadline)
        manifest = source_bytes(root / ".codex-plugin/plugin.json", root)
        if not matches_git(manifest, tree.get(".codex-plugin/plugin.json")):
            raise CatalogError("source_modified", "Native ECC manifest differs from its Git revision")
        roots[str(root)] = {"identity": identity, "tree": tree}
    skills = []
    for row in originals:
        proof = roots[row["plugin_root"]]
        try:
            checksum = prove_original(row, proof["tree"])
            skills.append({**row, "sha256": checksum})
        except (CatalogError, OSError, UnicodeError) as error:
            if not allow_partial:
                raise
            issue = CatalogError(getattr(error, "code", "source_unverified"),
                                 "ECC original could not be verified against its official revision", target=row["name"])
            skills.append({**row, "sha256": None, "verification_issue": issue.detail(),
                           "verification_observation": source_observation(row)})
    for root, proof in roots.items():
        if proof["identity"] and native_identity(Path(root), deadline=deadline) != proof["identity"]:
            raise CatalogError("catalog_stale", "Native ECC changed while its catalog was being verified")
    return {"owner": OWNER, "version": 2, "skills": skills,
            "roots": {root: proof["identity"] for root, proof in roots.items()},
            "cache_signature": cache_signature(roots)}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".ecc-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def config_value(text: str) -> bool | None:
    value = tomllib.loads(text).get("plugins", {}).get(PLUGIN, {}).get("enabled")
    if value is not None and not isinstance(value, bool):
        raise ManagementError("ECC enabled must be a TOML boolean")
    return value


def table_path(header: str) -> tuple[str, ...] | None:
    """Use TOML itself to decode quoted table names; never split on dots."""
    if not header.lstrip().startswith("[") or header.lstrip().startswith("[["):
        return None
    try:
        tree = tomllib.loads(header + "\n__ecc_table_probe__ = true\n")
    except tomllib.TOMLDecodeError:
        return None
    parts = []
    while isinstance(tree, dict) and "__ecc_table_probe__" not in tree:
        if len(tree) != 1:
            return None
        key, tree = next(iter(tree.items()))
        parts.append(key)
    return tuple(parts)


def edit_enabled(text: str, value: bool | None) -> str:
    """Change one canonical plugin table without reserializing other settings.

    Inline/dotted plugin declarations are deliberately rejected before mutation.
    This avoids ambiguous edits or silently damaging unrelated TOML.
    """
    parsed = tomllib.loads(text)
    lines = text.splitlines(keepends=True)
    start = end = None
    for index, line in enumerate(lines):
        if re.match(r"^\s*\[", line):
            if start is not None:
                end = index
                break
            if table_path(line.rstrip("\r\n")) == ("plugins", PLUGIN):
                start = index
    if start is None:
        if PLUGIN in parsed.get("plugins", {}):
            raise ManagementError('Use a [plugins."ecc@ecc"] table; inline/dotted declarations are unsupported')
        if value is None:
            return text
        suffix = "" if not text or text.endswith("\n") else "\n"
        return text + suffix + f'\n[plugins."{PLUGIN}"]\nenabled = {str(value).lower()}\n'
    end = len(lines) if end is None else end
    key = re.compile(r'^(\s*(?:enabled|"enabled"|\'enabled\')\s*=\s*)(true|false)(\s*(?:#.*)?)(\r?\n)?$')
    for index in range(start + 1, end):
        match = key.match(lines[index])
        if match:
            if value is None:
                del lines[index]
            else:
                lines[index] = match[1] + str(value).lower() + match[3] + (match[4] or "")
            break
    else:
        if parsed.get("plugins", {}).get(PLUGIN, {}).get("enabled") is not None:
            raise ManagementError("Cannot safely locate ECC enabled assignment")
        if value is not None:
            if not lines[start].endswith("\n"):
                lines[start] += "\n"
            lines.insert(start + 1, f"enabled = {str(value).lower()}\n")
    result = "".join(lines)
    if config_value(result) != value:
        raise ManagementError("ECC configuration edit failed validation")
    before = parsed.get("plugins", {}).get(PLUGIN, {}).copy()
    after = tomllib.loads(result).get("plugins", {}).get(PLUGIN, {}).copy()
    before.pop("enabled", None)
    after.pop("enabled", None)
    parsed.get("plugins", {}).pop(PLUGIN, None)
    remaining = tomllib.loads(result)
    remaining.get("plugins", {}).pop(PLUGIN, None)
    # A newly created parent table may be empty after removing this plugin.
    if not parsed.get("plugins"):
        parsed.pop("plugins", None)
    if not remaining.get("plugins"):
        remaining.pop("plugins", None)
    if parsed != remaining or before != after:
        raise ManagementError("ECC configuration edit changed unrelated settings")
    return result


class Codex:
    def __init__(self, binary: str, home: Path, timeout: float = 30):
        self.binary, self.timeout = binary, timeout
        self.env = {**os.environ, "CODEX_HOME": str(home)}

    def skills(self, cwd: Path, enable_ecc: bool = False, *, deadline=None) -> dict:
        deadline = min(deadline or float("inf"), time.monotonic() + self.timeout)
        command = [self.binary]
        if enable_ecc:
            # CLI override keys are unquoted; quoted dotted CLI keys don't work.
            command += ["-c", "plugins.ecc@ecc.enabled=true"]
        command += ["app-server", "--stdio"]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, env=self.env, bufsize=0)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        buffer = b""

        def send(message):
            process.stdin.write((json.dumps(message) + "\n").encode())
            process.stdin.flush()

        def response(request_id):
            nonlocal buffer
            while time.monotonic() < deadline:
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        message = json.loads(line)
                    except ValueError:
                        continue
                    if message.get("id") == request_id:
                        if "error" in message:
                            raise ManagementError(f"Codex RPC failed: {message['error']}")
                        return message["result"]
                if selector.select(min(0.2, max(0, deadline - time.monotonic()))):
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        raise ManagementError("Codex app-server exited before responding")
                    buffer += chunk
            raise ManagementError("Codex app-server skills/list timed out")

        try:
            send({"id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": "ecc-on-demand", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True}}})
            response(1)
            send({"method": "initialized"})
            send({"id": 2, "method": "skills/list", "params": {
                "cwds": [str(cwd)], "forceReload": True}})
            rows = response(2).get("data", [])
            if len(rows) != 1:
                raise ManagementError("Unexpected Codex skills/list response")
            return rows[0]
        finally:
            selector.close()
            process.terminate()
            try:
                process.wait(timeout=max(0, min(3, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdin.close()
            process.stdout.close()

    def verify_entrypoints(self, commands: dict[str, list[str]], cwd: Path) -> list[str]:
        issues = []
        for name, command in commands.items():
            try:
                completed = subprocess.run(command, cwd=cwd, env=self.env, capture_output=True,
                                           text=True, timeout=self.timeout)
                if completed.returncode:
                    raise ManagementError(f"exit {completed.returncode}; check the bound Python and rerun install_ecc.sh --apply")
                result = json.loads(completed.stdout)
                paths = [row.get("path") for row in result.get("matches", [])] if "matches" in result else [result.get("path")]
                if not paths or any(not path or not Path(path).is_file() for path in paths):
                    raise ManagementError("original document not resolved")
            except (OSError, ValueError, ManagementError, subprocess.TimeoutExpired) as error:
                issues.append(f"Entrypoint {name}: {error}")
        return issues

    def update(self) -> None:
        for arguments in (["plugin", "marketplace", "upgrade", "ecc", "--json"],
                          ["plugin", "add", PLUGIN, "--json"]):
            # Only the native lifecycle writes original plugin/cache files.
            result = subprocess.run([self.binary, *arguments], env=self.env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, timeout=180)
            if result.returncode:
                raise ManagementError(f"Native ECC update failed ({result.returncode}): {result.stderr.strip()}")


def catalog(codex: Codex, cwd: Path, *, deadline=None, allow_partial=False, diagnostics=None) -> list[dict]:
    row = (codex.skills(cwd, enable_ecc=True) if deadline is None else
           codex.skills(cwd, enable_ecc=True, deadline=deadline))
    if row.get("errors"):
        if not allow_partial:
            raise CatalogError("catalog_unavailable", "Native ECC inventory contains skills/list errors")
        if diagnostics is not None:
            diagnostics.append(CatalogError("catalog_incomplete", "Native inventory reported loading errors; omitted originals remain unavailable").detail())
    skills = []
    for skill in row.get("skills", []):
        if skill.get("pluginId") != PLUGIN:
            continue
        path = Path(skill["path"]).absolute()
        root = next((parent for parent in path.parents
                     if (parent / ".codex-plugin/plugin.json").is_file()), None)
        if root is None or (not allow_partial and not path.is_file()):
            raise ManagementError(f"ECC original is missing or has no native manifest: {path}")
        manifest = json.loads((root / ".codex-plugin/plugin.json").read_text())
        if manifest.get("name") != "ecc":
            raise ManagementError(f"Unexpected plugin manifest: {root}")
        if not allow_partial:
            source_bytes(path, root)
        skills.append({"name": skill["name"].removeprefix("ecc:"),
                       "description": skill.get("description", ""),
                       "path": str(path), "skill_dir": str(path.parent),
                       "plugin_root": str(root), "version": manifest.get("version"),
                       "plugin_id": PLUGIN})
    if not skills:
        raise ManagementError(f"Native ECC catalog unavailable; skills/list errors: {row.get('errors', [])}")
    required = {name for name in ENTRIES.values() if name}
    missing = required - {skill["name"] for skill in skills}
    if missing and not allow_partial:
        raise ManagementError(f"ECC originals missing: {', '.join(sorted(missing))}")
    if len({s["name"] for s in skills}) != len(skills):
        raise CatalogError("catalog_unavailable", "Native ECC inventory has duplicate names")
    return skills


SEARCH_TERMS = {
    "python": ["python", "パイソン"],
    "testing": ["test", "tests", "testing", "テスト", "pytest", "vitest"],
    "api": ["api", "エンドポイント", "rest"],
    "database": ["db", "database", "データベース"],
    "migrations": ["migration", "migrations", "移行", "マイグレーション"],
    "docker": ["docker", "コンテナ", "compose"],
    "security": ["security", "セキュリティ", "認証", "秘密情報"],
    "error": ["error", "errors", "エラー", "例外", "再試行"],
    "e2e": ["e2e", "playwright", "ブラウザーテスト"],
}


LANGUAGE_ALIASES = {
    "python": ("python", "パイソン", "django", "pytest"),
    "typescript": ("typescript", "ts"), "javascript": ("javascript", "js", "nodejs"),
    "golang": ("golang", "go"), "rust": ("rust",),
    "cpp": ("cpp", "c++"), "csharp": ("csharp", "c#", "dotnet"),
    "java": ("java", "springboot", "quarkus"), "kotlin": ("kotlin",),
    "ruby": ("ruby", "rails"), "php": ("php", "laravel"),
    "swift": ("swift",), "fsharp": ("fsharp", "f#"),
    "dart": ("dart", "flutter"), "perl": ("perl",),
}


def query_languages(text: str) -> set[str]:
    return {name for name, aliases in LANGUAGE_ALIASES.items()
            if any(re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", text.casefold())
                   for alias in aliases)}


def project_languages(cwd: Path) -> set[str]:
    """The nearest manifest boundary avoids guessing a monorepo-wide language."""
    manifests = {"pyproject.toml": "python", "requirements.txt": "python", "setup.py": "python",
                 "tsconfig.json": "typescript", "package.json": "javascript", "go.mod": "golang",
                 "Cargo.toml": "rust", "pom.xml": "java", "build.gradle": "java",
                 "build.gradle.kts": "kotlin", "Gemfile": "ruby", "composer.json": "php",
                 "Package.swift": "swift", "pubspec.yaml": "dart", "CMakeLists.txt": "cpp"}
    for directory in (cwd, *cwd.parents):
        languages = {lang for file, lang in manifests.items() if (directory / file).is_file()}
        for pattern, lang in (("*.csproj", "csharp"), ("*.fsproj", "fsharp")):
            if any(directory.glob(pattern)): languages.add(lang)
        if languages: return languages
        if (directory / ".git").exists(): break
    return set()


def skill_languages(name: str) -> set[str]:
    # React/Next and shared frontend guidance serve both JS and TS projects.
    if set(re.findall(r"[a-z0-9]+", name)) & {"react", "nextjs", "frontend"}:
        return {"typescript", "javascript"}
    return query_languages(name)


def search_catalog(skills: list[dict], query: str, cwd: Path, limit: int = 5,
                   *, language: str | None = None) -> list[dict]:
    normalized = query.casefold()
    target = query_languages(language) if language else query_languages(query)
    if language and (len(target) != 1 or language.casefold().strip() not in
                     {alias for aliases in LANGUAGE_ALIASES.values() for alias in aliases}):
        raise ManagementError(f"Unknown language: {language}; use a supported language name")
    explicit = [s for s in skills if s["name"] == normalized.removeprefix("ecc:")]
    if explicit: return explicit
    target = target or project_languages(cwd)
    tokens = set(re.findall(r"[a-z0-9]+", normalized))
    if "tdd" in tokens: tokens.add("testing")
    for term, aliases in SEARCH_TERMS.items():
        if any((alias in normalized if not alias.isascii() else alias in tokens) for alias in aliases):
            tokens.add(term)
            tokens.difference_update(alias for alias in aliases if alias.isascii() and alias != term)
    tokens.update(query_languages(query))
    results = []
    for skill in skills:
        languages = skill_languages(skill["name"])
        if target and languages and not target & languages: continue
        name_tokens = set(re.findall(r"[a-z0-9]+", skill["name"].casefold()))
        description_tokens = set(re.findall(r"[a-z0-9]+", skill["description"].casefold()))
        score = 8 * len(tokens & name_tokens) + len(tokens & description_tokens)
        if score:
            score += 2 * len(target & languages)
            results.append({**skill, "score": score})
    return sorted(results, key=lambda s: (-s["score"], s["name"]))[:limit]


class Manager:
    def __init__(self, home: Path, skills_root: Path, codex: Codex, cwd: Path):
        self.home, self.skills_root, self.codex, self.cwd = home, skills_root, codex, cwd
        self.directory = home / MANAGER_DIR
        self.config = (home / "config.toml").resolve()
        self.state_path = self.directory / "state.json"
        self.installed_script = self.directory / "ecc_on_demand.py"

    @contextmanager
    def lock(self, *, deadline=None):
        self.directory.mkdir(parents=True, exist_ok=True)
        lockfile = self.directory / ".lock"
        if lockfile.is_symlink():
            raise ManagementError("ECC manager lock is a symbolic link")
        with lockfile.open("a") as stream:
            self.acquire_lock(stream, fcntl.LOCK_EX, deadline)
            yield

    @staticmethod
    def acquire_lock(stream, kind, deadline):
        if deadline is None:
            fcntl.flock(stream, kind)
            return
        while True:
            try:
                fcntl.flock(stream, kind | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CatalogError("catalog_busy", "ECC catalog lock deadline reached; try refresh after the current operation")
                time.sleep(min(.01, remaining))

    @contextmanager
    def read_lock(self, *, deadline=None):
        path = self.directory / ".lock"
        if path.is_symlink():
            raise ManagementError("ECC manager lock is a symbolic link")
        if not path.exists():
            yield  # Legacy installations may predate the shared lock.
            return
        with path.open("rb") as stream:
            self.acquire_lock(stream, fcntl.LOCK_SH, deadline)
            yield

    def state(self) -> dict | None:
        if not self.state_path.exists():
            return None
        state = json.loads(self.state_path.read_text())
        if state.get("owner") != OWNER or state.get("version") not in (1, 2):
            raise ManagementError("Unknown ECC manager state; refusing to modify it")
        if state["config_path"] != str(self.config) or state["skills_root"] != str(self.skills_root):
            raise ManagementError("ECC manager state belongs to different config/skill paths")
        entries = list(ENTRIES) if state["version"] == 2 else [n for n in ENTRIES if n != "ecc-tdd"]
        if state["version"] == 2 and (state.get("entrypoints") != entries or not isinstance(state.get("python_executable"), str) or not Path(state["python_executable"]).is_absolute()):
            raise ManagementError("Invalid ECC runtime/entrypoint state")
        allowed = {str(self.installed_script)} | {
            str(self.skills_root / name / relative)
            for name in entries for relative in ("SKILL.md", "agents/openai.yaml")}
        if state.get("catalog_snapshot") is True:
            allowed.add(str(self.directory / "catalog.json"))
        if set(state["files"]) != allowed:
            raise ManagementError("Unexpected managed file paths in state")
        return state

    def check_files(self, state: dict) -> None:
        for filename, expected in state["files"].items():
            path = Path(filename)
            if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
                raise CatalogError("managed_file_modified", f"Managed file missing or changed; preserving it: {path}")

    def _load_snapshot(self, *, locked=False, deadline=None):
        with nullcontext() if locked else self.read_lock(deadline=deadline or time.monotonic() + 30):
            state = self.state()
            if not state or not state.get("catalog_snapshot"):
                raise CatalogError("catalog_missing", "Refresh ECC originals using install_ecc.sh --apply from the repository copy")
            self.check_files(state)
            value = json.loads((self.directory / "catalog.json").read_text())
        if value.get("owner") != OWNER or value.get("version") not in (1, 2):
            raise CatalogError("catalog_invalid", "Invalid ECC catalog snapshot; rerun install_ecc.sh --apply")
        skills = value.get("skills")
        if not isinstance(skills, list) or not skills:
            raise CatalogError("catalog_invalid", "ECC catalog has no originals")
        required = ("name", "description", "path", "skill_dir", "plugin_root")
        for skill in skills:
            blocked = (isinstance(skill, dict) and value["version"] == 2
                       and isinstance(skill.get("verification_issue"), dict)
                       and skill["verification_issue"].get("target") == skill.get("name")
                       and isinstance(skill["verification_issue"].get("code"), str))
            if (not isinstance(skill, dict) or any(not isinstance(skill.get(k), str) for k in required)
                    or (not blocked and not re.fullmatch(r"[0-9a-f]{64}", str(skill.get("sha256", ""))))
                    or (blocked and skill.get("sha256") is not None)
                    or skill["skill_dir"] != str(Path(skill["path"]).parent)):
                raise CatalogError("catalog_invalid", "Invalid ECC original record")
        if (len({s["name"] for s in skills}) != len(skills)
                or {name for name in ENTRIES.values() if name} - {s["name"] for s in skills}):
            raise CatalogError("catalog_invalid", "ECC catalog snapshot is missing required originals or has duplicates")
        return state, value

    def read_snapshot(self) -> list[dict]:
        """Full read-only audit, also retained for older callers."""
        _, value = self._load_snapshot()
        for row in value["skills"]:
            issue = original_issue(row)
            if issue:
                raise CatalogError(issue["code"], issue["message"], target=row["name"])
        return [{key: val for key, val in row.items() if key != "sha256"} for row in value["skills"]]

    def refresh(self, *, dry_run=False, deadline=None):
        """Reconcile owned metadata only; never install, enable or upgrade ECC."""
        deadline = deadline or time.monotonic() + 30
        _, baseline = self._load_snapshot(deadline=deadline)
        try:
            diagnostics = []
            candidate = make_snapshot(catalog(self.codex, self.cwd, deadline=deadline, allow_partial=True,
                                              diagnostics=diagnostics),
                                      deadline=deadline, allow_partial=True)
            present = {r["name"] for r in candidate["skills"]}
            for old in baseline["skills"]:
                if old["name"] not in present:
                    candidate["skills"].append({**old, "sha256": None,
                        "verification_issue": CatalogError("source_unregistered", "Native ECC no longer lists this original", target=old["name"]).detail(),
                        "verification_observation": source_observation(old)})
            if diagnostics:
                candidate["inventory_issues"] = diagnostics
        except (OSError, ValueError, ManagementError) as error:
            if isinstance(error, CatalogError):
                raise
            raise CatalogError("catalog_unavailable", "Native ECC inventory could not be verified") from None
        if dry_run:
            warnings = [r["verification_issue"] for r in candidate["skills"] if r.get("verification_issue")]
            warnings.extend(candidate.get("inventory_issues", []))
            return {"status": "planned", "original_skills": len(candidate["skills"]), "changed_files": 0,
                    "warnings": warnings, "warning_count": len(warnings)}
        with self.lock(deadline=deadline):
            state, current = self._load_snapshot(locked=True)
            if current != baseline and current != candidate:
                raise CatalogError("catalog_stale", "Another operation committed a newer ECC catalog")
            if cache_signature(candidate["roots"]) != candidate["cache_signature"]:
                raise CatalogError("catalog_stale", "Native ECC cache changed before catalog commit")
            if any(original_issue(row) for row in candidate["skills"] if not row.get("verification_issue")):
                raise CatalogError("catalog_stale", "ECC originals changed before catalog commit")
            for root, identity in candidate["roots"].items():
                if native_identity(Path(root), deadline=deadline) != identity:
                    raise CatalogError("catalog_stale", "Native ECC changed before catalog commit")
            blocked = [r["verification_issue"] for r in candidate["skills"] if r.get("verification_issue")]
            blocked.extend(candidate.get("inventory_issues", []))
            if candidate == current:
                return {"status": "needs_attention" if blocked else "ready",
                        "original_skills": len(candidate["skills"]), "changed_files": 0,
                        **({"warnings": blocked, "warning_count": len(blocked)} if blocked else {})}
            previous = {r["name"]: r for r in current["skills"]}
            healthy_changed = any(not r.get("verification_issue") and r != previous.get(r["name"])
                                  for r in candidate["skills"])
            if blocked and not healthy_changed:
                raise CatalogError(blocked[0]["code"], blocked[0]["message"], target=blocked[0].get("target"))
            path = self.directory / "catalog.json"
            new_catalog = (json.dumps(candidate, ensure_ascii=False, indent=2) + "\n").encode()
            updated = {**state, "files": {**state["files"], str(path): digest(new_catalog)}}
            new_state = (json.dumps(updated, indent=2) + "\n").encode()
            originals = {p: (p.read_bytes(), p.stat().st_mode & 0o777) for p in (path, self.state_path)}
            touched = []
            try:
                for p, data in ((path, new_catalog), (self.state_path, new_state)):
                    touched.append(p)
                    atomic_write(p, data, originals[p][1])
            except BaseException:
                for p in reversed(touched):
                    atomic_write(p, *originals[p])
                raise
        return {"status": "needs_attention" if blocked else "ready", "original_skills": len(candidate["skills"]),
                "changed_files": 2, **({"warnings": blocked, "warning_count": len(blocked)} if blocked else {})}

    def _lookup_snapshot(self, *, refresh=True, name=None):
        deadline = time.monotonic() + 30
        _, value = self._load_snapshot(deadline=deadline)
        issues = [issue for row in value["skills"] if (issue := original_issue(row))]
        retry = any(original_issue(row) and (not row.get("verification_issue") or
                    source_observation(row) != row.get("verification_observation")) for row in value["skills"])
        roots = {row["plugin_root"] for row in value["skills"]}
        changed = value.get("cache_signature") not in (None, cache_signature(roots))
        unknown = name is not None and name not in {r["name"] for r in value["skills"]}
        warnings = []
        if refresh and (retry or changed or unknown):
            try:
                self.refresh(deadline=deadline)
                _, value = self._load_snapshot(deadline=deadline)
                issues = [issue for row in value["skills"] if (issue := original_issue(row))]
            except (ManagementError, OSError, ValueError) as error:
                _, value = self._load_snapshot(deadline=deadline)  # Reuse a concurrent verified commit.
                issues = [issue for row in value["skills"] if (issue := original_issue(row))]
                warnings.append(error.detail() if isinstance(error, CatalogError) else
                                CatalogError("refresh_failed", "ECC catalog refresh failed; verified saved originals remain available").detail())
        elif changed:
            warnings.append(CatalogError("catalog_stale", "Native ECC cache changed; automatic refresh is disabled").detail())
        return value["skills"], [*warnings, *value.get("inventory_issues", []), *issues]

    def resolve(self, name, *, refresh=True):
        name = name.removeprefix("ecc:")
        skills, warnings = self._lookup_snapshot(refresh=refresh, name=name)
        matches = [s for s in skills if s["name"] == name]
        if len(matches) != 1:
            if warnings:
                raise CatalogError("catalog_unavailable", "Cannot establish whether the requested ECC original is available", target=name)
            raise CatalogError("skill_not_found", "ECC skill not found; use search", target=name)
        issue = original_issue(matches[0])
        if issue:
            raise CatalogError(issue["code"], issue["message"], target=name)
        result = {k: v for k, v in matches[0].items() if k != "sha256"}
        if warnings:
            result.update(warnings=warnings[:5], warning_count=len(warnings))
        return result

    def search(self, query, *, language=None, limit=5, refresh=True):
        skills, warnings = self._lookup_snapshot(refresh=refresh)
        candidates = search_catalog(skills, query, self.cwd, len(skills), language=language)
        matches = [{k: v for k, v in row.items() if k != "sha256"}
                   for row in candidates if not original_issue(row)][:limit]
        if candidates and not matches:
            raise CatalogError("sources_unavailable", "Matching ECC originals could not be verified")
        result = {"matches": matches}
        if warnings:
            result.update(warnings=warnings[:5], warning_count=len(warnings))
        return result

    def payload(self) -> dict[Path, bytes]:
        source = Path(__file__).resolve()
        template_root = source.parent / "skills"
        if not template_root.is_dir():
            # Installed manager already owns its entrypoints; it can re-apply
            # configuration. Upgrading wrapper templates uses the repo copy.
            state = self.state()
            if state is None:
                raise ManagementError("Run apply from the repository copy first")
            self.check_files(state)
            if state["version"] != 2:
                raise ManagementError("Update ECC entrypoints using install_ecc.sh --apply from the new repository copy")
            return {Path(path): Path(path).read_bytes() for path in state["files"]}
        files = {self.installed_script: source.read_bytes()}
        for name in ENTRIES:
            for relative in ("SKILL.md", "agents/openai.yaml"):
                text = (template_root / name / relative).read_text()
                command = (shlex.quote(os.path.abspath(sys.executable)) + " -B " + shlex.quote(str(self.installed_script))
                           + " --codex-home " + shlex.quote(str(self.home))
                           + " --codex " + shlex.quote(self.codex.binary))
                text = text.replace("python3 {{MANAGER}}", command)
                files[self.skills_root / name / relative] = text.encode()
        return files

    def preflight(self) -> dict | None:
        """Check local ownership/configuration without starting Codex or writing."""
        state = self.state()
        self.payload()
        if state:
            self.check_files(state)
            for name in ENTRIES:
                if name not in (state.get("entrypoints") or [n for n in ENTRIES if n != "ecc-tdd"]) and ((self.skills_root / name).exists() or (self.skills_root / name).is_symlink()):
                    raise ManagementError(f"Existing unmanaged skill; refusing to overwrite: {name}")
        else:
            for name in ENTRIES:
                path = self.skills_root / name
                if path.exists() or path.is_symlink():
                    raise ManagementError(f"Existing unmanaged skill; refusing to overwrite: {path}")
            if self.installed_script.exists() or self.installed_script.is_symlink():
                raise ManagementError("Existing unmanaged ECC manager script")
        text = self.config.read_text() if self.config.exists() else ""
        edit_enabled(text, False)
        check_mcps(text, state.get("mcps", {}) if state else {})
        return state

    def selected_mcps(self, requested=None) -> tuple[str, ...]:
        if requested is None:
            requested = (self.state() or {}).get("selected_mcps", RECOMMENDED_MCPS)
        return mcp_selection(requested)

    def apply(self, baseline: dict | None = None, *, _locked: bool = False, mcps=None) -> dict:
        selected = self.selected_mcps(mcps)
        originals = catalog(self.codex, self.cwd)
        with nullcontext() if _locked else self.lock():
            state = self.preflight()
            files = self.payload()
            snapshot = make_snapshot(originals)
            files[self.directory / "catalog.json"] = (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode()
            original = self.config.read_bytes() if self.config.exists() else b""
            changed_text = edit_enabled(original.decode(), False)
            selected = self.selected_mcps(mcps)
            changed_text, records, mcp_report = add_mcps(changed_text, state.get("mcps", {}) if state else {}, selected)
            changed = changed_text.encode()
            state = state or {"owner": OWNER, "version": 1,
                              "config_path": str(self.config), "skills_root": str(self.skills_root),
                              "previous_enabled": baseline["previous_enabled"] if baseline else config_value(original.decode()),
                              "backup": baseline["backup"] if baseline else str(self.directory / f"config.before-ecc-on-demand.{time.time_ns()}.toml")}
            new_state = {**state, "version": 2, "entrypoints": list(ENTRIES), "catalog_snapshot": True,
                         "python_executable": (os.path.abspath(sys.executable) if (Path(__file__).parent / "skills").is_dir()
                                               else state["python_executable"]), "codex_binary": self.codex.binary,
                         "mcps": records, "selected_mcps": list(selected),
                         "files": {str(path): digest(data) for path, data in files.items()}}
            writes = dict(files)
            if not self.state_path.exists():
                writes[Path(state["backup"])] = Path(baseline["backup"]).read_bytes() if baseline else original
            writes[self.config] = changed
            writes[self.state_path] = (json.dumps(new_state, indent=2) + "\n").encode()
            snapshots = {path: (path.read_bytes(), path.stat().st_mode & 0o777)
                         if path.exists() else None for path in writes}
            new_directories = set()
            for path in writes:
                parent = path.parent
                while not parent.exists():
                    new_directories.add(parent)
                    parent = parent.parent
            touched = []
            try:
                for path, data in writes.items():
                    if path.exists() and path.read_bytes() == data:
                        continue
                    atomic_write(path, data, snapshots[path][1] if snapshots[path] else 0o600)
                    touched.append(path)
            except BaseException:
                for path in reversed(touched):
                    snapshot = snapshots[path]
                    if snapshot:
                        atomic_write(path, *snapshot)
                    else:
                        path.unlink(missing_ok=True)
                for directory in sorted(new_directories, key=lambda p: len(p.parts), reverse=True):
                    if directory.exists():
                        directory.rmdir()
                raise
        return {"status": "applied", "original_skills": len(originals),
                "mcps": mcp_report, "selected_mcps": list(selected),
                "mcp_selection_scope": "add_missing_only; existing connections and opt-outs preserved",
                "entrypoints": list(ENTRIES), "backup": state["backup"],
                "changed_files": len(touched), "new_session_required": True}

    def doctor(self) -> dict:
        issues = []
        state = self.state()
        if state is None:
            issues.append("ECC on-demand has not been applied")
        else:
            try:
                self.check_files(state)
            except ManagementError as error:
                issues.append(str(error))
        config = self.config.read_text() if self.config.exists() else ""
        try:
            check_mcps(config, state.get("mcps", {}) if state else {})
        except ManagementError as error:
            issues.append(str(error))
        servers = tomllib.loads(config).get("mcp_servers", {})
        mcp_report = {name: "configured" if servers.get(name, {}).get("enabled", True) and name in servers
                      else "disabled" if name in servers else "not_configured" for name in MCP_SERVERS}
        if "context7" not in servers and "context7-mcp" in servers:
            mcp_report["context7"] = "configured_legacy_alias" if servers["context7-mcp"].get("enabled", True) else "disabled"
        if config_value(config) is not False:
            issues.append("ECC native plugin is enabled or lacks an explicit false setting; run apply")
        row = self.codex.skills(self.cwd)
        active = [s for s in row.get("skills", []) if s.get("enabled", True)]
        active_ecc = [s for s in active if s.get("pluginId") == PLUGIN]
        if active_ecc:
            issues.append(f"ECC native skills still active: {len(active_ecc)}")
        for name in ENTRIES:
            expected = str(self.skills_root / name / "SKILL.md")
            if not any(s["name"] == name and s["path"] == expected for s in active):
                issues.append(f"On-demand entrypoint unavailable: {name}")
        if row.get("errors"):
            issues.append(f"skills/list errors: {row['errors']}")
        originals = []
        try:
            originals = catalog(self.codex, self.cwd)
        except ManagementError as error:
            issues.append(str(error))
        snapshot_issues = []
        saved = None
        if state:
            try:
                _, saved = self._load_snapshot()
                snapshot_issues = [issue for r in saved["skills"] if (issue := original_issue(r))]
                snapshot_issues.extend(saved.get("inventory_issues", []))
                roots = {r["plugin_root"] for r in saved["skills"]}
                if saved.get("cache_signature") not in (None, cache_signature(roots)):
                    snapshot_issues.append(CatalogError("catalog_stale", "Native ECC cache changed; run refresh").detail())
                if {(r["name"], r["path"]) for r in saved["skills"]} != {(r["name"], r["path"]) for r in originals}:
                    snapshot_issues.append(CatalogError("catalog_stale", "Native ECC inventory changed; run refresh").detail())
                issues.extend(f"{i.get('target', 'catalog')}: {i['message']}" for i in snapshot_issues)
            except (ManagementError, OSError, ValueError) as error:
                issues.append(str(error))
        entrypoint_verification = "not_checked"
        if state and not issues:
            if state["version"] != 2:
                issues.append("Upgrade the four-entry installation using install_ecc.sh --apply from the new repository copy")
            else:
                commands = {}
                try:
                    for name in ENTRIES:
                        text = (self.skills_root / name / "SKILL.md").read_text()
                        match = re.search(r"`([^`]+)`", text)
                        command = shlex.split(match[1]) if match else []
                        expected = [state["python_executable"], "-B", str(self.installed_script)]
                        if command[:3] != expected:
                            raise ManagementError(f"Unexpected runtime binding: {name}; rerun install_ecc.sh --apply")
                        commands[name] = [*command, "--no-refresh"]
                    failures = self.codex.verify_entrypoints(commands, self.cwd)
                    issues.extend(failures)
                    entrypoint_verification = "failed" if failures else "originals_resolved_via_installed_commands"
                except (OSError, ValueError, ManagementError) as error:
                    issues.append(str(error)); entrypoint_verification = "failed"
        return {"status": "ready" if not issues else "needs_attention", "issues": issues,
                "catalog_issues": snapshot_issues,
                "verified_saved_original_skills": sum(not original_issue(r) for r in saved["skills"]) if saved else 0,
                "python_executable": state.get("python_executable") if state else None,
                "entrypoint_verification": entrypoint_verification,
                "mcps": mcp_report, "mcp_verification": "configuration_only; startup and credentials not tested",
                "selected_mcps": list(self.selected_mcps()), "recommended_mcps": list(RECOMMENDED_MCPS),
                "active_skills": len(active), "active_native_ecc_skills": len(active_ecc),
                "available_original_skills": len(originals),
                "original_versions": sorted({s["version"] for s in originals if s["version"]}),
                "yomiyasu_available": any(s["name"] == "yomiyasu" for s in active),
                "github_project_director_available": any(s["name"] == "github-project-director" for s in active),
                "catalog_errors": row.get("errors", []), "new_session_required": True}

    def update(self) -> dict:
        with self.lock():
            state = self.state()
            if state is None:
                raise ManagementError("Run apply before update")
            self.check_files(state)
            failure = None
            try:
                self.codex.update()
                self.apply(_locked=True)
            except (ManagementError, subprocess.TimeoutExpired, OSError) as error:
                failure = str(error)
            finally:
                # Native plugin add can enable ECC even after a partial failure.
                text = self.config.read_text()
                updated = edit_enabled(text, False).encode()
                if updated != text.encode():
                    atomic_write(self.config, updated, self.config.stat().st_mode & 0o777)
        report = self.doctor()
        report["native_update"] = "failed" if failure else "completed"
        if failure:
            report["status"] = "needs_attention"
            report["issues"].append(failure)
        return report

    def restore(self) -> dict:
        with self.lock():
            state = self.state()
            if state is None:
                return {"status": "already_restored"}
            self.check_files(state)
            entries = state.get("entrypoints", [n for n in ENTRIES if n != "ecc-tdd"])
            for name in entries:
                root = self.skills_root / name
                expected = {root / "SKILL.md", root / "agents", root / "agents/openai.yaml"}
                extras = [p for p in root.rglob("*") if p not in expected]
                if extras:
                    raise ManagementError(f"Unexpected files in managed skill; preserving them: {extras}")
            text = self.config.read_text()
            check_mcps(text, state.get("mcps", {}))
            if config_value(text) is not False:
                raise ManagementError("ECC setting changed after apply; run apply before restore")
            check_mcps(text, state.get("mcps", {}))
            restored = edit_enabled(text, state["previous_enabled"]).encode()
            for record in state.get("mcps", {}).values():
                restored = restored.replace(record["block"].encode(), b"", 1)
            paths = [self.config, self.state_path, *(Path(name) for name in state["files"])]
            snapshots = {path: (path.read_bytes(), path.stat().st_mode & 0o777) for path in paths}
            try:
                for filename in state["files"]:
                    Path(filename).unlink()
                for name in entries:
                    (self.skills_root / name / "agents").rmdir()
                    (self.skills_root / name).rmdir()
                atomic_write(self.config, restored, snapshots[self.config][1])
                self.state_path.unlink()
            except BaseException:
                # Recover the complete installed state even if one unlink fails
                # after other entrypoints have already been removed.
                for path, (data, mode) in snapshots.items():
                    if not path.exists() or path.read_bytes() != data:
                        atomic_write(path, data, mode)
                raise
        return {"status": "restored", "ecc_enabled": state["previous_enabled"],
                "backup_retained": state["backup"], "new_session_required": True}


def main(argv=None) -> int:
    installed_defaults = {}
    adjacent_state = Path(__file__).resolve().parent / "state.json"
    if adjacent_state.is_file():
        try:
            candidate = json.loads(adjacent_state.read_text())
            if candidate.get("owner") == OWNER:
                installed_defaults = candidate
        except (ValueError, OSError):
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path,
                        default=Path(os.environ.get("CODEX_HOME", str(adjacent_state.parent.parent)
                                     if installed_defaults else str(Path.home() / ".codex"))))
    parser.add_argument("--skills-root", type=Path,
                        default=Path(installed_defaults.get("skills_root", Path.home() / ".agents/skills")))
    parser.add_argument("--codex", default=installed_defaults.get("codex_binary", "codex"))
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("apply", "doctor", "update", "restore", "search", "resolve", "refresh"):
        sub = subcommands.add_parser(name)
        sub.add_argument("--json", action="store_true")
        if name == "apply":
            sub.add_argument("--mcps", help="追加するMCPのプリセット/名前をカンマ区切りで選択。未指定は前回の選択、初回はrecommended")
        if name == "search":
            sub.add_argument("query")
            sub.add_argument("--language", help="対象言語。未指定時は検索語と近いプロジェクト設定から判断")
            sub.add_argument("--limit", type=int, choices=range(1, 6), default=5)
        if name == "resolve":
            sub.add_argument("name")
        if name in ("search", "resolve"):
            sub.add_argument("--no-refresh", action="store_true", help="保存済み一覧だけを読み、同期しない")
        if name == "refresh":
            sub.add_argument("--dry-run", action="store_true", help="正式一覧を検証し、保存せず差分を確認する")
    args = parser.parse_args(argv)
    try:
        home = args.codex_home.expanduser().resolve()
        skills_root = args.skills_root.expanduser().resolve()
        cwd = args.cwd.expanduser().resolve()
        codex = Codex(args.codex, home)
        manager = Manager(home, skills_root, codex, cwd)
        if args.command in ("search", "resolve"):
            if args.command == "search":
                result = manager.search(args.query, limit=args.limit, language=args.language, refresh=not args.no_refresh)
            else:
                result = manager.resolve(args.name, refresh=not args.no_refresh)
        elif args.command == "refresh":
            result = manager.refresh(dry_run=args.dry_run)
        elif args.command == "apply":
            result = manager.apply(mcps=args.mcps)
        else:
            result = getattr(manager, args.command)()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "resolve":
            print(result["path"])
        elif args.command == "search":
            for skill in result["matches"]:
                print(f"{skill['name']}\t{skill['description']}\n  {skill['path']}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if not args.json and result.get("warnings"):
            print(json.dumps({"status": "partial", "warnings": result["warnings"],
                              "warning_count": result["warning_count"]}), file=sys.stderr)
        return 1 if result.get("status") == "needs_attention" else 0
    except (ManagementError, OSError, ValueError, KeyError) as error:
        print(json.dumps({"status": "error", "error": str(error),
                          **(error.detail() if isinstance(error, CatalogError) else {})}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
