# キットを選んでインストールする

[English](en/installation.md) | **日本語**

[リポジトリ概要](../README.ja.md) · [docs一覧](README.md)

[`install_all.sh`](../install_all.sh)では、`--only`で必要なキットを選ぶか、全キットを一括導入できます。
選んだキットの個別インストーラーを順番に呼び出すため、取得元、配置先、既存ファイルの保護方法はキットごとに異なります。導入前に予定を確認し、`--apply`で適用します。

共通CLI、ネイティブWindows、Claude Codeの導入は[OS・ホスト対応ガイド](cross-platform.md)を参照してください。
このページのBash経路はCodex向けの既存方式を維持しています。Plugin方式への移行は明示的に選択します。

## 前提条件

リポジトリをcloneして使います。一括スクリプトだけをダウンロードすると、呼び出すインストーラーや補助資材が不足します。
全ツールの標準導入はLinux / WSL2向けです。Bash、PATH上のPython 3.11以降の`python3`、venv・pip、
Node.js 20以降・npm、Git、curl、導入済みCodex CLI、外部配布元へのネットワーク接続が必要です。
導入済みWorkgraphを更新する場合は、同じ`python3`からPyYAMLを参照できるようにします。
準備方法は[WorkgraphのPython環境](basic-memory-workgraph/installation.md#python-tools)にあります。

Codex CLIには、各ツールが使うplugin・MCP・app-server等のコマンドが必要です。
選択したツールだけを入れる場合は、そのツールの前提条件を確認してください。
kotonoha単独では不足するPython・Node.jsを専用領域へ自動準備します。他キットの前提条件はそれぞれの導入ガイドを参照してください。
Design Research 2.5.0とUpstream 2.0.6の組み立てにはPython 3.11以上が必要です。
導入後のGitHub接続、モデルの認証、文書描画など、実際の利用に必要な準備は各ガイドで説明しています。

## 導入する

```bash
git clone https://github.com/Mak-GIBA/agent-intelliforge.git
cd agent-intelliforge
bash install_all.sh --list
bash install_all.sh --dry-run
bash install_all.sh --apply
```

引数なし、または`--dry-run`は、実行予定のコマンドだけの表示です。
個別インストーラーは起動せず、ダウンロードや導入先への書き込みも行いません。
前提ソフトの動作や配布元への接続は、この予定表示では確認しません。
`--apply`を付けると、以下の順序で実際に導入します。

| ID | 導入対象・標準動作 | 詳細 |
|---|---|---|
| `workgraph` | Basic Memory、公式plugin、Workgraph・hooks・保存プロジェクト。導入済みなら設定を保持する`--update` | [導入・更新](basic-memory-workgraph/installation.md) |
| `ux-stack` | ooui-design、認知負荷のガイド、画像付きUX検証、Product Design・Build Web Apps、UIレビュー、Playwright | [導入・更新](codex-ux-stack/installation.md) |
| `speckit` | 固定版から両ツールを組み立て・検証し、SpecKit CLIとWorkbench・上流工程のSkillを導入 | [導入・更新](speckit-upstream/installation.md) |
| `github-pm` | GitHub Project DirectorとCodex共通指示。ghの導入は別途指定 | [導入・更新](codex-github-pm/installation.md) |
| `design-research` | 固定版から両ツールを組み立て・検証し、単一入口の研究Skillとハーネスを導入 | [導入・更新](design-research/installation.md) |
| `ecc` | Codex標準ECC pluginと必要時に参照する入口。`--apply`で導入・設定 | [導入・更新・復元](codex-ecc/installation.md) |
| `office` | OfficeCLI、文書処理ライブラリ、Office Workbench。`--apply`で導入 | [導入・更新](codex-office/installation.md) |
| `kotonoha`（`yomiyasu`も互換） | meisekiの明晰化、yomiyasuの自然さ、段落構成・留保整理を統合。`--apply`で不足するPython・Node.jsと検査環境も準備 | [導入・更新](codex-yomiyasu/installation.md) |
| `herdr` | Herdr、herdr-open、Bash設定 | [導入とBash設定](herdr/installation.md) |

UX Stackは日本語のUI文言を仕上げる際にkotonohaを推奨します。
一括導入では両方が含まれ、個別選択なら次のように組み合わせられます。

```bash
bash install_all.sh --only ux-stack,kotonoha --dry-run
bash install_all.sh --only ux-stack,kotonoha --apply
```

`--only`はカンマ区切りでも、複数回でも指定できます。同じIDの重複は1回にまとめ、上の表の順序で実行します。
スクリプト自身の場所を基準に資材を参照するため、別の作業ディレクトリから絶対パスで呼び出すこともできます。

UpstreamとDesign Researchを組み合わせる場合は、両方を選びます。片方の導入で、もう片方が自動導入されるわけではありません。

```bash
bash install_all.sh --only speckit,design-research,kotonoha --dry-run
bash install_all.sh --only speckit,design-research,kotonoha --apply
```

両配布スクリプトは、固定コミットの元インストーラー2本を取得・照合して組み立てるため、通常は通信します。
一括スクリプトは`--base-dir`・`--offline`・`--build-only`を転送しません。
オフラインの組み立て・再配布は、[Design Research](design-research/installation.md#組み立てとオフライン利用)または[Upstream](speckit-upstream/installation.md#組み立てとオフライン利用)の個別手順を使います。
組み立て・自己テスト・更新・診断の確認結果と過去の停止条件は、[検証結果](design-research/validation.md)に記載しています。

## 再実行・更新・解除

既存の設定や編集済み資材の扱いは、各インストーラーの保護処理に従います。
一括スクリプトから`--force`を渡すことはありません。
導入済みWorkgraphは`CODEX_HOME`、未指定なら`~/.codex`にある配置を検出し、
`--update`で保存先・保存モードを維持しながらローカル資材とスキーマを更新します。
この経路ではBasic Memory本体や外部pluginを取得・更新しません。
既存配置が不完全でも、初回導入で設定を作り直す処理へは切り替えません。

ほかのツールは通常の導入経路を使います。すでにある管理対象をそのまま保持するツールもあるため、
一括導入の再実行がすべてのツールの最新版への更新になるわけではありません。
Design Researchの更新には`--update`、Upstreamの更新には`--apply --update`を個別に指定します。
特定の版への更新、任意機能、配置先変更は、表の導入ガイドに沿って個別インストーラーで指定します。
解除も各ガイドに従って行います。Herdrは専用の解除オプションがなく、管理対象のBash設定等を手動で取り除きます。
OfficeのMCP・Docling・OSパッケージ導入などの任意機能は、一括スクリプトからは指定しません。

## 途中で失敗した場合

選択したインストーラーと必要な補助コードがあるかを、導入開始前に確認します。
実行中に1つの導入処理が失敗した場合は、残りのツールも実行し、最後にツールごとの結果と未完了件数を表示します。
成功した導入を一括で取り消す処理はありません。原因を解消して全体を再実行するか、失敗したIDを`--only`で選び直してください。
個別インストーラーが中断を表す終了コード130または143を返した場合は、後続の導入を停止します。

| 終了コード | 意味 |
|---|---|
| `0` | 予定・一覧・ヘルプの表示完了、または選択した全導入処理が正常終了 |
| `1` | 1つ以上の導入処理が未完了。表示されたIDと個別ログを確認 |
| `2` | 引数が不正、または選択したインストーラー・補助コードが不足。導入処理は未開始 |
| `130` / `143` | 中断。先に完了した処理は保持 |

`COMPLETE`は選択したインストーラーの正常終了を示します。
実際のCodexセッションでのSkillの選択、モデルの出力品質、アプリや文書の完成までは示しません。
導入後はCodexを再起動し、各ガイドの状態確認・doctor・最初の利用手順を実行してください。
