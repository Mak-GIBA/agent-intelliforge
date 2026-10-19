# 追加配布経路の検証

[導入手順](cross-platform.md) · [開発手順](cross-platform-development.md)

2026-10-13にLinux環境で確認しました。既存のCodex経路を互換性の基準にし、追加経路は一時ホーム・一時設定・一時Skillディレクトリで検証しています。
本ページの追加配布経路の検証では、このPCの既存Skill、フック、MCP、AGENTS.mdを更新していません。後続のDesign Research 2.6.0 / Upstream 2.1.0の変更と通常経路でのPC更新は[同版の検証記録](design-research/validation.md)、日本語Skillの実装と評価は[kotonohaの検証記録](codex-yomiyasu/kotonoha-validation.md)にまとめています。

## 確認済み

| 検証 | 結果・確認した性質 |
|---|---|
| 変更前の既存試験 | 313件、成功。環境条件により4件スキップ |
| 変更後の全体試験 | Python 3.11で340件、失敗なし。既存と同じ4件をスキップ |
| 追加経路の単体・契約試験 | 27件、成功。予定表示の無変更、経路選択、手動編集の保護、ステージング復旧、Plugin登録失敗時の資材復旧を確認 |
| プロセス制御 | 出力上限、タイムアウト、子プロセス回収、大きな入力のstdin受け渡しを一時プロセスで確認 |
| Windows分岐の契約 | モックで、公式npm配置の直接起動、メタ文字を含む引数の保持、未知のbatch shimの拒否、ClaudeのPowerShell選択、子プロセス限定の設定を確認 |
| 文字コード | UTF-8の資材を既定の文字コードに依存せず読み書きすること、入れ子の呼び出し・明示したencodingを保つことを確認 |
| Claudeプロトコル | モックによる構造化出力の受け渡し、非構造化・失敗出力の拒否、読み取り専用役割、Web無効設定、隔離不足時の停止を確認 |
| Workgraph | Claudeイベントのターン識別、armなしではStopを起動しないこと、明示arm後の一度だけの評価、Planの拒否、プロンプトを状態に保存しないことを確認 |
| Codexの実Plugin管理CLI | CLI 0.162.1で、一時環境への導入・再実行・通常更新・モード切替・上流のみの更新・診断・解除を確認 |
| yomiyasuの実上流検査 | 配布パッケージの`kit-run ... lint`から、ハッシュ検証した上流scriptを実行できることを確認 |
| Codexの実隔離 | 一時fixtureの読み取り成功と書き込み拒否を確認。モデル実行は含まない |
| Research / Upstream資材 | 既存の固定版ベースのハッシュ照合、現在のアップグレード層の組み立て、既存の組み立て検査・自己テストを実施 |
| 単一ファイル配布 | yomiyasu、GitHub管理、Office、Herdrの正本と生成結果を照合。yomiyasuの自己テスト、Bash構文検査も成功 |
| Plugin資材 | Marketplaceの参照・名前・root内への収容、Upstreamの明示使用設定を確認。Codex SkillはSkill Creatorの静的検査に合格 |
| 標準パッケージ | wheel・sdistを構築。一時venvでwheelを導入し、パッケージ内資材から`inspect`と上記の実Codex導入・検査を実行 |
| GitHub Actions | [コード変更のCI](https://github.com/Mak-GIBA/agent-intelliforge/actions/runs/38281776674)が全ジョブ成功。Ubuntuの全体試験340件・4件スキップ、Ubuntu / Windows Server 2025それぞれの共通試験27件、両OSのwheel・sdist構築と配布パッケージの`inspect`を確認 |
| 編集・生成の一致 | キット定義、OS・ホストアダプター、生成物のハッシュを照合。古い生成物での構築を拒否することを確認 |

GitHub管理とOfficeのソース展開では、元のpayloadハッシュと同じZIPを再生成しました。HerdrのPython正本も元の単一ファイルと一致します。
従来の`install_*.sh`は、一括入口に追加した生成コメントを除いて変更前のファイルハッシュと一致します。既定値、実行分岐、終了コードを変更する移行は加えていません。

実CLI試験では、Codexの`plugin marketplace upgrade`がGit Marketplace専用で、管理するローカルMarketplaceには使えないことを確認しました。
追加経路はローカル資材を更新したうえで、公式の`plugin add`から対象Pluginを再導入します。パッケージ更新時に実行場所が変わっても登録先を保持するため、ホストのキャッシュを独自に編集しません。

## 未実施・適用限界

- ネイティブWindows 11でのキット導入、junction、PowerShell、ProcessContainer、ブラウザー操作は実機検証していません。Windows Server 2025のCIでは共通CLI・プロセス回収・配布形式を確認していますが、Windows 11での一連の利用を保証するものではありません。
- Claude Codeの実CLIによる`plugin validate`、実Plugin導入、認証、MXCでのモデル実行、研究・UX評価の全工程は未実施です。モックの成功をClaude実機の成功と扱いません。
- Skill Creatorの検査はCodex形式向けです。Claude公式の`disable-model-invocation`などの拡張は独立した契約検査の対象であり、Codexのvalidatorに合わせて削除していません。
- 新しい文章品質、研究結果の品質、画像レビューの精度はこの配布変更では測定していません。インストール成功と生成品質の改善は別です。
- 追加経路は既存の単独Skill・Workgraphフックとの競合を自動移行しません。既存設定と手動編集を残すため、移行先が競合していれば停止します。
- Claudeで利用できない製品専用機能を代替済みと扱いません。UXにはローカルPlaywrightを接続し、画像生成などの任意機能は利用者が接続した対応ツールの範囲で利用します。
- Officeの完全なページ描画、Docling、任意MCP、HerdrのWindowsセッション操作は別途実機確認が必要です。

保守用の構造化結果は[validation.json](cross-platform/validation.json)に残しています。検証に使ったローカルホームのパス、認証情報、会話内容は収録していません。
