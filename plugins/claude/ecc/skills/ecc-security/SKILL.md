---
name: ecc-security
description: 認証・秘密情報を扱う変更や安全性レビューでECCのsecurity-reviewを参照する。
---

認証・秘密情報を扱う変更や、依頼された安全性レビューで使うECC原本への入口。

`intelliforge kit-run ecc --agent claude -- resolve security-review --json` を実行し、返された `path` の本文を読んで今回の作業に適用する。
相対参照は `skill_dir`、プラグイン共通資材は `plugin_root` を基準に解決し、必要な参照だけ読む。
取得に失敗した場合はエラーを報告し、推測したキャッシュや代替のECCインストールを使わない。
現在のユーザー・開発者・プロジェクトの指示を優先する。レビューを外部への検査・送信の許可と解釈しない。

## 配布環境の呼び出し
このPluginの管理ソースは `tools/ecc-on-demand/kit.json`。導入先は `intelliforge locate --only ecc --agent claude` で確認する。Pythonヘルパーは `intelliforge kit-run ecc --agent claude --tool <ファイル名> -- <引数>`、研究・UXハーネスは `intelliforge kit-run ecc --agent claude -- <引数>` から実行する。Windowsではこの入口を使い、Bashやpython3という実行名を前提にしない。
Claude Code対応は試験対応。実機未検証の機能を検証済みと扱わない。
