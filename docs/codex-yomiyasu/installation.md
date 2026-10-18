# kotonohaのインストール・更新・解除

[English](../en/codex-yomiyasu/installation.md) | **日本語**

[概要](README.md) · [使い方](usage.md) · [検証結果](kotonoha-validation.md)

## 前提と導入

kotonohaは、必要なPython・Node.jsと文章検査ツールをユーザー専用領域へ用意します。既存の適合環境は再利用し、sudo、OSのパッケージ管理、永続的なPATH変更は行いません。Codexなど、Skillを使うホストは別途用意してください。

Linux / WSL2ではBash、curlまたはwget、tar、ハッシュ検査コマンドが必要です。WindowsではPowerShellを使います。

```bash
bash install_kotonoha.sh                 # 導入予定を表示
bash install_kotonoha.sh --apply         # Skillと検査環境を導入
bash install_kotonoha.sh --doctor        # 配置・ハッシュ・検査環境を診断
```

```powershell
.\install_kotonoha.ps1                  # 導入予定を表示
.\install_kotonoha.ps1 --apply
.\install_kotonoha.ps1 --doctor
```

一括導入は`bash install_all.sh --only kotonoha --apply`で実行します。共通CLIでは`intelliforge install --only kotonoha --apply`を使えます。Windowsの一括入口も、日本語キットだけならPythonやuvがなくても単体インストーラーへ委譲します。

### 名前と配置先

通常の執筆・推敲は`$kotonoha`から始めます。既存の`$yomiyasu`は同じ工程への互換入口です。段落だけの調整には`$paragraph-writing`、過剰な留保だけの調整には`$japanese-direct-writing`を使えます。

標準の配置先は`~/.agents/skills/`です。`--skills-dir PATH`で変更した場合は、診断・更新・解除でも同じパスを指定してください。互換性のため、内部のキットID・Plugin名と管理ディレクトリ名は`yomiyasu`を維持しています。従来の`install_codex_yomiyasu.sh`も新しい単体インストーラーと同じ正本から生成します。

同名の未管理Skillや別の場所にある同名Skillは上書き・二重登録しません。選択した全Skillを検査・準備してから配置し、切り替えに失敗した場合は切り替え済みのSkillも元へ戻します。

### 実行環境と取得する原本

Pythonが必要な場合は固定版uvを経由して3.11系を用意します。Node.jsは検証した24系LTSの公式配布をハッシュ照合して取得し、文章検査の依存パッケージはlockfileで固定します。

専用環境はSkillディレクトリの親の`.kotonoha-runtime`に保存します。Python bootstrapの保存先は、ユーザーデータ領域の`agent-intelliforge/kotonoha-bootstrap`です。Plugin方式ではキット状態ディレクトリの`dependencies/kotonoha`を使います。解除後も環境とバックアップは残ります。

初回導入ではmeisekiとyomiyasuの最新安定版Releaseを確認し、取得するcommitを確定します。yomiyasuはGit blob IDとサイズ、meisekiは対応確認済み資材のSHA-256を検査します。meisekiに未対応の規範変更がある場合は停止し、既存Skillを維持します。同じ構成で再実行しても、上流を自動更新しません。

paragraph-writingとjapanese-direct-writingは同梱版から導入・更新します。元のGistやZIPへ接続する必要はありません。

Python自体がない環境では、プレビューは通信せずbootstrapの概要を表示します。引数ごとの完全な予定表示には、既存のPythonを`PYTHON_BIN`で指定してください。`--apply`のない診断・ヘルプではPythonを自動取得しません。

## 対象を選ぶ

単体インストーラーの`--only`は、個々のSkillを選ぶ指定です。`all`（既定）、`yomiyasu`、`kotonoha`、`paragraph-writing`、`japanese-direct-writing`を使えます。一括導入・共通CLIの`--only kotonoha`と`--only yomiyasu`は、どちらも日本語キット全体を選びます。

```bash
bash install_kotonoha.sh --only paragraph-writing --apply
bash install_kotonoha.sh --only japanese-direct-writing --apply
bash install_kotonoha.sh --only yomiyasu --doctor
```

既存の適合Pythonがあれば、paragraph-writingまたはjapanese-direct-writing単独の導入に上流取得は不要です。

## 更新と発動モード

新しいインストーラーを用意し、更新内容を確認してから適用します。

