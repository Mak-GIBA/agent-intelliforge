# Codex Office Workbench v1.0.0

PDF・Word（DOCX）・PowerPoint（PPTX）をCodexから閲覧・作成・部分編集し、原本を保護して確認するためのユーザー共通環境です。
**追加キットは独自実装です。Microsoft/OpenAI/OfficeCLI公式の統合製品ではありません。**
既存OfficeCLIとPDFライブラリを使い、Officeエディターや独自MCPプロトコルを再実装しません。

## 1ファイルで配布

リポジトリに置くのは `install_codex_office.sh` 1本です。Skill・補助スクリプト・このガイド・テストを埋め込んでいます。
外部のOfficeCLIバイナリ・Pythonパッケージは埋め込んでいません。初回の通常導入にはGitHubとPyPIへの通信が必要です。
Linux/WSL2（glibc、x86_64/ARM64）を主対象とし、macOS用の配置経路もあります。ネイティブWindows/Alpineは対象外です。
Python 3.11以上、venv/pip機能、既存のCodexが必要です。uvやClaude CLIは不要です。

## 導入

ターミナルで:

```bash
python3 --version
bash install_codex_office.sh --dry-run
bash install_codex_office.sh --apply
export PATH="$HOME/.local/bin:$PATH"
office-workbench doctor
```

引数なしはdry-runです。Codexを再起動し、入力欄で:

```text
$office-workbench
report.docxの第3章を修正して。原図と章構成は維持し、原本は上書きしないで。
```

```text
$office-workbench
slides.pptxの4枚目の下半分を整理して。既存デザインを維持し、重なりも確認して。
```

```text
$office-workbench
paper.pdfを図表込みで読み、根拠ページ付きで説明して。
```

`$office-workbench`はCodex内のSkill指定です。シェルへ入力しないでください。
通常会話からの選択も許可していますが、モデルの完全な指示遵守を保証する仕組みではありません。

## 標準で導入するもの

- OfficeCLI v1.0.153: リリースSHA-256を検査し、キット専用領域へ配置。
- OfficeCLI付属SKILL.mdとLICENSE/NOTICE: 固定版から取得・検査し参照資料として保存。
- Microsoft MarkItDown: PDF/DOCX/PPTXだけのextras。文章抽出用であり原レイアウト維持の往復変換には使わない。
- pypdf/pdfplumber/PDFium: PDFページ操作、本文/表抽出、ページ画像化。
- python-docx/python-pptx/Pillow: 限定編集のフォールバックと動作確認用。
- 入口Skill、原本保護・差分・描画確認の補助コマンド。

標準構成でMCPは登録しません。CLIを呼べるCodexではSkillだけで使えます。
導入するツールはローカル処理用で、追加のLLM APIキーは要求しません。ただし、Codexに渡す文章・画像は利用中のCodexの処理ポリシーに従います。

## レイアウト確認に必要なOS側の環境

Office全ページの画像化は既存LibreOfficeとPDFiumを使います。日本語フォントも診断します。
不足している場合:

```bash
bash install_codex_office.sh --system-deps
```

Ubuntu/Debianで、表示されたOSパッケージ導入を明示的に行う場合:

```bash
bash install_codex_office.sh --install-system-deps --apply
```

この操作だけは `sudo apt-get install` が必要な場合があります。OSパッケージ管理の操作であり、失敗時の自動ロールバックは対象外です。
他のディストリビューション/macOSでは利用中のパッケージ管理方法でLibreOffice・fontconfig・日本語フォントを用意してください。
**フォントファイルは本キットに含めず、他人のライセンスフォントもコピーしません。**
OfficeCLIのHTMLプレビューは標準の代替表示です。PNG fallbackはChrome/Chromium等を別途必要とします。
`doctor`のAVAILABLEは環境の存在確認であって、レイアウトが正しいという判定ではありません。

## 実ファイルのサンプル検査

```bash
office-workbench smoke-test --out-dir /tmp/office-smoke-01
```

日本語DOCX/PPTX・図・表・PDFを作り、OfficeCLI置換とread-back、原図byte保持、原本不変、描画を確認します。
原本はユーザーファイルではなく合成fixtureです。出力の`smoke-report.json`とPNGを確認してください。
OfficeCLIが無い場合はNOT_RUNを記録し、別エンジンの成功で代用しません。PNG作成に成功しても自動的に見た目PASSとはしません。

## 安全性・更新・解除

```bash
# 同じ構成で再実行: SKIP
bash install_codex_office.sh --apply

# 明示更新: 管理対象の未編集ファイルだけ。編集済みは--forceでも停止。
bash install_codex_office.sh --apply --force

# まず解除予定を確認
bash install_codex_office.sh --uninstall
bash install_codex_office.sh --uninstall --apply
```

