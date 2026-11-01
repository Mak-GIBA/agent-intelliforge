# Repository Director：導入・更新・移行

[English](../en/repository-director/installation.md) | **日本語**

[概要](README.md) · [使い方](usage.md) · [検証範囲](validation.md)

## 導入

Linux / WSL2ではBashとPython 3.11以上が必要です。単体ファイルにSkill・ヘルパー・テストを内蔵し、通信せずに導入できます。
Codex本体は導入しません。gh・glabと認証は対応ホストを操作するときだけ必要です。

```bash
bash install_repository_director.sh --dry-run
bash install_repository_director.sh --apply
bash install_repository_director.sh --doctor
```

引数なしも予定表示です。予定表示は配置先の所有権・編集状態を検査するため、競合時は失敗します。
診断は導入状態とgh/glabの有無を確認します。認証・通信・モデル生成の確認は行いません。

一括導入と共通CLIでも同じキットを選べます。

```bash
bash install_all.sh --only repository-director --apply
intelliforge inspect --only repository-director
intelliforge install --only repository-director --apply
intelliforge install --only repository-director --agent claude --apply
```

Windowsは共通CLIのPlugin経路を使います。Claude対応は試験対応です。
[共通CLI・ホスト別の導入](../cross-platform.md)を参照してください。

## 配置と変更範囲

標準配置は次のとおりです。

| 場所 | 内容 |
| --- | --- |
| `~/.agents/skills/repository-director/` | Skillとヘルパー |
| `~/.local/bin/repository-director` | 文書ヘルパーの起動入口 |
| `~/.local/share/repository-director/install.json` | 所有権・ハッシュの管理記録 |

Codex共通AGENTSには、所有権を記録した短い案内だけを追加します。
非空のAGENTS.override.mdがある場合はそちらを使います。既存の他のルールは保持します。

`RD_SKILLS_DIR`、`RD_BIN_DIR`、`RD_DATA_HOME`、`CODEX_HOME`で絶対パスを指定できます。
既定のデータ先はXDG_DATA_HOMEにも従います。更新・診断・解除も同じ設定で実行してください。
対象プロジェクトの文書・ソース・依存定義・Git remote・hooksはインストールでは変更しません。
Plugin経路は既存のホスト管理コマンドで登録し、同じSkillと共通Python資材を配置します。

## 旧版から移行する

旧 `speckit` / `github-pm` は廃止しました。旧スクリプト名・Skill名・IDは互換エイリアスとして残していません。
まず予定と対象を確認し、その後に適用します。

```bash
bash install_repository_director.sh --migrate-legacy
bash install_repository_director.sh --migrate-legacy --apply

# 共通CLI・Pluginの旧版も、管理記録を確認して切り替える
intelliforge install --only repository-director --agent claude --migrate-legacy
intelliforge install --only repository-director --agent claude --migrate-legacy --apply
```

管理manifest・所有権・各ファイルのハッシュを照合し、未編集の旧Skill・起動ファイル・共通案内を退避して切り替えます。
Plugin登録はホストの管理コマンドで解除し、解除後の一覧も確認します。対応する旧runtimeは履歴として残します。
バックアップはSkillの探索先の外へ置きます。失敗時はローカル資材を復元し、ホスト復元が失敗した場合は対象を報告します。

手動編集、未管理の配置、ユーザー追加ファイル、異なるホームの管理記録は上書きせず停止します。
該当資材を安全な場所へエクスポートし、残すルールを確認してから手動で整理してください。
旧Upstreamのカスタム配置は `SWB_SKILL_DIR` / `SWB_BIN_DIR` / XDG設定も同じにします。
プロジェクトの文書、.specify、研究報告、承認履歴、specify本体と専用venvは削除・変換しません。

共通CLIの予定表示は配布経路を示すもので、ホストの認証や旧配置の完全な移行可否まで証明しません。

## 更新・解除・検査

```bash
bash install_repository_director.sh --update --dry-run
bash install_repository_director.sh --update --apply
bash install_repository_director.sh --uninstall
bash install_repository_director.sh --uninstall --apply
bash install_repository_director.sh --self-test
bash install_repository_director.sh --extract /absolute/path/empty-directory
```

未編集の管理ファイルだけ更新・解除できます。編集済みのSkillや共通案内は保持して停止します。
解除してもプロジェクト文書とバックアップは残ります。`--extract`は空の保存先へ書き込む操作です。
自己テストは一時環境の機能検査であり、文章品質や実GitHub/GitLabへの書き込みを検証するものではありません。

無効化されている旧Pluginは状態を推測して有効化せず、ホスト管理画面で意図した状態を確認してから移行します。
