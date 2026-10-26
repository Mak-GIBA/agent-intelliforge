# kotonoha 4.0.0の検証記録

2026-10-26に、単一フォルダへの統合と、yomiyasu v2.4.0・meiseki v0.10.0の採用を確認した記録です。架空の素材と完成稿、評定、実行条件、hashだけを保存し、モデルの内部推論や個人の原稿は含めていません。

| 記録 | 内容 |
|---|---|
| [initial/quality.json](initial/quality.json) | 初回18課題。E01の説明の重複により保留 |
| [revised/model/contract.json](revised/model/contract.json) | 課題、要件、規範hash、モデル、制限時間 |
| revised/model/baseline-*.json、candidate-*.json | 基準案・改訂版の完成稿と実行情報 |
| revised/model/review-*.json | 原文、X/Yの稿、評定。K03の回帰指摘も保持 |
| [revised/reader-repair/](revised/reader-repair/) | K03の1回の局所修正と別実行の再評定 |
| [revised/quality.json](revised/quality.json) | 修正後の判定と全証拠ファイルのhash |
| [revised/review.json](revised/review.json) | 9能力の確認、上流変更の採用・除外理由 |
| [revised/verification.json](revised/verification.json) | 採用前の規範・原典・評定への結び付け |
| [revised/metadata-correction.json](revised/metadata-correction.json) | 能力と課題IDの対応表だけを実際の課題に合わせた修正 |
| [native-summary.json](native-summary.json) | 実際のSkill読込2試行の要約 |

比較はE01〜E12とK01〜K06の18課題です。`gpt-6.1-sol`、`xhigh`、1呼出し180秒以内、全体30分以内、失敗時の自動再実行なしで実施しました。6課題ずつ生成し、各組を別実行で評定しています。改訂時の基準案は、モデル設定・入力hashが一致する既存の3記録を再利用しました。新たな基準案の生成回数として数えません。

評定にはSkill名や規範本文を渡さず、原文、依頼、完成稿X/Y、評価対象のラベルを渡しました。同じモデルの別実行による自動評定で、完全な盲検試験や人間の独立評価ではありません。初回E01を受けて規範を修正した後、改訂版のK03も一度修正しています。修正前の稿を削除せず、最終判定に`resolved_regressions`として記録しました。K群も今回の調整で確認済みとなったため、次回の未使用課題とは扱えません。

配布元`assets/kotonoha/UPSTREAMS.json`の`integration.quality_sha256`と`review_sha256`は、ここにある改訂版の同名JSONへ対応します。`quality.json`の`adapter_sha256`は比較対象のファイルへ対応し、採用状態を表す`UPSTREAMS.json`と再生成可能な`resources.json`を除きます。`verification.json`は採用前の候補を対象とするため、採用後の`UPSTREAMS.json`とはhashが異なります。

最終確認で、能力と課題IDの対応表に誤りがあったため、非規範の`capabilities.json`だけを修正しました。モデルに渡した入口・長文資料、検査器、原典、入力・出力は同一です。修正前の品質記録と検証記録も残し、モデルを再実行せず変更範囲を照合して結び付けを更新しました。診断のみの試行は「原稿を書き換えない」ことの確認で、あらゆる局所修正を評価したものではありません。

実Skill試行では、一時プロジェクトにkotonohaだけを配置し、他の利用者Skillを呼出し単位で無効にしました。短いメールと診断のみの依頼は、どちらも入口だけを全文読込して完了しました。要約中のtokenはシステム指示や複数のやり取りを含む値です。規範の文字数差から、課金・処理時間・内部適用回数の改善率は導きません。

再照合はJSONのhash確認とオフラインテストで行えます。モデルの再実行は明示的な費用と時間の判断が必要です。[比較コード](../../../../tools/codex-yomiyasu/evals/v4_compare.py)と[局所修正コード](../../../../tools/codex-yomiyasu/evals/v4_repair.py)を使用しました。
