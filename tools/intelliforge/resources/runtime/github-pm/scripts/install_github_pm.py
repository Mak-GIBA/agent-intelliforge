#!/usr/bin/env python3
"""Install a Codex Skill and managed global AGENTS guidance. No hooks or token edits."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tarfile
import tempfile
import urllib.request
import uuid
import zipfile

NAME = "github-project-director"
VERSION = "1.3.1"
MANIFEST = ".github-pm-install.json"
SOURCE = Path(__file__).resolve().parents[1] / "skills" / NAME


def safe_path(path: Path) -> Path:
    path = Path(os.path.abspath(path.expanduser()))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"Symlink destination is not supported: {part}")
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def members(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink inside Skill: {path}")
        if path.is_file() and path.name != MANIFEST:
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def load_owned(target: Path) -> dict | None:
    if not target.exists():
        return None
    if not target.is_dir() or not (target / MANIFEST).is_file():
        raise ValueError(f"Unmanaged path exists; refusing to overwrite: {target}")
    safe_path(target / MANIFEST)
    data = json.loads((target / MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("name") != NAME or not isinstance(data.get("files"), dict):
        raise ValueError("Invalid ownership manifest; restore it or choose another skills directory.")
    for name, sha in data["files"].items():
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or "\\" in name or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError("Unsafe manifest entry")
    members(target)  # Reject symlinks even in user-added files.
    return data



def backup_archive(target: Path) -> Path:
    # A ZIP cannot be discovered as another Skill. Never leave backup SKILL.md
    # directories inside ~/.agents/skills, even under a dot-prefixed name.
    backup = target.parent / f".{NAME}.backup-{uuid.uuid4().hex}.zip"
    try:
        with zipfile.ZipFile(backup, "x", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(target.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(target).as_posix())
    except BaseException:
        backup.unlink(missing_ok=True)
        raise
    return backup


GUIDE_BEGIN = b"<!-- github-project-director:begin -->"
GUIDE_END = b"<!-- github-project-director:end -->"


def codex_directory(value: Path | None = None) -> Path:
    return safe_path(value if value is not None else Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))


def read_optional(path: Path) -> bytes | None:
    safe_path(path)
    return path.read_bytes() if path.exists() else None


def selected_guidance(home: Path) -> Path:
    override = home / "AGENTS.override.md"
    content = read_optional(override)
    return override if content and content.strip() else home / "AGENTS.md"


def guidance_record(old: dict | None) -> dict | None:
    record = old.get("guidance") if old else None
    if record is None:
        return None  # v1.1 installations did not register global guidance.
    if (not isinstance(record, dict) or set(record) != {"home", "file", "sha256", "prefix", "created"}
            or not isinstance(record.get("home"), str) or not Path(record["home"]).is_absolute()
            or record.get("file") not in ("AGENTS.md", "AGENTS.override.md")
            or not isinstance(record.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
            or record.get("prefix") not in ("", "\n") or type(record.get("created")) is not bool):
        raise ValueError("Invalid global guidance ownership record")
    return record


def guidance_block(target: Path) -> bytes:
    # Encode the path as data, including literal newlines and quotation marks.
    location = json.dumps(str(target / "SKILL.md"), ensure_ascii=False)
    owner = hashlib.sha256(str(target).encode()).hexdigest()
    return (GUIDE_BEGIN.decode() + "\n<!-- owner: " + owner + " -->\n"
        "GitHubに関する依頼（Issue・PRの作成/編集/調査/レビュー、コメント、Projects、Actions、リリース等）では、\n"
        "作業前に github-project-director を読み、今回の依頼に該当する手順だけを適用する。\n"
        "日本語・英語の依頼、GitHub URL、会話中の対象から判断し、スキル名の明示は不要。\n"
        "「進捗を確認して」「残タスクを整理して」「今週の優先順位を見直して」「詰まっている作業は？」も、\n"
        "会話やリポジトリからGitHubが対象と分かれば適用する。英語の同等表現も対象。\n"
        "GitHubを出典として引用するだけの質問や、GitHub操作を伴わないローカル作業には適用しない。\n"
        "Issue・PR・コメントは開発者と非開発者が追える文章にし、目的・変更点・確認結果・次の行動を明確にする。\n"
        "起動と投稿は別。コメントの提案前に共有価値・既存記録との重複・依頼範囲を確認する。\n"
        "途中経過・再試行・個々のテスト成功は投稿せず、重要な変化をまとめる。定例は依頼または合意済み運用だけ。\n"
        "他の専門スキルと併用できる。適用は投稿・マージ等の権限を増やさず、依頼の範囲を広げない。\n"
        "Skill file (JSON-quoted absolute path): " + location + "\n" + GUIDE_END.decode() + "\n").encode()


def block_bounds(raw: bytes) -> tuple[int, int] | None:
    counts = raw.count(GUIDE_BEGIN), raw.count(GUIDE_END)
    if counts == (0, 0):
        return None
    if counts != (1, 1):
        raise ValueError("Malformed or duplicate GitHub guidance markers; repair before continuing")
    start, end = raw.index(GUIDE_BEGIN), raw.index(GUIDE_END) + len(GUIDE_END)
    if end <= start or (start and raw[start - 1:start] != b"\n") or raw[end:end + 1] not in (b"", b"\n"):
        raise ValueError("Malformed GitHub guidance block")
    return start, end + (raw[end:end + 1] == b"\n")


def plan_guidance(target: Path, old: dict | None, home_arg: Path | None,
                  force: bool, remove: bool = False) -> dict | None:
    record = guidance_record(old)
    if remove and not record:
        return None
    home = codex_directory(home_arg if home_arg is not None else Path(record["home"]) if record else None)
    if home == target or target in home.parents:
        raise ValueError("Global guidance directory must be outside the Skill directory")
    if record and home != Path(record["home"]):
        raise ValueError("Global guidance belongs to a different --codex-home; uninstall there before moving")
    path = home / record["file"] if record else selected_guidance(home)
    if not remove and record and selected_guidance(home) != path:
        raise ValueError("Global guidance is shadowed by another AGENTS file; uninstall then reinstall to relocate it")
    before = read_optional(path)
    raw = before or b""
    raw.decode("utf-8")  # Do not append to a file Codex cannot read as UTF-8.
    bounds = block_bounds(raw)
    if not record:
        # A second skills directory must not claim another installation's global rule.
        for name in ("AGENTS.md", "AGENTS.override.md"):
            other = read_optional(home / name) or b""
            if block_bounds(other):
                raise ValueError("Unowned global GitHub guidance exists; use its original installation")
        prefix = b"\n" if raw and not raw.endswith(b"\n") else b""
        body = guidance_block(target)
        after = raw + prefix + body
        record = {"home": str(home), "file": path.name, "sha256": hashlib.sha256(body).hexdigest(),
                  "prefix": prefix.decode(), "created": before is None}
    else:
        if not bounds:
            raise ValueError("Owned global guidance is missing; restore its block from backup before continuing")
        start, end = bounds
        body = raw[start:end]
        expected_owner = b"<!-- owner: " + hashlib.sha256(str(target).encode()).hexdigest().encode() + b" -->"
        if body.count(expected_owner) != 1:
            raise ValueError("Global guidance owner does not match this Skill directory")
        if hashlib.sha256(body).hexdigest() != record["sha256"] and not force:
            raise ValueError("Edited global guidance preserved; use --force for backed-up replacement/removal")
        if remove:
            if record["prefix"] and raw[max(0, start - 1):start] == b"\n":
                start -= 1
            after = raw[:start] + raw[end:]
            if not after and record["created"]:
                after = None
        else:
            body = guidance_block(target)
            after = raw[:start] + body + raw[end:]
            record = {**record, "sha256": hashlib.sha256(body).hexdigest()}
    return {"path": path, "before": before, "after": after, "record": record}


def atomic_bytes(path: Path, content: bytes | None) -> None:
    safe_path(path)
    if content is None:
        path.unlink(missing_ok=True)
        return
    fd, name = tempfile.mkstemp(prefix=".github-pm-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, (path.stat().st_mode & 0o777) if path.exists() else 0o644)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextlib.contextmanager
def installation_locks(target: Path, home: Path):
    locks = []
    try:
        for parent in (target.parent, home):
            parent.mkdir(parents=True, exist_ok=True)
            lock = parent / f".{NAME}.install-lock"
            if lock not in locks:
                lock.mkdir()
                locks.append(lock)
        yield
    finally:
        for lock in reversed(locks):
            lock.rmdir()


def publish(stage: Path, target: Path, change: dict | None, old: dict | None) -> None:
    """Publish both resources, retaining the old tree until both replacements succeed."""
    previous = None
    guide_written = False
    before_stat = change["path"].stat() if change and change["before"] is not None else None
    if change and read_optional(change["path"]) != change["before"]:
        raise ValueError("Global guidance changed during installation; retry after reviewing it")
    if old:
        backup = backup_archive(target)
        print(f"Previous Skill backup: {backup}")
    if change and change["before"] is not None:
        backup = change["path"].parent / f".{NAME}.backup-guidance-{uuid.uuid4().hex}.zip"
        with zipfile.ZipFile(backup, "x", zipfile.ZIP_DEFLATED) as archive:
            backup.chmod(0o600)
            archive.writestr(change["path"].name, change["before"])
        print(f"Previous global guidance backup: {backup}")
    try:
        if old:
            previous = target.parent.parent / f".{NAME}.previous-{uuid.uuid4().hex}"
            target.rename(previous)
        if change and change["before"] != change["after"]:
            atomic_bytes(change["path"], change["after"])
            guide_written = True
        stage.rename(target)
    except BaseException:
        # Restore the old Skill even if unrelated global edits prevent guidance rollback.
        try:
            if guide_written:
                if read_optional(change["path"]) != change["after"]:
                    raise RuntimeError("Global guidance changed during rollback; left untouched. Inspect the guidance backup.")
                atomic_bytes(change["path"], change["before"])
                if before_stat:
                    os.chmod(change["path"], before_stat.st_mode & 0o777)
                    os.utime(change["path"], ns=(before_stat.st_atime_ns, before_stat.st_mtime_ns))
        finally:
            if previous and not target.exists():
                previous.rename(target)
        raise
    if previous:
        shutil.rmtree(previous)


def run(args: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False,
                          env={**os.environ, "GH_PROMPT_DISABLED": "1", "GH_PAGER": "cat"})


def doctor(target: Path, hostname: str, codex_home: Path | None = None) -> int:
    result = {"skill": str(target), "installed": (target / "SKILL.md").is_file(),
              "version": None, "modified": [], "gh": False, "authenticated": False,
              "projects_cli": False, "codex": bool(shutil.which("codex")),
              "mcp_server_names": [], "note": "MCP presence is not authentication/tool-coverage proof."}
    if target.exists():
        data = load_owned(target)
        result["version"] = data.get("version")
        result["modified"] = [p for p, h in data["files"].items()
                              if not (target / p).is_file() or digest(target / p) != h]
    try:
        change = plan_guidance(target, load_owned(target), codex_home, False) if target.exists() else None
        registered = bool(target.exists() and guidance_record(load_owned(target)))
        result["guidance"] = {"registered": registered, "valid": registered and change is not None,
                              "path": str(change["path"]) if change else None,
                              "skill_exists": (target / "SKILL.md").is_file()}
    except (OSError, ValueError) as exc:
        result["guidance"] = {"registered": False, "valid": False, "error": str(exc)}
    gh = shutil.which("gh")
    if gh:
        result["gh"] = run([gh, "--version"]).returncode == 0
        result["authenticated"] = run([gh, "auth", "status", "--hostname", hostname]).returncode == 0
        result["projects_cli"] = run([gh, "project", "--help"]).returncode == 0
    codex = shutil.which("codex")
    if codex:
        try:
            raw = run([codex, "mcp", "list", "--json"])
            data = json.loads(raw.stdout) if raw.returncode == 0 else []
            if isinstance(data, dict):
                data = data.get("servers", [])
            if isinstance(data, list):
                result["mcp_server_names"] = [x["name"] for x in data
                    if isinstance(x, dict) and isinstance(x.get("name"), str)]
        except (ValueError, subprocess.TimeoutExpired):
            pass  # Never print raw config: it can contain environment credentials.
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["installed"] and not result["modified"] and result["authenticated"] and result["guidance"]["valid"] else 2


def download(url: str, limit: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "basic-memory-workgraph-github-pm"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Official release download exceeds size limit")
    return data


def gh_release(version: str | None) -> tuple[str, str, bytes]:
    """Download only the official cli/cli binary; verify its published checksum."""
    if version:
        if not re.fullmatch(r"v?\d+\.\d+\.\d+", version):
            raise ValueError("--gh-version must be X.Y.Z or vX.Y.Z")
        tag = "v" + version.removeprefix("v")
    else:
        data = json.loads(download("https://api.github.com/repos/cli/cli/releases/latest", 2_000_000))
        tag = data.get("tag_name", "")
        if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
            raise ValueError("Unexpected official GitHub CLI release tag")
    ver = tag[1:]
    system = {"Linux": "linux", "Darwin": "macOS"}.get(platform.system())
    arch = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine())
    if not system or not arch:
        raise ValueError("Automatic gh installation supports Linux/macOS amd64/arm64 only; use official OS packages.")
    stem = f"gh_{ver}_{system}_{arch}"
    filename = stem + (".tar.gz" if system == "linux" else ".zip")
    base = f"https://github.com/cli/cli/releases/download/{tag}"
    checksums = download(f"{base}/gh_{ver}_checksums.txt", 1_000_000).decode("utf-8")
    expected = None
    for line in checksums.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip("*") == filename:
            expected = fields[0]
    if not expected or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise ValueError("Binary not present in official checksum file")
    archive = download(f"{base}/{filename}", 100_000_000)
    if hashlib.sha256(archive).hexdigest() != expected.lower():
        raise ValueError("GitHub CLI checksum mismatch; nothing will be executed")
    name = stem + "/bin/gh"
    if system == "linux":
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as z:
            entry = z.getmember(name)
            if not entry.isfile() or entry.size > 200_000_000:
                raise ValueError("Unsafe gh archive member")
            binary = z.extractfile(entry).read()
    else:
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            entry = z.getinfo(name)
            if entry.file_size > 200_000_000:
                raise ValueError("Oversized gh binary")
            binary = z.read(entry)
    return ver, expected.lower(), binary


def install(target: Path, force: bool, dry_run: bool, with_gh: bool,
            bin_dir: Path, gh_version: str | None, codex_home: Path | None = None) -> None:
    source_files = members(SOURCE)
    if not {"SKILL.md", "agents/openai.yaml", "scripts/github_inspect.py", "references/native-operations.md",
            "references/planning-and-meetings.md", "references/writing-and-tracking.md"} <= source_files.keys():
        raise ValueError("Incomplete checkout; this installer requires the skills/ and scripts/ directories.")
    old = load_owned(target)
    if old and not force:
        print(f"SKIP: installed Skill preserved (including local edits): {target}")
        if with_gh and not shutil.which("gh"):
            print("Use --force --install-gh, or install gh with your OS package manager.")
        return
    unknown = set(members(target)) - set(old["files"]) if old else set()
    collisions = unknown & set(source_files)
    if collisions:
        raise ValueError("New package would overwrite user-added files: " + ", ".join(sorted(collisions)))
    change = plan_guidance(target, old, codex_home, force)
    need_gh = with_gh and not shutil.which("gh")
    gh_target = safe_path(bin_dir / "gh")
    if need_gh and gh_target.exists():
        raise ValueError(f"gh already exists outside PATH; add its directory to PATH: {gh_target}")
    print(json.dumps({"dry_run": dry_run, "skill": str(target), "action": "update" if old else "install",
                      "files": sorted(source_files), "preserve_user_files": sorted(unknown),
                      "gh": (gh_version or "official latest, resolved on apply") if need_gh else "reuse/no change",
                      "global_guidance": str(change["path"]),
                      "guidance_action": "update" if guidance_record(old) else "register",
                      **({"guidance_block": guidance_block(target).decode()} if dry_run else {}),
                      "untouched": ["hooks.json", "config.toml", "project AGENTS.md", "Basic Memory", "ECC", "GitHub data"]},
                     ensure_ascii=False, indent=2))
    if dry_run:
        return
    stage = None
    with installation_locks(target, Path(change["record"]["home"])):
        try:
            if load_owned(target) != old:
                raise ValueError("Skill changed during installation; retry after reviewing it")
            change = plan_guidance(target, old, codex_home, force)
            # Outside the skills discovery directory, but normally on the same filesystem.
            stage = Path(tempfile.mkdtemp(prefix=f".{NAME}.stage-", dir=target.parent.parent))
            if old:
                shutil.copytree(target, stage, dirs_exist_ok=True)
                for name, sha in old["files"].items():
                    p = stage / name
                    if name not in source_files and p.is_file() and digest(p) == sha:
                        p.unlink()
            for name in source_files:
                dest = stage / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() and not dest.is_file():
                    raise ValueError(f"File/directory conflict: {name}")
                shutil.copyfile(SOURCE / name, dest)
                dest.chmod(0o644)
            (stage / MANIFEST).write_text(json.dumps({"name": NAME, "version": VERSION, "files": source_files, "guidance": change["record"]}, indent=2) + "\n", encoding="utf-8", newline="\n")
            if need_gh:
                ver, sha, binary = gh_release(gh_version)
                bin_dir.mkdir(parents=True, exist_ok=True)
                # Finish the binary before publishing; link fails if a racing install exists.
                fd, temporary = tempfile.mkstemp(prefix=".gh-install-", dir=bin_dir)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(binary)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temporary, 0o755)
                    os.link(temporary, gh_target)
                finally:
                    Path(temporary).unlink(missing_ok=True)
                print(f"Installed official gh {ver}: {gh_target}; archive SHA256={sha}")
            publish(stage, target, change, old)
            stage = None
            print(f"Installed {NAME} {VERSION}: {target}")
            print(f"Registered global guidance: {change['path']}")
            if not shutil.which("gh") and not need_gh:
                print("SETUP REQUIRED: authenticate an existing GitHub MCP, or install gh (--install-gh) and run gh auth login.")
            print("Start a new Codex session. Say: $github-project-director このプロジェクトのIssue構成を見直して")
            print("You may append your own request after the Skill name. Natural-language selection also remains enabled.")
            print("No remote writes occurred. GitHub authentication/Projects permissions must be configured by the user.")
        finally:
            if stage and stage.exists():
                shutil.rmtree(stage)


def uninstall(target: Path, dry_run: bool, force: bool, codex_home: Path | None = None) -> None:
    old = load_owned(target)
    if not old:
        print("SKIP: not installed")
        return
    modified = [p for p, h in old["files"].items() if (target / p).exists() and digest(target / p) != h]
    if modified and not force:
        raise ValueError("Edited files preserved; use --force for backed-up removal: " + ", ".join(modified))
    change = plan_guidance(target, old, codex_home, force, remove=True)
    print(json.dumps({"uninstall": str(target), "dry_run": dry_run, "modified": modified,
                      "global_guidance": str(change["path"]) if change else None}))
    if dry_run:
        return
    stage = None
    home = Path(change["record"]["home"]) if change else codex_directory(codex_home)
    with installation_locks(target, home):
        try:
            if load_owned(target) != old:
                raise ValueError("Skill changed during uninstall; retry after reviewing it")
            change = plan_guidance(target, old, codex_home, force, remove=True)
            stage = Path(tempfile.mkdtemp(prefix=f".{NAME}.stage-", dir=target.parent.parent))
            shutil.copytree(target, stage, dirs_exist_ok=True)
            for name in old["files"]:
                (stage / name).unlink(missing_ok=True)
            (stage / MANIFEST).unlink()
            for directory in sorted((p for p in stage.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                with contextlib.suppress(OSError):
                    directory.rmdir()
            publish(stage, target, change, old)
            stage = None
            with contextlib.suppress(OSError):
                target.rmdir()
            print("Uninstalled owned Skill files and global guidance only; gh/auth/user files unchanged.")
        finally:
            if stage and stage.exists():
                shutil.rmtree(stage)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="No persistent writes and no dependency downloads")
    parser.add_argument("--force", action="store_true", help="Update/remove owned files only, after backup")
    parser.add_argument("--doctor", action="store_true", help="Read-only installation/auth diagnostics")
    parser.add_argument("--uninstall", action="store_true", help="Remove only this installer's files")
    parser.add_argument("--install-gh", action="store_true", help="If missing, install verified official gh binary (opt-in)")
    parser.add_argument("--gh-version", help="Pin optional gh download, e.g. X.Y.Z; never upgrades an existing gh")
    parser.add_argument("--skills-dir", type=Path, default=Path.home() / ".agents/skills")
    parser.add_argument("--codex-home", type=Path, help="Global guidance directory (CODEX_HOME or ~/.codex); existing ownership reused on update/removal")
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local/bin")
    parser.add_argument("--hostname", default="github.com", help="GitHub host for doctor; no implicit host switching")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ required")
    if args.gh_version and not args.install_gh:
        parser.error("--gh-version requires --install-gh")
    if args.doctor and (args.force or args.uninstall or args.install_gh):
        parser.error("--doctor is read-only; do not combine with mutations")
    if args.uninstall and args.install_gh:
        parser.error("--uninstall and --install-gh are incompatible")
    try:
        target = safe_path(args.skills_dir / NAME)
        if args.doctor:
            return doctor(target, args.hostname, args.codex_home)
        if args.uninstall:
            uninstall(target, args.dry_run, args.force, args.codex_home)
        else:
            install(target, args.force, args.dry_run, args.install_gh, safe_path(args.bin_dir), args.gh_version, args.codex_home)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__ == "__main__":
    raise SystemExit(main())
