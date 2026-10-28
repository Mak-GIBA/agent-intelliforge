#!/usr/bin/env python3
"""Opt-in report-only study: three uses, shared 900 seconds and 13 native calls.

Inputs and all receipts stay in the explicitly selected private output directory.
Never reruns scientific experiments or updates the source report/state.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
import json
import random
import os
import signal
import subprocess
from pathlib import Path
import sys
import time
import tomllib

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('writing_native', ROOT/'tools/kotonoha/evals/flow_native.py')
native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)


def save(path, value):
    native.save(path, value)


def synthetic(kind):
    negative = kind == 'equal-results'
    decision = ('同じ入力で正解率はともに80.0%。追加依存がある方式への置換は勧めない。'
                if negative else '設計上の適合性からラッパーを候補とするが、効果は未測定で採用は保留する。')
    results = ({'status': 'measured', 'tasks': 10, 'repetitions': 2, 'outputs_per_method': 20,
                'baseline_accuracy': '80.0%', 'candidate_accuracy': '80.0%', 'delta': '0.0 percentage points',
                'scope': '合成タスクの限定比較。独立した利用者や本番環境は未検証。',
                'failures': '失敗も分母に含めた。速度・費用は未測定。'} if negative else
               {'status': 'unmeasured', 'scope': '文献・設計調査のみ。実装・速度・精度・費用の比較は未実施。'})
    return {'config': {'mode': 'research', 'brief': '既存方式とラッパー方式の比較を初見の技術者に説明する',
                       'phase_timeout': 60, 'evaluation_purpose': 'effectiveness' if negative else 'design'},
            'plan': {'goal': '同じ入力を維持して置換の判断をする', 'baseline': '逐次パーサー'},
            'dossier': {'question': 'ラッパー方式へ置き換える根拠はあるか',
                'candidates': [
                    {'id': 'A', 'name': '逐次パーサー', 'summary': '入力文を順に読み、同じ構造のレコードを返す。既存の採用方式。'},
                    {'id': 'B', 'name': 'ラッパー方式', 'summary': '入力を外部OSSのAPIへ渡し、その戻り値を既存レコードに変換する。変換層と依存が増える。'}],
                'sources': [{'id': 'SYNTHETIC', 'title': '合成された設計記録', 'read_level': 'fixture',
                             'scope': '実在するOSS・論文の読了を意味しない。ライセンスと実環境の互換性は未確認。'}],
                'decision': {'status': 'provisional', 'candidate_id': 'A' if negative else 'B', 'rationale': decision,
                             'unresolved': ['本番条件での検証', 'ライセンス・API互換性の確認']},
                'limitations': ['改善の実証や採用承認はない。']},
            'review': {'reason': decision, 'checks': []}, 'evaluation_summary': results}, (
               '# 方式の比較\n\n## 課題\n入力文をレコードに変換する方式の置換を検討した。\n\n## 結果\n'+
               json.dumps(results, ensure_ascii=False)+'\n\n## 判断\n'+decision+'\n')


def invoke_native(prompt, cwd, contract, deadline, schema=None):
    # One shared ceiling also covers descendants of the Node CLI launcher.
    fn = native.invoke
    original = native.subprocess.run
    def bounded_run(argv, **kwargs):
        timeout = kwargs.pop('timeout')
        kwargs.pop('capture_output', None)
        input_text = kwargs.pop('input')
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True, **kwargs)
        try:
            stdout, stderr = process.communicate(input_text, timeout=timeout)
            return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, _ = process.communicate()
            raise subprocess.TimeoutExpired(argv, timeout, output=stdout) from exc
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    native.subprocess.run = bounded_run
    try:
        return fn(prompt, cwd, contract, deadline, schema=schema)
    finally:
        native.subprocess.run = original


def run(args):
    scripts = args.source/'tools/design-research/skill/scripts'
    sys.path.insert(0, str(scripts))
    import report_composition as composition
    import report_document
    import runtime
    root = args.output.resolve()
    if root.exists() and not args.resume: raise ValueError('Output directory must be new')
    root.mkdir(parents=True, exist_ok=True)
    config = tomllib.loads((Path.home()/'.codex/config.toml').read_text())
    contract = {'model': config['model'], 'effort': config.get('model_reasoning_effort', 'medium')}
    prior = root/'study-contract.json'
    saved = json.loads(prior.read_text()) if args.resume else None
    start = saved.get('started_at', prior.stat().st_mtime) if saved else time.time()
    if saved:
        contract = saved['model']
    deadline = start+900; calls = []
    if args.resume:
        calls = [json.loads(p.read_text()) for p in root.glob('*/call-*/receipt.json')]
    original_hashes = {str(p): native.sha(p.read_bytes()) for p in (args.case_report, args.case_state)}
    if saved and original_hashes != saved['input_hashes']:
        raise ValueError('Original report/study changed since the shared study began')
    if not args.resume: save(root/'study-contract.json', {'model': contract, 'started_at': start, 'seconds': 900, 'max_calls': 13,
                                    'input_hashes': original_hashes, 'experiment_execution': False})
    cases = []
    old = json.loads(args.case_state.read_text())
    actual = {k: copy.deepcopy(old[k]) for k in ('config', 'plan', 'dossier', 'review', 'evaluation_summary')}
    actual['review'].pop('dossier_json', None)
    actual['plan'].pop('evaluation_json', None)
    # Report projection: keep reviewed decision, mechanisms, comparisons, experiments and all trial results.
    # Full original state remains hash-frozen beside this projection for checking decisive omissions.
    for key in ('claims', 'sources', 'reader_guide'):
        actual['dossier'].pop(key, None)
    actual['review'].pop('sources', None)
    actual['dossier']['derived_report_difference'] = composition.difference('65.1', '52.7')
    actual_name = 'actual-retry' if args.resume else 'actual'
    cases.append((actual_name, actual, args.case_report.read_text()))
    cases += [(name, *synthetic(name)) for name in ('unmeasured', 'equal-results')]
    results = []
    def persist():
        save(root/'study-results.json', {'model': contract, 'elapsed_seconds': round(time.time()-start, 2),
                'calls': len(calls), 'max_calls': 13, 'cases': results,
                'meaning': 'Model reviews verify only these frozen inputs; human acceptance is unknown.'})
    for name, state, reference in cases:
        workspace = root/name; run_dir = workspace/'runs/report-only'; run_dir.mkdir(parents=True, exist_ok=True)
        directory = run_dir/'composition-v2'; directory.mkdir(exist_ok=True)
        if not (directory/'reference.md').exists(): (directory/'reference.md').write_text(reference)
        state.update(run_id='report-only', iteration=1, sources={}, evidence={},
                     expected_source={'head': '', 'files': {}}, report_contract_version=2, execution_contract_version=2)
        state['config'] = {**state['config'], 'project': str(workspace), 'slug': name,
                           'phase_timeout': 60, 'allow_network': False, 'test_commands': []}
        state['report_finalization'] = {'target_status': 'research_complete',
                                        'science_sha256': report_document.substantive_signature(state)}
        if args.resume and (run_dir/'state.json').exists():
            state = json.loads((run_dir/'state.json').read_text())
            # Retain the failed reader's receipt; invalidate only its publication-path interpretation.
            state['units'] = {k:v for k,v in state.get('units', {}).items() if v.get('role') != 'report-reviewer'}
        before = report_document.substantive_signature(state)
        def invoke(role, schema, current, _workspace, _run, validator):
            if len(calls) >= 13 or time.time() >= deadline:
                raise runtime.Blocked('Shared native study budget exhausted')
            trial = workspace/f'call-{len(calls)+1}'; trial.mkdir()
            task = current['report_task']
            prompt = (composition.instructions(role)+'\nRead every supplied input file completely in bounded chunks to avoid output truncation. Parent runs lint. '
                      'Do not edit files, execute checks, run research, use network or write memory.\nTASK:\n'+
                      json.dumps(task, ensure_ascii=False))
            result = invoke_native(prompt, trial, contract, deadline, schema=schema)
            result['role'] = role; result['case'] = name
            entry = task.get('writing_entry')
            if entry:
                result['observed_skill_reads'] = native.observed_reads(Path(entry['path']).parent, result['tools'])
            calls.append({'role': role, 'case': name, 'status': result['status'], 'elapsed_seconds': result['elapsed_seconds']})
            save(trial/'receipt.json', result); persist()
            if result['status'] != 'completed': raise runtime.Blocked('Native call '+result['status'])
            value = json.loads(result['output'])
            validator(value, current)
            return value
        try:
            composition.finish(state, workspace, run_dir, invoke)
            composition.assert_artifacts(state, workspace)
            text = state['report_polish']['approved_document']
            (workspace/'report.md').write_text(text)
            result = {'case': name, 'status': 'accepted', 'report': str(workspace/'report.md'),
                      'science_unchanged': before == report_document.substantive_signature(state),
                      'semantic_review': state['report_polish']['review']}
        except Exception as exc:
            result = {'case': name, 'status': 'incomplete', 'reason': str(exc)}
        results.append(result); persist()
    actual_result = results[0]
    if actual_result['status'] == 'accepted' and len(calls) < 13 and time.time() < deadline:
        trial = root/'blinded-comparison'; trial.mkdir()
        manuscripts = [('original', args.case_report.read_text()), ('revised', Path(actual_result['report']).read_text())]
        random.Random(19357).shuffle(manuscripts)
        for label, (_, text) in zip(('A', 'B'), manuscripts): (trial/(label+'.md')).write_text(text)
        save(trial/'key.json', dict(zip(('A', 'B'), (x[0] for x in manuscripts))))
        schema = composition.obj({'preferred': {'type': 'string', 'enum': ['A', 'B', 'equal', 'incomplete']},
                'reason': composition.S, 'issues_A': composition.STRINGS, 'issues_B': composition.STRINGS})
        prompt = ('Read A.md and B.md completely. Read the frozen evidence file at '+
                  str(root/actual_name/'runs/report-only/composition-v2/evidence.json')+
                  '. Compare two technical reports without guessing their origin. Which better explains the research '
                  'question, mechanisms, actual results, support, adoption decision and limits for an initial '
                  'technical reader? Check that denominator, metric/value association, failures, uncertainty and '
                  'proposed versus implemented status are preserved. Prefer neither for being shorter or having '
                  'prescribed headings. State concrete advantages and omissions. No edits/network/research. Return JSON.')
        receipt = invoke_native(prompt, trial, contract, deadline, schema=schema)
        calls.append({'role': 'blinded-comparison', 'status': receipt['status']})
        save(trial/'receipt.json', receipt); persist()
    if any(native.sha(Path(p).read_bytes()) != h for p,h in original_hashes.items()):
        raise RuntimeError('Original study/report changed')
    persist()
    print(json.dumps({'output': str(root), 'cases': results, 'calls': len(calls)}, ensure_ascii=False))
    return 0 if all(r['status']=='accepted' and r['science_unchanged'] for r in results) else 2


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resume', action='store_true', help='Reuse the original shared deadline and spent calls')
    p.add_argument('--source', type=Path, required=True, help='Assembled Design Research sources')
    p.add_argument('--case-report', type=Path, required=True)
    p.add_argument('--case-state', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True, help='Private new output directory')
    raise SystemExit(run(p.parse_args()))
