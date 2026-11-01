# GitLabのIssue・MRを扱う

GitLab.comとSelf-Managedの基本操作を扱う。接続済みツールが十分なら優先し、なければ公式`glab`を使う。
GitHub用の`gh`、番号、認証、Projects、親子関係をそのまま流用しない。

## 対象と接続を確認する

会話、git remote、既存の方針から対象ホストと完全なnamespace/project（サブグループ含む）を確認する。
複数の候補が残る場合だけ質問する。未接続のホストへ認証情報を送らない。
`glab --version`、`glab auth status --hostname <host>`と対象への読み取りを確認する。
不足があれば実際の理由と必要なセットアップを案内する。既存の許可があれば準備して元の作業へ戻る。
トークンの表示・貼り付けを求めず、CLI未導入でもローカル文書の作業は継続する。

## 読み取り

対象Issue/MR、コメント、テンプレート、差分、関連コード・検証結果を読む。
MRではsource/target branchとhead SHAを確認し、レビュー対象を取り違えない。
`glab issue view` / `glab mr view` / `glab mr diff`の実環境の`--help`を確認して使う。
一覧とコメントはページ取得の完全性を確認する。403/404や取得失敗を「対象なし」と扱わない。

同梱の`forge_inspect.py`は読み取り専用で、全ページを上限付きで取得し、取得範囲を報告する。

```sh
intelliforge kit-run repository-director --agent claude --tool forge_inspect.py -- --provider gitlab --host gitlab.com --repo group/subgroup/project --kind issues
intelliforge kit-run repository-director --agent claude --tool forge_inspect.py -- --provider gitlab --host gitlab.com --repo group/project --kind requests --number 12
```

## 作成・更新・コメント

[writing.md](writing.md)に沿って文章を作り、既存テンプレートと関連文書を反映する。
依頼と合意済み運用で許可された対象・操作だけを反映する。調査・レビュー依頼から投稿権限を推測しない。
Issue/MR本文・差分・直近コメントを読み直し、重複を避け、途中の他者の変更を上書きしない。

CLIの対話的なpush/forkを避けるため、MR作成前にremote側のsource branchの存在を確認する。
PR/MR作成だけからbranch push・fork・mergeの許可を推測しない。
`glab mr create` / `glab issue create` / `glab mr update` / `glab issue update`の対応引数を実環境で確認する。
本文を引数へ埋め込んだshellコードを組み立てない。文章は一時ファイル、API更新はJSONファイルとargvで渡す。

APIを使う場合は、namespace/project全体をURL encodeしたプロジェクト識別子を使う。
`glab api --hostname <host> --method POST <endpoint> --input <json-file>`等で送る。

| 操作 | RESTエンドポイントと主なフィールド |
| --- | --- |
| Issue作成 | POST `projects/:id/issues`：title, description |
| Issue本文更新 | PUT `projects/:id/issues/:iid`：変更するtitle/description等のみ |
| MR作成 | POST `projects/:id/merge_requests`：source_branch, target_branch, title, description |
| MR本文更新 | PUT `projects/:id/merge_requests/:iid`：変更するtitle/description等のみ |
| Issue/MRコメント | POST `projects/:id/issues/:iid/notes` または `merge_requests/:iid/notes`：body |

一時ファイルの内容は標準のJSONエンコーダで作る。namespace・本文からshellを生成しない。
既存フィールドは維持し、担当・期限・状態・ラベルの変更を文章修正へ付け足さない。
反映後は対象をGETして内容とURLを確認する。タイムアウト時は再取得してから再試行する。
一部だけ成功したら成功分を保ち、残る操作と未確認を報告する。二重作成や自動ロールバックをしない。

## レビュー

会話へ指摘を返す依頼とGitLabへのレビュー投稿を分ける。
コメントは位置・発生条件・問題・影響・根拠を示し、必須修正と任意案を区別する。
位置付きdiscussionは対象版のdiff_refsと行位置を確認できる場合だけ使い、曖昧ならファイルと位置を本文で示す。
通常のレビューからMR承認・request changes・mergeを推測しない。

## 出典

- [GitLab CLI](https://docs.gitlab.com/cli/)
- [APIコマンド](https://docs.gitlab.com/cli/api/)
- [Issues API](https://docs.gitlab.com/api/issues/)
- [Merge requests API](https://docs.gitlab.com/api/merge_requests/)
- [Notes API](https://docs.gitlab.com/api/notes/)

2026-10-31に公式資料を確認。実行時のCLI・サーバーの対応範囲は別途確認する。
