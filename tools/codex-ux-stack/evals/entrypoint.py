#!/usr/bin/env python3
"""Opt-in, one bounded read-only model trial of seven UX entry decisions.

Default only describes the trial. --apply uses a new output directory; no retries.
This evaluates decisions/instruction use, not actual UI implementation or browser runs.
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
CASES = [
    {'id': 'new-app', 'request': 'チームのプロジェクトとタスクを扱う管理アプリを新しく設計・実装して。画面と主要操作の確認まで任せます。', 'context': '既存アプリはない。実装Skillとブラウザー環境は利用可能。'},
    {'id': 'design-only', 'request': '申請の作成から承認までの導線とワイヤーフレームを作って。保存失敗と入力保持も含めて。今回は設計まで。', 'context': '目的と利用者は既存資料にある。実装は未着手。'},
    {'id': 'findings-only', 'request': 'この画面を実操作して問題点だけ指摘して。再設計の成果物やコード変更は不要です。', 'context': 'アプリとURLは既知。既存のスクリーンショットは古い。'},
    {'id': 'review-redesign', 'request': '文書を探して編集するたびに一覧へ戻るのが不便です。実画面をレビューし、必要なら画面構造から見直す案を図で比較して。コードは変えないで。', 'context': '実装済み。承認済みの設計契約がある。新しい案は未承認。'},
    {'id': 'improve', 'request': '編集から一覧に戻ると検索条件が消えるので改善して。修正と再確認まで進めて。', 'context': '既存コード、URL、必須テスト、該当Journeyは分かっている。'},
    {'id': 'small-css', 'request': '保存ボタンの文字がモバイルで折り返されるのでCSSだけ直して。画面構成は変えないで。', 'context': '対象コンポーネントと画面は特定済み。設計契約はない。'},
    {'id': 'human-edit', 'request': '人が編集したローカルSVGの導線図を、元の案と現在の契約と比較して取り込んで。実装はまだしないで。', 'context': '比較元、編集済みSVG、現在の設計契約が利用可能。'},
]


def fingerprint(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true'); parser.add_argument('--out', type=Path)
    parser.add_argument('--model', default='gpt-6.1-sol'); args = parser.parse_args()
    if not args.apply:
        print(json.dumps({'cases': [c['id'] for c in CASES], 'attempts': 1, 'timeout_seconds': 300,
                          'limits': 'Read-only decision trial; no app, external services, or harness execution'})); return
    if not args.out or args.out.exists(): parser.error('--apply requires a new --out directory')
    out = args.out.resolve(); workspace = out / 'workspace'; workspace.mkdir(parents=True)
    for name, source in [('ux', 'ux'), ('ooui-design', 'ooui-design'), ('ux-visual-design', 'ux-visual-design'), ('ux-gan-harness', 'skill')]:
        shutil.copytree(ROOT / source, workspace / 'skills' / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    prompt = '''これは架空の7依頼に対して、UXの共通入口がどう判断するかを確認する試験です。
skills/ux/SKILL.mdを読み、必要な専門Skillと資料だけを読んでください。専門Skillはskills/<名前>/SKILL.mdにあります。
実装SkillとしてBuild Web Apps、コード確認としてweb-design-guidelinesも利用可能と仮定できます。
各依頼に必要な工程、使うSkill、変更できるもの、変更しないもの、完了条件を判断してください。
今回の試験自体は読み取りだけです。ファイル変更、アプリやサーバーやハーネスの起動、外部接続、subagent、
この作業領域以外のファイル・設定・環境情報の読み出しは行わないでください。
この試験上の読み取り制限を架空の依頼の権限へ混同せず、各依頼の実装・提案の範囲を判断してください。
JSONオブジェクト1つを返し、cases配列の各要素にid、stages（skillと目的を含む工程配列）、
allowed_changes、preserved、completion、reasonを日本語で書いてください。
単なるSkill名一覧ではなく、実際にその依頼をどう進めるかを短く具体化してください。
CASES:
''' + json.dumps(CASES, ensure_ascii=False)
    (out / 'prompt.txt').write_text(prompt)
    before = fingerprint(workspace)
    metadata = {'model': args.model, 'cli': subprocess.check_output(['codex', '--version'], text=True).strip(),
                'cases': CASES, 'source_sha256': before, 'timeout_seconds': 300}
    command = ['codex', 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral', '--skip-git-repo-check',
               '--sandbox', 'read-only', '--model', args.model, '-c', 'model_reasoning_effort="medium"',
               '--json', '-C', str(workspace), '-']
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, start_new_session=True)
    process.stdin.write(prompt); process.stdin.close()
    messages = []; endings = []
    def consume():
        with (out / 'events.jsonl').open('w') as log:
            for line in process.stdout:
                try: event = json.loads(line)
                except ValueError: continue
                kind = event.get('type'); item = event.get('item', {})
                if kind == 'item.completed' and item.get('type') in ('agent_message', 'command_execution'):
                    log.write(json.dumps(event, ensure_ascii=False) + '\n'); log.flush()
                    if item.get('type') == 'agent_message': messages.append(item.get('text', ''))
                elif kind in ('turn.completed', 'turn.failed', 'error'):
                    log.write(json.dumps(event, ensure_ascii=False) + '\n'); log.flush(); endings.append(event)
    reader = threading.Thread(target=consume, daemon=True); reader.start()
    metadata['timeout'] = False
    try: process.wait(timeout=300)
    except subprocess.TimeoutExpired:
        metadata['timeout'] = True; os.killpg(process.pid, signal.SIGTERM)
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
    reader.join(timeout=5)
    metadata.update(exit_code=process.returncode, endings=endings, inputs_unchanged=fingerprint(workspace) == before)
    result = messages[-1] if messages else ''
    (out / 'result.txt').write_text(result)
    try:
        value = json.loads(result.removeprefix('```json\n').removesuffix('\n```'))
        metadata['all_cases_returned'] = {c['id'] for c in value['cases']} == {c['id'] for c in CASES}
        (out / 'result.json').write_text(json.dumps(value, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError): metadata['all_cases_returned'] = False
    (out / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps({k: metadata[k] for k in ('exit_code', 'timeout', 'inputs_unchanged', 'all_cases_returned')}, ensure_ascii=False))
    print('Read the actual decisions and instruction reads; these fields are not a quality verdict.')


if __name__ == '__main__': main()
