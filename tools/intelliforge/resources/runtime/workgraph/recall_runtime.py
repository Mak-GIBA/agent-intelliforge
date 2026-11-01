#!/usr/bin/env python3
"""Select a YAML-capable Python; provision only on an explicit installer path."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tempfile
import venv

REPAIR = 'Run bash install_basic_memory_workgraph.sh --update (without --dry-run) to repair the recall runtime.'
OWNER = 'basic-memory-workgraph/recall-runtime-v1'
PROBE = "import json,sys,yaml; assert yaml.safe_load('ok: true') == {'ok': True}; print(json.dumps({'python':sys.executable,'yaml':True,'yamlVersion':yaml.__version__}))"


def python_in(directory):
    return Path(directory) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def probe(python):
    """Do not resolve a venv's Python symlink into the system interpreter."""
    path = Path(python).expanduser().absolute()
    report = {'python': str(path), 'yaml': False}
    try:
        result = subprocess.run([str(path), '-I', '-c', PROBE], capture_output=True,
                                text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get('yaml') is True:
                report.update(yaml=True, yamlVersion=data.get('yamlVersion'))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return report


def current_report():
    report = {'python': sys.executable, 'yaml': False}
    try:
        import yaml
        if yaml.safe_load('ok: true') == {'ok': True}:
            report.update(yaml=True, yamlVersion=yaml.__version__)
    except (ImportError, AttributeError, ValueError):
        pass
    return report


def cli_path(value):
    executable = shutil.which(str(value))
    if not executable:
        raise ValueError('Recall CLI unavailable; check BM_RECALL_CLI')
    return Path(executable).resolve()


def cli_pythons(executable):
    parent = executable.parent
    return [parent / 'python', parent / 'python3', parent / 'python.exe']


def read_config(codex):
    path = Path(codex) / 'basic-memory-workgraph/config.json'
    config = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not isinstance(config, dict):
        raise ValueError('Recall configuration must be an object')
    return config


def select(config, codex, explicit_cli=None, explicit_python=None):
    """Read-only selection. Explicit choices fail closed; stale saved choices recover."""
    explicit_python = explicit_python or os.environ.get('BM_RECALL_PYTHON')
    explicit_cli = explicit_cli or os.environ.get('BM_RECALL_CLI')
    if explicit_python:
        report = probe(explicit_python)
        if not report['yaml']:
            raise ValueError('BM_RECALL_PYTHON requires a working Python with PyYAML. ' + REPAIR)
        if explicit_cli:
            cli_path(explicit_cli)
        return report
    candidates = []
    if explicit_cli:
        candidates.extend(cli_pythons(cli_path(explicit_cli)))
        # An explicitly chosen CLI must not silently select an unrelated runtime.
        for python in candidates:
            report = probe(python)
            if report['yaml']:
                return report
        raise ValueError('Selected Basic Memory environment requires PyYAML; set BM_RECALL_PYTHON explicitly. ' + REPAIR)
    if config.get('recallPython'):
        candidates.append(config['recallPython'])
    saved = config.get('recallCli')
    if isinstance(saved, list) and saved and isinstance(saved[0], str):
        try:
            candidates.extend(cli_pythons(cli_path(saved[0])))
        except ValueError:
            pass
    for name in ('bm', 'basic-memory'):
        executable = shutil.which(name)
        if executable:
            candidates.extend(cli_pythons(Path(executable).resolve()))
    candidates.extend([sys.executable, python_in(Path(codex) / 'basic-memory-workgraph/runtime')])
    seen = set()
    for python in candidates:
        path = str(Path(python).expanduser().absolute())
        if path in seen:
            continue
        seen.add(path)
        if not Path(path).is_file():
            continue
        report = probe(path)
        if report['yaml']:
            return report
    return None


def provision(directory, requirements):
    """Build in staging; never pip-install into user/system/Basic Memory environments."""
    directory = Path(directory).absolute()
    for path in (directory, *directory.parents):
        if path.is_symlink():
            raise ValueError('Linked recall runtime directory refused')
    marker = directory / '.workgraph-runtime.json'
    previous_marker = None
    if directory.exists():
        if marker.is_symlink() or not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")).get('owner') != OWNER:
            raise ValueError('Unmanaged recall runtime directory; preserve it and choose BM_RECALL_PYTHON')
        previous_marker = marker.read_bytes()
        report = probe(python_in(directory))
        if report['yaml']:
            return report
    directory.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.recall-runtime-', dir=directory.parent) as temporary:
        stage = Path(temporary) / 'venv'
        venv.EnvBuilder(with_pip=True).create(stage)
        result = subprocess.run([str(python_in(stage)), '-I', '-m', 'pip', 'install',
                                 '--disable-pip-version-check', '-r', str(requirements)],
                                capture_output=True, text=True, timeout=300)
        if result.returncode or not probe(python_in(stage))['yaml']:
            raise ValueError('Could not prepare recall PyYAML runtime; check network/venv support. Existing configuration was preserved.')
        (stage / marker.name).write_text(json.dumps({'owner': OWNER}) + '\n', encoding="utf-8", newline="\n")
        backup = None
        if directory.exists():
            if directory.is_symlink() or previous_marker is None or marker.is_symlink() or marker.read_bytes() != previous_marker:
                raise ValueError('Recall runtime directory changed during preparation; retry without overwriting it')
            backup = directory.with_name(directory.name + '.bak.' + Path(temporary).name)
            directory.rename(backup)
        try:
            stage.rename(directory)
            report = probe(python_in(directory))
            if not report['yaml']:
                raise ValueError('Prepared recall runtime failed validation')
            return report
        except (OSError, ValueError):
            if directory.exists():
                directory.rename(stage)
            if backup is not None:
                backup.rename(directory)
            raise


def ensure(codex, config=None, prepare=False, explicit_cli=None):
    report = select(read_config(codex) if config is None else config, codex, explicit_cli)
    if report is None and prepare:
        report = provision(Path(codex) / 'basic-memory-workgraph/runtime',
                           Path(__file__).with_name('requirements-export.txt'))
    return report


def reexec_if_needed(config, force_binding=False):
    """Repair an incorrectly launched helper, once, using only its saved runtime."""
    selected = config.get('recallPython')
    matches = selected and os.path.normcase(os.path.abspath(selected)) == os.path.normcase(os.path.abspath(sys.executable))
    if current_report()['yaml'] and (not force_binding or not selected or matches):
        return
    if selected and not os.environ.get('_WORKGRAPH_RECALL_REEXEC') and probe(selected)['yaml']:
        os.execve(str(Path(selected).expanduser().absolute()),
                  [str(selected), *sys.argv], {**os.environ, '_WORKGRAPH_RECALL_REEXEC': '1'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-dir', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    parser.add_argument('--prepare', action='store_true', help='Allow creation of a dedicated managed venv')
    args = parser.parse_args()
    try:
        report = ensure(args.codex_dir, prepare=args.prepare)
        if report is None:
            raise ValueError('No Python with PyYAML available. ' + REPAIR)
        print(report['python'])
    except (OSError, ValueError, subprocess.TimeoutExpired, subprocess.SubprocessError) as exc:
        parser.exit(1, 'Recall runtime: ' + str(exc) + '\n')



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__ == '__main__':
    main()
