# Codex UX Stack：インストール・更新・解除

[English](../en/codex-ux-stack/installation.md) | **日本語**

[概要](README.md) · [使い方](usage.md) · [検証範囲](validation.md) · [docs一覧](../README.md)

## 管理対象だけを更新する

```bash
bash install_codex_ux_stack.sh --update
ux-gan-harness doctor --project /path/to/app --check-mcp
```

`--update`は導入済みの管理対象を更新します。1.4.0では標準構成に加わった `ux-visual-design` も追加します。
未導入のPlugin・外部MCP・任意Skillは追加せず、解除・無効化したMCPも復元しません。
旧版はバックアップし、手動編集済み・未管理の同名資材は保持して未完了を報告します。
新規導入は従来の引数なし、未導入分を含めた再適用は`--force`を使います。

## 前提条件と導入

Linux / WSL2、Bash、Python 3.10以上、Node.js 20以上、npm、構造化exec出力・plugin・MCPに対応する認証済みCodex CLIが必要です。
ハーネスの実行にはGit、ChromiumのOS依存ライブラリ、Codexサンドボックスを起動できるホスト環境も必要です。

リポジトリのルートで実行します。スクリプト1ファイルだけをコピーして実行することもできます。

~~~bash
bash install_codex_ux_stack.sh --help
bash install_codex_ux_stack.sh --dry-run
bash install_codex_ux_stack.sh
bash install_codex_ux_stack.sh --doctor
~~~

**引数なしは実際に導入します。** --dry-runは予定表示だけで、ダウンロード・登録・導入先への書き込みを行いません。
インストーラーはCodexのログイン、対象アプリへの依存追加、データ移行を行いません。

## オプション

| オプション | 動作 |
|---|---|
| なし | 不足する標準構成を導入 |
| --deep | 固定コミットのux-critiqueも導入 |
| --visual-tools whimsical,figma | 選択した公式Remote MCPを登録。既存設定・無効化を保持し、認証は別に実行 |
| --doctor --check-design-mcp | 任意MCPの登録・接続・認証・広告された機能を分けて診断。外部への書き込みはしない |
| --update | 導入済みの管理対象だけを更新し、未導入のPlugin・MCPは追加しない |
| --force | このインストーラーが導入した未編集の対象を再配置・再登録 |
| --dry-run | 導入・解除の予定表示 |
| --status | 資材と登録の検査。ブラウザーは起動しない |
| --doctor | 資材・登録に加え、Chromium起動とCodexサンドボックスを確認 |
| --uninstall | このインストーラーが導入した未編集の対象だけを解除 |
| --extract PATH | 空または未使用のディレクトリへソースを展開。導入はしない |
| --codex-home PATH | Codex設定と実行環境の保存先 |
| --skills-root PATH | 新規Skillの保存先 |
| --bin-dir PATH | 起動コマンドの保存先 |
| --no-browser-download | Chromium取得を省略。実行可能かは別途確認 |
| --help / -h | ヘルプ表示 |

既存のSkillは指定先、CodexのSkillディレクトリ、~/.agents/skillsを確認し、重複導入を避けます。
手動導入や編集済みの対象は--forceでも置き換えません。無効化されている対象pluginは自動で有効化せず原因を報告します。

## 取得元・版・配置

| 対象 | 取得・版 | 新規の保存先 |
|---|---|---|
| ooui-design・参照資料 | 配布物1.4.0。OOUIと認知負荷の基準を同梱 | ~/.agents/skills/ooui-design/ |
| ux-visual-design | 配布物1.4.0。Skill・契約・編集可能な成果物・MCPヘルパー | ~/.agents/skills/ux-visual-design/ |
| Product Design / Build Web Apps | openai-curated-remoteのCodex管理版。実際の版を記録 | Codexのplugin環境 |
| web-design-guidelines | vercel-labs/agent-skillsのコミット063bee94c3f4df8453406c830b0a7df0f2860278 | ~/.agents/skills/web-design-guidelines/ |
| ux-critique | Thecsiz/ux-critiqueのコミット3da293cafb639195bf71797590081d4ffb0045ba | ~/.agents/skills/ux-critique/ |
| ハーネス・専用Skill・共通設計基準 | 配布物1.4.0 | ~/.agents/skills/ux-gan-harness/ |
| ブラウザー環境 | Playwright 1.63.0 / Playwright MCP 0.0.83、埋め込みnpm lockfile | CODEX_HOME/ux-stack/runtime/ |
| 起動コマンド | ハーネスのBashへ渡すラッパー | ~/.local/bin/ux-gan-harness |
| 導入記録・バックアップ | ハッシュ、版、処理結果、旧資材 | CODEX_HOME/ux-stack/ |

