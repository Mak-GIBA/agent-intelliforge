"""Shared safety utilities for the locally installed office workbench."""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
from pathlib import Path
import signal
from agent_intelliforge import subprocess_bridge as subprocess
import tempfile

class OfficeError(RuntimeError):
    pass

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def absolute(value: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(value))))

def no_symlinks(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise OfficeError(f'Symlink is not an allowed managed path: {part}')

def paths() -> dict[str, Path]:
    home = absolute(os.environ.get('HOME', str(Path.home())))
    def xdg(name, fallback):
        raw = os.environ.get(name)
        if raw and not Path(raw).is_absolute():
            raise OfficeError(f'{name} must be an absolute path')
        return absolute(raw or fallback)
    return {
        'home': home,
        'data': xdg('XDG_DATA_HOME', home / '.local/share') / 'codex-office',
        'config': xdg('XDG_CONFIG_HOME', home / '.config') / 'codex-office/install.json',
        'skill': home / '.agents/skills/office-workbench',
        'launcher': home / '.local/bin/office-workbench',
        'codex': absolute(os.environ.get('CODEX_HOME', str(home / '.codex'))),
    }

def load_json(path: Path) -> dict:
    try:
        v = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise OfficeError(f'Cannot read JSON: {path}: {e}') from e
    if not isinstance(v, dict):
        raise OfficeError(f'Expected JSON object: {path}')
    return v

def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    no_symlinks(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        with contextlib.suppress(FileNotFoundError): os.unlink(name)

def new_file(path: Path, data: bytes, mode: int = 0o600) -> None:
    """Exclusive, atomic publication; never overwrite a source or an existing output."""
    no_symlinks(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.chmod(name, mode)
        os.link(name, path)   # Fails if target already exists, including hardlinks.
    except FileExistsError as e:
        raise OfficeError(f'Output already exists; choose a new path: {path}') from e
    finally:
        with contextlib.suppress(FileNotFoundError): os.unlink(name)

def run(argv: list[str], *, timeout: int = 180, env=None, cwd=None, check=True):
    """No shell. Kill the process group on timeout, not just the immediate child."""
    if not argv or any(not isinstance(x, str) for x in argv):
        raise OfficeError('Invalid command arguments')
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=err, start_new_session=True)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError): os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise OfficeError(f'Command timed out after {timeout}s: {Path(argv[0]).name}')
        limit = 12 * 1024 * 1024
        out.seek(0); err.seek(0)
        stdout = out.read(limit + 1); stderr = err.read(limit + 1)
        if len(stdout) > limit or len(stderr) > limit:
            raise OfficeError('Command output exceeded 12 MiB; narrow the requested range')
        result = subprocess.CompletedProcess(argv, proc.returncode,
                    stdout.decode('utf-8', errors='replace'), stderr.decode('utf-8', errors='replace'))
        if check and result.returncode:
            # Limit error output; never include full env or authentication credentials.
            raise OfficeError(f'{Path(argv[0]).name} exited {result.returncode}: {result.stderr[-2500:]}')
        return result

def office_env() -> dict[str, str]:
    return {**os.environ, 'OFFICECLI_SKIP_UPDATE': '1', 'OFFICECLI_NO_AUTO_RESIDENT': '1',
            'OFFICECLI_RESIDENT_FLUSH': 'each', 'PYTHONDONTWRITEBYTECODE': '1'}

@contextlib.contextmanager
def lock(path: Path):
    no_symlinks(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as e:
        raise OfficeError(f'Another operation may be active. Inspect, do not blindly delete: {path}') from e
    try:
        with os.fdopen(fd, 'w') as f: f.write(str(os.getpid()))
        yield
    finally:
        with contextlib.suppress(FileNotFoundError): path.unlink()

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
