"""Small, hash-bound file ownership layer for the new optional install path."""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
import shutil
import tempfile
import uuid

from .catalog import ForgeError, safe_relative
from .portable import file_lock


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_path(path: Path) -> None:
    for part in (path, *path.parents):
        reparse = part.exists() and bool(getattr(part.lstat(), 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))
        if part.is_symlink() or reparse or (getattr(part, "is_junction", lambda: False)()):
            raise ForgeError(f"Linked destination is not managed: {part}")
        if part != path and part.exists() and not part.is_dir():
            raise ForgeError(f"Non-directory parent: {part}")


def atomic_write(path: Path, data: bytes) -> None:
    check_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".intelliforge-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def inventory(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        check_path(path)
        if path.is_file() and path.name != ".intelliforge.json":
            result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def verify(root: Path, owner: str) -> dict:
    check_path(root)
    marker = root / ".intelliforge.json"
    if not marker.is_file():
        raise ForgeError(f"Unmanaged destination; preserving it: {root}")
    value = json.loads(marker.read_text(encoding="utf-8"))
    if value.get("owner") != owner or value.get("files") != inventory(root):
        raise ForgeError(f"Edited or foreign destination; preserving it: {root}")
    return value


def replace_tree(root: Path, owner: str, files: dict[str, bytes]) -> Path | None:
    """Stage, backup and replace; restore the previous tree if commit fails."""
    check_path(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(root.parent / ("." + root.name + ".lock")):
        if root.exists():
            verify(root, owner)
        stage = Path(tempfile.mkdtemp(prefix="." + root.name + "-", dir=root.parent))
        backup = None
        try:
            folded = set()
            for name, data in files.items():
                relative = safe_relative(name)
                key = relative.as_posix().casefold()
                if key in folded: raise ForgeError('Case-colliding payload paths: ' + name)
                folded.add(key)
                if relative.name == ".intelliforge.json":
                    raise ForgeError("Payload cannot replace the ownership manifest")
                path = stage / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (stage / ".intelliforge.json").write_text(json.dumps(
                {"schema_version": 1, "owner": owner, "files": inventory(stage)},
                ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            if root.exists():
                backup = root.with_name(root.name + ".backup-" + uuid.uuid4().hex)
                root.rename(backup)
            try:
                stage.rename(root)
            except BaseException:
                if backup and not root.exists():
                    backup.rename(root)
                raise
            return backup
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def remove_tree(root: Path, owner: str) -> None:
    check_path(root)
    if not root.exists():
        return
    with file_lock(root.parent / ("." + root.name + ".lock")):
        verify(root, owner)
        shutil.rmtree(root)
