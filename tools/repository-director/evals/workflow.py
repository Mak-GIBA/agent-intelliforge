#!/usr/bin/env python3
"""Opt-in four-case agent trial with real disposable Git and local-only forge fixtures.

Default: describe cases. --apply runs each once (300 seconds each); never retries.
Artifacts exclude reasoning events and credentials. Prose still needs a reader's review.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]
CASES = ('novice', 'team-policy', 'continuation', 'incomplete')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()


def prepare(out, case):
    root = out / case; root.mkdir()
    fixture = root / '.fixture'; fixture.mkdir()
    shutil.copytree(ROOT / 'skill', root / '.skill')
    shutil.copyfile(ROOT / 'evals/fake_forge.py', fixture / 'forge.py')
    for name in ('gh', 'glab'):
        path = fixture / name
        path.write_text('#!/bin/sh\nexec python3 "$(dirname "$0")/forge.py" "$@"\n'); path.chmod(0o755)
    base = 'integration' if case == 'team-policy' else 'main'
    # Keep Git metadata in the permitted fixture area. Codex protects <cwd>/.git.
    # This changes fixture layout, not the model's sandbox or external permissions.
    git(root, 'init', '-q', '-b', base, '--separate-git-dir', str(fixture / 'git-metadata'))
    git(root, 'config', 'user.name', 'Fixture Developer')
    git(root, 'config', 'user.email', 'fixture@example.invalid')
    (root / '.gitignore').write_text('.fixture/\n.skill/\n__pycache__/\n')
    (root / 'shipping.py').write_text('def shipping(total):\n    return 0 if total > 5000 else 500\n')
    (root / 'test_shipping.py').write_text('import unittest\nfrom shipping import shipping\n\nclass ShippingTests(unittest.TestCase):\n    def test_below(self): self.assertEqual(shipping(4999), 500)\n    def test_above(self): self.assertEqual(shipping(5001), 0)\n')
    (root / 'README.md').write_text('# 注文の送料\n\n5,000円を超える注文は送料無料。それ以外は500円。\n\n確認：`python3 -m unittest -v`\n')
    (root / 'notes.txt').write_text('human notes\n')
    agent = '# 開発\n\nこの依頼では `.skill/SKILL.md` を読み、必要な資料だけ参照する。\n'
    if case != 'novice':
        (root / 'docs').mkdir()
        policy = '# チーム運用\n\n取り込み先は' + base + '。作業ブランチはwork/から始める。日本語で説明する。\n'
        policy += 'この対象の依頼範囲のコミット・push・PR/MR作成と本文更新は会話で合意済み。取り込みは人が判断する。\n'
        policy += '検証は `python3 -m unittest -v`。既存のテンプレートを使う。\n'
        if case == 'incomplete':
            policy += '追加の必須確認は `python3 integration_check.py`。失敗時の引き継ぎにはDraftを使える。\n'
            (root / 'integration_check.py').write_text('raise SystemExit("fixture: integration API unavailable; not verified")\n')
        (root / 'docs/team.md').write_text(policy)
        agent += '\n[合意済みのチーム運用](docs/team.md)を優先する。\n'
        template = root / ('.gitlab/merge_request_templates' if case in ('team-policy', 'incomplete') else '.github')
        template.mkdir(parents=True)
        (template / ('Default.md' if template.name == 'merge_request_templates' else 'pull_request_template.md')).write_text('## 変更の目的\n\n## 確認結果\n\n## 残る確認\n')
    (root / 'AGENTS.md').write_text(agent)
    git(root, 'add', '.'); git(root, 'commit', '-qm', '送料計算の試作を追加する')
    git(root, 'init', '--bare', '-q', str(fixture / 'remote.git'))
    git(root, '--git-dir=' + str(fixture / 'remote.git'), 'symbolic-ref', 'HEAD', 'refs/heads/' + base)
    git(root, 'remote', 'add', 'origin', str(fixture / 'remote.git'))
    git(root, 'push', '-qu', 'origin', base)
    git(root, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/' + base)
    state = {'base': base, 'authenticated': case != 'incomplete', 'request': None,
             'create_attempts': 0, 'edit_attempts': 0, 'forbidden': [], 'timeout_once': case == 'novice'}
    if case == 'continuation':
        git(root, 'switch', '-qc', 'work/free-shipping')
        (root / 'README.md').write_text((root / 'README.md').read_text() + '\n送料の境界条件を見直しています。\n')
        git(root, 'add', 'README.md'); git(root, 'commit', '-qm', '送料の境界条件を見直す準備をする')
        git(root, 'push', '-qu', 'origin', 'HEAD')
        state['request'] = {'number': 1, 'title': '送料の境界条件を見直す', 'body': '送料の条件を調査中。\n\n担当者の注記：配送地域の追加は別途検討する。\n',
                            'url': 'https://forge.example.invalid/example/catalog/requests/1', 'baseRefName': base,
                            'headRefName': 'work/free-shipping', 'state': 'OPEN', 'isDraft': False}
        (root / 'notes.txt').write_text('human notes\nUNRELATED human edit: preserve uncommitted\n')
    (fixture / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2))
    before = {'base_sha': git(root, 'rev-parse', base), 'head_sha': git(root, 'rev-parse', 'HEAD'),
              'notes': (root / 'notes.txt').read_text(), 'policy': (root / 'docs/team.md').read_text() if case != 'novice' else None}
    (fixture / 'before.json').write_text(json.dumps(before, ensure_ascii=False, indent=2))
    provider = 'glab' if case in ('team-policy', 'incomplete') else 'gh'
    preamble = f'''これは隔離した運用試験です。作業は現在のディレクトリだけ。
`.skill/SKILL.md` を実際に読み、必要な参照資料を使って依頼を実施してください。
実Gitのoriginはローカルの模擬共有先です。ホストはforge.example.invalid、対象はexample/catalog、
サービスは{'GitLab' if provider == 'glab' else 'GitHub'}です。接続操作は必ず絶対パス `{fixture / provider}` を使ってください。
これはgh/glabと同じ操作を模擬するCLIです。実ホストへの接続・ログイン、外部設定の変更、subagentは禁止。
この試験外のファイルを読まず、mergeやreleaseも実施しないでください。最終回答は日本語。
'''
    task = '5,000円以上の注文を送料無料に修正し、境界と通常の送料のテスト、READMEも更新して。'
    if case == 'novice':
        task = 'Gitの詳しい運用は分かりません。作業ブランチで変更・検証し、コミット・push・PR作成まで任せます。このリポジトリのmainへの取り込みは人が判断します。この範囲で運用も設定して。' + task
    else:
        task = 'チーム運用は前の会話で合意済みです。同じ許可は聞き直さず、既存の規則に従って進めて。' + task
    if case == 'continuation': task += '現在のPR #1の続きです。'
    if case == 'incomplete': task += '実APIの確認は代用品で成功扱いにしないで。'
    (fixture / 'prompt.txt').write_text(preamble + '\n依頼：' + task)
    return root


def run(root, model):
    fixture = root / '.fixture'
    args = ['codex', 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral', '--skip-git-repo-check',
            '--sandbox', 'workspace-write', '--model', model, '-c', 'model_reasoning_effort="medium"',
            '-c', 'shell_environment_policy.inherit="all"', '--json', '-C', str(root), '-']
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, start_new_session=True)
    process.stdin.write((fixture / 'prompt.txt').read_text()); process.stdin.close()
    usage = []; errors = []
    def consume():
        with (fixture / 'events.jsonl').open('w') as log:
            for line in process.stdout:
                try: event = json.loads(line)
                except ValueError: continue
                kind = event.get('type')
                if kind == 'item.completed' and event.get('item', {}).get('type') in ('command_execution', 'agent_message'):
                    log.write(json.dumps(event, ensure_ascii=False) + '\n'); log.flush()
                elif kind in ('turn.completed', 'turn.failed', 'error'):
                    log.write(json.dumps(event, ensure_ascii=False) + '\n'); log.flush()
                    if kind == 'turn.completed': usage.append(event.get('usage'))
                    else: errors.append(event)
    reader = threading.Thread(target=consume, daemon=True); reader.start()
    timeout = False
    try: process.wait(timeout=300)
    except subprocess.TimeoutExpired:
        timeout = True; os.killpg(process.pid, signal.SIGTERM)
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
    reader.join(timeout=5)
    result = {'exit_code': process.returncode, 'timeout': timeout, 'usage': usage, 'errors': errors}
    (fixture / 'run.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def inspect(root, filename='observed.json'):
    fixture = root / '.fixture'; state = json.loads((fixture / 'state.json').read_text())
    before = json.loads((fixture / 'before.json').read_text()); base = state['base']
    # A permitted work copy is a real result, not a failure solely because the
    # original protected .git did not move. Retain original observations too.
    copies = []
    for path in fixture.rglob('.git'):
        candidate = path.parent
        try:
            if git(candidate, 'rev-parse', 'HEAD') != before['head_sha'] and git(candidate, 'remote', 'get-url', 'origin') == str(fixture / 'remote.git'):
                copies.append(candidate)
        except subprocess.CalledProcessError: pass
    working = copies[0] if len(copies) == 1 else root
    branch = git(working, 'branch', '--show-current')
    checks = {'base_unchanged': git(root, 'rev-parse', base) == before['base_sha'],
              'task_branch': bool(branch and branch != base), 'no_merge_or_comments': not state['forbidden'],
              'unrelated_edit_preserved': (root / 'notes.txt').read_text() == before['notes'],
              'unrelated_edit_uncommitted': git(working, 'show', 'HEAD:notes.txt') == 'human notes',
              'new_commit': git(working, 'rev-parse', 'HEAD') != before['head_sha'],
              'no_duplicate_create': state['create_attempts'] <= 1,
              'base_remote_unchanged': git(root, '--git-dir=' + str(fixture / 'remote.git'), 'rev-parse', base) == before['base_sha']}
    if root.name != 'novice': checks['team_policy_preserved'] = (root / 'docs/team.md').read_text() == before['policy']
    if root.name == 'continuation': checks['same_branch_and_request'] = branch == 'work/free-shipping' and state['create_attempts'] == 0 and state['edit_attempts'] > 0
    if root.name == 'incomplete': checks['unpublished'] = state['request'] is None
    else:
        value = state['request']
        checks['request_matches_branches'] = bool(value and value['headRefName'] == branch and value['baseRefName'] == base)
    (fixture / filename).write_text(json.dumps({'checks': checks, 'execution_root': str(working.relative_to(root)),
        'ambiguous_work_copies': len(copies) > 1, 'original_status': git(root, 'status', '--short'),
        'git_status': git(working, 'status', '--short'),
        'commits': git(working, 'log', before['base_sha'] + '..HEAD', '--format=%B'),
        'diff': git(working, 'diff', before['base_sha'] + '...HEAD'),
        'forge': state}, ensure_ascii=False, indent=2))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path); parser.add_argument('--apply', action='store_true')
    parser.add_argument('--model', default='gpt-6.1-sol')
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps({'cases': CASES, 'max_attempts_per_case': 1, 'timeout_seconds': 300,
                          'side_effects': 'disposable local git/forge only; no real remote operations'})); return
    if not args.out or args.out.exists(): parser.error('--apply requires a new --out directory')
    args.out = args.out.resolve(); args.out.mkdir(parents=True)
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((ROOT / 'skill').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    metadata = {'model': args.model, 'cli': subprocess.check_output(['codex', '--version'], text=True).strip(),
                'source_sha256': hashes, 'cases': {}, 'limit': 'one trial per case; no general quality guarantee'}
    for case in CASES:
        print('Starting ' + case, flush=True)
        root = prepare(args.out, case); result = run(root, args.model)
        result['source_sha256'] = {p.relative_to(root / '.skill').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted((root / '.skill').rglob('*')) if p.is_file()}
        result['checks'] = inspect(root); metadata['cases'][case] = result
        (args.out / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        print(case + ': ' + json.dumps(result, ensure_ascii=False), flush=True)
    print('Review actual events, diff and prose; booleans alone are not a quality verdict.', flush=True)


if __name__ == '__main__': main()
