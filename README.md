<p align="center">
  <img src="docs/assets/agent-intelliforge-logo.png" alt="Agent Intelliforge" width="960">
</p>

<h1 align="center">Agent Intelliforge</h1>

<p align="center">
  <strong>Codexの調査・設計・実装・知識の再利用を支える、用途別の導入キット。</strong>
</p>

<p align="center">
  <a href="docs/README.md"><img src="https://img.shields.io/badge/Codex-Skills_%26_Tooling-0f172a?style=flat-square" alt="Codex Skills &amp; Tooling"></a>
  <a href="docs/cross-platform.md"><img src="https://img.shields.io/badge/Platform-Linux_%2F_WSL2_%2F_Windows-475569?style=flat-square" alt="Linux / WSL2 / Windows"></a>
</p>

<p align="center">
  <a href="#quick-start">はじめる</a> ·
  <a href="#kits">キット一覧</a> ·
  <a href="#workflow">利用例</a> ·
  <a href="docs/README.md">ガイド</a>
</p>

---

Agent Intelliforgeは、Codexに調査・設計・検証・文書編集の手順とツールを導入するキット集です。
要件の整理、技術方式の比較、画面の設計と操作確認、GitHubでの進捗管理など、目的に合うキットを選んで既存のプロジェクトで使えます。
日本語の執筆・推敲には、meisekiとyomiyasuを統合した独自Skillのkotonohaを用意しています。

主な対象はCodexです。Linux / WSL2では既存のBashインストーラーを使い、ネイティブWindowsとClaude CodeにはPlugin方式の導入経路を用意しています。Claude Codeは試験対応です。

作業で得た知識を次の仕事へ引き継ぐ仕組みも備えています。
Workgraphは、試行でつまずいた点と検証済みの対処法、ユーザーからの修正指示を、条件と根拠付きの知識として残すか評価します。
似た作業で参照し、同じ調査や修正指示を繰り返す手間を減らすことを目指します。保存する知識の種類は設定で選びます。

<a id="quick-start"></a>
<a id="はじめに"></a>

## はじめる

