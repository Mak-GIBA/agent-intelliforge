# kotonohaの使い方

[概要](README.md) · [導入](installation.md) · [検証](validation.md)

## 目的と範囲を伝える

```text
$kotonoha この報告書を、初めて読む技術者にも仕組みが分かるように推敲して。数値・条件・確信度は保って。
$kotonoha このメールを必要な箇所だけ整えて、本文だけ返して。
$kotonoha この文書の段落構成だけ点検して。今は書き換えず、問題を教えて。
$kotonoha 不要な予防線を減らして。未測定の結果は未測定のままにして。
```

文書全体の作成・推敲、段落だけの整理、留保だけの整理、診断を同じ入口で扱います。専門用語・引用・コード・数値・否定・条件・主体・因果・確信度を保ち、資料にない事実や担当者を足しません。詳しさや短さ、検査スコアの改善だけを目的にしません。

## 読み込むもの

SKILL.mdに旧版の工程順と参照条件があります。基本の推敲では、読者境界→明晰化→自然さ→読者レビューの資料を一度ずつ読み、同じ下書きへ適用します。複数段落を設計・再構成するときは段落構成、重要な主張の理由や処理を追えないときは説明の深さ、留保を扱うときは留保整理の詳細を読みます。ファイル推敲は編集前後に検査します。出典と保守の資料は通常の執筆では不要です。原典の全量読込や他Skillの呼び出しはしません。

## ファイルの検査

原稿のコピーを納品先の外へ残し、前後の本文と意味・構造を照合します。以下のpythonには、導入時に用意した専用Pythonを使えます。

```bash
python ~/.agents/skills/kotonoha/scripts/writing_lint.py before.md
python ~/.agents/skills/kotonoha/scripts/writing_lint.py after.md --before before.md
python ~/.agents/skills/kotonoha/scripts/check.py outline after.md
python ~/.agents/skills/kotonoha/scripts/check.py compare before.md after.md --protect=--apply
```

最新版の統合検査はcheck.py source-check run|verifyから使います。--state-dirで作業用記録先を明示します。詳細は同梱のfile-review.mdにあります。検査器は本文を変更せず、文章中の指摘と実行不能を区別します。数値やハッシュの一致だけで意味保持や人の承認を証明しません。

共通CLIでは `intelliforge kit-run kotonoha --tool writing_lint.py -- after.md --before before.md` を使えます。旧キットIDの互換エイリアスは廃止しました。

## 上流の更新

普段の執筆では通信・更新しません。更新を調べるにはインストーラーの--check-update、原典の新規統合にはリポジトリのupdate_upstreams.pyを使います。[導入と更新](installation.md)を参照してください。

meisekiの詳細は明晰化資料から否定・条件／修飾／名詞化などの該当節へ、yomiyasuの詳細は仕上げ資料から表現・文書種別の該当資料へ辿ります。原版Skill本文も同梱していますが、全量読込や別Skillの起動は通常工程に含めません。原版の外部送信・採点・提出書式はkotonohaの工程へ持ち込みません。
