#!/usr/bin/env python3
"""Explicit native v3/candidate study: 24 uses, one shared 60 minute ceiling.

Stores final outputs and bounded tool receipts, never reasoning or credentials.
No edits of generated answers, no automatic retries. Round 2 reruns the candidate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib

HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def clean(value, cwd):
    if isinstance(value, str):
        return value.replace(str(cwd), '<trial>').replace(str(Path.home()), '<user-home>')
    if isinstance(value, list):
        return [clean(x, cwd) for x in value]
    if isinstance(value, dict):
        return {k: clean(v, cwd) for k, v in value.items()}
    return value


def invoke(prompt, cwd, contract, deadline, schema=None, runtime=None):
    remaining = min(180, deadline-time.time())
    if remaining <= 0:
        raise RuntimeError('Shared 60 minute budget exhausted')
    disabled = sorted({str(p.resolve()) for root in (Path.home()/'.agents/skills', Path.home()/'.codex/skills')
                       if root.is_dir() for p in root.rglob('SKILL.md')})
    rows = ','.join('{path='+json.dumps(p)+',enabled=false}' for p in disabled)
    out = cwd/'final-output.txt'
    args = ['codex', 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral', '--skip-git-repo-check',
            '--sandbox', 'workspace-write' if schema is None else 'read-only', '--model', contract['model'],
            '-c', 'model_reasoning_effort='+json.dumps(contract['effort']),
            '-c', 'project_doc_max_bytes=0', '-c', 'skills.config=['+rows+']',
            '-c', 'web_search="disabled"', '--json', '--output-last-message', str(out)]
    if schema:
        save(cwd/'schema.json', schema)
        args += ['--output-schema', str(cwd/'schema.json')]
    args += ['-']
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    if runtime:
        env['KOTONOHA_RUNTIME_DIR'] = str(runtime)
    started = time.time()
    try:
        proc = subprocess.run(args, input=prompt, cwd=cwd, env=env, capture_output=True, text=True,
                              encoding='utf-8', timeout=remaining)
        code, stdout = proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as exc:
        code = None
        stdout = exc.stdout or ''
        if isinstance(stdout, bytes):
            stdout = stdout.decode('utf-8', 'replace')
    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    tools = []
    for event in events:
        item = event.get('item', {})
        if event.get('type') == 'item.completed' and item.get('type') not in {'reasoning', 'agent_message'}:
            tools.append({k: item[k] for k in ('type', 'command', 'exit_code', 'status', 'aggregated_output') if k in item})
    text = out.read_text(encoding='utf-8') if out.is_file() else None
    return {'status': 'completed' if code == 0 and text is not None else 'timeout' if code is None else 'execution_failed',
            'elapsed_seconds': round(time.time()-started, 2), 'prompt_sha256': sha(prompt.encode()),
            'output': text, 'usage': next((e.get('usage') for e in reversed(events) if e.get('type') == 'turn.completed'), None),
            'tools': tools}


def native(task, arm, source, runtime, contract, deadline):
    with tempfile.TemporaryDirectory(prefix='kotonoha-flow-trial-') as td:
        cwd = Path(td)
        skills = cwd/'.agents/skills'
        skills.mkdir(parents=True)
        if arm == 'baseline':
            if (source/'SKILL.md').is_file():
                shutil.copytree(source, skills/'kotonoha')
            else:
                for name in ('kotonoha', 'yomiyasu', 'paragraph-writing', 'japanese-direct-writing'):
                    shutil.copytree(source/name, skills/name)
        else:
            shutil.copytree(source, skills/'kotonoha')
        before = inventory(skills)
        suffix = '.txt' if task['id'] == 'W18' else '.md'
        draft = cwd/('draft'+suffix)
        final = cwd/('result'+suffix)
        if task['mode'] != 'chat':
            draft.write_text(task['input'], encoding='utf-8')
        prompt = ('' if task['id'] in {'W01', 'W10'} else '$kotonoha ')+task['instruction']
        if task['mode'] == 'chat':
            prompt += '\n\n原稿・素材:\n'+task['input']
        prompt += '\n\n作業はこの一時プロジェクト内のローカル編集だけに限定してください。ネット接続、外部サービス、別モデルの起動、Skillや実行環境の導入・更新は行わないでください。'
        result = invoke(prompt, cwd, contract, deadline, runtime=runtime)
        result['text'] = final.read_text(encoding='utf-8') if final.is_file() else result['output']
        result['draft_unchanged'] = task['mode'] == 'chat' or draft.read_text(encoding='utf-8') == task['input']
        result['skills_unchanged'] = inventory(skills) == before
        result['final_file_present'] = final.is_file()
        outputs = '\n'.join(t.get('aggregated_output', '') for t in result['tools'] if t.get('exit_code') == 0)
        outputs = re.sub(r'(?m)^\s*\d+\t', '', outputs)
        reads = []
        for p in skills.rglob('*.md'):
            raw = p.read_text(encoding='utf-8')
            if raw.strip() and raw.strip() in outputs:
                reads.append(p.relative_to(skills).as_posix())
        result['full_reads'] = sorted(reads)
        # Commands remain as evidence for parent inspection; do not infer mental application counts.
        commands = '\n'.join(t.get('command', '') for t in result['tools'])
        result['checker_commands'] = {n: commands.count(n) for n in ('writing_lint.py', 'check.py')}
        result['diagnosis_has_no_result_file'] = task['mode'] != 'diagnose' or not final.exists()
        result['id'] = task['id']
        result['arm'] = arm
        return clean(result, cwd)


def route_errors(task, record):
    errors = []
    if record['status'] != 'completed' or not record.get('text'):
        errors.append('No completed final output')
    if not record['skills_unchanged'] or not record['draft_unchanged']:
        errors.append('Input or Skill files changed')
    if task['mode'] == 'file' and not record['final_file_present']:
        errors.append('Requested output file missing')
    if not record['diagnosis_has_no_result_file']:
        errors.append('Diagnosis produced a rewritten file')
    required = [] if task['id'] in {'W21', 'W22', 'W23', 'W24'} else ['audience', 'clarity', 'finish', 'review']
    required += task['conditional']
    for name in required:
        path = 'kotonoha/references/'+name+'.md'
        if path not in record['full_reads']:
            errors.append('Required reference not observed: '+path)
    if task['mode'] == 'file':
        for name, count in record['checker_commands'].items():
            if count == 0:
                errors.append('Checker invocation not observed: '+name)
    return errors


STR = {'type': 'string'}
LIST = {'type': 'array', 'items': STR}
ROW = {'type': 'object', 'properties': {'id': STR, 'X_errors': LIST, 'Y_errors': LIST,
       'regressions_X': LIST, 'regressions_Y': LIST, 'evidence': STR},
       'required': ['id', 'X_errors', 'Y_errors', 'regressions_X', 'regressions_Y', 'evidence'], 'additionalProperties': False}
REVIEW = {'type': 'object', 'properties': {'cases': {'type': 'array', 'items': ROW}}, 'required': ['cases'], 'additionalProperties': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--round', type=int, choices=(1, 2), default=1)
    a = parser.parse_args()
    root = a.candidate.resolve()
    adapter = root/'adapter'
    tasks = json.loads((HERE/'flow-tasks.json').read_text(encoding='utf-8'))['tasks']
    config = tomllib.loads((Path.home()/'.codex/config.toml').read_text(encoding='utf-8'))
    sources = inventory(adapter)
    bound = {k: v for k, v in sources.items() if k not in {'UPSTREAMS.json', 'resources.json'}}
    model = root/('native-r'+str(a.round))
    model.mkdir(exist_ok=True)
    first = root/'native-r1/contract.json'
    contract = {'protocol': 'native-flow-v1', 'model': config['model'], 'effort': config.get('model_reasoning_effort', 'medium'),
                'started_epoch': time.time(), 'budget_seconds': 3600, 'timeout_per_call': 180, 'automatic_retries': 0,
                'tasks': tasks, 'baseline_sha256': inventory(a.baseline), 'adapter_sha256': bound,
                'runtime_settings_sha256': sha((a.runtime/'settings.json').read_bytes())}
    runner=Path(__file__).read_bytes()
    (model/'runner.py').write_bytes(runner)
    contract['runner_sha256']=sha(runner)
    if first.is_file():
        original = json.loads(first.read_text(encoding='utf-8'))
        for key in ('model', 'effort', 'tasks', 'baseline_sha256', 'runtime_settings_sha256'):
            if contract[key] != original[key]:
                raise ValueError('Frozen comparison conditions changed: '+key)
        contract['started_epoch'] = original['started_epoch']
    save(model/'contract.json', contract)
    deadline = contract['started_epoch']+3600
    critical, regressions, routes = [], [], []
    try:
        for i, task in enumerate(tasks):
            arms = ('baseline', 'candidate') if i % 2 == 0 else ('candidate', 'baseline')
            for arm in arms:
                target = model/(task['id']+'-'+arm+'.json')
                if target.exists():
                    continue
                if arm == 'baseline' and a.round == 2:
                    shutil.copy2(root/'native-r1'/target.name, target)
                else:
                    value = native(task, arm, a.baseline if arm == 'baseline' else adapter, a.runtime, contract, deadline)
                    save(target, value)
                record = json.loads(target.read_text(encoding='utf-8'))
                print(task['id'], arm, record['status'], 'reads='+str(len(record['full_reads'])), flush=True)
            candidate = json.loads((model/(task['id']+'-candidate.json')).read_text(encoding='utf-8'))
            routes.extend(task['id']+': '+x for x in route_errors(task, candidate))
            if inventory(adapter) != sources:
                raise RuntimeError('Candidate changed during native comparison')
        for batch in range(6):
            selected = tasks[batch*4:(batch+1)*4]
            pairs = []
            labels = {}
            for i, task in enumerate(selected):
                order = ('baseline', 'candidate') if i % 2 == 0 else ('candidate', 'baseline')
                labels[task['id']] = 'Y' if i % 2 == 0 else 'X'
                pairs.append({**{k: task[k] for k in ('id', 'instruction', 'input', 'requirements')},
                              'versions': {label: json.loads((model/(task['id']+'-'+arm+'.json')).read_text())['text']
                                           for label, arm in zip(('X', 'Y'), order)}})
            target = model/('review-'+str(batch)+'.json')
            if not target.exists():
                prompt = ('原文・依頼・要件と二つの出力X/Yを比較してください。版の出自は不明です。意味・事実・数値・否定・条件・確信度・義務・範囲の変更や脱落、捏造を各版のerrorsへ記録してください。'
                          '相手版より説明の深さ、段落、自然さ、情報効率が具体的に悪い点だけをregressionsへ記録します。単なる文体の好みや短さは劣化ではありません。'
                          '診断依頼は指摘の出力として評価し、完成稿を要求しません。実際の文に基づくevidenceを付け、問題がなければ空配列にします。道具を使わずJSONだけ返してください。\n'+json.dumps(pairs, ensure_ascii=False))
                with tempfile.TemporaryDirectory(prefix='kotonoha-flow-review-') as td:
                    receipt = invoke(prompt, Path(td), contract, deadline, schema=REVIEW)
                    if receipt['status'] != 'completed' or receipt['tools']:
                        raise RuntimeError('Review did not complete without tools')
                    graded = json.loads(receipt['output'])
                    save(target, {'result': graded, 'receipt': clean(receipt, Path(td)), 'pairs': pairs})
            graded = json.loads(target.read_text())['result']
            if {row['id'] for row in graded['cases']} != {t['id'] for t in selected} or len(graded['cases']) != 4:
                raise RuntimeError('Incomplete/duplicate review cases')
            for row in graded['cases']:
                label = labels[row['id']]
                critical.extend(row['id']+': '+x for x in row[label+'_errors'])
                regressions.extend(row['id']+': '+x for x in row['regressions_'+label])
            print('review', batch, 'completed', flush=True)
        quality = {'protocol': 'native-flow-v1', 'status': 'passed' if not critical and not regressions and not routes else 'held',
                   'case_ids': [t['id'] for t in tasks], 'completed_pairs': 24, 'critical_errors': critical,
                   'unresolved_regressions': regressions, 'route_failures': routes, 'adapter_sha256': bound,
                   'artifacts': {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in model.iterdir() if p.is_file()},
                   'scope': '24 paired native uses, one output per arm, separate blinded-label same-model review; no universal equivalence proof'}
        save(root/'quality.json', quality)
        print(json.dumps({k: v for k, v in quality.items() if k not in {'artifacts', 'adapter_sha256'}}, ensure_ascii=False), flush=True)
        return 0 if quality['status'] == 'passed' else 2
    except (OSError, ValueError, RuntimeError) as exc:
        save(root/'quality.json', {'protocol': 'native-flow-v1', 'status': 'held', 'error': str(exc), 'adapter_sha256': bound})
        print(str(exc), flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
