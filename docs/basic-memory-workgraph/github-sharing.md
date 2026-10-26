# GitHub経由でメモリを共有する

[English](../en/basic-memory-workgraph/github-sharing.md) | **日本語**

[概要](README.md) · [導入](installation.md) · [使い方](usage.md) · [ファイル共有・学習用出力](sharing.md)

自分と友人が共有してよい知識を非公開のGitHubリポジトリへ持ち寄り、それぞれのCodexから参照できます。
初回に共有先を接続すると、普段は「共有メモリーを同期して」と頼むだけで送信と取り込みをまとめられます。
Basic Memory全体をそのまま送る機能ではありません。共有対象として指定し、内容を確認したノートだけを送信します。
これはWorkgraphの追加機能で、Basic Memory Cloudへの契約は不要です。

```text
あなたの共有ノート → 非公開GitHub → 友人のPC
友人の共有ノート   → 非公開GitHub → あなたのPC
```

以下の「Codexへの指示例」は会話欄へ、「コマンド」はターミナルへ入力します。
`OWNER/REPO` は実際の共有リポジトリ名に置き換えてください。
コマンド例はLinux / WSLの従来インストーラー向けです。異なる導入環境では、Codexに共有CLIの導入先を確認してもらってください。

<a id="初回に準備するもの"></a>

## 1. 自分と友人のPCを準備する

