"""Python 3.10-compatible launcher; bind the manager to a checked 3.11+ runtime."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    home = Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex')))
    arguments = sys.argv[1:]
    for i, argument in enumerate(arguments):
        if argument == '--codex-home' and i+1 < len(arguments): home = Path(arguments[i+1])
        elif argument.startswith('--codex-home='): home = Path(argument.split('=',1)[1])
    candidate = os.environ.get('PYTHON_BIN')
    if not candidate:
        state = home.expanduser()/'ecc-on-demand/state.json'
        if state.is_file():
            data = json.loads(state.read_text(encoding='utf-8'))
            if data.get('owner') != 'basic-memory-workgraph/ecc-on-demand':
                raise ValueError('Unknown ECC state; preserving it')
            candidate = data.get('python_executable')
    candidate = candidate or 'python3'
    binary = shutil.which(candidate)
    if not binary:
        raise ValueError('ECC Python is unavailable. Set PYTHON_BIN to a Python 3.11+ executable and rerun install_ecc.sh --apply.')
    # Do not resolve symlinks: a venv executable must retain its environment.
    binary = os.path.abspath(binary)
    result = subprocess.run([binary, '-c', 'import sys; raise SystemExit(sys.version_info < (3,11))'], timeout=10)
    if result.returncode:
        raise ValueError('ECC requires Python 3.11+. Set PYTHON_BIN to its executable and rerun install_ecc.sh --apply.')
    os.execv(binary, [binary, '-B', str(Path(__file__).with_name('install_ecc.py')), *arguments])


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('ERROR: '+str(error), file=sys.stderr); raise SystemExit(2)
