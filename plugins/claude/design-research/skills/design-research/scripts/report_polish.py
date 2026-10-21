"""Whole-document writing before publication, bound to a frozen scientific review."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
from agent_intelliforge import subprocess_bridge as subprocess
import sys

from runtime import Blocked, atomic_bytes, atomic_json, sha256, regular_path
from execution_units import digest, unit
from report_document import body, body_hash, editable_blocks, substantive_signature


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


S = {'type': 'string'}
PATCH = obj({'status': {'type': 'string', 'enum': ['proposed', 'blocked']}, 'reason': S,
             'base_sha256': S, 'replacements': {'type': 'array', 'items': obj({'id': S, 'text': S})}})
REVIEW = obj({'status': {'type': 'string', 'enum': ['reviewed', 'blocked']}, 'reason': S,
              'base_sha256': S, 'accepted': {'type': 'boolean'},
              'issues': {'type': 'array', 'items': S}})


def resolve_entry(project):
    roots = [Path(project)/'.agents/skills', Path(project)/'.codex/skills',
             Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex')))/'skills',
             Path.home()/'.agents/skills', Path.home()/'.codex/skills']
    for name in ('kotonoha', 'yomiyasu'):
        for root in roots:
            path = root/name/'SKILL.md'
            if path.is_file():
                workflow = root/'yomiyasu/references/workflow.md'
                files = [path] + ([workflow] if workflow.is_file() else [])
                return {'name': name, 'path': str(path),
                        'files': [{'path': str(p), 'sha256': sha256(p)} for p in files],
                        'scripts': str(root/'yomiyasu/scripts'),
                        'runtime': str(root.parent/'.kotonoha-runtime/settings.json')}
    return None


def instructions(role):
    if role == 'report-writer':
        return ('Read writing_entry.path and its workflow, applying kotonoha (or the selected yomiyasu entry) '
                'to the ENTIRE draft as one document. Read all hashed input files. Preserve the report order and '
                'scientific content. Improve paragraph connections, clarity and natural Japanese once; do not '
                'summarize away mechanisms, conditions, negative results or uncertainty. Return only replacements '
                'for editable_blocks with their exact IDs and base_sha256. Omit unchanged blocks. No new headings, '
                'tables, code, numbers, claims, citations or adoption judgments. Inspect repair_issues if supplied. '
                'The parent owns snapshots and lint execution. Read files as needed, but use no network or '
                'installations and do not edit report/project files. Preserve the draft language; polish Japanese '
                'narrative only. Return status=proposed.')
    return ('Read the original WHOLE draft, candidate report and frozen dossier/review. Independently verify '
            'all altered passages in context: negation, cause, scope, certainty, comparisons, actor, temporal '
            'claims, numbers, sources, methods and adoption status. Evaluate actual reader understanding, '
            'not a word-count/keyword score. Reject invented detail, lost caveats or misleading conclusions. '
            'Return accepted and concrete issues, base_sha256 exactly as supplied, status=reviewed. '
            'Do not fix scientific records or silently accept differences. No network or report edits.')


def protected(text, state):
    # Ordered tokens catch exchanged values and references, not just a set equality.
    identities = set()
    for field in ('sources', 'claims', 'candidates', 'experiments'):
        identities.update(str(x['id']) for x in (state.get('dossier') or {}).get(field, []))
    identity = '|'.join(re.escape(x) for x in sorted(identities, key=len, reverse=True))
    pattern = r'!?\[[^\]]*\]\([^)]*\)|https?://[^\s)]+|<[^>]+>|\$[^$\n]+\$|`[^`]+`|[+-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?%?'
    if identity:
        pattern += r'|(?<![\w-])(?:' + identity + r')(?![\w-])'
    return re.findall(pattern, text)


def apply_patch(value, task, state):
    if value['base_sha256'] != task['base_sha256']:
        raise Blocked('Report polish: stale draft hash')
    indexed = {p['id']: p for p in task['editable_blocks']}; changes = {}; seen = set()
    for row in value['replacements']:
        key = row['id']; text = row['text']
        if key not in indexed or key in seen:
            raise Blocked('Report polish: unknown/duplicate paragraph ID')
        seen.add(key); previous = indexed[key]['text']
        if not text.strip() or protected(text, state) != protected(previous, state):
            raise Blocked('Report polish: protected number, ID, source, equation or code changed')
        if any(re.match(r'^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|[|>]|```|~~~|\$\$)', s) for s in text.splitlines()):
            raise Blocked('Report polish: narrative cannot change document structure')
        changes[key] = text
    result = task['body']
    for p in reversed(task['editable_blocks']):
        if p['id'] in changes:
            result = result[:p['start']] + changes[p['id']] + result[p['end']:]
    return result


def snapshot(path, text):
    raw = text.encode('utf-8')
    if path.exists() and path.read_bytes() != raw:
        raise Blocked('Report polish: immutable writing artifact changed: ' + path.name)
    if not path.exists():
        atomic_bytes(path, raw)
    return {'path': str(path), 'sha256': sha256(path)}


def lint(entry, before, after, directory, timeout):
    """Actual offline tool results are retained separately from scientific evidence."""
    output = directory/'lint.json'
    if output.exists():
        return json.loads(output.read_text('utf-8'))
    settings = Path(entry['runtime']); helper = Path(entry['scripts'])/'writing_lint.py'
    result = {'status': 'unavailable', 'reason': 'Writing lint runtime is not installed'}
    if settings.is_file() and helper.is_file():
        try:
            python = json.loads(settings.read_text('utf-8')).get('python', sys.executable)
            commands = [[python, str(helper), str(before)],
                        [python, str(helper), str(after), '--before', str(before)]]
            rows = []
            for command in commands:
                r = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
                rows.append({'argv': command, 'exit_code': r.returncode,
                             'stdout': r.stdout[-200000:], 'stderr': r.stderr[-20000:]})
            result = {'status': 'executed', 'results': rows,
                      'scope': 'Lint findings, not proof of readability or meaning preservation'}
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result = {'status': 'failed', 'reason': str(exc)}
    atomic_json(output, result)
    return result


def finish(state, workspace, run_dir, invoke):
    """Resume finalization alone; completed experiments and scientific reviews stay frozen."""
    from report import publish
    basis = state['report_finalization']
    if basis['science_sha256'] != substantive_signature(state):
        raise Blocked('Report polish: scientific review changed during finalization')
    current = state.get('report_polish', {})
    if current.get('status') in {'complete', 'skipped_unavailable', 'not_required'}:
        if current.get('science_sha256') != basis['science_sha256']:
            raise Blocked('Report polish: finalization signature changed')
        return
    language_sample = json.dumps([state['config']['brief'], state.get('dossier'), state.get('review')], ensure_ascii=False)
    if not re.search(r'[\u3040-\u30ff\u3400-\u9fff]', language_sample):
        state['report_polish'] = {'status': 'not_required', 'science_sha256': basis['science_sha256'],
                                  'reason': 'No Japanese narrative to polish'}
        return
    entry = resolve_entry(state['config']['project'])
    if not entry:
        state['report_polish'] = {'status': 'skipped_unavailable', 'science_sha256': basis['science_sha256'],
                                  'reason': 'kotonoha and yomiyasu are unavailable; no installation attempted'}
        atomic_json(run_dir/'state.json', state)
        return
    # Freeze the selected entry. A changed skill on resume must not certify an old edit.
    if current.get('writing_entry') and current['writing_entry'] != entry:
        raise Blocked('Report polish: writing skill changed; start a new report run')
    cycle = current.get('cycle', 0) + (current.get('status') == 'rejected')
    state['report_polish'] = {**current, 'status': 'draft', 'science_sha256': basis['science_sha256'],
                              'writing_entry': entry, 'cycle': cycle}
    publish(state, workspace, run_dir)
    draft = (workspace/'report.md').read_text('utf-8'); original = body(draft)
    signature = body_hash(original)
    directory = regular_path(run_dir/'writing'/signature/str(cycle)); directory.mkdir(parents=True, exist_ok=True)
    before = directory/'before.md'
    if before.exists():
        if current.get('before_sha256') and sha256(before) != current['before_sha256']:
            raise Blocked('Report polish: immutable draft file changed')
        draft = before.read_text('utf-8')
        if body_hash(body(draft)) != signature:
            raise Blocked('Report polish: immutable draft changed')
    snapshot(before, draft)
    state['report_polish']['before_sha256'] = sha256(before)
    base_task = {'draft': draft, 'body': original, 'base_sha256': signature,
                 'editable_blocks': editable_blocks(original), 'writing_entry': entry,
                 'science_sha256': basis['science_sha256'], 'repair_issues': []}
    def call(role, schema, task, validator, suffix):
        state['report_task'] = task; state['phase'] = role
        atomic_json(run_dir/'state.json', state)
        return unit(role, schema, state, workspace, run_dir, invoke, validator,
                    name=f'{role}-{cycle}-{suffix}')
    candidate = None
    try:
        for attempt in range(2):
            task = copy.deepcopy(base_task)
            def validate_patch(value, s):
                apply_patch(value, task, s)
            patch = call('report-writer', PATCH, task, validate_patch, str(attempt))
            candidate = apply_patch(patch, task, state)
            report = draft.replace('## 結論\n' + original, '## 結論\n' + candidate, 1)
            after = directory/f'after-{attempt}.md'; snapshot(after, report)
            lint_result = lint(entry, before, after, directory/str(attempt), state['config']['phase_timeout'])
            review_task = {**base_task, 'candidate_report': report, 'candidate_sha256': body_hash(candidate),
                           'lint': lint_result}
            def validate_review(value, _state):
                if value['base_sha256'] != signature or (value['accepted'] and value['issues']):
                    raise Blocked('Report polish: review has a stale hash or contradictory acceptance')
            checked = call('report-reviewer', REVIEW, review_task, validate_review, str(attempt))
            if checked['accepted']:
                if basis['science_sha256'] != substantive_signature(state):
                    raise Blocked('Report polish: scientific records changed')
                state['report_polish'].update(status='complete', base_sha256=signature,
                    approved_body='## 結論\n' + candidate + '\n\n',
                    artifacts={'before': str(before.relative_to(workspace)),
                               'after': str(after.relative_to(workspace)),
                               'lint': str((directory/str(attempt)/'lint.json').relative_to(workspace))},
                    artifact_hashes={'before': sha256(before), 'after': sha256(after),
                                     'lint': sha256(directory/str(attempt)/'lint.json')},
                    artifact_link_root='workspace',
                    review=checked)
                return
            base_task['repair_issues'] = checked['issues'] or [checked['reason']]
        state['report_polish']['status'] = 'rejected'
        raise Blocked('Report polish: final reader/meaning review rejected the draft after one repair')
    finally:
        state.pop('report_task', None)
        atomic_json(run_dir/'state.json', state)


def assert_artifacts(state, workspace):
    pol = state.get('report_polish', {})
    if pol.get('status') == 'complete':
        for name, value in pol['artifacts'].items():
            p = regular_path(Path(workspace)/value)
            if not p.is_file() or sha256(p) != pol['artifact_hashes'][name]:
                raise Blocked('Report polish: writing artifact changed: ' + name)

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
