---
name: upstream-review
description: "次の承認チェックポイントを固定し、ユーザーが確認するreview packetを作る。明示呼び出し専用。"
---
# upstream-review

対象・目的はコマンド後の文章から読む。modeは`review`に固定する。
共通CLI: `intelliforge kit-run speckit --agent codex --`

`doctor`と`overview`で対象を確認し、`approval-plan`で未承認・staleのIDを読む。
`review --project <root> --checkpoint next --write`で本文とIDを固定する。
対象ID・要旨・未解決事項・共通条件・固定レビューのリンクを提示する。
どのIDを承認・修正するか確認する。明示承認までapproveは実行しない。
沈黙や過去の一般的なOKを今回の承認に使わない。review作成自体は承認ではない。
詳しい確認手順: `../../assets/references/PHASES.md`のレビュー節。
最後は確認ページへのリンク1つと今回の対象IDを示す。

## 配布環境の呼び出し
このPluginの管理ソースは `tools/speckit-upstream/kit.json`。導入先は `intelliforge locate --only speckit --agent codex` で確認する。Pythonヘルパーは `intelliforge kit-run speckit --agent codex --tool <ファイル名> -- <引数>`、研究・UXハーネスは `intelliforge kit-run speckit --agent codex -- <引数>` から実行する。Windowsではこの入口を使い、Bashやpython3という実行名を前提にしない。
