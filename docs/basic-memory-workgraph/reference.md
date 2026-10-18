# Basic Memory Workgraph：保存方針・配置・仕組み

[English](../en/basic-memory-workgraph/reference.md) | **日本語**

[概要](README.md) · [導入](installation.md) · [使い方](usage.md) · [共有](sharing.md) · [仕組み](reference.md) · [困ったとき](troubleshooting.md) · [docs一覧](../README.md)

ターミナルのコマンドは、特に指定がなければこのリポジトリのルートで実行します。
「Codexへの依頼例」はCodexの会話欄に入力します。

<a id="details"></a>

## 保存方針・配置・仕組み

### 保存品質

正本は[memory-policy.md](../../tools/basic-memory-workgraph/memory-policy.md)です。抽象Memoryの自動保存は、以下をすべて満たす知識に限ります。

| 基準 | 内容 |
|---|---|
| 再利用性 | 元の案件以外で使える具体的な場面がある |
| 有用性 | 次回の判断・手順を改善し、失敗や再調査を減らす |
| 根拠 | 実際の確認で裏付けられている。十分な検証なら1回でもよい |
| 持続性 | 適用条件・例外・再確認条件が明確 |
| 追加価値 | 既存メモや容易に確認できる一般知識にない価値がある |

明示された継続的な好みも、範囲と例外を添えて保存できます。
作業日誌、完了報告、成果物一覧、一般論、根拠のない推測は自動保存しません。
progressiveは修正なしの成功例も扱い、採用推定を観測事実と根拠を添えた解釈として区別します。
`acceptance` は明示承認、`assessments` は採用推定、`verification` は確認した性質です。
承認不明でも保存・文脈に合う再利用は可能で、検証だけの場合は採用評価を空にします。
検索用のObservationsには、文脈、再利用できる特徴、根拠の種類、限界をまとめます。実際の要求・出力・修正の順序はInteractionに残し、再利用前にその根拠と反証を確認します。
設計根拠と固定会話例の比較は[採用エビデンスの設計と評価](evidence-design.md)を参照してください。
新しい根拠・条件がなければ、既存ノートへ利用日時だけを追記することもありません。
重複検索に失敗した場合は、自動保存を見送ります。

`smart` は日本語・英語の修正・調整・成功・採用／撤回・作業上の発見や回避策の手掛かりと、Codexが意味的に認識した候補を使います。
すべてを捕捉する保証はありません。候補検出は保存の許可ではなく、内容の判断はCodexが行います。

### 作業の振り返りと指示の長さ

Codex自身の実行経路も、「試行・障害・対処・検証・次回の適用条件」の要約として振り返ります。
修正指示の有無によらず、確認できた学びだけを5基準で選びます。原因の推測と対処の検証は区別します。
フックには共通の保存基準を一度だけ渡し、事例・修正・監査・Skillレビューの詳しい手順は、対象の操作前に既存の参照資料を読みます。

開始・終了フック全文の短縮率は、変更前の[固定ベースライン](../../tests/fixtures/workgraph-prompt-baseline.json)と同じ4設定で検査します。
実行環境のパスだけを正規化し、共通ポリシー、参照案内、有効化コマンドも計数に含めます。
文字数による比較であり、実際のモデルの入力トークン数や保存判断の品質を測るものではありません。
自己テストでは各全文の20%以上の短縮、参照資料の配置、モード・設定の保持と、一度限りの評価を確認します。
保存可否の意味判断は[架空のシナリオ](../../tests/POLICY_SCENARIOS.md)で別に点検します。

2026-10-12の確認値です。`auto=smart / correction=scoped / case=progressive / skill=review`で比較し、
標準設定、事例・Skill登録を有効にした設定、自動保存offでも同じ短縮基準を満たしました。

| フック全文（文字数） | 変更前 | 変更後 | 削減率 |
|---|---:|---:|---:|
| 開始時 | 20,120 | 13,604 | 32.4% |
| 終了時 | 18,282 | 13,310 | 27.2% |

自動保存offでは終了時の保存評価を起動しません。共通ポリシー本文は16,628文字から12,718文字へ短縮しています。
Workgraphの38テストと既存環境更新の14テスト、Bash構文検査を通過しました。

### Planでは参照のみ、実装モードで保存評価

開始時フックは検索方針と、そのセッション・ターンだけの有効化コマンドを渡します。
Codexが**現在は実装モードかつ書き込み可能**と確認した場合にだけ、回答前にその補助コマンドを実行します。
通常はユーザーがコマンドを操作する必要はありません。Plan／読み取り専用や追加評価中は実行しません。
終了時フックは有効化済みターンだけ、一度の保存評価を依頼します。

Planでも過去のMemoryを検索・参照できます。終了時の短い判定プロセス自体は呼ばれますが、
保存評価の追加ターンは起動しません。トークンなし・古いトークン・別ターン・設定不備・`auto=off`も評価しません。
更新前に始まったターンはトークンがないため、追加評価を見送ります。

