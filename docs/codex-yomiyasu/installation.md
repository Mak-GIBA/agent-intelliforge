# kotonohaのインストール・更新・解除

[概要](README.md) · [使い方](usage.md)

## 前提と導入

Linux / WSL2はBash、HTTPS取得と展開に使うcurl（またはwget）・tar・ハッシュ検査コマンドが必要です。WindowsはPowerShellを使います。Skillを使うCodex等のホストは事前に用意してください。

Python・Node.jsがなくても`--apply`でユーザー専用環境を準備します。Pythonが必要な場合は固定版uvを経由して3.11系を用意し、Node.jsは検証した24系LTSの公式配布をハッシュ照合して取得します。検査パッケージはlockfileに固定します。sudo、OSのパッケージ管理、永続的なPATH変更は行いません。

```bash
bash install_kotonoha.sh                 # 予定表示
bash install_kotonoha.sh --apply         # Skillと実行環境
bash install_all.sh --only kotonoha --apply
```

```powershell
.\install_kotonoha.ps1                  # 予定表示
.\install_kotonoha.ps1 --apply
```

従来名の単体インストーラーも同じ正本から生成します。共通CLIは`intelliforge install --only kotonoha --apply`でも選択でき、既存のキットID・Plugin名`yomiyasu`は維持します。Windowsの一括入口はPython/uvがなくても、日本語キットだけなら単体bootstrapへ委譲します。

Python自体がない環境のプレビューは、取得せずbootstrapの概要を表示します。引数ごとの完全なプレビューには既存のPythonを`PYTHON_BIN`で指定してください。`--apply`を付けない診断・ヘルプでも、Pythonを自動取得しません。

専用環境はskillsディレクトリの親にある`.kotonoha-runtime`、Python bootstrapはユーザーデータ領域の`agent-intelliforge/kotonoha-bootstrap`へ保存します。Pluginではキット状態ディレクトリの`dependencies/kotonoha`を使います。解除しても環境とバックアップは残ります。


```bash
bash install_codex_yomiyasu.sh
bash install_codex_yomiyasu.sh --apply
bash install_codex_yomiyasu.sh --doctor
```

標準ではkotonoha、yomiyasu互換入口、paragraph-writing、japanese-direct-writingを導入します。meisekiとyomiyasuの初回導入ではGitHub Releasesの最新安定版を調べ、その実行で取得するcommitを確定します。
yomiyasuはGit blob IDとサイズ、meisekiは対応確認済み資材のSHA-256を検査してから配置します。meisekiに未対応の規範変更がある場合は停止し、既存Skillを維持します。正常な再実行では上流を勝手に更新しません。
同じ構成での再実行は既存の導入を保持し、上流を自動更新しません。

paragraph-writingとjapanese-direct-writingは、役割を限定した現在の本文と由来の記録を同梱しています。導入時に元のGistやZIPへアクセスする必要はありません。各スキルの発動設定は、選んだモードに合わせて生成します。

既定の配置先は`~/.agents/skills/`の下にある各スキル名のディレクトリです。
`--skills-dir PATH`で親ディレクトリを変えた場合は、診断・更新・解除でも同じ指定を使います。
同名の未管理Skillや別の場所の同名Skillを検出した場合は上書き・二重登録をしません。
選択した全スキルの検証と準備を済ませてから配置します。ディレクトリの切り替えに失敗した場合は、切り替え済みのSkillも元へ戻します。

## 対象を選ぶ

`--only all|yomiyasu|paragraph-writing|japanese-direct-writing`で導入・更新・診断・解除の対象を選べます。既定は`all`です。

```bash
bash install_codex_yomiyasu.sh --only paragraph-writing --apply
bash install_codex_yomiyasu.sh --only japanese-direct-writing --apply
bash install_codex_yomiyasu.sh --only yomiyasu --doctor
bash install_all.sh --only yomiyasu --apply
```

既存の適合Pythonがあれば、paragraph-writingまたはjapanese-direct-writing単独の導入に上流取得は不要です。一括導入の`kotonoha`と互換ID`yomiyasu`は同じ日本語キットを導入します。
1.3.0、2.0.0-proposal.1、proposal.2から2.0.0-proposal.3へ移行する場合は、次の更新を使います。入口と補助スキルを更新し、yomiyasuの上流原本を最新安定版から取得します。既存の発動モードは保持します。

```bash
bash install_codex_yomiyasu.sh --update --apply
```

## 更新と発動モード

```bash
bash install_codex_yomiyasu.sh --check-update
bash install_codex_yomiyasu.sh --update
bash install_codex_yomiyasu.sh --update --apply
```

