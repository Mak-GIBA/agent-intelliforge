---
name: upstream-approve
description: "明示されたreviewとIDだけをhash-bound approvalとして記録する。明示呼び出し専用。"
disable-model-invocation: true
---
# upstream-approve

対象・目的はコマンド後の文章から読む。modeは`approve`に固定する。
共通CLI: `intelliforge kit-run speckit --agent claude --`

現在のユーザー発言が具体的なreviewのIDを明示承認した場合だけ記録する。
`review --latest`を読む。指定されたreview_idを優先し、曖昧なら確認する。
`approve --review <ID> --id <item> --by <label> --reference <今回の発言>`をdry-runする。
一致を確認して`--apply`。全部承認はこのreview全体への明示承認がある場合だけ。
checkとapproval-planを再確認する。STALE系は再レビューし、自動再承認しない。
STALE_REVIEW等は再レビューへ戻す。記録は本人性の暗号認証ではない。未適用なら未記録と報告する。
詳しい手順: `../../assets/references/PHASES.md`の承認節。
最後は確認ページと記録したID・承認状態を示す。

## 配布環境の呼び出し
このPluginの管理ソースは `tools/speckit-upstream/kit.json`。導入先は `intelliforge locate --only speckit --agent claude` で確認する。Pythonヘルパーは `intelliforge kit-run speckit --agent claude --tool <ファイル名> -- <引数>`、研究・UXハーネスは `intelliforge kit-run speckit --agent claude -- <引数>` から実行する。Windowsではこの入口を使い、Bashやpython3という実行名を前提にしない。
Claude Code対応は試験対応。実機未検証の機能を検証済みと扱わない。
