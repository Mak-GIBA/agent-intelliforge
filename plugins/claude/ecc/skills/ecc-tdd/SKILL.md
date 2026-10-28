---
name: ecc-tdd
description: 新機能実装・不具合修正・リファクタリングで、言語共通のTDDと対象技術のテスト手順を適用する。コード変更を伴わない調査・文書修正は対象外。
---

`intelliforge kit-run ecc --agent claude -- resolve tdd-workflow --json` を実行し、返された `path` の原本を読む。

変更対象の言語、既存テスト、実行方法を確認する。`intelliforge kit-run ecc --agent claude -- search 'testing' --language typescript --json` の言語を対象に合わせ、関連するテスト原本を追加で読む。最初に読む原本はTDDを含め1〜3件に絞る。共通ライブラリや複数言語の変更は管理CLIのグローバル引数`--cwd`で対象ディレクトリを選んで判断し、無関係な言語で代用しない。

変更する振る舞いについて、期待した理由で失敗するテストを先に実行する。依存不足や構文エラーを期待した失敗と扱わない。最小限の実装で成功させ、必要なリファクタリング後に関連テストを再実行する。実行したコマンドと失敗・成功を区別して報告し、未実行を成功と扱わない。

現在のユーザー・開発者・プロジェクトの指示を優先する。既存の回帰テストで十分な場合は重複テストを増やさず、網羅率はプロジェクトの基準に従う。原本が取得できない場合は停止理由を示し、ECCの再有効化や更新で回避しない。

相対参照は返された `skill_dir`、共通資材は `plugin_root` を基準にする。他の原本は `resolve` で取得し、必要な節だけ読む。

## 配布環境の呼び出し
このPluginの管理ソースは `tools/ecc-on-demand/kit.json`。導入先は `intelliforge locate --only ecc --agent claude` で確認する。Pythonヘルパーは `intelliforge kit-run ecc --agent claude --tool <ファイル名> -- <引数>`、研究・UXハーネスは `intelliforge kit-run ecc --agent claude -- <引数>` から実行する。Windowsではこの入口を使い、Bashやpython3という実行名を前提にしない。
Claude Code対応は試験対応。実機未検証の機能を検証済みと扱わない。
