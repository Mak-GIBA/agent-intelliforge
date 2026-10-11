"""Bind saved native outcomes to exact original prompt hashes; no model calls."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/codex-yomiyasu/evals'))
import run_study
import verify_native

evidence = ROOT / 'docs/codex-yomiyasu/evidence/study-2026-10-11'
provenance = json.loads((evidence / 'native-prompt-provenance.json').read_text())
for name, expected in provenance['source_files'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
tasks = {task['id']: task for task in run_study.native_tasks()}
seen = set()
for trial in provenance['trials']:
    path = evidence / trial['receipt']
    assert trial['receipt'] not in seen
    seen.add(trial['receipt'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == trial['receipt_sha256']
    saved = json.loads(path.read_text())
    task = tasks[saved['task']]
    prompt = task['prompt'] + '\n送信・インストール・ユーザー設定変更は不要です。完成稿だけを返してください。'
    assert trial['reconstructed_prompt'] == prompt
    assert hashlib.sha256(prompt.encode()).hexdigest() == saved['prompt_sha256'] == trial['original_prompt_sha256']
    assert trial['expected_reads'] == saved['expected_reads'] == task['expected']
assert len(seen) == 32
assert seen == {str(path.relative_to(evidence)) for path in (evidence / 'native').glob('*.json')}
verified = verify_native.verify(evidence, ROOT / 'tools/codex-yomiyasu/evaluation-v200')
counts = {arm: sum(row['route_pass'] for name, row in verified.items() if '-' + arm + '-' in name)
          for arm in ['baseline', 'a', 'b', 'c']}
assert counts == {'baseline': 6, 'a': 5, 'b': 8, 'c': 8}
print(json.dumps({'status': 'verified', 'exact_original_prompt_hashes': 32,
                  'full_read_receipts': 32, 'route_passes': counts,
                  'task_prompts': {key: value['prompt'] for key, value in tasks.items()},
                  'limits': ['Scope is these eight fixtures in the original isolated environment.',
                             'Reading is observed; private internal application count is not.',
                             'Timeout outcomes remain unavailable. No model generation or installation.']},
                 ensure_ascii=False, indent=2))
