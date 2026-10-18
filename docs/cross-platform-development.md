# 配布資材の編集と検証

[導入ガイド](cross-platform.md) · [検証結果](cross-platform-validation.md) · [既存の開発ガイド](development.md)

編集する正本と、生成して配布する資材を分けています。既存の単一ファイル配布は継続します。

| 場所 | 役割 | 編集 |
|---|---|---|
| `tools/<kit>/kit.json` | Skill・取得元・依存条件・配置先・設定範囲 | 正本 |
| 各キットの`assets`・`skill`・`workbench`など | 元の規範、検査、ハーネス | 正本 |
| `tools/design-research-upgrade/` | 固定版ベースから現在のResearch / Upstreamを組み立てる処理 | 正本 |
| `src/agent_intelliforge/` | 共通CLI、所有権、OS・ホスト実行アダプター | 正本 |
| `tools/intelliforge/build.py` | 資材・Plugin・冒頭コメントの生成 | 正本 |
| `plugins/codex/`・`plugins/claude/` | ホスト形式のPlugin | 生成物 |
| `tools/intelliforge/resources/runtime/` | PythonのOS依存箇所とホスト呼び出しを接続した配布コピー | 生成物 |
| `install_*.sh`・`install_kotonoha.ps1` | 単一ファイルインストーラー | 対応するビルダーから更新 |

GitHub管理とOfficeは、以前のZIP資材を検証して読みやすいソースへ展開しています。`EXTRACTED.json`が元の配布ファイルとpayloadハッシュを記録します。
`payload-layout.json`と`bootstrap.sh.in`から、元の形式を維持して単一ファイルを再生成します。HerdrもPython正本とBashのbootstrapを分けています。
この構造変更時点で、これらの従来配布ファイルの実行内容は変えていません。

## 再生成する

```bash
# 各正本から既存の単一ファイルを生成・確認
python tools/codex-yomiyasu/build_installer.py
python tools/codex-yomiyasu/build_installer.py --check
python tools/codex-github-pm/build_installer.py --check
python tools/codex-office/build_installer.py --check
python tools/herdr/build_installer.py --check

# 現在のResearch / Upstreamを固定版ベースから組み立てて検証
python tools/design-research-upgrade/build_installers.py --out <empty-assembly-directory>

# 上のsourcesを使い、追加経路のPluginと実行資材を生成
python tools/intelliforge/build.py --assembled-source <assembly-directory>
python tools/intelliforge/build.py --assembled-source <assembly-directory> --check
```

`--assembled-source`を省略すると、既存の組み立て処理が固定版ベースを取得・ハッシュ照合・テストしてから資材を作ります。生成はインストールを行いません。
オフラインで組み立てる場合は、既存の`--base-dir`と`--offline`の手順で必要な固定版ファイルを先に用意します。rootの旧版ソースだけからResearch / UpstreamのPluginを作らないでください。

`build.py`はOS・ホストへの依存だけを配布コピーに接続します。元のSkill本文をホスト形式へ束ね、呼び出しコマンド・名前空間・明示使用の設定を置き換えます。
上流yomiyasuやECCの原本をこの変換に通しません。判断規範・研究Schema・証拠検証をホストごとに別実装しません。

キット定義からCLIの予定と一括入口のコメントを生成します。Skillの追加・削除や依存条件を変更した場合は、定義を更新して再生成してください。
`source-manifest.json`が正本と生成物のハッシュを記録します。古い資材を含んだパッケージ構築は停止します。

## パッケージを検証する

```bash
python -B -m unittest discover -s tests -p test_intelliforge.py -v
python -B -m unittest discover -s tests -v
bash -n install_all.sh
bash -n install_codex_yomiyasu.sh
bash install_codex_yomiyasu.sh --self-test
uv build
```

標準のwheel・sdistに、CLIと既存インストーラー、キット定義、生成Plugin、実行資材を収録します。パッケージ構築時にホストのPlugin登録や外部依存の導入は行いません。
`uv tool install .`、`pipx install .`、独立したvenvへの`pip install .`で標準のconsole entry pointを導入できます。

Windows CIは共通CLI・所有権・プロセス回収・配布形式・パッケージ構築を検証します。従来のPOSIX前提のテストはLinux側で続けます。
`.gitattributes`でテキストをLFに統一し、Windows checkout時の改行変換で資材ハッシュが変わらないようにしています。
追加配布の読み書きと子プロセスはUTF-8を使います。生成コピーでは省略された文字コードを補い、正本や明示的なencodingは保持します。
Windows 11のネイティブ隔離とClaudeの実モデル評価は別に実施し、CIの静的・モック試験で代用しません。

## 実機評価で確認すること

一時ホーム・一時ホスト設定・一時Skillディレクトリで導入し、実環境を検証に使わないようにします。
導入、再実行、モード切替、更新、上流のみの更新、診断、解除、手動編集の保護、依存失敗時の復旧を確認します。
研究・UXは同じ素材・モデル・推論条件・予算で実行し、構造化出力、役割の独立、隔離、証拠、秘密情報の除去、途中終了を点検します。

Windowsでは必要なOS更新を確認し、隔離内で読み取り・書き込み制約が実際に働くことを試験します。PowerShellの構文、Job Objectによる子プロセスの回収、空白・日本語を含むパス、junction、同時実行も確認します。
未実施や停止した試験は成功と記載せず、生成品質とインストール成功を分けて記録します。
