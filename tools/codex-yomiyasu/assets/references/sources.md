# 参照先と利用範囲

確認日：2026-10-11。最新版の固定的な保証ではなく、今回の設計時点の記録。

- 既存インストーラー：Mak-GIBA/basic-memory-workgraph、commit f0efd23a53c1c1cd028775aa415cc3f34ca5661a。CLI、管理manifestのowner/schema、バックアップ・更新・編集保護の設計を継承。
  https://github.com/Mak-GIBA/basic-memory-workgraph
- 上流：nanaism/yomiyasu v1.1.1、commit 373356eb874af5184962c88e925ea7eb58450318。実際の推敲規則とlint/diffは上流原本を利用し、インストール時に取得する。MITとUNICODE-LICENSE.txtを保持する。
  https://github.com/nanaism/yomiyasu/releases/tag/v1.1.1
- coji/natural-japanese：書く前の構成設計、検出と判断の分離を設計比較に使用。コード・スキル本文を取り込んだり、追加インストールしたりしない。
  https://github.com/coji/natural-japanese
- tqkqt0/humanizer-jp：日本語の定型表現、応答残り、書き手の文体への適合を比較。コード・スキル本文は同梱しない。
  https://github.com/tqkqt0/humanizer-jp
- bamboo-nova/meiseki：意味を保持した明晰化、読みやすさと個性付与の区別を比較。コード・スキル本文は同梱しない。
  https://github.com/bamboo-nova/meiseki
- Purdue OWL, On Paragraphs：一段落一論点、統一性、つながり、主題文という一般的な段落原則を参照。記事本文は転載しない。
  https://owl.purdue.edu/owl/general_writing/academic_writing/paragraphs_and_paragraphing/index.html
- Harvard College Writing Center, Anatomy of a Body Paragraph：主題、根拠、その解釈の関係と、不必要な末尾再要約を避ける考え方を参照。記事本文は転載しない。
  https://writingcenter.fas.harvard.edu/anatomy-body-paragraph
- OpenAI, Build skills：SKILL.md、参照資料、ユーザー配置、明示・暗黙選択の仕様を確認。
  https://developers.openai.com/codex/skills/

独自の日本語本文・例文・検査ロジックは、この提案のために作成した。上流の本文は上流フォルダに分離し、著作権表示とライセンスを変更しない。

## 2.0.0-proposal.2で追加確認した原典

- blader/humanizer：定型的な対比、意義の水増し、会話・制作説明の残存、提出前レビューを比較した。架空の感想や体験、編集報告を本文に足す出力形式は採用しない。
  https://github.com/blader/humanizer
- iKora128/stop-ai-slop-jp：日本語の構造的な定型と主体・具体性の対比例を比較した。立場や感情、語尾のばらつきを強制する規則は採用しない。
  https://github.com/iKora128/stop-ai-slop-jp
- hardikpandya/stop-slop：簡潔な構造点検を比較した。副詞・受動態の全面禁止は採用しない。
  https://github.com/hardikpandya/stop-slop
- nakashimatakaya/deslop-ja：検出と判断の分離、ジャンルによる誤検知対策を比較した。一人称や体験を付与する規則、固定点数に達するまでの反復改稿は採用しない。
  https://github.com/nakashimatakaya/deslop-ja
- OpenAI, Evaluating Skills：明示・暗黙起動と負例を実機で試し、実行記録と完成稿を分けて確認する手順を参照した。
  https://developers.openai.com/blog/eval-skills

実スキルの原典5件の固定commitとSHA-256、採用・除外範囲、現行版＋改善3案の実測はリポジトリの比較記録に保存した。原典の本文・検査器をこの配布物に追加したり、別の文体スキルを自動インストールしたりしない。原典の自己評価やコーパスの主張を今回の改善効果の証拠として扱わない。


## 説明の深さ（独自版2.0.0-proposal.3）

説明の役割、読者の未解決の疑問、資料に基づく具体化はこのリポジトリで記述した独自規範。次の一次資料の確認可能なSKILL本文を比較し、段落・意味保持の重複、固定リズムや自己採点反復を持ち込まずに整理した。外部Skillは新たに導入していない。

- [japanese-tech-writing（固定版）](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d/8f2d57610a73efc97d743c9b0b0ecb1002e09fa4)
- [natural-japanese（固定commit）](https://github.com/coji/natural-japanese/blob/9a78a42964096da509b8f3e011f0085a5f080151/skills/natural-japanese/SKILL.md)
- [cognitive-rhythm-writing（固定版）](https://gist.github.com/k16shikano/eb2929f13ed19c97188393d297be8432/a3b1e26beced71d582e13314fb6f5b179b023c76)
- [Google Technical Writing: Audience](https://developers.google.com/tech-writing/one/audience)