CODEX_HOMEの省略時は~/.codexです。ChromiumはPlaywrightのキャッシュへ取得し、PLAYWRIGHT_BROWSERS_PATHがあればその設定を使います。
標準MCPは固定版のNodeエントリーポイントと、取得したChromiumの実行パスを使います。
既存のMCPは独自設定を保護します。配置前に資材を検査し、再配置時は旧資材をbackups/へ残します。

skills@latestへの依存は外しました。取得するSkillの正本は[sources.json](../../tools/codex-ux-stack/sources.json)、
ブラウザーの正本は[npm lockfile](../../tools/codex-ux-stack/browser/package-lock.json)です。配布元にあるライセンス・参照資材も保存します。
ライセンスファイルがない原本は、その事実をUPSTREAM_SOURCE.jsonに記録します。

OOUIと認知負荷の参照資料は、同じ正本からooui-designとハーネスへ配置します。
ハーネスには自身の資料を同梱するため、別のSkill配置先には依存しません。
日本語UI文言と設計・レビュー・改善レポートにはkotonohaを推奨し、未導入なら既存のyomiyasuも使えます。[日本語Skillの導入手順](../kotonoha/installation.md)で別途導入してください。UX Stackからは自動導入しません。
現在の`status` / `doctor`は互換入口のyomiyasuの有無を表示します。日本語Skillが未導入でも、UX Stackの導入失敗にはしません。
Basic Memoryが利用可能なら、スキルは既存の設定に従って関連する過去の指摘を参照します。
参照は読み取りのみで、未導入・参照不能でも作業を続けます。UX StackからMemoryの導入・設定変更は行いません。

## 更新・確認

~~~bash
bash install_codex_ux_stack.sh --status
bash install_codex_ux_stack.sh --doctor
bash install_codex_ux_stack.sh
bash install_codex_ux_stack.sh --force
bash install_codex_ux_stack.sh --deep --force
~~~

管理対象を更新し、新しい標準Skillを追加する場合は`--update`を使います。引数なしでは不足する標準Skillが追加されますが、
既存の未編集ハーネスはそのままです。status / doctorは新スキルとハーネスの参照資料も確認するため、
旧ハーネスのままでは未準備として報告します。未管理・編集済みの同名Skillは保護します。

対象ごとにINSTALLED・SKIP・FAILEDを表示します。一部が失敗すると終了コード1とINCOMPLETEになります。
先に導入した対象は残り、原因を解消して再実行できます。plugin・MCPを含む一括ロールバックはありません。
ファイルの置き換えに失敗した場合は直前の資材を復元します。

COMPLETEは導入処理の完了です。ブラウザー、Codexサンドボックス、モデル、アプリの操作は別の確認です。
Skillが候補に出なければCodexを再起動して$ooui-designまたは$ux-gan-harnessを入力してください。
起動コマンドがPATHにない場合は、保存先の絶対パスでも使えます。

## Whimsical／Figmaの任意連携

```bash
bash install_codex_ux_stack.sh --visual-tools whimsical
bash install_codex_ux_stack.sh --visual-tools figma
bash install_codex_ux_stack.sh --visual-tools whimsical,figma
bash install_codex_ux_stack.sh --doctor --check-design-mcp
```

