# kotonoha — 明晰で自然な日本語を書く

[docs一覧](../README.md) · [導入手順](installation.md) · [使い方](usage.md)

日本語の技術文書、仕様書、Issue・PR、報告文などを、意味を保ったまま読みやすく整えるためのSkillです。
数値、専門用語、条件、断定の強さを保ち、読みにくい構文や重複を整理します。重要な主張が抽象語で止まる箇所では、資料にある仕組みや実際の変化まで説明します。
kotonoha 3.0.0は、meisekiの構文明晰化、段落構成、説明の具体化、留保の整理、yomiyasuの自然さを一つの執筆工程に統合した独自Skillです。上流原本を順番に全文読み込みする方式ではなく、必要な規範を参照して同じ下書きを仕上げます。両上流の原本・版・ライセンスは分離して保持します。

通常は`$kotonoha`で依頼します。既存の`$yomiyasu`は互換入口、paragraph-writingとjapanese-direct-writingは部分作業の入口として利用できます。短いメールや十分な原稿へ不要な説明を追加しません。

`--apply`は必要なPython、Node.js、textlint、markdownlintもユーザー専用領域へ用意します。既存の適合環境を再利用し、システムの既定環境やシェル設定を変更しません。インストーラーの正本と依存バージョンは`tools/codex-yomiyasu/`で確認・編集できます。

[install_kotonoha.sh](../../install_kotonoha.sh)と[install_kotonoha.ps1](../../install_kotonoha.ps1)は単体で使えます。
引数なしでは予定を表示し、`--apply`で導入します。旧名の[install_codex_yomiyasu.sh](../../install_codex_yomiyasu.sh)も引き続き使えます。

## 導入するもの

| 資材 | 提供元 | 役割 |
|---|---|---|
| meisekiの原本・構文規範・検査設定 | [bamboo-nova/meiseki](https://github.com/bamboo-nova/meiseki) | 否定・係り受け・名詞化・冗長表現を明晰にする基礎 |
| yomiyasuの原本・lint・diff | [nanaism/yomiyasu](https://github.com/nanaism/yomiyasu) | 日本語の推敲手順と静的検査 |
| kotonohaの入口と共通フロー | このリポジトリ | 読者、段落、表現、留保を一続きで点検し、意味と事実を保持する |
| paragraph-writing | このリポジトリ。Gistに由来する旧版から役割を限定 | 段落構成の単独依頼とkotonohaの構成工程で使う |
| japanese-direct-writing | 提供されたZIPに由来する旧版から役割を限定 | 留保の単独依頼とkotonohaの点検工程で使う |
| `scripts/check.py` | このリポジトリ | 読者に不要な制作説明、段落の冒頭、数値・コード等の変化を調べ、原本の検査も実行する |

meisekiの原本は`meiseki-upstream/SKILL.upstream.md`と設定・辞書・MITライセンスを保存します。yomiyasuの上流原本は`upstream/SKILL.upstream.md`と参照資料・検査スクリプト・ライセンスを含めて保存します。補助スキルの現在の本文はこのリポジトリで管理し、由来と変更の扱いを`UPSTREAM.json`・`SOURCE.json`に記録します。1.3.0のZIP原本そのものを配置する方式から変わっています。
補助スキルは同梱版から導入・更新し、GistやZIPの元の保存先へはアクセスしません。
ECC、Basic Memory、Office Workbench、GitHub Project Directorは必須の依存ではありません。
既存のHook、MCP、AGENTS、他のSkillの設定は変更しません。

## 導入から利用へ

1. [導入手順](installation.md)で配置先と更新方法を確認します。
2. [使い方](usage.md)で対象の文章と保持する条件を指定します。

kotonohaは上流の規範を用途別に統合した独自Skillです。文章への効果、指示量の比較、成功例・失敗例、未検証範囲は[kotonohaの検証](kotonoha-validation.md)に記載しています。限定した素材の自動評価であり、一般的な品質優位性は実証していません。インストーラーの自己テストと文章品質の評価は別です。

旧版の評価は[検証履歴](validation.md)、説明の深さに関する以前の設計は[説明の設計](explanation-design.md)に残しています。
