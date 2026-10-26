# kotonoha：明晰で自然な日本語を書く

[English](../en/codex-yomiyasu/README.md) · [導入](installation.md) · [使い方](usage.md) · [検証](validation.md)

4.0.0は、明晰化・段落構成・説明の深さ・留保の整理・自然さを、一つのSkillへまとめます。通常は `$kotonoha` と依頼内容を指定します。段落だけの修正や診断も同じ入口で範囲を指定できます。

規則・検査器・原典・ライセンスはkotonohaフォルダに揃い、他の日本語Skillを探しません。短い依頼は入口だけで進め、長文やファイル検査の詳細は必要なときだけ読みます。上流原本の全文を毎回読み込まず、同じ原稿を工程ごとに再生成しません。

上流はyomiyasuとmeisekiの最新安定版を検出し、差分の確認と能力比較を経て採用します。取得した最新版と、kotonohaへ統合・検証した採用版は別に表示します。実際の採用状態はSkill内のUPSTREAMS.json、能力と評価ケースの対応はcapabilities.jsonで確認できます。

3.0.0までのyomiyasu・paragraph-writing・japanese-direct-writing入口は、所有元を確認できる未編集版だけ更新時にバックアップして退役させます。編集・追加ファイルや管理外の同名Skillは自動で消しません。コマンド名やkit選択名のyomiyasuは互換名として残ります。

これは両上流を統合した独自Skillです。原版の自動フック・外部判定API・理解度クイズ・PDF機能は自動導入しません。能力比較の結果と制約は[検証結果](validation.md)を参照してください。
