# Repository Director

[English](../en/repository-director/README.md) | **日本語**

[導入・移行](installation.md) · [使い方](usage.md) · [検証範囲](validation.md) · [docs一覧](../README.md)

リポジトリの目的と運営方針を決め、上流文書を索引でつなぎ、その資料を参照して開発を進めるSkillです。
既存コードから仕様書・AGENTS・READMEを後付けする用途と、新規開発の両方に対応します。
GitHubのIssue・PR・Projects、GitLabのIssue・MR、コミットの説明も扱います。

旧GitHub Project DirectorとSpecKit Upstreamを統合した独自キットです。旧スクリプト・キットID・Skillの互換入口は廃止しました。
公式SpecKit、専用JSON、承認台帳、研究ツールを必須にしません。既存の文書・SpecKit資材・履歴は保持できます。

## 文書のつなぎ方

短いREADME（目的・始め方）とAGENTS（開発ルール）から、docsの索引と用途別の仕様へ進みます。
目的・背景、運営方針、要件、全体設計、コアロジック、検証・運用を分け、必要な場合は機能別に追加します。
既存の日本語名・独自配置の正本を優先し、重複作成や一律の移動を避けます。
依頼者の要望は背景・理由・採否や保留・仕様への反映を要約し、必要な出典を添えます。

参考にしたLISTBOXのAGENTS・README・索引と6つの仕様書は、役割分担、相互参照、現状と未確認の区別を実際に確認しました。
LISTBOX固有の技術選定やテスト制約を他のプロジェクトへ強制しません。[確認内容](validation.md#参考構成の確認)

## 最初の依頼

対象リポジトリでCodexへ入力します。

```text
$repository-director
既存コードを調べ、仕様書とAGENTSとREADMEを整えて。実装は変えず、分からない業務要件は確認して。
```

対話が既定です。「お任せで」と指定すると、開発上の方針を選んで理由と仮定を残します。
事業目的、依頼者の合意、実行していない検証結果は推測しません。
インストールは対象プロジェクトを変更せず、文書整備は別の依頼で行います。
