# 共通CLIとOS・ホスト対応

[README](../README.md) · [従来の一括導入](installation.md) · [検証結果](cross-platform-validation.md)

Codexを既定の対象にし、既存のLinux / WSL2導入を保ったまま配布経路を追加しています。
Claude CodeのPluginと実行アダプターは試験対応です。Codexのインストールや認証を必要とせず、Claude自身のCLIと認証を使います。

| 対象 | 共通CLIが選ぶ経路 | 既存導入への影響 |
|---|---|---|
| Codex / Linux・WSL2 | 従来の`install_all.sh`と個別スクリプト | 名前・既定値・設定・管理方式を継続 |
| Codex / Linux・WSL2で`--plugin` | 公式Plugin管理CLIと独立した管理資材 | 明示的に選択。既存Skill・Workgraphフックとの競合は停止 |
| Codex / ネイティブWindows | 公式Plugin管理CLIとPython実行アダプター | 既存資材の自動移行は行わない |
| Claude Code | Claude公式Plugin管理CLIと独立した管理資材 | Codexの設定を編集しない。実機・モデル評価は未実施 |
| Herdr | CLIと作業ディレクトリの再利用ラッパー | Pluginを作らず、追加経路ではシェル設定を編集しない |

## 導入前に内容を確認する

Python 3.11以上と、選んだホストの公式CLIを用意します。Windowsでも管理者権限、Bash、WSL、Dockerはこの追加経路の前提ではありません。
CLIの配布には[uvのツール環境](https://docs.astral.sh/uv/guides/tools/)を使えます。PyPIへの公開はまだ行っていません。

```bash
git clone https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge
uv tool install .
intelliforge list
intelliforge inspect --only yomiyasu --json
```

cloneした資材から標準のwheelを構築して導入します。パッケージの構築はダウンロードやホスト設定の更新を行いません。生成済み資材と編集用ソースが一致しなければ構築を止めます。

`inspect`、および`--apply`のない導入・更新・解除は、キット定義の表示だけです。ネットワーク接続、依存ソフトの導入、Plugin管理CLIの起動を行いません。
正本の[`kit.json`](../tools/)と一括スクリプトの冒頭コメントから、取得元・Skill名・依存ソフト・配置先・設定範囲を確認できます。

## 導入する

```bash
# Linux / WSL2：既存Codex方式。ホスト指定を省略できる
intelliforge install --only yomiyasu --apply

# Codex Plugin方式を明示的に選択
intelliforge install --agent codex --plugin --only yomiyasu --apply

# Claude Code
intelliforge install --agent claude --only yomiyasu --apply
```

WindowsのPowerShellでも同じ`intelliforge`コマンドを使います。checkoutからの入口も用意しています。

```powershell
uv tool install .
.\install_all.ps1 --only yomiyasu
.\install_all.ps1 --only yomiyasu --apply
```

Pluginのフック・Skill本文はPATH上の`intelliforge`を呼び出します。導入時にCLIの存在を確認します。公式の[Codex Plugin形式](https://developers.openai.com/plugins/build/plugins)と[Claude Plugin形式](https://code.claude.com/docs/en/plugins-reference)を生成し、各ホストの管理コマンドに登録します。
登録元は管理するローカルMarketplaceです。Pythonパッケージを更新しても、ホストが参照するパスを維持できます。

複数のキットは`--only ux-stack,design-research,yomiyasu`のように指定します。`--agent both`はホストごとに別の資材を導入します。
全選択では、そのキットに必要な外部ソフトの準備も必要です。GitHub管理には`gh`の導入と認証、Officeの完全な描画にはLibreOfficeや適切なフォントなどを用意してください。

## 更新・診断・解除

まずCLIのパッケージを更新し、各キットを更新します。checkoutを更新するGit操作は利用者の管理下で行います。

```bash
uv tool install --force .
intelliforge update --agent claude --only yomiyasu --apply
intelliforge doctor --agent claude --only yomiyasu
intelliforge uninstall --agent claude --only yomiyasu --apply
```

Codex Plugin方式の管理には`--agent codex --plugin`を付けます。Linuxの既定方式の更新は従来の個別インストーラーへ委譲し、対応する既存コマンドがない操作は自動で代替しません。

```bash
# 上流yomiyasuだけ更新。独自規範・補助Skillはそのまま
intelliforge update --agent claude --only yomiyasu --upstream-only --apply
# 自動使用の許可を切り替える
intelliforge update --agent claude --only yomiyasu --mode explicit --apply
intelliforge update --agent claude --only yomiyasu --mode auto --apply
# 実際の資材と上流原本の保存先を調べる
intelliforge locate --agent claude --only yomiyasu
intelliforge locate --agent claude --only yomiyasu --upstream
```

更新前に所有権・ファイルハッシュを確認します。未管理資材、手動編集、リンク・junction、危険な相対パス、大小文字で衝突するファイル名は上書きしません。
更新はステージングとバックアップを経て反映し、資材の反映やPlugin登録に失敗した場合は管理資材を戻します。ホストCLIの外部状態は独自に書き換えず、失敗があればそのホストの一覧で状態を確認します。
解除では管理するPluginまたはSkillだけを外し、バックアップ・設定・上流原本・依存環境を残します。Memoryのノートや研究成果物を削除しません。

## 研究・UX評価を実行する

入口は既存のSkillを維持します。Claudeでは`/design-research:design-research`、`/ux-stack:ux-gan-harness`、`/speckit:upstream-new`などの名前になります。
生成する本文のコマンドは次の共通入口に接続します。

```bash
intelliforge kit-run design-research --agent claude -- doctor --project <project>
intelliforge kit-run design-research --agent claude -- research --project <project> --brief "比較する方式と制約" --slug comparison --allow-network
intelliforge kit-run ux-stack --agent claude -- audit --project <project> --url http://localhost:3000
intelliforge kit-run speckit --agent claude -- doctor --project <project>
```

Claudeでは、既存の役割別プロンプト・JSON Schema・評価予算・成果物検証を使い、`claude -p`の構造化出力を受け取ります。構造化出力がない実行や失敗した実行を成功として扱いません。
UXのブラウザー操作は同梱のPlaywright経路を使い、他製品専用のブラウザー機能を利用可能と見なしません。
モデルによる修正の権限、原稿・事実の保持、独立したレビュー、証拠の点検は既存の規範を維持します。

ネイティブWindowsのCodex評価には、対応する[Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)が必要です。
Claudeの評価・実験にはNode.js 24以上と固定版[Microsoft MXC SDK](https://github.com/microsoft/mxc)を導入し、Windows ProcessContainer、Linux Bubblewrap、macOS Seatbeltを明示的に選びます。
OSの必要な更新やバックエンドが不足したら停止し、隔離を省略しません。一般のWindows CIが通っても、Windows 11の実際の隔離を確認したことにはなりません。
Windowsの実験用コマンドはPowerShellの構文を使い、Bashの任意のコマンド文字列を機械的に翻訳しません。
ClaudeのWindows実験では[公式PowerShellツール](https://code.claude.com/docs/en/env-vars)を子プロセス内で有効にします。利用者の環境変数や設定ファイルには書き込みません。
WindowsのホストCLIはネイティブ実行ファイルを優先し、公式npm配置の`.cmd`は対応するJavaScript入口をNode.jsで直接起動します。未知のbatch shimには処理を委ねません。

```bash
# 一時ファイルだけで読み取り専用境界を確認。モデルは呼ばない
intelliforge doctor --agent codex --only design-research --isolation-smoke
intelliforge doctor --agent claude --only design-research --isolation-smoke
```

## キット固有の準備

- yomiyasuは独自規範と上流原本の保存先・バージョンを分けます。上流ファイルは改変せず、リリースのcommit・blob・サイズを元のインストーラーの検証で照合します。
- Workgraphは元の保存ポリシーとテンプレートを使います。Claudeの会話イベントにはセッションごとのターン識別子を割り当て、Planでの書き込み禁止・明示的なarm・一度だけのStop評価を保ちます。MCPには`uvx`が必要です。既存のBasic Memoryプロジェクトやノートは移行せず、必要なプロジェクト選択とスキーマ配置は明示的に行います。
- ECCの追加経路は、公式リリースのtagとcommitを記録した原本を必要時に読みます。従来のCodex経路は公式ECC Pluginを継続します。追加経路は他のSkillや任意のMCPを一括有効化しません。必要なMCPはホストの公式コマンドで選択します。
- Officeは固定版OfficeCLIと元のPython依存条件を使います。Windows x64 / ARM64の配布ハッシュを照合します。MCP、Docling、システム描画ソフトなどの追加機能は自動で有効にしません。
- Herdrは既存実行ファイルを優先します。Windows x64で未導入なら固定版公式ZIPをハッシュ検証して導入します。作業ディレクトリの再利用は`intelliforge kit-run herdr --agent <host> -- <directory>`から実行します。未知のセッション形式では停止します。

Windows実機とClaudeの実モデルによる一連の評価は、この環境では未実施です。[確認済みの範囲と残る検証](cross-platform-validation.md)を区別して利用してください。
