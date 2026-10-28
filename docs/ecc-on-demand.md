# ECCを必要なときに読む

[English](en/ecc-on-demand.md) | **日本語**

ECCの原本をCodex標準プラグインのキャッシュに残し、初期スキル一覧には短い入口だけを載せます。
Python 3.11以降、Linux / WSL2、導入済みのCodexとネイティブECCプラグインが必要です。

ECC自体が未導入の場合は、[ECCのインストーラー](codex-ecc/installation.md)で原本の導入とこの設定をまとめて行えます。

管理用Pythonの要件は、開発対象の言語を制限しません。TDD、TypeScript／JavaScript、Go、Rust、C++、C#等の原本を必要時に参照できます。

## 導入と確認

リポジトリのルートから実行します。

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py apply
python3 tools/ecc-on-demand/ecc_on_demand.py doctor
```

`apply` は、Codexのユーザー設定で `plugins."ecc@ecc".enabled = false` にし、
`~/.agents/skills/` に `ecc-tdd`、`ecc-python`、`ecc-errors`、`ecc-security`、`ecc-library` を配置します。
管理CLIは `${CODEX_HOME:-~/.codex}/ecc-on-demand/ecc_on_demand.py` に配置します。
設定のバックアップと管理状態も同じディレクトリに保存します。バックアップの権限は所有者のみ読み書き可能です。
ECCの原本、Basic Memory、既存のMCP、スキル一覧の上限は変更しません。
初回の既定ではFirecrawlとChrome DevToolsを独立MCPとして追加します。
既存の同名設定と無効指定は保持します。Context7の旧名`context7-mcp`があれば二重登録しません。
Firecrawlは[公式のキー不要接続](https://github.com/firecrawl/firecrawl-mcp-server#hosted-mcp-keyless-free-tier)で検索・本文取得・文書解析を利用できます。
利用回数には制限があり、`crawl`・`map`には認証が必要です。
Chrome DevToolsのstdio接続にはNode.jsと`npx`、利用可能なブラウザーが必要です。
GitHubは既存の公式連携または`gh`を使います。

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py apply --mcps recommended,browser,cloudflare
python3 tools/ecc-on-demand/ecc_on_demand.py apply --mcps none
```

`--mcps`は`apply`の後に指定します。`research`はContext7とParallel Search、`browser`はPlaywrightとChrome DevTools、
`cloudflare`はContext7とCloudflare Docsを選びます。プリセットと接続名をカンマで組み合わせられます。
選択は保存され、未指定の再適用やルートのインストーラーによる更新で引き継ぎます。
`none`や別の選択への変更は既存接続を削除・無効化しません。以前の管理対象MCPも保持します。
新規登録に使うパッケージは実測した版に固定し、既存接続のバージョン・引数はそのまま保持します。

Sequential Thinkingは明示指定のみ、Token Optimizerは登録対象外です。今回の比較では前者の正答増加を確認できず、
後者には新しい会話で必要な情報を取得できない失敗がありました。既定2件も精度改善を保証する選択ではなく、
Web検索・本文取得とブラウザー診断の接続を用意するためのものです。Firecrawlは過去の比較試験の対象外です。
用途別の判断と実測例は[MCPの導入判断](codex-ecc/mcp-evaluation.md)、
選択肢の詳細は[ECCのインストール](codex-ecc/installation.md)を参照してください。

`--codex-home PATH`、`--skills-root PATH`、`--cwd PATH` はサブコマンドの前に指定できます。
同名の未管理スキルや、導入後に手で変更した管理ファイルがある場合は上書きせず停止します。
既存TOMLのコメントと他の設定を保持します。ECC設定がインラインテーブルやドット区切りのキーで書かれている場合は自動編集しません。
通常の`[plugins."ecc@ecc"]`テーブルに整理してから適用してください。

Pythonは`PYTHON_BIN`、記録済みの実行パス、`python3`の順に選び、3.11以上を確認します。
導入された入口は検証済みPythonの絶対パスを使います。仮想環境のパスは維持し、システムのPythonは変更しません。
初回に`python3`が古い場合は、次のように指定します。以後の更新・診断は記録した実行パスを使います。

```bash
PYTHON_BIN=/path/to/python3.11 bash install_ecc.sh --apply
bash install_ecc.sh --doctor
```

4入口の旧管理状態は更新時に5入口へ移行します。手動編集・未管理の同名スキルは保持して停止し、途中失敗は更新前へ戻します。
Pythonを移動・削除した場合は`PYTHON_BIN`で新しい実行ファイルを指定し、リポジトリの`install_ecc.sh --apply`から更新してください。
導入済み管理CLIだけではスキルテンプレートを更新できません。

反映は新しいセッションで確認してください。実行中の共有Codexデーモンは再起動しません。

## 使用する入口

| 入口 | 取得する原本 |
|---|---|
| `ecc-tdd` | 言語共通の`tdd-workflow`と対象技術のテスト手順 |
| `ecc-python` | `python-patterns` |
| `ecc-errors` | `error-handling` |
| `ecc-security` | `security-review` |
| `ecc-library` | 依頼に合う専門スキルを最大5件検索し、必要な1〜3件を読む |

