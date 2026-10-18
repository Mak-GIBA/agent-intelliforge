# UpstreamとDesign Research：出力先と確認の順序

対象アプリで最初に開くのは、`docs/upstream/README.md`の確認ページです。今の段階、今回確認する文書とID、承認待ち、研究の状態、次の操作をまとめています。Upstream 2.1.0 / Design Research 2.6.0以降では、文書・研究・レビュー・承認の更新後にこのページを更新します。保存先を変更したプロジェクトでは、設定された`docs_dir`の`README.md`が入口です。

ページの内容を最新状態で読むには、対象アプリのターミナルで次を実行します。通常の表示はファイルを書き換えません。

```bash
speckit-workbench overview --project .
speckit-workbench overview --project . --json
# 文書を変更した後、保存する確認ページも更新する
speckit-workbench overview --project . --write
```

既存の`README.md`がある場合は上書きしません。`--write`は競合を知らせるため、元の内容を残して移動・統合した後に生成します。既存資料を読むだけの依頼では、確認ページの保存も行いません。

## どこに何が保存されるか

文書の正本、研究の報告、完全な実行記録には異なる役割があります。正本の要件・設計・検証を確認し、判断の根拠が必要な箇所から研究報告と固定した証拠へ進みます。

| 場所 | 内容 | 確認すること | Gitへの保存 |
|---|---|---|---|
| `docs/upstream/README.md` | 生成する確認ページ | 今の段階、対象ID、未解決事項、次の操作 | 共有する案内として保存できる |
| `docs/upstream/requirements.md` | 目的、利用場面、ストーリー、機能・品質・制約 | 何を達成するか、受入条件、現状と合意と提案の区別 | 正本として保存 |
| `docs/upstream/design.md` | 全体構成、採用方式、変更影響、研究との対応 | 要件を満たす根拠、関連ID、統合時の制約 | 正本として保存 |
| `docs/upstream/verification.md` | 検証計画、合格条件、実行結果 | 未実行と実測の区別、設計との対応 | 正本として保存 |
| `specs/<feature>/` | SpecKit公式の機能別`spec.md`、`plan.md`、`tasks.md`等 | 機能の詳細と実装タスク | 必要な機能詳細を保存 |
| `docs/design-research/<topic>/report.md`、`figures/` | 最新の研究報告と図 | 比較条件、結論、測定結果、限界 | 報告として保存 |
| `docs/design-research/<topic>/evidence/<run-id>/` | 採用runの固定報告、入力・出力、必要な実行記録とmanifest | 報告の根拠、欠落・改変がないか | 設計判断に使ったものを保存 |
| `.artifacts/design-research/<topic>/` | 新規テーマの完全なrun、状態、試行、作業コピー、詳細ログ | 中断の再開、再検討、実行失敗の調査 | 新規テーマ作成時にignore。通常はローカルのみ |
| `.specify/workbench/` | 研究計画、固定レビュー、対応索引、承認台帳、gate | 承認対象と整合性、運用の調査 | 合意・計画の追跡に必要な記録を保存 |

`report.md`は更新される最新報告です。設計が採用した根拠は、run IDを指定した`evidence/`の固定報告に結びます。新しい案を採用する際は新しいrunを出力し、既存の証拠を上書きしません。

以前からあるテーマは保存先を維持します。旧テーマの`docs/design-research/<topic>/runs/`は移動・削除せず、新しいCLIでも読み取り・再開・再検討できます。既に追跡されている記録をignoreの追加で追跡解除することもありません。

## 8つのコマンドで確認すること

以下はCodexの会話欄で選ぶSkillです。どの入口でも、最後は確認ページと今回の対象IDを案内します。文書を用意したこと、レビューしたこと、承認を記録したこと、アプリが動作したことは別々に確認します。

| 入口 | 更新・出力するもの | ユーザーが確認する箇所 | 今回の完了条件と次の操作 |
|---|---|---|---|
| `$upstream-new` | 要件・設計・検証。必要なら`specs/`と研究報告 | 利用者の目的、ストーリー、受入条件、構成と検証方針 | 対象範囲の文書と未決事項が整理されたらreviewへ |
| `$upstream-existing` | 既存の正本。現状・合意・改善案を区別 | 実装の出典、既存合意との差、推測が混じっていないか | 現状と提案の境界を確認し、合意する変更をreviewへ |
| `$upstream-change` | 変更対象の要件・設計・検証 | 変更理由、影響するID、互換性・移行 | 変更範囲と再確認対象が揃ったらreviewへ |
| `$upstream-bug` | 期待挙動、再現根拠、設計・回帰検証計画 | 再現条件、期待との差、修正方針 | 原因と未確認事項を整理し、方針のreviewへ。修正実行は別途依頼 |
| `$upstream-refactor` | 不変条件、品質目標、設計・移行計画 | 外部挙動、改善の測り方、切り戻し | 不変条件と改善条件を確認してreviewへ |
| `$upstream-check` | 点検結果。修正依頼がある場合だけ正本を更新 | 曖昧さ、矛盾、根拠不足、stale | 点検結果と修正対象が分かったら必要な修正・再レビューへ |
| `$upstream-review` | `.specify/workbench/reviews/`の固定レビュー | 本文・共通条件、対象ID、未解決事項 | 承認または修正するIDを指定する。作成だけでは承認されない |
| `$upstream-approve` | 明示承認したIDの承認記録 | review ID、対象ID、現在の承認状態 | 記録と整合性を確認し、次の段階へ。staleなら再レビュー |

