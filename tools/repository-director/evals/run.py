#!/usr/bin/env python3
"""Explicit text-generation comparison. Never invoked by installation/self-test.

Uses the same CLI settings, fictional inputs and request for both variants. No
repository tools, commits or remote posting are requested. Human review remains
necessary: successful JSON generation is not a readability score.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]

CASES=[
 {'id':'small-bug','request':'コミットメッセージとPR本文を日本語で作って。',
  'facts':'検索条件を変更してもページ位置が残り、3ページ目で絞り込むと結果があっても空になる。変更は条件変更時にpage=1へ戻す。通常のページ移動は維持。単体テストは条件変更と通常の移動の2件成功。ブラウザーは未確認。'},
 {'id':'feature-pending','request':'GitLabのMR本文を日本語で作って。',
  'facts':'入力途中の申込みを利用者本人だけが再開できる機能を追加。保存APIと復元画面を実装。保存失敗時は保存済みと表示しない。本人以外のアクセス拒否と保存失敗のテストは成功。再ログイン後の復元テストは未実行。公開は未実施。'},
 {'id':'core-change','request':'コミットメッセージとPR本文を日本語で作って。',
  'facts':'検索候補を毎回計算すると遅いため、プロジェクト単位のキャッシュへ変更。別プロジェクトの結果は共有しない。更新時に失効。応答形式は維持。分離と失効のテスト成功。速度は未計測。'},
 {'id':'review','request':'必須修正と任意改善が伝わるレビューコメントを日本語で作って。',
  'facts':'src/profile.ts:18で未ログイン時にもuser.nameを参照するため例外になる。nullの場合はサインインへ誘導する必要がある。変数名pの改名は任意。指摘は会話に返すだけで投稿しない。'},
 {'id':'blocked','request':'引き渡し用コメント案を日本語で作って。',
  'facts':'申込み保存APIが停止しており結合確認できない。画面の実装とモックによる保存失敗テストは完了。実APIでの保存は未確認。復旧を待つかテスト用APIを使うか判断が必要。同じ経過を何度もIssueへ投稿しない。'},
 {'id':'existing-docs','request':'下記の既存コードと資料から、AGENTS、README、docs/INDEX、要件とコアロジック説明を、ファイル名と本文のJSON配列として提案して。コード修正はしない。お任せで方針を整理して。',
  'facts':{'files':{'search.py':'def search(rows, query, page):\n    filtered = [r for r in rows if query.lower() in r.lower()]\n    return filtered[(page-1)*20:page*20]\n',
                     'tests/test_search.py':'def test_casefold():\n    assert search(["Apple"], "apple", 1) == ["Apple"]\n',
                     'README.md':'# Catalog\n商品名を検索する試作。\n',
                     'AGENTS.md':'# 既存ルール\n外部APIや本番DBに接続しない。\n'},
           'unknowns':['事業目的','正式な件数・ページ番号の要件','本番環境','テスト実行結果'],
           'constraints':'テストファイルは存在するが今回未実行。事業目的を捏造しない。既存ルールを保持。入力コードへ修正案を適用しない。'}}
]


def sha(data):return hashlib.sha256(data.encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--legacy-source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--apply',action='store_true')
    p.add_argument('--variant',choices=('both','old','new'),default='both');a=p.parse_args()
    if a.out.exists() and any(a.out.iterdir()):raise SystemExit('Use a missing/empty output directory')
    a.out.mkdir(parents=True,exist_ok=True)
    old=a.legacy_source
    contexts={
      'old':'\n\n'.join((old/rel).read_text() for rel in (
          'tools/codex-github-pm/skills/github-project-director/SKILL.md',
          'tools/codex-github-pm/skills/github-project-director/references/writing-and-tracking.md',
          'tools/speckit-upstream/assets/skill/SKILL.md','tools/speckit-upstream/assets/prompts/existing.md')),
      'new':'\n\n'.join((ROOT/rel).read_text() for rel in (
          'skill/SKILL.md','skill/references/writing.md','skill/references/existing.md','skill/references/policy.md'))}
    if a.variant!='both':contexts={a.variant:contexts[a.variant]}
    task='''You are evaluating supplied workflow instructions on fictional material.
Do not call any tools, inspect the filesystem, delegate work, post, commit or execute commands.
Use only the workflow and facts provided below. Return one JSON object with a "cases" array,
each item containing "id" and "output" (the complete requested Japanese text).
For existing-docs, put the proposed file array as a JSON string in output.
Keep facts, uncertainty and existing rules intact. No factual context beyond the material exists.
WORKFLOW:\n{context}\nCASES:\n{cases}\n'''
    metadata={'cases':CASES,'conditions':'Same fictional inputs and Codex CLI defaults; ephemeral/read-only, user configuration not loaded. No tools requested. One batch per variant; not a statistical study.', 'variants':{}}
    if a.apply:metadata['cli_version']=subprocess.check_output(['codex','--version'],text=True).strip()
    with tempfile.TemporaryDirectory(prefix='repository-director-generation-') as temp:
        workspace=Path(temp);(workspace/'AGENTS.md').write_text('Use only the prompt. No tools. Return the requested text.\n')
        for name,context in contexts.items():
            prompt=task.format(context=context,cases=json.dumps(CASES,ensure_ascii=False))
            (a.out/(name+'-prompt.txt')).write_text(prompt)
            metadata['variants'][name]={'prompt_sha256':sha(prompt),'executed':False}
            if not a.apply:continue
            print('Generating '+name,flush=True)
            output=a.out/(name+'.json')
            result=subprocess.run(['codex','exec','--ignore-user-config','--ephemeral','--sandbox','read-only',
                                   '--skip-git-repo-check','--json','-C',str(workspace),'-o',str(output),'-'],
                                  input=prompt,text=True,capture_output=True,timeout=600)
            events=[]
            for line in result.stdout.splitlines():
                try:events.append(json.loads(line))
                except ValueError:pass
            tools=[e for e in events if e.get('type') in ('item.started','item.completed') and e.get('item',{}).get('type') in ('command_execution','mcp_tool_call','web_search')]
            metadata['variants'][name].update(executed=True,exit_code=result.returncode,tool_calls=len(tools),
                usage=[e.get('usage') for e in events if e.get('type')=='turn.completed'])
            model=re.search(r'^model:\s+(\S+)',result.stderr,re.M)
            metadata['variants'][name]['model']=model[1] if model else 'CLI default; no model ID exposed in captured events'
            if result.returncode or tools or not output.is_file():
                (a.out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
                raise SystemExit('Generation failed or used tools; inspect local CLI state. No quality pass is claimed.')
            raw=output.read_text();raw=raw.removeprefix('```json\n').removesuffix('\n```')
            value=json.loads(raw)
            if {c['id'] for c in value['cases']}!={c['id'] for c in CASES}:raise SystemExit('Missing evaluation cases')
            output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    (a.out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(a.out)


if __name__=='__main__':main()
