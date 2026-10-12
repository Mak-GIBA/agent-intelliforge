"""Verify that checked-in distribution resources match their editable sources."""
from pathlib import Path
import hashlib
import json


def snapshot(root: Path):
    result = {}
    for directory in (root/'tools',root/'src/agent_intelliforge'):
        for path in sorted(directory.rglob('*')):
            relative = path.relative_to(root).as_posix()
            parts = path.relative_to(root).parts
            if any(part in ('resources','node_modules','__pycache__','.git') or part.startswith('evaluation') or part=='evals' for part in parts): continue
            if path.name in ('source-manifest.json',) or path.suffix == '.pyc' or not path.is_file(): continue
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def verify(root: Path):
    expected = json.loads((root/'tools/intelliforge/source-manifest.json').read_text(encoding='utf-8'))
    if expected['sources'] != snapshot(root):
        raise RuntimeError('Editable sources changed. Run python tools/intelliforge/build.py before packaging.')
    for name, digest in expected['outputs'].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Stale generated distribution: ' + name)