`--check-update`はyomiyasuの最新安定版と、補助スキルの同梱版を、それぞれ導入版と比較します。
`--update`は`--apply`がなければ通信せず予定を表示します。適用時にyomiyasuの上流版を確定し、検査してから配置します。
paragraph-writingまたはjapanese-direct-writing単独の更新確認・更新は通信せず、実行しているスクリプトの同梱版を使います。
既存の管理ファイルに編集や欠落がある場合は、`--force`を付けても停止します。
更新前の資材はバックアップに残します。

上流を更新せず、このリポジトリの入口・運用設定と補助スキルを更新する場合は`--force --apply`を使います。ただし上流の必須ファイルが欠ける旧導入は、まず`--update --apply`で整えてください。2.0系列では`upstream/UNICODE-LICENSE.txt`も必須です。
既存の各Skillの発動モードは保持します。新規の補助スキルは管理済みyomiyasuのモードを継承し、全て新規なら`auto`にします。
`--mode`を指定すると選択したSkillへ適用します。既存設定を変更するときは、次のように明示します。

```bash
bash install_codex_yomiyasu.sh --mode explicit --force --apply
bash install_codex_yomiyasu.sh --mode auto --force --apply
```

新規導入の既定は`auto`で、文章を仕上げる依頼でSkillの自動選択を許可します。
`explicit`は各スキル名を指定して使う設定です。`agents/openai.yaml`の`allow_implicit_invocation`を`false`にします。毎回答を校正するHookは登録しません。

## 上流だけを更新する・取得版を固定する

```bash
bash install_codex_yomiyasu.sh --update --upstream-only
bash install_codex_yomiyasu.sh --update --upstream-only --apply
bash install_codex_yomiyasu.sh --check-update --upstream-ref v1.1.1
bash install_codex_yomiyasu.sh --update --upstream-ref v1.1.1 --apply
```

`--upstream-only`は`--update`と併用し、yomiyasuの上流原本だけを更新します。独自ルールとその版、説明用の`references/explanation.md`、補助2スキルは保持します。`--upstream-ref`は更新または更新確認で、取得対象を安定版Releaseのtagに固定します。独自ルールの版を指定するオプションではありません。

## 解除と検査

```bash
bash install_codex_yomiyasu.sh --uninstall
bash install_codex_yomiyasu.sh --uninstall --apply
bash install_codex_yomiyasu.sh --only paragraph-writing --uninstall --apply
bash install_codex_yomiyasu.sh --only japanese-direct-writing --uninstall --apply
bash install_codex_yomiyasu.sh --self-test
bash install_codex_yomiyasu.sh --extract /tmp/yomiyasu-review
```

標準の解除は管理する日本語Skillが対象です。個別解除では`--only`を付けます。手で編集した管理ファイルや追加ファイルを検出した場合は、選択した全スキルの解除前に停止します。
バックアップは親フォルダの`.yomiyasu-installer-backups/`へ、Skill名付きのZIPで保存します。
配置・解除の切り替えが完了した後、旧一時フォルダの清掃だけに失敗した場合は、操作の完了と残ったパスを警告します。
`--doctor`は通信せず配置・ハッシュ・発動設定・既知の競合を調べます。
競合する別の校正Skillを検出しても、そのSkillを無効化しません。
`--project PATH`で競合診断の対象プロジェクトを指定できます。

自己テストは一時環境と模擬の上流応答を使います。実際の配布元への通信やモデルの文章品質は検証しません。
比較研究のモデル実行は`evals/run_study.py`や`evals/explanation_study.py`の明示実行専用で、インストール時には動きません。補助2スキルは同梱版を導入し、上流yomiyasuの最新安定版取得とは別に管理します。
`--extract`は同梱資材を未使用または空のディレクトリへ展開します。インストールは行いません。`--self-test`と`--extract`は`--only`と併用できません。
yomiyasuの原本をローカルから配置するには`--source-dir PATH --apply`を使います。ローカルGit checkout、管理済み導入のsnapshot、旧v1.0.4固定版のフラット原本を受け付け、形式に応じてファイルを検査します。
`--source-dir`はyomiyasuを含む導入・更新で使います。`--upstream-ref`と併用できません。

## 上流と依存の確認

通常更新では両上流の最新安定版を確認します。`--update --upstream-only --apply`は従来どおりyomiyasu上流だけを更新し、kotonoha・meiseki・独自規範・検査環境を保持します。`--check-update`は未対応のmeiseki変更もエラーとして知らせます。

導入前に実行環境の準備が失敗した場合、Skillは切り替えません。途中まで取得した所有済みキャッシュは再利用できます。自動対応はLinux glibc、macOS、Windowsのx64/ARM64向け配布を定義しています。実機検証の範囲は[検証記録](kotonoha-validation.md)で確認してください。

`--source-dir`を明示した場合は、meisekiも対応確認済みの同梱原本を使い、両上流のネットワーク取得を省略します。実行環境・検査依存が未準備なら、その取得には接続が必要です。既に準備した専用環境は再利用します。