標準の一括導入はLinux / WSL2向けです。Codex CLIを用意し、[前提条件と設定の変更範囲](docs/installation.md#前提条件)を確認してください。
個別キットのOS・Python・Node.jsの対応範囲は、それぞれの導入ガイドに記載しています。

```bash
git clone https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge

# 導入できるキットと実行予定を確認
bash install_all.sh --list
bash install_all.sh --dry-run
```

まず日本語の執筆・推敲を使うなら、独自Skillの`kotonoha`を導入できます。必要なPython・Node.jsと検査ツールもユーザー専用領域へ自動で用意します。

```bash
bash install_all.sh --only kotonoha --apply
```

画面の設計・検証も使う場合は、キットを組み合わせます。

```bash
bash install_all.sh --only ux-stack,kotonoha --apply
```

全キットの導入は`bash install_all.sh --apply`で実行できます。
一括インストーラーは引数なしでも予定表示にとどまり、`--apply`で実際に導入します。
個別インストーラーは引数なしの動作が異なるため、直接実行するときは各ガイドを確認してください。
更新・再実行・解除は[一括導入ガイド](docs/installation.md#再実行更新解除)から各キットの手順へ進めます。

### 共通CLI・Windows・Claude Code

共通CLIの`intelliforge`では、導入するキットとホストを指定できます。Linux / WSL2のCodexでは既存のインストーラーを呼び出し、ネイティブWindowsとClaude Codeでは各ホストの公式Plugin管理コマンドへ接続します。共通CLI自体はPythonパッケージとして導入します。

```bash
# cloneしたリポジトリで実行。uvの独立したツール環境にCLIを導入
uv tool install .
intelliforge inspect --only kotonoha
intelliforge install --only kotonoha --apply

# Claude CodeはCodexを導入せず利用可能（試験対応）
intelliforge inspect --agent claude --only kotonoha
intelliforge install --agent claude --only kotonoha --apply
```

日本語キットの単体インストーラーは、不足するPythonも準備します。Bashでは`bash install_kotonoha.sh --apply`、Windowsでは`.\install_kotonoha.ps1 --apply`を使います。

WindowsではPowerShellを使います。長いパスを含む研究資料を取得できるよう、clone時に`--config core.longpaths=true`を指定してください。導入の予定は`python intelliforge.py inspect`、適用は`install_all.ps1`からも実行できます。PluginのフックやヘルパーにはPATH上の共通CLIが必要です。

```powershell
git clone --config core.longpaths=true https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge
uv tool install .
intelliforge inspect --only kotonoha
intelliforge install --only kotonoha --apply
```

導入内容の正本は[`tools/*/kit.json`](tools/)です。Skill名、取得元、依存ソフト、配置先、設定の変更範囲を読み、`inspect --json`で選択した経路の予定を確認できます。既存のSkillやフックと競合する場合は、自動移行せず停止します。
詳しい手順、更新・解除、検証範囲は[共通CLIとOS・ホスト対応](docs/cross-platform.md)にまとめています。

<a id="kits"></a>

## 用途別のキット

キット名から概要、導入手順、使用例へ進めます。`ID`は`install_all.sh --only`で指定する名前です。

| ID | キット | できること |
|---|---|---|
| `workgraph` | [Basic Memory Workgraph](docs/basic-memory-workgraph/README.md) | 試行・つまずき・検証済みの対処、修正指示から、次の仕事にも使える知識を蓄積する。 |
| `ux-stack` | [Codex UX Stack](docs/codex-ux-stack/README.md) | 対象と操作を中心に画面を設計し、実装、画像付きレビュー、ブラウザーでの操作確認を進める。 |
| `speckit` | [SpecKit Upstream](docs/speckit-upstream/README.md) | 利用者の目的・懸念・ユースケースを要件にし、方式研究を設計と検証計画へ反映する。 |
| `github-pm` | [GitHub Project Director](docs/codex-github-pm/README.md) | Issue・PR・Projectsを調査・整理し、担当、期限、依存関係、進捗を会話から扱う。 |
| `design-research` | [Design Research](docs/design-research/README.md) | コアロジックの方式を一次資料と実験で比較し、条件・結果・未検証事項を報告にまとめる。 |
| `ecc` | [Codex ECC](docs/codex-ecc/README.md) | ECCの原本を保持し、Python実装、エラー処理、安全性レビューなどの手順を必要なときに読む。 |
| `office` | [Office Workbench](docs/codex-office/README.md) | PDF・Word・PowerPointを読み、原本を保護しながら編集と差分・描画の確認を行う。 |
| `kotonoha`（互換ID: `yomiyasu`） | [kotonohaと日本語執筆](docs/codex-yomiyasu/README.md) | 意味と条件を保って日本語を整え、段落の論旨や仕組みが伝わる説明にする。 |
| `herdr` | [Herdr](docs/herdr/README.md) | 作業ディレクトリに対応するターミナルworkspaceを開き、既存workspaceを再利用する。 |

<a id="workflow"></a>

## 導入後の使い方

対象プロジェクトをCodexで開き、会話欄に依頼を入力します。以下は各キットを導入した後の使用例です。

### 作るものと検証方法を整理する

```text
$upstream-new 社内文書を検索し、根拠を確認して回答できるアプリを作りたい。利用者、要件、設計、検証計画を整理して。
```

### 技術選定に比較の根拠を持たせる

```text
$design-research このプロジェクトの検索精度を改善する方法を比較し、評価条件をそろえて検証して。
```

### 設計書を、仕組みが伝わる日本語にする

```text
$kotonoha この設計書を、技術用語と条件を保って、仕組みや実際の変化が伝わる日本語に整えて。
```

全体の要件・設計はUpstream、特定の方式の比較はDesign Researchから始めます。
たとえば検索アプリなら、検索方式の比較結果を全体設計へ反映し、UX Stackで検索画面と操作を確認できます。
kotonohaは設計書や報告文を仕上げる工程で使えます。

各キットは単独でも利用できます。組み合わせる場合も、研究結果の採用、設計の承認、アプリの実装はそれぞれの手順に沿って進めます。
[上流工程の使い方](docs/speckit-upstream/usage.md)と[研究テーマの分割・設計の見直し](docs/speckit-upstream/reassessment.md)に、連携の流れをまとめています。

## 導入と運用の設計

- **必要なものから始める。** `--only`で導入対象を選べます。ECCの専門手順やkotonohaの追加規範は、必要な場面で参照する構成です。
- **変更範囲を確認できる。** 導入ガイドに、取得元、配置先、既存設定の扱い、更新・解除の手順をまとめています。保護処理と任意機能はキットごとに異なります。
- **検証の根拠を残す。** 自己テスト、回帰テスト、文章生成の比較評価などを、対象に合わせて用意しています。測定条件と未実施の範囲も確認できます。

導入の成功と、実際の成果物の品質は別に確認します。
[UXの検証範囲](docs/codex-ux-stack/validation.md)、[研究環境の検証結果](docs/design-research/validation.md)、[日本語執筆の評価](docs/codex-yomiyasu/validation.md)に、それぞれの根拠があります。

## エージェントを並列実行する前に

複数のエージェントを並列に走らせる場合は、メモリ不足に備えてswap領域の拡張をおすすめします。
ビルド・テスト・ブラウザー検証が重なると、個々の作業では足りていたRAMを使い切ることがあります。
swapは、RAMに収まりきらないメモリの一部をディスクへ退避し、メモリ不足によるプロセスの強制終了を起きにくくします。
ただし、退避と読み戻しが頻繁になると処理が遅くなるため、重いテストを順番に実行するなど、同時にかかる負荷も調整してください。([Red Hatのswap解説](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_storage_devices/getting-started-with-swap))

まず、現在のRAMとswapを確認します。以下の16 GiBは設定例です。既存のswap容量、同時に動かす処理、ディスクの空き容量に合わせて調整してください。

```bash
free -h
swapon --show
```

<details>
<summary>Linux：swapファイルを16 GiB追加する</summary>

Ubuntuなど、ルートのファイルシステムがext4 / XFSの環境向けです。`df -h /`で16 GiBを追加しても十分な空きが残ることを確認してください。
既存のswapは保持し、専用ファイルを追加します。同名ファイルがある場合は上書きせず停止します。
Btrfsでは[専用の作成手順](https://btrfs.readthedocs.io/en/latest/Swapfile.html)を使ってください。

```bash
df -h /
findmnt -no FSTYPE /

sudo bash <<'SWAP'
set -eu
swapfile=/swapfile-agent-intelliforge
case "$(findmnt -no FSTYPE /)" in
  ext4|xfs) ;;
  *) echo 'この手順はext4 / XFS向けです。' >&2; exit 1 ;;
esac
if [ -e "$swapfile" ] || [ -L "$swapfile" ]; then
  echo "$swapfile は既に存在するため、処理を中止します。" >&2
  exit 1
fi
umask 077
dd if=/dev/zero of="$swapfile" bs=1M count=16384 status=progress
chmod 600 "$swapfile"
mkswap "$swapfile"
swapon "$swapfile"
# 再起動後も有効にする
if ! grep -qE '^/swapfile-agent-intelliforge[[:space:]]' /etc/fstab; then
  printf '%s\n' "$swapfile none swap defaults 0 0" >> /etc/fstab
fi
if [ -d /run/systemd/system ]; then
  systemctl daemon-reload
fi
SWAP

swapon --show
free -h
```

ファイルの作成・有効化は[swapファイルの導入手順](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_storage_devices/getting-started-with-swap)に沿っています。

</details>

<details>
<summary>WSL2：swap容量を16 GBに設定する</summary>

WindowsのPowerShellから設定ファイルを開きます。swapファイルを置くWindows側のディスクにも空き容量を確保してください。

```powershell
notepad "$env:USERPROFILE\.wslconfig"
```

既存の設定を残し、`[wsl2]`セクションの`swap`だけを追加・変更します。セクションがなければ、以下を追記してください。

```ini
[wsl2]
swap=16GB
```

ファイルを保存し、WSL内の作業も保存してからPowerShellで以下を実行します。すべてのWSLディストリビューションが停止します。

```powershell
wsl --shutdown
```

WSLを起動し直し、Linux側で`free -h`と`swapon --show`を確認してください。
設定はWSL2全体に適用されます。詳細は[MicrosoftのWSL設定ガイド](https://learn.microsoft.com/en-us/windows/wsl/wsl-config#wslconfig)を参照してください。

</details>

## ドキュメントと開発

| 知りたいこと | ガイド |
|---|---|
| 導入対象・前提条件・更新方法 | [一括インストール](docs/installation.md) |
| キット別の導入手順・使用例 | [ドキュメント一覧](docs/README.md) |
| 知識の保存・共有・点検 | [Workgraphの使い方](docs/basic-memory-workgraph/usage.md) · [共有](docs/basic-memory-workgraph/sharing.md) · [点検](docs/basic-memory-workgraph/troubleshooting.md) |
| 正本の編集・配布物の生成・検証 | [開発ガイド](docs/development.md) |

ルートの`install_*.sh`は従来の導入入口です。共通CLIは`src/agent_intelliforge/`、正本とキット定義は`tools/`で管理します。生成するPluginは`plugins/`、利用ガイドと評価資料は`docs/`、回帰テストは`tests/`にあります。
生成資材を直接編集せず、正本を直して再生成します。[配布資材の編集と検証](docs/cross-platform-development.md)に手順をまとめています。
一括インストーラー、Workgraph、Codex ECCはリポジトリ一式で使います。それ以外のキットは個別スクリプト単体でも使えます。
Design ResearchとUpstreamは固定版ベースを取得・照合して組み立てるため、オフライン利用には[個別の準備](docs/design-research/installation.md#組み立てとオフライン利用)が必要です。

このリポジトリは、独自の作業手順と導入・管理ツールを、外部のSkill・Plugin・CLIと組み合わせています。
Codex、Basic Memory、SpecKit、ECC、Playwright、meiseki、yomiyasu等の上流プロジェクトは各提供元が管理しています。
導入資材の提供元と独自機能の区分は、各キットの概要・導入ガイドに記載しています。

<details>
<summary>旧Workgraph READMEのリンク</summary>

旧READMEの項目は、以下の専用ガイドへ移動しています。

| 旧項目 | 現在のガイド |
|---|---|
| <a id="start"></a>初回インストール | [初回インストール](docs/basic-memory-workgraph/installation.md#start) |
| <a id="python-tools"></a>Python環境の準備 | [Python環境の準備](docs/basic-memory-workgraph/installation.md#python-tools) |
| <a id="update"></a>アップデート | [アップデート](docs/basic-memory-workgraph/installation.md#update) |
| <a id="daily"></a>日常の使い方 | [日常の使い方](docs/basic-memory-workgraph/usage.md#daily) |
| <a id="modes"></a>設定を変更する | [設定を変更する](docs/basic-memory-workgraph/usage.md#modes) |
| <a id="correction-mode"></a>文脈付き修正指示の保存 | [文脈付き修正指示の保存](docs/basic-memory-workgraph/usage.md#correction-mode) |
| <a id="progressive-mode"></a>段階的なCase保存 | [段階的なCase保存](docs/basic-memory-workgraph/usage.md#progressive-mode) |
| <a id="share"></a>Memoryを共有する | [Memoryを共有する](docs/basic-memory-workgraph/sharing.md#share) |
| <a id="training"></a>学習用JSONL出力 | [学習用JSONL出力](docs/basic-memory-workgraph/sharing.md#training) |
| <a id="troubleshooting"></a>困ったとき | [困ったとき](docs/basic-memory-workgraph/troubleshooting.md#troubleshooting) |
| <a id="audit"></a>記憶の点検 | [記憶の点検](docs/basic-memory-workgraph/troubleshooting.md#audit) |
| <a id="details"></a>保存方針・配置・仕組み | [保存方針・配置・仕組み](docs/basic-memory-workgraph/reference.md#details) |
| <a id="update-details"></a>更新の詳細 | [更新の詳細](docs/basic-memory-workgraph/installation.md#update-details) |
| <a id="uninstall"></a>解除 | [解除](docs/basic-memory-workgraph/installation.md#uninstall) |
| <a id="development"></a>開発・検証 | [開発・検証](docs/development.md#development) |

</details>