`ecc-tdd`は新機能実装・不具合修正・リファクタリングでも自動選択できます。
TDD原本と対象技術のテスト原本を読み、期待したテスト失敗、最小実装、成功、必要なリファクタリングを確認します。
文書だけの変更には適用せず、既存テストやプロジェクトの網羅率基準を尊重します。

入口は自動選択も有効です。明示する場合は `$ecc-library` などと指定します。
React・Cloudflare・GitHub・記憶管理は既存の専門スキルを優先します。
ECC本文のTDDやデプロイ方針より、現在のユーザー・開発者・プロジェクトの指示が優先されます。

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py search 'Python テスト' --json
python3 tools/ecc-on-demand/ecc_on_demand.py search 'DB マイグレーション' --json
python3 tools/ecc-on-demand/ecc_on_demand.py resolve api-design --json
```

`resolve` は本文のパス、スキルのディレクトリ、プラグインのルート、バージョンを返します。
相対参照は原本の位置から解決します。原本がない場合はエラーを返し、別キャッシュへ推測で切り替えません。
検索は名前・説明を使う軽量な順位付けです。`search 'testing' --language typescript --json`のように言語を指定できます。
未指定では検索語、次に作業ディレクトリに近い構成ファイルから判断します。Go／Golang、C++／CPP、C#／CSharp等の表記を正規化し、他言語専用の候補を除外します。
複数言語のリポジトリでは、グローバル引数`--cwd`を`search`の前に置き、対象ディレクトリを指定してください。
文意全体を理解する検索ではないため、候補が合わない場合は英語の技術名で検索するか、名前を指定してください。

導入・更新時に、独立した`codex app-server`の`skills/list`で正式な原本の一覧を確認します。
一覧と原本のハッシュを管理ディレクトリの`catalog.json`に保存します。通常の`search`・`resolve`は保存済み一覧と内容を検証して読み、内部でCodexを起動しません。
原本が変更・削除された場合は停止し、リポジトリの`install_ecc.sh --apply`で一覧を更新します。キャッシュ内の別バージョンへ推測で切り替えません。
診断では保存済み一覧と現在の正式な一覧を照合します。会話やモデル呼び出しは開始しません。
初期一覧が減っても、選んだ本文を読む分のコンテキストは消費します。

## 更新と復元

```bash
python3 tools/ecc-on-demand/ecc_on_demand.py update
python3 tools/ecc-on-demand/ecc_on_demand.py restore
```

`update` は `codex plugin marketplace upgrade ecc --json` と `codex plugin add ecc@ecc --json` を使います。
更新が途中で失敗した場合もECCの有効設定を `false` に戻し、診断結果を返します。
更新後にCodexからフックの信頼確認が要求されることがあります。本ツールはフックを自動承認しません。
原本は新しいネイティブカタログから解決するため、入口のバージョン固定パスを書き換える必要はありません。
入口や管理CLI自体の更新には、新しいリポジトリのコピーから`apply`を実行します。
ECC原本と管理資材をまとめて更新する場合は、ルートの`install_ecc.sh --update --apply`を使います。

`configure-ecc` や直接の `codex plugin add` はECCを再有効化する場合があります。
`doctor` が再有効化を検出したら `apply` で戻してください。

`restore` は導入前のECCの有効値に戻し、管理対象の入口とCLIを取り除きます。
追加したMCPのうち変更されていない管理対象設定も取り除き、元から存在する接続は保持します。
管理対象MCPに手動で認証情報や引数を追加した場合は、消さずに停止します。
新しいECCインストーラーでECC自体を初めて導入した環境では、原本を残し、ECCを無効状態に保ちます。
導入後に追加した無関係な設定は保持し、設定バックアップも残します。
管理ファイルや有効値が手で変更されている場合は、その変更を消さず停止します。

## 停止する機能

ECCプラグインを無効化すると、付属スキルの一覧登録、付属Chrome DevTools MCP、
ECCのCodex用SessionStartフックが止まります。独立して設定したMCPは継続します。

ECC 2.2.2のSessionStartは、前回要約、instinct、学習済みスキルの紹介、技術構成を注入し、
ECCの保存領域を作成します。また、既定では30日を超えたECC要約を削除し、条件付きでobserverのセッション登録を行います。
無効化後はこれらの開始時処理が止まりますが、保存データは削除しません。
Basic Memoryのフック、Codexの会話履歴、Claude Code側のECC設定は別です。

`doctor` は新しい独立app-serverのカタログを確認します。モデルに渡される一覧が省略されていないかは、
新規セッションの診断ログでも確認してください。実行中のセッションの一覧は置き換えません。
各入口の診断は、記載されたコマンドを実行して原本の取得まで確認します。
MCPについては設定だけを検証し、起動・認証・ツール実行は別途確認します。

## 検証

```bash
python3 -m unittest discover -s tests -p 'test_ecc_on_demand.py' -v
```

テストは隔離した設定と原本を使い、再適用、衝突、復元、更新成功・失敗、欠損、検索、RPCの取得を確認します。
実際のECC更新やユーザーの設定変更は行いません。
