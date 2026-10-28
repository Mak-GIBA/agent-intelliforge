# Agent Intelliforge ドキュメント

[English](en/README.md) | **日本語**

[リポジトリ概要](../README.ja.md) · [一括インストール](installation.md) · [開発・検証](development.md)

[共通CLI・Windows・Claude Code](cross-platform.md) · [配布資材の編集手順](cross-platform-development.md) · [追加経路の検証結果](cross-platform-validation.md)

目的に合うキットを選び、概要・導入手順・使い方の順に読めます。
Linux / WSL2でCodexへ導入する場合は[一括インストール](installation.md)、ネイティブWindowsやClaude Codeでは[共通CLIの導入ガイド](cross-platform.md)から始めてください。
導入済みなら、表の「導入後の使い方」から依頼例と確認方法へ進めます。

| 対象 | 概要・収録ツール | インストール・更新・解除 | 導入後の使い方 |
|---|---|---|---|
| 知識を蓄積する | [Basic Memory Workgraph](basic-memory-workgraph/README.md) | [導入手順](basic-memory-workgraph/installation.md) | [使い方と設定](basic-memory-workgraph/usage.md) |
| OOUIからUI/UXを設計し、実装・画像付き検証・改善を進める | [Codex UX Stack](codex-ux-stack/README.md) | [導入手順](codex-ux-stack/installation.md) | [使い方](codex-ux-stack/usage.md) |
| ストーリーから要件・方式研究・全体設計へ進める | [SpecKit Upstream](speckit-upstream/README.md) | [導入手順](speckit-upstream/installation.md) | [使い方](speckit-upstream/usage.md) |
| GitHubのIssue・PR・Projects・進捗を整理する | [GitHub Project Director](codex-github-pm/README.md) | [導入手順](codex-github-pm/installation.md) | [使い方](codex-github-pm/usage.md) |
| コアロジックをテーマ別に比較・実測・再評価する | [Design Research](design-research/README.md) | [導入手順](design-research/installation.md) | [使い方](design-research/usage.md) |
| ECCを導入し、必要なスキルだけ参照する | [Codex ECC](codex-ecc/README.md) | [導入・更新・復元](codex-ecc/installation.md) | [使い方](codex-ecc/usage.md) |
| PDF・Word・PowerPointを閲覧・編集する | [Office Workbench](codex-office/README.md) | [導入手順](codex-office/installation.md) | [使い方](codex-office/usage.md) |
| 日本語を明晰にし、段落・説明・表現・留保を整える | [kotonohaと日本語執筆](kotonoha/README.md) | [導入手順](kotonoha/installation.md) | [使い方](kotonoha/usage.md) |
| 作業ディレクトリからターミナルworkspaceを開く | [Herdr](herdr/README.md) | [導入とBash設定](herdr/installation.md) | [使い方](herdr/usage.md) |

## キットを組み合わせる

画面の設計と日本語UI文言にはUX Stackとkotonohaを使えます。UX Stackで対象・操作・状態を整理し、kotonohaでラベルや説明を推敲します。短いラベルは長文化せず、必要な情報を隠さないことを優先します。

### Design ResearchとUpstreamを組み合わせる

まず[出力先と確認の順序](upstream-research-workflow.md)を読み、対象アプリの確認ページから正本・研究報告・採用した証拠へ進みます。8つのコマンドの確認事項と、予約管理・検索改善の具体例をまとめています。

機能・システム全体の設計は`$upstream-new`・`$upstream-change`、特定の方式の研究は`$design-research`から始めます。
短い依頼から、ストーリー・懸念・ユースケース・要件、テーマ別研究、統合設計、検証計画へ進みます。

- [Upstreamの使い方](speckit-upstream/usage.md)：作業の順序、図・画面例、レビューと明示承認。
- [研究テーマの分割と既存判断の見直し](speckit-upstream/reassessment.md)：複数テーマの依存・統合と場面別の入口。
- [Design Researchの使い方](design-research/usage.md)：候補比較、報告、再評価・中断再開・状況確認。
- [組み立てと現在の検証範囲](design-research/validation.md)：同梱試験、組み立て・更新・診断の結果と、修正前の停止条件。

## Workgraphを詳しく使う

- [ナレッジグラフの構造と具体例](basic-memory-workgraph/knowledge-graph.md)
- [Memoryの共有・インポート・学習用JSONL出力](basic-memory-workgraph/sharing.md)
- [保存方針・配置・仕組み](basic-memory-workgraph/reference.md)
- [困ったとき・記憶の点検](basic-memory-workgraph/troubleshooting.md)
- [採用エビデンスの設計と評価](basic-memory-workgraph/evidence-design.md)

## ECCの管理CLIを詳しく使う

[ECCを必要なときに読む](ecc-on-demand.md)で、原本の検索・取得、更新・復元、停止する起動時処理を説明しています。

## 文書の読み方

`bash`や`python3`のコードブロックはターミナルで実行します。特に指定がなければ、
このリポジトリのルートが作業場所です。`text`の依頼例はCodexの会話欄へ入力します。
SpecKitのプロジェクト操作、各Skillの利用例、Herdrの起動は、作業対象のプロジェクト側で行います。

「Plugin」は機能をまとめた配布単位、「Skill」はCodexが参照する作業手順、
「MCP」は外部ツールをCodexから呼び出すための接続です。
「CLI」はターミナルで実行するコマンド、「hook」は会話等のイベントに応じて動く処理を指します。

各ガイドのインストール挙動は、このリポジトリにあるスクリプトを基準にしています。
外部ツールの配布名や機能は変わることがあるため、参照資料と導入時の確認方法も掲載しています。

## 開発・説明の追加

[開発ガイド](development.md)に、検証方法、説明の保守方針、
[新しいインストーラー用の雛形](_templates/installer/README.md)の使い方をまとめています。