```bash
bash install_kotonoha.sh --check-update
bash install_kotonoha.sh --update
bash install_kotonoha.sh --update --apply
bash install_kotonoha.sh --doctor
```

`--check-update`は両上流の最新安定版と同梱の独自規範・補助Skillを確認し、未対応のmeiseki変更もエラーとして知らせます。`--update`は`--apply`がなければ通信せず予定を表示し、適用時に取得版を確定・検査して配置します。補助Skill単独の更新確認・更新は通信せず同梱版を使います。

上流版を保ち、同梱の入口・運用設定・補助Skillだけを更新する場合は`--force --apply`を使います。ただし、上流の必須ファイルが欠ける旧導入は、まず`--update --apply`で整えてください。2.0系列以降では`upstream/UNICODE-LICENSE.txt`も必須です。

既存の管理ファイルに編集・欠落があると、`--force`でも停止します。更新前の資材は、Skill名付きZIPとして`.yomiyasu-installer-backups/`へ保存します。配置・解除の完了後に旧一時フォルダーの清掃だけが失敗した場合は、完了した操作と残ったパスを警告します。

既存Skillの発動モードは保持します。新規Skillは管理済みyomiyasuのモードを引き継ぎ、全て新規なら`auto`です。モードを変更する場合は明示します。

```bash
bash install_kotonoha.sh --mode explicit --force --apply
bash install_kotonoha.sh --mode auto --force --apply
```

`auto`は依頼に合うSkillの自動選択を許可する設定です。yomiyasu互換入口は明示呼び出し用として扱います。`explicit`では各Skill名を指定して使い、`agents/openai.yaml`の`allow_implicit_invocation`を`false`にします。毎回答を校正するHookは登録しません。

## 上流だけを更新する・取得版を固定する

```bash
bash install_kotonoha.sh --update --upstream-only
bash install_kotonoha.sh --update --upstream-only --apply
bash install_kotonoha.sh --check-update --upstream-ref v1.1.1
bash install_kotonoha.sh --update --upstream-ref v1.1.1 --apply
```

`--upstream-only`は`--update`と併用し、yomiyasuの上流原本だけを更新します。kotonoha、meiseki、独自規範とその版、`references/explanation.md`、補助Skill、検査環境は保持します。`--upstream-ref`は安定版Releaseのtagを指定するオプションで、独自規範の版を指定するものではありません。

## 解除と検査

```bash
bash install_kotonoha.sh --uninstall
bash install_kotonoha.sh --uninstall --apply
bash install_kotonoha.sh --only paragraph-writing --uninstall --apply
bash install_kotonoha.sh --only japanese-direct-writing --uninstall --apply
bash install_kotonoha.sh --self-test
bash install_kotonoha.sh --extract /tmp/yomiyasu-review
```

標準の解除は管理する日本語Skill全体が対象です。個別解除には`--only`を使います。手動編集や追加ファイルがあれば、選択した全Skillの解除前に停止します。

`--doctor`は通信せず、配置・ハッシュ・発動設定・既知の競合と検査環境を調べます。競合する校正Skillを検出しても無効化しません。`--project PATH`で競合診断の対象プロジェクトを指定できます。

自己テストは一時環境と模擬の上流応答を使い、導入・更新・解除・検査の挙動を確認します。実際の配布元への通信やモデルの文章品質を検証するものではありません。文章比較は`evals/run_study.py`や`evals/explanation_study.py`などを明示実行し、インストール時には動かしません。

`--extract`は未使用または空のディレクトリへ同梱資材を展開し、インストールは行いません。`--self-test`と`--extract`は`--only`と併用できません。

## 上流と依存の確認

`--source-dir PATH --apply`では、ローカル原本からyomiyasuを配置できます。受け付けるのはGit checkout、管理済み導入のsnapshot、旧v1.0.4固定版のフラット原本です。形式に応じて検査し、meisekiには対応確認済みの同梱原本を使います。両上流のネットワーク取得は省略しますが、未準備の実行環境や検査依存の取得には接続が必要です。`--source-dir`はyomiyasuを含む導入・更新で使い、`--upstream-ref`とは併用できません。

実行環境の準備に失敗した場合はSkillを切り替えません。途中まで取得した所有済みキャッシュと、準備済みの専用環境は再利用できます。

自動準備用の配布はLinux glibc、macOS、Windowsのx64 / ARM64向けに定義しています。配布の定義と実機検証は別であり、確認済みのOS・操作は[検証記録](kotonoha-validation.md)を参照してください。
