#!/usr/bin/env python3
"""Audit saved outcomes in the parent's isolated scratch root; never regenerate them."""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import mean

B = Path('docs/codex-yomiyasu/evidence/study-2026-10-11')
F = Path('tools/codex-yomiyasu/evaluation-v200')
ART = Path('experiments/artifacts')
ARMS = ['baseline', 'a', 'b', 'c']
Q = ['paragraph', 'naturalness', 'reader_fit']
CONTRACT_SHA = '5131f1a304337549e1edf26354dace3d33116b61eeb27ca0b3083c61b0170537'
TASKS_SHA = '756c6c3409ad6db0451b78365bbf260c5f727c6281f1852c75f2473a3be90149'
HASHES = {}
PROGRESS = {}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def read(path):
    path = Path(path)
    require(not path.is_absolute() and '..' not in path.parts, 'non-relative input path')
    data = path.read_bytes()
    HASHES[path.as_posix()] = digest(data)
    return data


def load(path):
    return json.loads(read(path))


def save(name, data):
    ART.mkdir(parents=True, exist_ok=True)
    (ART / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def initial():
    c = load(B / 'research-inputs/capture.json')
    original = load(B / 'contract.json')
    require(original == c['contract'], 'capture/original contract mismatch')
    require(original['arms'] == ARMS and original['repeats'] == 2, 'candidate/repeat mismatch')
    tasks = [{'id': t['id'], 'input': {'genre': t['genre'], 'instruction': t['instruction'], 'text': t['input']},
              'expected': {'must_keep': t['must_keep'], 'meaning_errors': [], 'requester_residue': [],
                           'minimum_each_quality_score': 3}} for t in original['tasks']]
    require(digest(canonical(tasks)) == TASKS_SHA, 'frozen task inputs/labels mismatch')
    return c, tasks


def grid(c, group):
    rows = c['native'] if group == 'native' else c['outputs'][group]
    tasks = [f'N{i}' for i in range(1, 9)] if group == 'native' else (
        [f'W{i:02d}' for i in range(1, 13)] if group == 'writing' else [f'H{i}' for i in range(1, 7)])
    arms = ARMS if group != 'holdout' else ['baseline', 'c']
    repeats = [1, 2] if group == 'writing' else [1]
    keys = [(r['task'], r['arm'], r['repeat']) for r in rows]
    require(len(keys) == len(set(keys)), group + ': duplicate trial')
    require(set(keys) == {(t, a, r) for t in tasks for a in arms for r in repeats}, group + ': coverage mismatch')
    return sorted(rows, key=lambda r: (r['task'], r['arm'], r['repeat']))


def receipts(c, group, selected=None):
    result = []
    for snapshot in grid(c, group):
        if selected is not None and snapshot['task'] not in selected:
            continue
        name = f"{snapshot['task']}-{snapshot['arm']}-{snapshot['repeat']}.json"
        path = B / group / name
        require(snapshot['receipt_file'] == path.as_posix(), 'receipt locator mismatch')
        raw = load(path)
        require(HASHES[path.as_posix()] == snapshot['receipt_sha256'], 'receipt hash mismatch: ' + name)
        for key in ['status', 'elapsed_seconds', 'prompt_sha256', 'output', 'usage', 'task', 'arm', 'repeat', 'job_id']:
            require(key in raw and raw[key] == snapshot[key], name + ': ' + key + ' mismatch')
        for key in ['tools', 'error']:
            if key in snapshot:
                require(raw.get(key) == snapshot[key], name + ': ' + key + ' mismatch')
        require(raw['job_id'] == name[:-5], 'job identity mismatch')
        require(re.fullmatch(r'[0-9a-f]{64}', raw['prompt_sha256']) is not None, 'invalid stored prompt hash')
        require(isinstance(raw['status'], str) and raw['status'], 'missing outcome status')
        if raw['status'] == 'completed':
            require(isinstance(raw['output'], str) and raw['output'].strip(), 'missing completed final output')
        if raw['status'] == 'timeout':
            require(raw['output'] is None, 'timeout unexpectedly has a final output')
        result.append({'task_id': raw['task'], 'candidate_id': raw['arm'], 'trial_id': str(raw['repeat']),
                       'output': raw['output'], 'receipt_file': path.as_posix(),
                       'receipt_sha256': HASHES[path.as_posix()], 'receipt': raw})
    PROGRESS[group] = result
    return result


def rating_index(ratings):
    result = {}
    for rating in ratings:
        name = rating['output_file']
        require(name not in result, 'duplicate rating output_file: ' + name)
        require(isinstance(rating['meaning_errors'], list) and isinstance(rating['requester_residue'], list), 'invalid rating findings')
        require(isinstance(rating['evidence'], str) and rating['evidence'].strip(), 'missing grading rationale')
        for key in Q:
            require(type(rating[key]) is int and 1 <= rating[key] <= 4, 'invalid quality score')
        result[name] = rating
    return result


def grades(c, group, records):
    by_name = {Path(r['receipt_file']).name: r for r in records}
    jobs = load(B / (group + '-grade-jobs.json'))
    units = load(B / 'writing-smaller-review-units.json') if group == 'writing' else None
    mapped, provenance, history = {}, {}, []
    for path in sorted((B / (group + '-grades')).glob('*.json')):
        raw = load(path)
        match = re.fullmatch(r'([BU])(\d+)', path.stem)
        require(match is not None, 'unknown grading unit')
        label, index = match.group(1), int(match.group(2)) - 1
        schedule = units['units'] if label == 'U' else jobs
        require(0 <= index < len(schedule), 'grading unit missing from schedule')
        names = schedule[index]
        require(all(name in by_name for name in names), 'unknown output in review unit')
        history.append({'path': path.as_posix(), 'sha256': HASHES[path.as_posix()], 'unit_output_files': names, 'receipt': raw})
        if raw['status'] != 'completed':
            require(not raw.get('ratings'), 'failed grading unit has ratings')
            continue
        local = rating_index(raw['ratings'])
        require(len({r['id'] for r in raw['ratings']}) == len(raw['ratings']), 'duplicate unit-local rating ID')
        completed = {name for name in names if by_name[name]['receipt']['status'] == 'completed'}
        require(set(local) == completed, 'completed review unit rating coverage mismatch: ' + path.name)
        for name, rating in local.items():
            m = re.fullmatch(r'X(\d+)', rating['id'])
            require(m is not None and 1 <= int(m.group(1)) <= len(names), 'invalid unit-local rating ID')
            require(name not in mapped, 'completed output regraded or duplicate rating: ' + name)
            mapped[name] = rating
            provenance[name] = {'path': path.as_posix(), 'sha256': HASHES[path.as_posix()], 'local_id': rating['id']}
    require(mapped == rating_index(c['ratings'][group]), 'capture/original ratings mismatch')
    completed = {name for name, r in by_name.items() if r['receipt']['status'] == 'completed'}
    require(set(mapped) == completed, 'missing completed-output rating or rating on a failed generation')
    missing_units = [f'B{i+1:02d}' for i in range(len(jobs)) if not (B / (group + '-grades') / f'B{i+1:02d}.json').exists()]
    return mapped, provenance, {'receipts': history, 'scheduled_original_units_without_saved_receipt': missing_units,
                                'smaller_unit_reason': units['reason'] if units else None}


def attach(records, ratings, provenance):
    for r in records:
        name = Path(r['receipt_file']).name
        completed = r['receipt']['status'] == 'completed'
        grade = ratings.get(name)
        require((grade is not None) == completed, 'outcome/rating availability mismatch: ' + name)
        quality = {k: grade[k] for k in Q} if grade else None
        passed = completed and not grade['meaning_errors'] and not grade['requester_residue'] and all(grade[k] >= 3 for k in Q)
        r['values'] = {'delivered_pass': int(passed)}
        r['grading_evidence'] = {
            'receipt_file': r['receipt_file'], 'receipt_sha256': r['receipt_sha256'],
            'output_file': name, 'status': r['receipt']['status'], 'rating': grade,
            'rating_provenance': provenance.get(name), 'quality': quality,
            'formula': 'completed AND meaning_errors=[] AND requester_residue=[] AND each quality score>=3',
            'reason': 'conjunction satisfied' if passed else (
                'completed outcome fails at least one grading condition' if completed else 'no completed final outcome; language quality unobserved'),
            'prompt_text_independently_verified': None}
    return records


def timing_usage(records):
    result = {}
    for scope, subset in [('all_trials', records), ('completed_trials', [r for r in records if r['receipt']['status'] == 'completed'])]:
        times = [r['receipt']['elapsed_seconds'] for r in subset if isinstance(r['receipt'].get('elapsed_seconds'), (int, float)) and math.isfinite(r['receipt']['elapsed_seconds'])]
        usages = [r['receipt']['usage'] for r in subset if isinstance(r['receipt'].get('usage'), dict)]
        keys = sorted({k for u in usages for k in u})
        result[scope] = {'n': len(subset), 'elapsed_observed_n': len(times), 'elapsed_missing_n': len(subset)-len(times),
                         'mean_elapsed_seconds': mean(times) if times else None,
                         'usage_observed_n': len(usages), 'usage_missing_n': len(subset)-len(usages),
                         'reported_usage': {k: {'n': sum(k in u for u in usages),
                         'sum': sum(u.get(k, 0) for u in usages)} for k in keys}}
    return result


def summaries(records):
    result = {}
    for arm in sorted({r['candidate_id'] for r in records}):
        rows = [r for r in records if r['candidate_id'] == arm]
        rated = [r for r in rows if r['grading_evidence']['rating'] is not None]
        passing = sum(r['values']['delivered_pass'] for r in rows)
        result[arm] = {'attempted': len(rows), 'status_counts': dict(Counter(r['receipt']['status'] for r in rows)),
                       'completed_and_rated': len(rated), 'delivered_pass_count': passing,
                       'delivered_pass_fraction': passing / len(rows),
                       'completed_output_quality_pass_fraction': passing / len(rated) if rated else None,
                       'quality': {k: {'mean': mean(r['grading_evidence']['rating'][k] for r in rated) if rated else None,
                                      'distribution': dict(Counter(str(r['grading_evidence']['rating'][k]) for r in rated))} for k in Q},
                       'three_point_output_files': [r['receipt_file'] for r in rated if any(r['grading_evidence']['rating'][k] == 3 for k in Q)],
                       'reference_time_and_usage': timing_usage(rows)}
    return result


def envelope(scope):
    return {'contract_sha256': CONTRACT_SHA, 'scope': scope, 'input_sha256': dict(HASHES),
            'limitations': ['Saved outcomes only; no model regeneration or new independent language grader.',
                            'Same-model automatic ratings, fixed small tasks, ceiling effects, unbalanced grading contexts.',
                            'Stored prompt hashes can be compared; raw prompt texts are unavailable in this bundle.',
                            'Elapsed times and reported usage are reference values, not causal speed or billed-cost measurements.',
                            'Operational failures do not establish linguistic failure; adoption completeness is a post-hoc condition.']}


def writing(c, tasks):
    records = receipts(c, 'writing')
    ratings, provenance, history = grades(c, 'writing', records)
    attach(records, ratings, provenance)
    notes = load(B / 'execution-notes.json')
    audit = envelope('main_writing_audit')
    audit.update({'records': records, 'recalculated': summaries(records), 'grading_history': history,
                  'execution_notes_original': notes, 'audit_status': 'saved_outcomes_and_grades_verified_with_prompt_text_gap'})
    paired = {'contract_sha256': CONTRACT_SHA, 'tasks': tasks,
              'trials': [{k: r[k] for k in ['task_id', 'candidate_id', 'trial_id', 'output', 'values', 'grading_evidence']} for r in records]}
    save('writing-paired.json', paired)
    save('writing-audit.json', audit)


def protected(c, tasks):
    selected = {'W01', 'W02', 'W05', 'W06', 'W08', 'W10', 'W11', 'W12'}
    writing_rows = receipts(c, 'writing', selected)
    captured_grades = rating_index(c['ratings']['writing'])
    snapshot_provenance = {name: {'path': (B / 'research-inputs/capture.json').as_posix(),
                                 'sha256': HASHES[(B / 'research-inputs/capture.json').as_posix()],
                                 'scope': 'frozen rating snapshot; original grading receipts checked by audit-writing'} for name in captured_grades}
    attach(writing_rows, captured_grades, snapshot_provenance)
    holdout_tasks = load(B / 'holdout-tasks.json')
    require(holdout_tasks == c['holdout_tasks'], 'holdout task manifest mismatch')
    holdout_rows = receipts(c, 'holdout')
    ratings, provenance, history = grades(c, 'holdout', holdout_rows)
    attach(holdout_rows, ratings, provenance)
    task_lookup = {t['id']: t for t in c['contract']['tasks'] + holdout_tasks}
    extra = {'W05': ['田中様', '佐藤'], 'W06': ['REQ-12', 'REQ-13'], 'W08': ['[1]'],
             'W12': ['山田様', '鈴木'], 'H1': ['REQ-21'], 'H3': ['伊藤様', '高橋'],
             'H6': ['図2', '[^a]']}
    examples = []
    for r in writing_rows + holdout_rows:
        task = task_lookup[r['task_id']]
        before, after = task['input'], r['output']
        anchors = re.findall(r'\d+月\d+日|\d+(?:\.\d+)?(?:%|倍|日間|日|万円|時間|ページ)|\d+\.\d+', before)
        anchors += extra.get(r['task_id'], [])
        fence = chr(96) * 3
        anchors += re.findall(re.escape(fence) + r'[^\n]*\n.*?' + re.escape(fence), before, flags=re.S)
        anchors += re.findall(r'>[^\n]+', before)
        if r['task_id'] == 'W11':
            anchors += [x for x in task['must_keep'] if x.startswith('$') or 'max_retry' in x]
        if r['task_id'] == 'H5':
            anchors += ['enabled = false']
        if r['task_id'] == 'H6':
            anchors += [line for line in before.splitlines() if line.startswith('|') or line.startswith('[^a]:')]
        anchors = list(dict.fromkeys(anchors))
        probes = [{'anchor': a, 'present': None if after is None else a in after} for a in anchors]
        step_numbers = re.findall(r'(?m)^\s*(\d+)\.', before)
        retained_steps = None if after is None else re.findall(r'(?m)^\s*(\d+)\.', after) == step_numbers
        removed = {'W08': '[^note]:', 'W12': 'ご依頼に沿ってメール文面を作成しました。',
                   'H4': '<!-- 編集者へ：', 'H6': '[^b]:'}.get(r['task_id'])
        examples.append({**r, 'common_input': task, 'literal_probes': probes,
                         'specified_step_numbers': step_numbers, 'step_numbers_retained': retained_steps,
                         'specific_production_note_removed': None if after is None or removed is None else removed not in after,
                         'interpretation': 'Literal probes cover specified tokens, quotation/code/format only. Missing literals require review and are not an automatic semantic-error grade.'})
    report = envelope('protected_examples_and_supplementary_holdout')
    report.update({'examples': examples, 'holdout_recalculated': summaries(holdout_rows), 'holdout_grading_history': history,
                   'literal_findings': [e['receipt_file'] for e in examples if any(p['present'] is False for p in e['literal_probes'])
                                        or e['step_numbers_retained'] is False or e['specific_production_note_removed'] is False]})
    supplement = envelope('supplementary_holdout_excluded_from_frozen_primary_tasks')
    supplement.update({'holdout_task_manifest': holdout_tasks, 'paired_outputs': holdout_rows, 'recalculated': summaries(holdout_rows),
                       'not_a_primary_evaluation_export': True})
    save('protected-examples.json', report)
    save('holdout-paired.json', supplement)


def native(c, tasks):
    manifest = load(F / 'frozen-sources.json')
    require(manifest == c['contract']['source_hashes'], 'frozen-source manifest mismatch')
    excluded_cache = []
    for relative, expected in manifest['files'].items():
        if '__pycache__' in Path(relative).parts and relative.endswith('.pyc'):
            excluded_cache.append({'path': relative, 'declared_sha256': expected,
                                   'reason': 'Historical non-instruction cache; not distributed as a project input.'})
            continue
        require(digest(read(F / relative)) == expected, 'frozen source content mismatch: ' + relative)
    records = receipts(c, 'native')
    jobs = load(B / 'native-jobs.json')
    require(len(jobs) == len(records) and {(j['task'], j['arm'], j['repeat']) for j in jobs}
            == {(r['task_id'], r['candidate_id'], int(r['trial_id'])) for r in records}, 'native job manifest mismatch')
    verification = load(B / 'native-read-verification.json')
    snapshots = {Path(r['receipt_file']).name: r for r in c['native']}
    require(set(verification) == set(snapshots), 'native verification coverage mismatch')
    expected_routes = {'N1': ['yomiyasu', 'paragraph-writing', 'japanese-direct-writing'],
                       'N2': ['yomiyasu', 'paragraph-writing', 'japanese-direct-writing'],
                       'N3': ['paragraph-writing'], 'N4': ['paragraph-writing'],
                       'N5': ['japanese-direct-writing'], 'N6': ['japanese-direct-writing'], 'N7': [], 'N8': []}
    prompt_hashes = {}
    for r in records:
        raw, name = r['receipt'], Path(r['receipt_file']).name
        v = verification[name]
        require(v == snapshots[name]['verification'], 'captured native verification mismatch')
        expected = expected_routes[r['task_id']]
        require(raw['expected_reads'] == snapshots[name]['expected_reads'] == v['expected_reads'] == expected, 'saved expected route mismatch')
        require(raw['status'] == v['status'], 'native status mismatch')
        previous = prompt_hashes.setdefault(r['task_id'], raw['prompt_sha256'])
        require(previous == raw['prompt_sha256'], 'native candidates have differing stored prompt hashes')
        observed = {}
        for skill in ['yomiyasu', 'paragraph-writing', 'japanese-direct-writing']:
            relative = Path(r['candidate_id']) / 'assets' / ('SKILL.md' if skill == 'yomiyasu' else skill + '/SKILL.md')
            text = read(F / relative).decode('utf-8')
            matches = []
            mentions = []
            for index, event in enumerate(raw['tools']):
                command = event.get('command', '')
                if skill + '/SKILL.md' in command:
                    mentions.append(index)
                output = event.get('aggregated_output', '')
                if event.get('type') == 'command_execution' and event.get('exit_code') == 0 and event.get('status') == 'completed' and skill + '/SKILL.md' in command and isinstance(output, str) and text in output:
                    matches.append({'tool_index': index, 'command': command, 'exit_code': event['exit_code'],
                                    'content_sha256': digest(text.encode('utf-8')), 'tool_output_sha256': digest(output.encode('utf-8')),
                                    'matched_full_skill_text': text})
            observed[skill] = {'successful_full_reads': matches, 'commands_mentioning_skill_file': mentions}
        full_names = {s for s, evidence in observed.items() if evidence['successful_full_reads']}
        mentioned_names = {s for s, evidence in observed.items() if evidence['commands_mentioning_skill_file']}
        negative_control = not expected
        passed = raw['status'] == 'completed' and set(expected) <= full_names and (not negative_control or not mentioned_names)
        r.update({'expected_reads_from_saved_metadata': expected, 'full_read_evidence': observed,
                  'route_pass_recalculated': passed, 'negative_control': negative_control,
                  'unexpected_skill_file_commands': sorted(mentioned_names - set(expected)),
                  'duplicate_full_read_skills': sorted(s for s, ev in observed.items() if len(ev['successful_full_reads']) > 1),
                  'saved_verification': v, 'original_prompt_text_verified': None,
                  'route_intent_provenance': 'saved metadata and matching stored hashes; raw prompt text absent',
                  'internal_application_count': None})
        require(passed == raw['route_pass'] == snapshots[name]['route_pass'] == v['route_pass'], 'recalculated/saved native route mismatch: ' + name)
        for skill, reads in raw.get('reads', {}).items():
            require(skill in observed, 'unknown saved skill read')
            actual = observed[skill]['successful_full_reads']
            for saved in reads:
                require(any(all(saved.get(k) == event.get(k) for k in ['command', 'exit_code', 'content_sha256']) for event in actual),
                        'saved read not backed by successful command/full content')
    notice = load(B / 'native-setup-invalid/NOTICE.json')
    excluded = load(B / 'native-setup-invalid/N1-a-1.json')
    notes = load(B / 'execution-notes.json')
    report = envelope('native_full_read_audit')
    report.update({'records': records, 'frozen_sources_verified': True, 'excluded_historical_caches': excluded_cache,
                   'excluded_setup': {'notice': notice, 'receipt': excluded, 'included_in_comparison': False},
                   'execution_notes_original': notes, 'original_prompt_text_available': False,
                   'audit_status': 'full_reads_checked_route_intent_conditional_on_saved_metadata',
                   'recalculated': {arm: {'attempted': len([r for r in records if r['candidate_id'] == arm]),
                                         'route_pass': sum(r['route_pass_recalculated'] for r in records if r['candidate_id'] == arm),
                                         'status_counts': dict(Counter(r['receipt']['status'] for r in records if r['candidate_id'] == arm)),
                                         'completed_missing_required_read': [r['receipt_file'] for r in records if r['candidate_id'] == arm and r['receipt']['status'] == 'completed' and not r['route_pass_recalculated']],
                                         'negative_control_routes': sum(r['negative_control'] and r['route_pass_recalculated'] for r in records if r['candidate_id'] == arm)}
                                    for arm in ARMS}})
    save('native-audit.json', report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['writing', 'protected-holdout', 'native'], required=True)
    args = parser.parse_args()
    target = {'writing': 'writing-audit.json', 'protected-holdout': 'protected-examples.json', 'native': 'native-audit.json'}[args.mode]
    try:
        c, tasks = initial()
        {'writing': writing, 'protected-holdout': protected, 'native': native}[args.mode](c, tasks)
    except Exception as exc:
        save(target, {'contract_sha256': CONTRACT_SHA, 'scope': args.mode, 'status': 'invalid_audit',
                      'error_type': type(exc).__name__, 'error': str(exc), 'input_sha256': HASHES,
                      'verified_receipt_progress': PROGRESS, 'remaining_checks': 'unobserved; no successful measurement inferred'})
        print(json.dumps({'status': 'invalid_audit', 'artifact': str(ART / target), 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
