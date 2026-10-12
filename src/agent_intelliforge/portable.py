"""OS primitives used only by the new distribution and portable runtime."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time
import sys
import errno
import tempfile
import shutil


def native_command(argv: list[str], *, windows: bool | None = None) -> list[str]:
    """Resolve known npm host shims without invoking cmd.exe on literal arguments."""
    windows = os.name == 'nt' if windows is None else windows
    if not windows or not argv:
        return list(argv)
    executable = shutil.which(argv[0]) or argv[0]
    path = Path(executable)
    if path.suffix.lower() not in ('.cmd', '.bat'):
        return [str(path), *argv[1:]]
    entries = {'codex': '@openai/codex/bin/codex.js',
               'claude': '@anthropic-ai/claude-code/cli.js'}
    entry = entries.get(path.stem.lower())
    script = path.parent / 'node_modules' / entry if entry else None
    node = shutil.which('node')
    if not node or script is None or not script.is_file():
        from .catalog import ForgeError
        raise ForgeError('Use a native CLI or its official npm layout; unknown batch shims are not executed: ' + path.name)
    return [node, str(script), *argv[1:]]


@contextmanager
def file_lock(path: Path, *, blocking: bool = True):
    from .ownership import check_path
    check_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            if not handle.read(1):
                handle.write(b"\0"); handle.flush()
            handle.seek(0)
            mode = msvcrt.LK_NBLCK
            while True:
                try:
                    msvcrt.locking(handle.fileno(), mode, 1)
                    break
                except OSError as error:
                    if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK): raise
                    if not blocking:
                        raise BlockingIOError("Lock already held") from error
                    time.sleep(0.05)
            try:
                yield handle
            finally:
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            try:
                yield handle
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def shell_command(command: str) -> list[str]:
    import shutil
    if os.name == "nt":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            raise RuntimeError("PowerShell is required on Windows")
        return [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]
    return ["bash", "-c", command]


def popen_options() -> dict:
    return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}


def terminate(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    if os.name == "nt":
        if process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    else:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            if sig == signal.SIGTERM:
                time.sleep(0.05)
    if process.poll() is None:
        process.wait(timeout=10)


def capture(argv: list[str], *, cwd, env, timeout: float, limit: int = 4 * 1024 * 1024, input_text: str | None = None) -> dict:
    """Threaded pipe draining works on Windows and bounds output on every OS."""
    if os.name == 'nt': argv = [sys.executable, str(Path(__file__).with_name('windows_job.py')), *native_command(argv)]
    prompt_input = tempfile.TemporaryFile() if input_text is not None else None
    try:
        if prompt_input is not None:
            prompt_input.write(input_text.encode('utf-8')); prompt_input.seek(0)
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=prompt_input if prompt_input is not None else subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, **popen_options())
    finally:
        if prompt_input is not None: prompt_input.close()
    pending = queue.Queue(maxsize=32)
    chunks = {"stdout": bytearray(), "stderr": bytearray()}
    def read(stream, name):
        try:
            while data := stream.read(65536):
                pending.put((name, data))
        finally:
            pending.put((name, None))
    readers = [threading.Thread(target=read, args=(stream, name), daemon=True)
               for name, stream in (("stdout", process.stdout), ("stderr", process.stderr))]
    for reader in readers:
        reader.start()
    started = time.monotonic()
    ended, timed_out, truncated = set(), False, False
    try:
        while len(ended) < 2:
            if time.monotonic() - started >= timeout and not timed_out:
                timed_out = True; terminate(process)
            try:
                name, data = pending.get(timeout=0.1)
            except queue.Empty:
                continue
            if data is None:
                ended.add(name); continue
            available = limit - len(chunks[name])
            chunks[name].extend(data[:max(0, available)])
            if len(data) > available:
                truncated = True; terminate(process)
        process.wait(timeout=10)
    finally:
        terminate(process)
        for stream in (process.stdout, process.stderr):
            stream.close()
        for reader in readers:
            reader.join(timeout=2)
    return {"exit_code": process.returncode, "timed_out": timed_out, "truncated": truncated,
            **{name: data.decode("utf-8", "replace") for name, data in chunks.items()}}
