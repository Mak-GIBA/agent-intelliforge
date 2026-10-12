"""Process-boundary adapter used by generated copies, never by legacy Codex.

Codex arguments pass through. Only explicit Claude runtimes translate role
execution. Windows shell/path conversions stay within the portable distribution.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess as native
import sys
import tempfile

from .portable import shell_command, native_command


def __getattr__(name):
    return getattr(native, name)


def adapt(argv):
    if isinstance(argv, (str, bytes)):
        return argv
    argv = [str(item) for item in argv]
    if not argv:
        return argv
    if os.environ.get("INTELLIFORGE_AGENT") == "claude" and Path(argv[0]).stem == "codex":
        # The bridge explicitly implements only the harness's execution protocol.
        return [sys.executable, "-m", "agent_intelliforge.provider", *argv[1:]]
    if os.name == "nt":
        if argv[0] in ("bash", "/bin/bash", "sh") and len(argv) > 2 and argv[1] == "-c":
            return shell_command(argv[2])
        if argv[0] == "/bin/true":
            return [sys.executable, "-c", "raise SystemExit(0)"]
        if Path(argv[0]).stem == "codex" and "sandbox" in argv:
            boundary = argv.index("--") if "--" in argv else None
            if boundary is not None:
                argv = argv[:boundary + 1] + adapt(argv[boundary + 1:])
        if argv[0] == "bash" and len(argv) > 1 and argv[1].endswith("gan-harness.sh"):
            return [sys.executable, str(Path(argv[1]).with_name("harness.py")), *argv[2:]]
    return native_command(argv)


def options(kwargs):
    kwargs = dict(kwargs)
    if (kwargs.get('text') or kwargs.get('universal_newlines')) and 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
    if kwargs.get('env') is not None and os.environ.get('INTELLIFORGE_AGENT'):
        # Preserve routing/package discovery through deliberately scrubbed test
        # environments. Never re-inject credentials or personal HOME settings.
        kwargs['env'] = dict(kwargs['env'])
        for name in ('INTELLIFORGE_AGENT','INTELLIFORGE_STATE_DIR','INTELLIFORGE_KIT_HOME','PYTHONPATH'):
            if name in os.environ: kwargs['env'][name] = os.environ[name]
    if os.name == "nt" and kwargs.pop("start_new_session", False):
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | native.CREATE_NEW_PROCESS_GROUP
    return kwargs


def run(argv, *args, **kwargs):
    return native.run(adapt(argv), *args, **options(kwargs))


def Popen(argv, *args, **kwargs):
    argv = adapt(argv)
    if os.name == 'nt' and kwargs.get('start_new_session') and isinstance(argv, list):
        argv = [sys.executable, str(Path(__file__).with_name('windows_job.py')), *argv]
    return native.Popen(argv, *args, **options(kwargs))


def call(argv, *args, **kwargs):
    return native.call(adapt(argv), *args, **options(kwargs))


def check_output(argv, *args, **kwargs):
    return native.check_output(adapt(argv), *args, **options(kwargs))


def check_call(argv, *args, **kwargs):
    return native.check_call(adapt(argv), *args, **options(kwargs))