登録先は公式の `https://mcp.whimsical.com/mcp` と `https://mcp.figma.com/mcp` です。
Codexネイティブのapp-server設定APIで選択先だけを更新し、既存の手動設定を再利用します。
登録とOAuth認証は別です。診断に表示された登録名で、公式の認証フローを実行します。

```bash
codex mcp login whimsical
codex mcp login figma
bash install_codex_ux_stack.sh --doctor --check-design-mcp
```

同じURLが別名で登録されている場合は、その名前を使います。重複登録、既存の認証情報の複製、
無効化されたサービスの再有効化は行いません。OAuth未完了、接続失敗、機能取得失敗、対象への書き込み権限は別の状態です。
doctorは外部ファイルへ書き込まないため、`write_permission: not_tested` は正常な診断結果です。
実行時にツール一覧と引数スキーマを確認し、実際に編集するファイル・フレーム・ノードを限定します。

`--status` は接続せず `not_probed` を返します。選択したMCPの登録が失敗しても、導入済みのCoreは残ります。
manifestの `design_mcp_pending` に未完了を記録し、原因解消後に同じ選択で再実行できます。
登録成功後の検証だけが中断した場合は、再実行時に既存登録として再利用し、所有権を推測して取得しません。
手動登録と同様に解除対象外として残るため、必要なら公式CLIで対象名を確認して解除します。
`core_ready` と `design_mcp_ready` は独立しており、外部MCPの未接続だけでCoreを利用不能にはしません。

追加配布経路では `intelliforge install --only ux-stack --agent codex --plugin --visual-tools whimsical,figma --apply`、
診断は `intelliforge doctor --only ux-stack --agent codex --plugin --check-design-mcp` です。
プレビューは `--apply` を省略するか `--dry-run` を付けます。Claude経路へのCodex用MCP登録は行いません。

現在の接続方法は [WhimsicalのCodex連携](https://whimsical.com/integrations/codex)、
[Figma Remote MCP](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)、
[Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)を参照してください。

## 解除・復旧

~~~bash
bash install_codex_ux_stack.sh --uninstall --dry-run
bash install_codex_ux_stack.sh --uninstall
~~~

導入記録にある未編集の対象だけを解除します。
もともと存在した対象、編集済みの資材・設定、アプリの成果物、ブラウザーキャッシュ、バックアップは残ります。
解除できない依存対象がある場合はブラウザー環境も保護し、未完了を報告します。

手動編集を保持して更新する場合は、保存先とmanifest.json、バックアップを比較してください。
編集を別の場所へ保存し、導入先を空けて再実行した後に必要な変更を戻せます。

<a id="troubleshooting"></a>

## 困ったとき

| 状況 | 確認・対処 |
|---|---|
| pluginが見つからない | codex plugin list --available --jsonで配布名・marketplaceを確認 |
| Skillが候補に出ない | 保存先とSkillの無効化設定を確認 |
| 設計参照資料が欠落・空・旧版 | 未編集の管理対象は--forceで更新。同名の未管理・編集済みSkillは内容を保管してから導入先を確認 |
| Chromiumが起動しない | doctorで原因を確認し、PlaywrightのOS依存ライブラリを用意 |
| 独自MCP設定が残る | その設定を検査。ハーネスは失敗理由を記録してローカル経路へ切替可能 |
| bwrap・ユーザー名前空間の権限エラー | ホスト／コンテナーのCodexサンドボックス対応を修復。権限は迂回せず停止 |
| 編集済みとして再導入が止まる | ハッシュと内容を比較し、編集を別に保管してから更新 |
| ダウンロードやnpmが失敗 | 既存資材は削除されない。原因を解消して再実行 |
| 起動コマンドが見つからない | ~/.local/bin/ux-gan-harness doctorを実行するかbin-dirをPATHへ追加 |

参考：[Codexの非対話実行](https://developers.openai.com/codex/noninteractive/)、[Skillの配置と呼び出し](https://developers.openai.com/codex/skills/)、[Playwright MCP](https://github.com/microsoft/playwright-mcp)、[Linuxサンドボックス](https://github.com/openai/codex/blob/main/codex-rs/linux-sandbox/README.md)。
