---
name: upstream-approve
description: "明示されたreviewとIDだけをhash-bound approvalとして記録する。明示呼び出し専用。"
disable-model-invocation: true
---
# upstream-approve — hash-bound approvalの記録

共通CLI: `intelliforge kit-run speckit --agent claude --`
成果物と確認先: `../../assets/references/ARTIFACTS.md`

## 契約
現在のユーザー発言が、review packet内の具体的IDを明示的に承認している場合だけ実行する。
「全部承認」は、ユーザーが今回のreviewについて明示的にそう述べた場合だけ許可する。
この記録はローカルのワークフロー証跡であり、本人性を暗号学的に認証しない。

## 必ず実施
1. `intelliforge kit-run speckit --agent claude -- review --project <root> --latest` で最新reviewを表示する。ユーザーがreview_idを指定した場合はそれを優先する。
2. 現在のユーザー発言から承認対象IDを特定する。曖昧なら承認せず確認する。
3. まず `approve` を `--apply` なしで実行し、対象IDとreview_idが一致することを確認する。
4. current user turnが明示承認であることを確認したら、同じ引数に`--apply`を付ける。
   `--by`にはユーザーを表す非機密ラベル、`--reference`には今回の明示承認を特定できる短い説明を入れる。
5. `intelliforge kit-run speckit --agent claude -- check --project <root> --phase draft` と `intelliforge kit-run speckit --agent claude -- approval-plan --project <root>` を再実行し、
   承認状態を確認する。
6. STALE_REVIEW、STALE_APPROVAL、STALE_DEPENDENCY_APPROVALが出たら、承認を強行せず `/speckit:upstream-review` に戻す。
7. ARTIFACTS.mdに従い、承認対象の正本へのリンクと現在の承認状態を示す。内部の要約・台帳は調査が必要な場合だけ案内する。
   記録を適用しなかった場合は未記録とし、作成していないファイルは成果物として案内しない。

## 禁止
- ユーザーの沈黙や推測を承認に変換しない。
- review後に変更された内容を古いreviewで承認しない。
- staleな下流設計・検証を自動再承認しない。

## 配布環境の呼び出し
このPluginの管理ソースは `tools/speckit-upstream/kit.json`。導入先は `intelliforge locate --only speckit --agent claude` で確認する。Pythonヘルパーは `intelliforge kit-run speckit --agent claude --tool <ファイル名> -- <引数>`、研究・UXハーネスは `intelliforge kit-run speckit --agent claude -- <引数>` から実行する。Windowsではこの入口を使い、Bashやpython3という実行名を前提にしない。
Claude Code対応は試験対応。実機未検証の機能を検証済みと扱わない。