## 例1：予約管理の標準的な設計

「スタッフが今日の予約を確認し、変更・取り消しをできるようにしたい」と`$upstream-new`へ伝えます。Codexは目的、利用場面、重複予約などの懸念から要件を整理します。既存のCRUDやトランザクションで解ける部分は、その根拠を記録し、研究の必要性を判断します。

要件`BOOK-FR-001`を「予約の変更が一件だけ保存される」、設計`BOOK-DES-001`を「更新をトランザクションで扱う」、検証`BOOK-TEST-001`を「同時変更時の保存件数を確認する」とした例です。これらは説明用のIDであり、実行済みの結果ではありません。

確認ページから、要件の受入条件、設計の方式と関連ID、検証の手順・合格条件を順に確認します。予約機能の詳細が必要なら`specs/<feature>/`へ進みます。研究を実行していなければ、研究報告や証拠の出力はありません。今回のIDをreviewで固定し、承認するIDを指定した後にapproveで記録します。検証計画が承認されても、アプリのテストはまだ未実行です。

## 例2：検索精度を改善する方式研究

「検索の取りこぼしを減らしたい。応答時間も維持したい」と`$upstream-change`へ伝えます。Codexは要件を見直し、不確実な部分を候補抽出と順位付けなどのコアロジックに分けます。`.specify/workbench/research-plan.json`には、関連要件ID、研究の問い、固定する入力・評価条件、依存関係を記録します。

各テーマをDesign Researchで調べた後、確認ページから`docs/design-research/ranking/report.md`へ進みます。最初に比較条件・基準案・候補案の実出力、主要指標、失敗例、限界を確認します。研究が`research_complete`でも、方式を全体設計へ採用したことや効果が実測されたことは別に確認します。

例えば採用するrunが`RUN-EXAMPLE`なら、Codexは次の操作で必要な証拠を確認・固定します。run IDとtopicは実際の値に置き換えます。

```bash
bash <design-research-skill>/scripts/gan-harness.sh export-evidence \
  --project . --topic ranking --run-id RUN-EXAMPLE --related-id SEARCH-DES-001
# 出力対象を確認した後、同じ引数で適用
bash <design-research-skill>/scripts/gan-harness.sh export-evidence \
  --project . --topic ranking --run-id RUN-EXAMPLE --related-id SEARCH-DES-001 --apply
```

出力は`docs/design-research/ranking/evidence/RUN-EXAMPLE/`です。manifestにrun ID、ソースの版、関連ID、ファイルのハッシュを記録します。必要なstdout・stderr、評価入力・出力、実行receipt、要件・研究計画の固定入力も残します。根拠に必要なファイルがない、またはハッシュが一致しない場合は出力を止めます。

Codexは返されたbindingに、採用候補、関連する設計ID、採用理由を加え、design.mdのv3 bindingへ反映します。ユーザーは設計の要件IDとの対応、固定報告へのリンク、全体での精度・速度・費用の検証方針を確認します。個別研究の成功を全体の成功に置き換えず、統合後の検証計画をverification.mdへ戻してからreviewへ進みます。

## clone後に根拠を確認する

Gitに保存するのは、人が読む報告・図と、設計に採用した証拠一式です。途中の試行や作業コピーはローカルに残します。共有する対象をGitの差分で確認し、コミット・pushは通常の操作として行います。

別のPCでcloneした後は、確認ページ、正本、固定報告、図を読むことができます。ローカルの`.artifacts/`がなくても次の検証は実行できます。

```bash
bash <design-research-skill>/scripts/gan-harness.sh verify-evidence \
  --package docs/design-research/ranking/evidence/RUN-EXAMPLE
```

この検証は、記録された依存ファイルの存在とハッシュの一致を調べます。研究の科学的な正しさ、本人性、ユーザーの承認を証明するものではありません。中断runの完全な再開には元のローカル実行記録と環境が必要です。条件や要件が変わった場合は、同じrunを再開せず新しい研究・再検討を行います。

## Skillの入口と詳しい手順

8つのUpstream Skillは入口に必要な指示だけを持ち、`flow --brief`と段階別の`PHASES.md`へ進みます。通常の`flow`は従来どおり詳しい手順を表示します。Design Researchも、状態確認では実行用の長い参照を読み込まず、研究を実行する段階で評価・保存単位・証拠の契約を読みます。

入口の文字数と、開始時に必ず読む資料の文字数を別々に測定します。詳しい契約を別ファイルへ移しただけで読み込み量が減ったとは扱わず、必要な段階で必要な参照を読む構成にします。
