"""Portable bindings for the unchanged Office workbench and pinned OfficeCLI."""
from __future__ import annotations

import json
import platform
from pathlib import Path
import sys
import venv

from .ownership import atomic_write, digest
from .runtime import checked, dependency_directory, load, python_in

WINDOWS_ASSETS = {
    'win-x64': '05dd712595690672ea1c220a516c0996a27f7c3e7f870a270c19d538e9fc04f3',
    'win-arm64': '617718b8fab036766c4e7f47f65aaac8e9297a7b9a168f8a4952f3bdc534d699',
}


def prepare(bundle, home):
    # Reuse the original HTTPS-only downloader, size limits and reference checks.
    sys.path.insert(0, str(bundle))
    installer = load(bundle / 'install.py', '_intelliforge_office_installer')
    versions = json.loads((bundle / 'versions.json').read_text(encoding='utf-8'))
    directory = dependency_directory(home, 'office')
    environment = directory / 'venv'; venv.EnvBuilder(with_pip=True).create(environment)
    python = python_in(environment)
    checked([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', *versions['python_requirements']], timeout=1200)
    import os
    if os.name == 'nt':
        machine = platform.machine().lower()
        key = 'win-arm64' if machine in ('arm64', 'aarch64') else 'win-x64' if machine in ('amd64', 'x86_64') else None
        if not key: raise ValueError('Unsupported Windows OfficeCLI architecture: ' + machine)
        expected = WINDOWS_ASSETS[key]
    else:
        key = installer.platform_key(); expected = versions['officecli_assets'][key]
    binary = directory / ('officecli.exe' if os.name == 'nt' else 'officecli')
    url = f'https://github.com/iOfficeAI/OfficeCLI/releases/download/v{versions["officecli_version"]}/officecli-{key}' + ('.exe' if os.name == 'nt' else '')
    installer.fetch_checked(url, binary, expected); binary.chmod(0o755)
    checked([str(binary), '--version'])
    manifest = {'owner': 'codex-office-workbench', 'kit_version': versions['kit_version'],
                'release': str(directory), 'python': str(python),
                'officecli': {'path': str(binary), 'sha256': expected},
                'features': {'assets_only': False, 'docling': False}}
    atomic_write(home / 'office-install.json', (json.dumps(manifest, indent=2) + '\n').encode())
    atomic_write(directory / 'pip-freeze.txt', checked([str(python), '-m', 'pip', 'freeze']).encode())
    return {'python': str(python), 'office_manifest': str(home / 'office-install.json')}


def bindings(namespace):
    import os
    home = Path(os.environ['INTELLIFORGE_KIT_HOME'])
    def paths():
        return {'home': Path.home(), 'data': home, 'config': home / 'office-install.json',
                'skill': home / 'bundle/skills/office-workbench', 'launcher': Path(sys.executable),
                'codex': home / 'disabled-host-settings'}
    namespace['paths'] = paths
    if os.name == 'nt':
        from .portable import capture
        from .subprocess_bridge import adapt
        import subprocess
        def run(argv, *, timeout=180, env=None, cwd=None, check=True):
            result = capture(adapt(argv), cwd=cwd, env=env, timeout=timeout, limit=12*1024*1024)
            if result['timed_out'] or result['truncated']:
                raise namespace['OfficeError']('Command exceeded its time/output limit')
            process = subprocess.CompletedProcess(argv, result['exit_code'], result['stdout'], result['stderr'])
            if check and process.returncode: raise namespace['OfficeError'](process.stderr[-1200:])
            return process
        namespace['run'] = run
