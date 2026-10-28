# kotonoha 4.1.1 共有パッケージ

kotonohaは日本語の文書・技術解説・記事・メールを執筆、推敲するSkillです。明晰化・段落構成・説明の深さ・留保の整理・自然さの資料と、検査器・原典・ライセンスを同梱しています。

## 配置方法

ZIPを展開し、`skills/kotonoha`フォルダを受け取り側PCのSkillフォルダへコピーします。

- Linux・macOS: `~/.agents/skills/kotonoha/`
- Windows: `%USERPROFILE%\.agents\skills\kotonoha\`

既存の同名フォルダは、Skill検索対象の外（例: `~/.agents/skill-backups/`）へバックアップしてから入れ替えてください。以前の共有ZIPから配置した`yomiyasu`・`paragraph-writing`・`japanese-direct-writing`も、バックアップを残して検索対象の外へ退避できます。他の用途で別途導入した同名Skillは、その管理元と利用状況を確認して扱ってください。

コピー後、Codexの新しいセッションで指定します。

```text
$kotonoha この文章を、意味と情報量を保って推敲して。
```

基本の推敲では読者境界・明晰化・自然さ・読者レビューの資料を読み、段落・説明・留保・ファイル検査は作業内容に応じて追加します。一つの下書きに各工程を適用し、必要な具体例と例外は同じフォルダ内で参照します。元PCのインストール所有情報や自動更新設定は含みません。

## 文章検査の準備（任意）

文章の規範と原典参照はコピーだけで利用できます。textlint・markdownlintを使う場合は、受け取り側でPython 3.11以上を用意し、専用環境を準備します。準備時は通信し、必要に応じてNode.jsとnpm依存を取得します。

Linux・macOS:

```bash
python3 "$HOME/.agents/skills/kotonoha/scripts/writing_runtime.py" "$HOME/.agents/.kotonoha-runtime" --prepare
```

Windows（PowerShell）:

```powershell
py -3 "$env:USERPROFILE\.agents\skills\kotonoha\scripts\writing_runtime.py" "$env:USERPROFILE\.agents\.kotonoha-runtime" --prepare
```

Pythonの実行名が異なる場合は置き換えます。検査用環境はZIPに含めず、受け取り側で作成します。文章作成中に環境や上流を自動更新しません。

## 原典と検証台帳

採用上流はyomiyasu v2.4.0、meiseki v0.10.0です。執筆・推敲の規則を統合した独自Skillです。詳細は`skills/kotonoha/references/sources.md`、採用commitは`UPSTREAMS.json`にあります。

`resources.json`は原典の整合性検査に必要なので残してください。台帳は配布元の署名やインストール所有権を証明するものではありません。

`CONTENTS.json`に版・配布元commit・コピー元のhash、`SHA256SUMS.txt`にパッケージ内ファイルのhashを記録しています。個人設定・認証情報・キャッシュ・元PC専用の実行環境は含めていません。検査の指摘数やファイル一致だけでは、文章内容の正しさや意味保持は保証されません。