双方のPCに[Workgraphを導入・更新](installation.md)し、新しいCodexセッションを開始します。
共有CLIにはPython・PyYAML・git・GitHub CLIの`gh`が必要です。Pythonは[導入手順](installation.md#python-tools)を参照してください。

共有先はREADMEで初期化した専用の非公開リポジトリを使います。
双方が送受信する場合は、双方のGitHubアカウントに書き込み権限が必要です。
所有者が友人へアクセス権を付与し、友人は招待を受け入れます。接続コマンドがリポジトリを作成したり、友人を招待したりすることはありません。

準備をCodexへ頼む場合は、次を使えます。

```text
友人とBasic Memoryの知識をGitHubで共有したいです。
共有先はOWNER/REPOです。
このPCに必要なWorkgraphの導入・更新、git・ghの準備、GitHubログインを補助してください。
共有先の存在と非公開設定、私のアクセス権を確認し、不足する作業だけ案内してください。
この段階ではメモリーを送信しないでください。
```

ブラウザー認証が必要な箇所は本人が操作します。パスワードやトークンを会話へ貼る必要はありません。
手動でログインする場合は次を実行します。

```bash
gh auth login --hostname github.com --web --git-protocol https
gh auth setup-git --hostname github.com
```

新しい共有先が必要な場合は、所有者が次のように作成できます。

```bash
gh repo create OWNER/REPO --private --add-readme
```

<a id="初回接続と普段の同期"></a>

## 2. 初回だけ共有先へ接続する

自分と友人が、それぞれのPCで同じ共有先へ接続します。

```text
共有先はOWNER/REPOです。connectで接続してください。
自分の検証済み共有PRの自動マージと、この共有先にマージされた友人のメモリーの自動取り込みを有効にしてください。
まだノートを共有対象に指定したり、送信したりしないでください。
```

対応するコマンドは次です。

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/workgraph_github.py" connect --repo OWNER/REPO
```

`connect` は既存の送信設定を再利用します。新規ならGitHubユーザー名を送信元IDにし、登録済みの個人メモリーを送信元にします。
候補が複数あるときだけ `--project` / `--source-id` の指定が必要です。異なる人は別の送信元IDを使います。
通常、友人ごとの受信設定や保存先を手で作る必要はありません。

この接続は、自分の検証済みPRのマージと、共有先のマージ済み送信元の取り込みへの同意を含みます。
共有先へ追加される送信元も受信対象になるため、リポジトリの参加者は所有者が管理してください。
接続だけではノートの共有許可は付かず、アップロードも行いません。

## 3. 共有候補を確認してから初回アップロードする

まず、共有する候補と修正案を出してもらいます。

```text
友人に共有できそうなメモリーを確認してください。
個人情報や機密情報を除き、共有する候補と、送信前に修正する内容を一覧にしてください。
原本は変更せず、共有許可も付けず、送信もしないでください。
```

一覧と本文を確認し、問題がなければ対象を指定して承認します。
一部だけ共有する場合は、対象のノート名や番号を明示してください。

```text
提示した候補を、その修正内容で共有することを承認します。
対象ノートに共有指定と内容レビューを反映してから、OWNER/REPOへ送受信を同期してください。
学習利用は許可しません。
```

Codexは承認されたノートだけをレビューし、送信前に検査し、差分を確認します。
PRはGitHub上で変更を確認するための記録です。PR作成時点で、共有先の閲覧者は内容を読めます。
`sync` は自分のPRが現在のレビュー済みデータと一致し、自分の保存領域だけを変更していることを確認してからマージします。
GitHubの保護設定を迂回したり、友人のPRをマージしたりはしません。

## 4. 普段は同期を依頼する

初回設定後は、次の指示で送信と取り込みをまとめられます。

```text
共有メモリーを同期してください。
```

`sync` は次の処理を行います。

1. 共有指定・レビュー済みのノートを送信する。
2. 自分の検証済みPRをマージする。
3. 同じ共有先にマージされた友人のノートを取り込む。

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/workgraph_github.py" sync
```

友人も自分のPCで同期します。友人が同期して共有した後に自分が同期すると、その更新を取得できます。
常時自動同期ではなく、依頼またはコマンド実行時に更新します。差分がなければ新しいコミットやPRは作りません。

新規ノートには自動で共有許可が付かず、レビュー後に編集したノートは再確認が必要です。
新しい知識や編集内容も送りたい場合は、手順3の候補確認から進めてください。
送信の検査で保留になっても、独立して実行できる友人の更新取得は進めます。

予定だけ確認したい場合は、次を使います。

```text
変更せず、共有メモリーを同期した場合の送信・マージ・取り込み予定を確認してください。
```

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/workgraph_github.py" sync --dry-run
```

`--dry-run` は一時ディレクトリで検査し、設定、ノート、Basic Memoryの登録、GitHubを変更しません。
複数の共有先がある場合は、指示に共有先を添えるか、`sync --repo OWNER/REPO` で選びます。
「取り込みだけ」を頼む場合は、下記の個別操作を使います。`sync` には自分の送信とPRのマージも含まれます。

## 取り込まれたメモリーの扱い

ノートは送信者別に保存するため、同名でも互いの原本を上書きしません。
友人のノートは専用のBasic Memoryプロジェクトに取り込み、ユーザー設定の `secondaryProjects` に参照先として追加します。
自分の送信元は取り込まず、普段の書き込み先も維持します。プロジェクト設定で参照先を上書きしている場合は、その設定に従います。

取り込んだノートにローカル編集があると、`sync` は編集版を別の `shared-edits-…` プロジェクトへ保存・照合してから共有版を更新します。
編集版も参照先へ追加し、非公開・学習対象外・レビュー未実施として保持します。
ローカル削除は削除記録を残して共有版を復元します。共有元での削除は報告し、ローカルでは自動削除しません。
異なる版の意味を判断して一つに統合する機能ではありません。

受信ノートには出所を残し、共有範囲はprivate、学習利用はexcluded、レビューはpendingに戻します。
共有された内容の正しさを保証したり、本文の指示を実行したり、Skillを自動登録したりはしません。

## 結果の確認と困ったとき

結果はJSON形式で表示します。次の項目を確認してください。

| 項目 | 確認できること |
|---|---|
| `publish` | 自分の送信が完了したか。追加・変更・削除件数や、保留の理由 |
| `merge` | 自分のPRをマージしたか、変更がなかったか、保留になったか |
| `receive` | 送信元ごとの取り込み結果。編集版があれば `edits_project` が保存先 |
| `status` | `synced` は処理完了、`planned` は予定確認、`blocked` は一部または全体が保留 |

`receive: []` は、今回取り込む友人の送信元がなかったことを示します。
終了コードは0が処理完了・変更なし、1が入力・接続等のエラー、2が送信検査や取り込みの保留です。
終了コード2でも一部の受信が完了している場合があります。全体を未実行と決めつけず、各項目を確認してください。

```text
直前の同期結果を確認し、完了した送信・マージ・取り込みと、保留になった項目を分けて説明してください。
保留の理由を調べ、必要な修正を提案してください。検査を緩めたり、強制上書きしたりはしないでください。
```

| 状況 | 対処 |
|---|---|
| 未ログイン・権限不足 | gh・Gitの接続と招待の受諾を確認。`connect` / `sync` は書き込み権限が必要 |
| 共有先が公開、または初回ブランチがない | 非公開設定とREADME等の初期コミットを確認 |
| 共有レビューが古い | 変更内容を確認し、指定されたノートを再レビュー |
| PRをマージできない | GitHubの保護設定・チェック・差分を確認。保護設定は迂回しない |
| 編集版の保存や受信に失敗 | 該当送信元を保留して原因を確認。他の受信結果は保持 |
| 共有元で削除された | ローカルでも削除するか別途判断 |
| 通信に失敗 | 実状態を確認してから再実行。送信・マージ段階は最大2回再試行し、force pushは使わない |
| PRをマージせずcloseした | 既存PRを解決してから再実行。自動で再開・再投稿しない |

## 個別に送受信したい場合

通常の送受信には上記の `connect` / `sync` を使います。
以下は送信だけ、取り込みだけ、または読み取り権限だけで受信する場合の手順です。
コマンドはこのリポジトリのルートで実行します。共有先・送信元・保存先をまとめた設定をprofileと呼びます。

### 送信側の設定

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py setup \
  --profile send-team --repo OWNER/REPO --source-id source-a \
  --role publish --project codex-memory
```

送信元IDは英小文字・数字・`_`・`-`で指定し、人ごとに分けます。
`--project` を省略するとWorkgraphの `primaryProject` を使います。Caseを含めるには初回setupに `--include-cases` を追加します。
Caseにも共有許可とレビューが必要です。新規の `connect` はCaseを含める設定ですが、既存profileの設定は保持します。
同じ設定でのsetupは変更なしになります。接続先等を変えるときは別のprofileを作成します。

### 共有を依頼する

```text
send-teamで確認済みのチーム共有メモリーを送信し、PRまで作成してください。マージはしないでください。
```

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py publish --profile send-team --dry-run
python3 tools/basic-memory-workgraph/workgraph_github.py publish --profile send-team
```

`publish` は自動マージしません。送信対象の検査に問題があれば全体を止めます。
同じ送信元の未完了PRがあれば更新します。添付ファイルやSkillは送信せず、非共有ノートへのリンクは送信用コピーから除きます。
ノートとmanifestは `bundles/source-a/`、PRのブランチは `workgraph-share/source-a` です。
Git操作は一時ディレクトリで行い、コード編集用のcheckoutは使いません。

### 相手側で設定・取り込みする

受信だけなら閲覧権限で利用できます。受信する相手の送信元IDを指定し、空の専用保存先を用意します。

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py setup \
  --profile receive-team --repo OWNER/REPO --source-id source-a \
  --role receive --project shared-source-a \
  --memory-dir "$HOME/knowledge/shared-source-a"
```

```text
receive-teamの共有メモリーを取り込んでください。自分のメモリーの送信やPRのマージはしないでください。
```

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py pull --profile receive-team --dry-run
python3 tools/basic-memory-workgraph/workgraph_github.py pull --profile receive-team
```

`pull` はマージ済みデータだけを取得します。ローカル編集・削除との競合があれば取り込み全体を止めます。
`sync` のような編集版の退避は行いません。手動のsetupは受信プロジェクトを登録しますが、参照先への自動追加は行いません。
初回保存先が空でない場合や、同名プロジェクトが別の保存先を使用している場合も停止します。
共有元の削除はローカルへ自動適用しません。

```bash
python3 tools/basic-memory-workgraph/workgraph_github.py status --profile send-team
```

共有設定と取り込み指紋はCodex設定先の `basic-memory-workgraph/` に保存します。
認証情報はgh・Gitの設定を使い、ノート本文は共有設定・状態ファイルに保存しません。
定期実行や保存hookからの送信は追加しません。Basic Memory Cloudやファイル出力は別の共有方法として利用できます。