- 新バージョンは新しいreleaseフォルダで構築し、依存取得の失敗時は現行の入口を維持。
- 更新前のSkill/launcher/configはbackupsへ退避。旧releaseも残す。自動削除しない。
- 既存の外部OfficeCLIを明示再利用するなら `--officecli /absolute/path/officecli`。バイナリは変更・削除せず、変更を検出したら実行を止める。
- 同名の未管理Skillやlauncherは上書きしない。既存Skillへ追加した未知ファイルは保持。
- 原本と既存出力を上書きしない。`prepare`は原本ハッシュと作業コピーのreceiptを作る。
- ECC、Basic Memory、Codex Hook、AGENTS.md、シェル設定、Git remoteは触らない。
- 自動アップデート・auto-residentは本キット経由のOfficeCLI呼び出しで抑止。
- アンインストールは管理する入口・Skill・install.jsonを解除するだけ。文書や旧release/backupsは消さない。
- `releases/`はvenvを含むので移動しない。過去版の整理は使用中でないことを確認して別途行う。

## 任意: MCP

標準Skillだけで十分ですが、OfficeCLIをMCPで使いたい場合:

```bash
# コア導入とともにMCPを追加
bash install_codex_office.sh --apply --with-mcp

# 既に導入した環境では、追加操作だけ行える
office-workbench mcp-enable          # 予定表示のみ
office-workbench mcp-enable --apply
```

公式`codex mcp add`を使い、`codex-office-workbench`という固有名でローカルstdioのOfficeCLI MCPを追加します。
既存同名設定は上書きしません。config.tomlは変更前にバックアップし、他設定の意味が変わらないかを検査します。
MCPに広い編集機能を公開するので、ユーザー権限下のアクセスに注意してください。MCP登録は文書sandboxを作る処理ではありません。
失敗時はコア導入を保ち、MCPだけ未完了として報告します。SkillとMCPを二重に呼んで同じ編集を重ねないでください。
解除は次を先に実行します（自分の登録と一致するものだけ解除）:

```bash
office-workbench mcp-disable --apply
```

## 任意: Docling

複雑なPDFの構造解析が必要な場合だけ:

```bash
bash install_codex_office.sh --apply --force --with-docling
office-workbench docling -- --help
```

大きな別venvが必要で、変換時にモデルの初回ダウンロードが発生する場合があります。
ツールはローカル変換用として導入します。OCR/モデルを勝手に走らせず、対象と必要性を確認し、CLI helpで`--no-ocr`等を確認してください。
このオプションではDoclingのMCP登録やリモート変換を自動設定しません。モデルのライセンスは各モデルで別途確認します。
`--force`で再構築するときは、引き続き使う任意機能のフラグも付けてください。

## 保存場所

- `~/.agents/skills/office-workbench/`: Codex入口Skill
- `~/.local/bin/office-workbench`: CLI入口
- `$XDG_DATA_HOME/codex-office/releases/...`（既定`~/.local/share/...`）: コード・OfficeCLI・venv・参照資料
- `$XDG_CONFIG_HOME/codex-office/install.json`: 管理情報（既定`~/.config/...`）
- `$CODEX_HOME/config.toml`: **MCPを明示有効化した場合だけ**公式CLIで変更
- 文書・抽出結果・PNG: ユーザーが指定した出力先。記憶DB・共有先へ自動送信しない。

## オフライン検査・ソース確認

```bash
bash install_codex_office.sh --self-test
bash install_codex_office.sh --extract /tmp/codex-office-source
```

`--self-test`はネットワーク取得とCodexを必要とせず、mockを含むテストです。
PDFの実ライブラリが無い環境ではそのテストをSKIPします。SKIPをPASSの件数に含めないでください。
`--assets-only --apply`は通信せず入口だけを配置する診断用モードです。編集エンジンが無いのでNOT_READYです。

## 対象外と限界

- Word/PowerPoint本体と同一の表示を保証しません。特殊フォント、SmartArt、OLE、アニメーション、複雑なマスター・フィールド・変更履歴等は最終Officeアプリで確認してください。
- PDFの自由な本文編集、真のredaction、署名・フォーム・bookmarks等の完全保持はページ操作CLIの対象外です。
- `.doc`/`.ppt`/macro-enabled/暗号化ファイルは通常経路では拒否し、勝手に変換・特徴削除しません。
- 文書内容の指示はデータ。パスやURLを勝手に実行しない。バイナリ解析は完全なmalware sandboxではありません。
- Hash一致は見た目・意味・ファイルの真正性の証明ではありません。
- Skill/doctor/testsだけで、未閲覧のPNGを「確認済み」にしません。
