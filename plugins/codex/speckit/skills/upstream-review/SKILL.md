---
name: upstream-review
description: "次の承認チェックポイントを固定し、ユーザーが確認するreview packetを作る。明示呼び出し専用。"
---
# upstream-review — ユーザー合意のためのレビュー固定化

共通CLI: `intelliforge kit-run speckit --agent codex --`
方式: `../../assets/references/METHOD.md`
成果物と確認先: `../../assets/references/ARTIFACTS.md`

## 契約
このSkillは「何をユーザーに確認してもらうか」を固定する。承認そのものは記録しない。
沈黙、次の話題への移動、過去の一般的なOKを今回の承認とみなさない。

## 必ず実施
1. 対象プロジェクトを確認し、`intelliforge kit-run speckit --agent codex -- doctor --project <root>` を実行する。
2. `intelliforge kit-run speckit --agent codex -- approval-plan --project <root>` で現在のapproval profileと未承認/再承認項目を確認する。
3. 原則として `intelliforge kit-run speckit --agent codex -- review --project <root> --checkpoint next --write` を実行する。
   ユーザーが明示したcheckpointがあれば、そのcheckpointを使用する。
4. 保存されたreview packetの内容を読み、以下をユーザーへ簡潔に示す。
   - review_id
   - 今回レビューするIDと要旨
   - 未決定事項・矛盾・適用範囲
   - 対象の節の本文と文書全体に適用する共通条件（旧形式は文書全体）
   - 既に承認済みだが変更でstaleになった項目
   ARTIFACTS.mdに従い、正本の確認箇所・対象IDと、固定したreview packetのMarkdownリンク1つを示す。JSONは調査に必要な場合だけ補足する。
5. 「どのIDを承認するか／修正するか」を確認して停止する。
   このSkill内ではapproveコマンドを実行しない。

## 禁止
- review packetを作っただけでstatusをapprovedへ変えない。
- 全項目を勝手に一括承認しない。
- アプリ実装、DB変更、デプロイを開始しない。

## 配布環境の呼び出し
このPluginの管理ソースは `tools/speckit-upstream/kit.json`。導入先は `intelliforge locate --only speckit --agent codex` で確認する。Pythonヘルパーは `intelliforge kit-run speckit --agent codex --tool <ファイル名> -- <引数>`、研究・UXハーネスは `intelliforge kit-run speckit --agent codex -- <引数>` から実行する。Windowsではこの入口を使い、Bashやpython3という実行名を前提にしない。
