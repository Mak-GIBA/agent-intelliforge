"""Read kit definitions without executing installers or contacting their sources."""
from __future__ import annotations

import json
import os
from pathlib import Path

ORDER = ("workgraph", "ux-stack", "speckit", "github-pm", "design-research",
         "ecc", "office", "yomiyasu", "herdr")
MARKETPLACE = "agent-intelliforge"


class ForgeError(RuntimeError):
    """An actionable failure; never a request to overwrite unowned resources."""


def distribution_root() -> Path:
    """Prefer the checkout only when it is a real source distribution."""
    override = os.environ.get("INTELLIFORGE_SOURCE_ROOT")
    candidates = [Path(override)] if override else [Path(__file__).resolve().parents[2],
                                                  Path(__file__).parent / "resources"]
    for candidate in candidates:
        if (candidate / "install_all.sh").is_file() and (candidate / "tools").is_dir():
            return candidate.resolve()
    raise ForgeError("Distribution resources missing; run python tools/intelliforge/build.py before packaging.")


def safe_relative(value: str) -> Path:
    from pathlib import PurePosixPath
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ForgeError(f"Unsafe resource path: {value}")
    reserved = {'con','prn','aux','nul', *(f'com{i}' for i in range(1,10)), *(f'lpt{i}' for i in range(1,10))}
    if any(part.rstrip(' .') != part or part.split('.')[0].casefold() in reserved for part in path.parts):
        raise ForgeError(f'Not a portable resource path: {value}')
    return Path(*path.parts)


def definitions(root: Path | None = None) -> dict[str, dict]:
    root = root or distribution_root()
    result = {}
    for path in sorted((root / "tools").glob("*/kit.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        identity = value.get("id")
        if value.get("schema_version") != 1 or identity not in ORDER or identity in result:
            raise ForgeError(f"Invalid or duplicate kit definition: {path}")
        for required in ("name", "version", "legacy", "skills", "sources", "dependencies",
                         "destinations", "settings", "plugin"):
            if required not in value:
                raise ForgeError(f"Missing {required}: {path}")
        safe_relative(value["legacy"]["script"])
        for skill in value["skills"]:
            safe_relative(skill["source"])
        value = dict(value, definition=path.relative_to(root).as_posix())
        result[identity] = value
    missing = set(ORDER) - result.keys()
    if missing:
        raise ForgeError("Missing kit definitions: " + ", ".join(sorted(missing)))
    return {key: result[key] for key in ORDER}


def selection(value: list[str] | None, catalog: dict[str, dict]) -> list[dict]:
    ids = []
    for part in value or []:
        ids.extend(part.split(","))
    ids = ["yomiyasu" if item == "kotonoha" else item for item in ids]
    if any(not item or item not in catalog for item in ids):
        raise ForgeError("Unknown/empty kit selection; use intelliforge list.")
    return [kit for key, kit in catalog.items() if not ids or key in ids]


def source_path(root: Path, value: str) -> Path:
    path = root / safe_relative(value)
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ForgeError(f"Linked/escaping source resource: {value}")
    return path


def summary(kit: dict) -> str:
    """Generated comments share their facts with inspect and the execution plan."""
    components = ", ".join(skill["name"] for skill in kit["skills"]) or "CLI integration"
    lines = [f"Kit: {kit['id']} — {kit['name']}", f"Skills: {components}"]
    lines += ["Source: " + item["url"] + " (" + item["revision"] + ")" for item in kit["sources"]]
    lines += ["Destination: " + item for item in kit["destinations"]]
    lines += ["Settings: " + ("; ".join(kit["settings"]) or "none")]
    lines += ["Edit: " + kit["definition"], "Inspect: intelliforge inspect --only " + kit["id"],
              "Regenerate: python tools/intelliforge/build.py"]
    return "\n".join("# " + line for line in lines)
