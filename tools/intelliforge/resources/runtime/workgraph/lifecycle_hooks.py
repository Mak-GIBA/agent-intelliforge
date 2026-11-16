"""Manage native hook replacement without editing plugin files or unrelated TOML."""
import copy
import json
from pathlib import Path
import re

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # Compatibility for existing Python 3.10 installers.
    except ImportError:
        raise ValueError('Lifecycle hook configuration needs Python 3.11+ or tomli from requirements-export.txt') from None

EVENTS = (
    ('SessionStart', 'session-start', 'startup|resume|compact', 'session_start'),
    ('PreCompact', 'pre-compact', 'manual|auto', 'pre_compact'),
)
MANIFEST = 'managed-lifecycle.json'


def native_key(event):
    return f'codex@basic-memory:hooks/hooks.json:{event}:0:0'


def edit_enabled(text, key, value):
    """Edit one scalar, then prove the parsed TOML changed only that scalar."""
    before = tomllib.loads(text)
    expected = copy.deepcopy(before)
    node = expected.setdefault('hooks', {}).setdefault('state', {}).setdefault(key, {})
    if value is None:
        node.pop('enabled', None)
    else:
        node['enabled'] = value
    headers = list(re.finditer(r'^\s*\[(?!\[)[^\n]+\][ \t]*(?:#[^\n]*)?$', text, re.MULTILINE))
    matches = []
    for index, header in enumerate(headers):
        try:
            probe = tomllib.loads(header.group().strip() + '\n__workgraph_probe = true\n')
            if probe.get('hooks', {}).get('state', {}).get(key, {}).get('__workgraph_probe') is True:
                matches.append((header, headers[index+1].start() if index+1 < len(headers) else len(text)))
        except (ValueError, AttributeError):
            pass
    if len(matches) > 1:
        raise ValueError('Ambiguous lifecycle hook table; preserve and repair manually')
    if matches:
        header, end = matches[0]
        body = text[header.end():end]
        scalar = re.compile(r'^(\s*enabled[ \t]*=[ \t]*)(?:true|false)([ \t]*(?:#[^\n]*)?)$', re.MULTILINE)
        if scalar.search(body):
            body = scalar.sub(lambda m: m[1] + str(value).lower() + m[2] if value is not None else '', body)
        elif value is not None:
            body = '\nenabled = ' + str(value).lower() + body
        result = text[:header.end()] + body + text[end:]
    else:
        if key in before.get('hooks', {}).get('state', {}):
            raise ValueError('Inline lifecycle hook settings need a dedicated TOML table')
        result = text.rstrip() + '\n\n[hooks.state.' + json.dumps(key) + ']\n'
        if value is not None:
            result += 'enabled = ' + str(value).lower() + '\n'
    if tomllib.loads(result) != expected:
        raise ValueError('Lifecycle edit would change unrelated TOML; no files changed')
    return result


def prepare(codex, hooks, command):
    settings = codex / 'config.toml'
    text = settings.read_text(encoding='utf-8') if settings.exists() else ''
    parsed = tomllib.loads(text)
    manifest_path = codex / 'basic-memory-workgraph' / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {'version': 1, 'original_enabled': {}}
    if manifest.get('version') != 1 or not isinstance(manifest.get('original_enabled'), dict):
        raise ValueError('Invalid managed lifecycle settings; no files changed')
    original = manifest['original_enabled']
    allowed = {native_key(event[3]) for event in EVENTS}
    if any(key not in allowed or (value is not None and not isinstance(value, bool)) for key, value in original.items()):
        raise ValueError('Invalid original lifecycle enablement; no files changed')
    for event, verb, matcher, suffix in EVENTS:
        key = native_key(suffix)
        current = parsed.get('hooks', {}).get('state', {}).get(key, {}).get('enabled')
        if current is not None and not isinstance(current, bool):
            raise ValueError('Native hook enabled must be a boolean')
        original.setdefault(key, current)
        kept = []
        for group in hooks.get(event, []):
            entries = [entry for entry in group.get('hooks', []) if 'basic_memory_workgraph.py' not in entry.get('command', '')]
            if entries:
                kept.append({**group, 'hooks': entries})
        if original[key] is not False:
            kept.append({'matcher': matcher, 'hooks': [{
                'type': 'command', 'command': command + ' ' + verb,
                'timeout': 30, 'statusMessage': 'Loading bounded Basic Memory context' if event == 'SessionStart' else 'Checking bounded Basic Memory compaction context',
            }]})
            text = edit_enabled(text, key, False)
        hooks[event] = kept
    return [(settings, text), (manifest_path, json.dumps(manifest, indent=2) + '\n')]


def restore(codex):
    """Return native enablement edits; caller applies them before removing assets."""
    path = codex / 'basic-memory-workgraph' / MANIFEST
    settings = codex / 'config.toml'
    if not path.exists() or not settings.exists():
        return []
    manifest = json.loads(path.read_text(encoding="utf-8"))
    text = settings.read_text(encoding="utf-8")
    for key, original in manifest['original_enabled'].items():
        if key not in (native_key(event[3]) for event in EVENTS) or original not in (None, True, False):
            raise ValueError('Invalid original lifecycle state')
        current = tomllib.loads(text).get('hooks', {}).get('state', {}).get(key, {}).get('enabled')
        if current is False and original is not False:
            text = edit_enabled(text, key, original)
    return [(settings, text)]

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
