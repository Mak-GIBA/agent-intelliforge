# kotonohaの導入・更新

[概要](README.md) · [使い方](usage.md) · [検証](validation.md)

## 導入

Python 3.11以上を推奨します。スタンドアロンエンジンは3.10以上に対応し、不足する実行環境は導入操作でユーザー領域へ準備します。文章作成中に自動導入はしません。

```bash
bash install_kotonoha.sh --dry-run
bash install_kotonoha.sh --apply
bash install_kotonoha.sh --doctor
```

既定の配置先は ~/.agents/skills/kotonoha/ です。--skills-dirで親を指定できます。Windowsではinstall_kotonoha.ps1を使います。検査用Python・Node.js・npm依存は隣接する専用領域で管理します。原典は検証した組合せを同梱し、実行環境の準備では通信する場合があります。MCP・hooks・AGENTS.mdを変更せず、文書を外部へ送信しません。

## 既存版の更新

```bash
bash install_kotonoha.sh --update --dry-run
bash install_kotonoha.sh --update --apply
```

既存の--mode auto|explicitは保持します。未編集の旧3入口は完全なバックアップを残して退役します。編集・追加ファイル・管理外の同名フォルダがあれば、準備前に停止します。--forceでもユーザー編集を消しません。置換中の例外では元のフォルダを復元します。

キットID・Plugin名・実行入口はkotonohaです。旧インストーラーと旧キットIDは廃止しました。上流OSSのyomiyasuという名称は維持します。

## 共通CLI・Pluginの旧名からの移行

`intelliforge update --only kotonoha --agent codex --apply`（Claudeでは`--agent claude`）を使います。まず`--apply`を省略して移行予定を確認できます。既存の導入方式を引き継ぎ、旧名を互換エイリアスとして実行しません。

所有権とハッシュが一致する管理対象だけを移行します。推敲モードを保持し、絶対パスを含む依存環境は新しい配置へ再準備します。旧環境は`migration-backups/`に残します。新旧の併存、独自編集、所有権不明、リンク先があれば変更前に停止します。移行前に旧CLIを終了してください。

Pluginは公式ホストCLIで新名の導入と有効状態を確認してから旧登録を退役します。旧Pluginが無効で、ホストCLIに無効化機能がなければ移行を停止します。現行Codex CLIはこの制約に該当します。設定やキャッシュの直接編集で回避しません。通常の失敗は旧状態へ復元し、ホスト側の復元コマンドも失敗した場合は旧原本と復旧用バックアップを保持します。

## 上流最新版の確認と統合

```bash
bash install_kotonoha.sh --check-update
python3 tools/kotonoha/update_upstreams.py check
cp -a tools/kotonoha/assets/kotonoha /tmp/kotonoha-baseline
python3 tools/kotonoha/update_upstreams.py prepare --source all --candidate /tmp/kotonoha-candidate
```

prepareは最新安定リリースをcommitとハッシュで固定し、原典・規則・差分・未確認事項を候補ディレクトリへ保存します。個別対象は--source yomiyasuまたはmeiseki、安定リリースの固定は個別対象に--ref TAGを指定します。現在の採用版と導入済みSkillは変更しません。

保守担当者は候補の原典差分を読み、内部規則・アダプター・依存の変更と能力の対応を確認します。review.jsonへ採用・除外の理由と確認済み能力を記録します。旧版との規範照合に加え、現行版と候補版を24用途で実際に起動するevals/flow_native.pyを使い、参照・検査・完成稿の比較を候補のquality.jsonへ保存します。既定の全体上限は60分です。インストーラーがAIを自動起動することはありません。

```bash
python3.11 tools/kotonoha/evals/flow_native.py --candidate /tmp/kotonoha-candidate --baseline /tmp/kotonoha-baseline --runtime "$HOME/.agents/.kotonoha-runtime"
python3 tools/kotonoha/update_upstreams.py verify --candidate /tmp/kotonoha-candidate
python3 tools/kotonoha/update_upstreams.py promote --candidate /tmp/kotonoha-candidate
```

verifyは品質記録と固定された候補・出力の一致を検査します。promoteは検証済みの原典・規則・アダプターを一組でリポジトリへ反映します。重大な意味変更、未反映の対象機能、品質低下、記録の欠落・改変は保留です。取得できたことと能力の検証は別です。

比較には受け取り側で準備した専用lint環境を--runtimeで指定します。規範の修正後は同じ候補へ--round 2を指定し、新設計側を全件再実行します。必要な場合は最後の--round 3まで実行できます。既存の試行を別の規範・実行コードへ付け替えることはできず、元の制限時間は延長しません。

比較コードはPython 3.11以上と認証済みCodex CLIを使い、利用者設定のモデル・推論設定を呼出しに固定します。モデル実行には費用と時間がかかります。固定課題での比較を一般的な能力の証明とは扱わず、重要な変更では未使用の課題でも確認します。

--update --upstream-onlyは互換操作として、未統合の最新版があればUPSTREAM_REVIEW_REQUIREDを返して既存版を保持します。GitHub API制限・通信障害でも現在の採用版を消しません。配布元の真正性や人の承認をハッシュから推測しません。

## 解除と共有

--uninstall --dry-runで予定を確認し、--uninstall --applyで管理対象を解除します。編集や追加があれば停止し、バックアップは残します。

共有するときはkotonohaフォルダだけをコピーできます。resources.jsonは実行時の原典検証に必要なので残します。.installer.jsonは導入所有情報であり、手動共有では省けます。検査用の実行環境とsettings.jsonは受け取り側で準備し、個人の設定・キャッシュ・認証情報を配布しません。

4.1.0はFLOW.jsonの旧規範照合と、24用途の実出力・参照記録・別実行の評定が揃うまで採用を保留します。4.0.0の一括入力による比較や、完成稿だけを試験の外で直した記録では代替しません。
