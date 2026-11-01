# Repository Directorの使い方

[English](../en/repository-director/usage.md) | **日本語**

[概要](README.md) · [導入・移行](installation.md) · [検証範囲](validation.md)

## 既存コードから文書を整備する

```text
$repository-director
このプロジェクトのコード・テスト・既存資料を調べ、上流文書とAGENTSとREADMEを整えて。
実装は変更しないで。重要な不明点は対話で詰めて。
```

まず全体像と対象範囲を把握し、機能・権限・主要処理・データ・テストを追って本文を作成します。
既存仕様は索引へつなぎ、足りない目的・運営方針・コアロジックの説明を補います。
実装から確認した現状、合意済み要件、改善提案を分け、矛盾や未実装を隠しません。
実行環境がなければ静的調査として範囲を示し、未実行のテストを成功と記載しません。
文書整備だけではソース、依存、ロックファイル、DBを変更しません。

```text
packages/searchだけを対象に、お任せで方針を整理して。既存のルールは残して。
```

モノレポは対象外のパッケージを変更せず、親の方針を守ります。
お任せでも事業上の目的・正式な要件を作りません。不明点と仮定を残します。

## 新規開発と通常の変更

```text
$repository-director
社内文書を検索するアプリの目的と要件、設計、検証方法、開発方針を整理して。
```

```text
$repository-director
検索方式を変更して。運営方針と関連設計を読み、実装・テスト・説明文書を一緒に更新して。
```

目的・利用者・制約から要件と設計を整理します。方式の不確実性が高い場合は利用可能な研究Skillで根拠を調べます。
小さな変更で全資料を作り直さず、関係する仕様と検証条件だけを見直します。

## 文書ヘルパー

```bash
repository-director inspect --project /absolute/path/app
repository-director init --project /absolute/path/app --mode existing
repository-director init --project /absolute/path/app --mode existing --apply
repository-director check --project /absolute/path/app
repository-director check --project /absolute/path/app --base main
```

`init`は索引、案内、明示的な下書きの配置です。本文を調査・策定するAI処理ではありません。
Skillがコードを調べて内容を仕上げます。下書きのまま整備完了とは報告しません。
既存本文と独自ルールは保持し、同じ処理の再実行で節を重複させません。
独自の正本には `--document requirements=specs/current.md`、索引には `--index docs/navigation.md` を指定できます。
役割名は purpose / policy / requirements / architecture / core / verification です。
`--approach delegate`はお任せの下書き方針、Claudeの共通入口には `--agent claude` を使います。

Pluginでは次の入口を使います。WindowsでもBashに依存しません。

```text
intelliforge kit-run repository-director --agent claude -- inspect --project <target>
intelliforge kit-run repository-director --agent claude -- check --project <target>
```

`check`の終了値は0が構造エラーなし、1がリンク等の構造エラー、2が実行・入力エラーです。
下書きや索引から到達できない文書は確認候補です。意味的な一致やテスト結果の真実性は内容と実測で確認します。

## 変更説明とリモート操作

```text
この差分のコミットメッセージとPR本文を作って。目的と変わる動作、確認結果、残件が伝わるかも確認して。
```

```text
GitLabのこのMRをレビューして。指摘は会話に返して。
```

元の依頼・差分・検証結果と文章を照合します。未確認を隠さず、短い変更は短く説明します。
レビューや下書きの依頼だけでは投稿しません。GitHub/GitLabの実操作は接続済みツールまたは公式gh/glabを使い、対象・権限・重複を確認します。
合意済み範囲の投稿は同じ許可を聞き直さず、反映後に再取得して確認します。