Codex 0.157.1のフック入力の `permission_mode` は承認設定由来で、Plan／実装モードを
判別できません（[該当実装](https://github.com/openai/codex/blob/rust-v0.157.1/codex-rs/core/src/hook_runtime.rs#L1031)）。
このため有効化はCodexによるモード確認に依存し、確認漏れでは追加評価を見送ります。
`permission_mode=plan` が明示された場合も起動を拒否します。途中でPlanへ変わった場合は、
有効化済みでも保存を行わないようpolicyで要求します。ホスト側のモードを直接検証する仕組みではありません。

状態にはランダムな制御トークン、候補・有効化フラグ、形式版のみを保持し、会話本文は記録しません。
トークンは終了時に消費し、同じ評価の並行実行・再実行を防ぎます。raw transcriptの読み取りは行いません。
MCPサーバー側で全クライアントの書き込みを強制的に制限する仕組みではありません。

### ノートの配置

| フォルダー | 用途 |
|---|---|
| `rules/` | 条件付きのルール、明示された継続的な好み |
| `workflows/` | 再利用手順、Skill化判断と背景 |
| `validations/` | 再利用できる確認方法 |
| `cases/` | 具体的インタラクション、既存の自由形式事例 |
| `corrections/` | 明示保存依頼または `correction=scoped` による文脈付き修正指示 |
| `artifacts/` | 成果物や登録済みSkillへの参照 |
| `projects/` | 明示依頼による長期スコープ |
| `schemas/` | ノート構造の定義 |

従来の7種類を維持し、新項目は任意項目として追加しています。既存ノートを一括変換しません。
具体事例は `type: case` のMarkdown内に、版付きのJSONブロックとして保持します。
通常のObservations／Relationsも使えるため、`generalized_to` / `learned_from` 等で抽象Memoryと結べます。
詳細と記入例は[CAPTURE.md](../../tools/basic-memory-workgraph/templates/CAPTURE.md)を参照してください。

Skillのレビュー基準と登録手順は[SKILL_REVIEW.md](../../tools/basic-memory-workgraph/templates/SKILL_REVIEW.md)にあります。
登録済みSkillのArtifactは `kind: skill` と `skill:<name>` を持ち、Workflowから `packaged_as` で結びます。
実行手順はSkill、背景・根拠・適用条件はWork Graphに残します。関連付けのためだけにノート一式を作りません。

### 共有・学習用メタデータ

| frontmatter | 既定 | 意味 |
|---|---|---|
| `sharing_scope` | `private` | `team` / `public` の明示で共有対象を指定 |
| `training_use` | `excluded` | `approved` の明示で学習利用を指定 |
| `privacy_review` | `pending` | 内容レビューの状態 |
| `review_sha256` | なし | 本文・メタデータに結び付いたレビューの指紋 |
| `integrity_status` | `unreviewed`扱い | 整合性の点検状態。`needs_review` は共有・学習用出力を保留 |

項目がない旧ノートはprivate・学習対象外として扱います。
これはCLIの出力対象を選ぶための指定であり、ファイル自体のアクセス制御や暗号化ではありません。

### インストール先のファイル

以下は `${CODEX_HOME:-$HOME/.codex}` 配下です。

| 配置 | 内容 |
|---|---|
| `basic-memory.json` | 保存先と共通policy。`checkpointOnCompact=false` |
| `basic-memory-workgraph/config.json` | 評価・事例・Skillのモード |
| `basic-memory-workgraph/memory-policy.md` | 開始・終了hookの共通基準 |
| `basic-memory-workgraph/templates/` | 事例形式、Skillレビュー、スキーマの参照資料 |
| `basic-memory-workgraph/workgraph_tools.py` | 共有・JSONL出力・点検・Skill登録CLI |
| `basic-memory-workgraph/workgraph_sequence.py` | Case v2の構造・根拠参照検証 |
| `basic-memory-workgraph/workgraph_github.py` | privateリポジトリへのPR作成・取り込み・更新CLI |
| `basic-memory-workgraph/github-sharing.json` | 初回setupで保存する共有先・送信元・プロジェクトの設定 |
| `basic-memory-workgraph/github-state/` | 取り込み済みノートの指紋・取得コミット・操作ロック。本文は保持しない |
| `AGENTS.md`の管理ブロック | メモリ共有・取り込みの依頼から共有手順を読む入口。他の指示は保持 |
| `hooks/basic_memory_workgraph.py` | 方針注入、検索案内、保存評価依頼 |
| `hooks.json` | hook登録 |

導入済みCLIは、リポジトリ以外の場所からも実行できます。

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/workgraph_tools.py" --help
```

この場合も、そのPython環境にPyYAMLが必要です。
GitHub共有CLIにはgit・ghも必要です。認証情報はgh・Gitの既存設定を使い、共有設定には保存しません。
定期送信や保存hookからの送信はありません。操作例は[GitHub経由の共有](github-sharing.md)を参照してください。
公式pluginの設定探索はその仕様に従います。プロジェクトの `.codex/basic-memory.json` に
設定がある場合、ユーザー設定より優先されることがあります。
既存の `captureEvents` は保持します（未設定ならtrue）。公式pluginのイベント記録とは別に、
本フックでは本文を記録しません。圧縮時の自動checkpointは無効です。
