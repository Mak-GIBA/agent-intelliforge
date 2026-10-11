# 説明の深さの比較・回帰検証

品質比較の固定資材と実行記録は [evaluation-explanation](../../../../tools/codex-yomiyasu/evaluation-explanation/) に保存する。旧比較のデータは変更しない。モデル生成、匿名採点、必要時の実ファイル参照、配布回帰試験は別々の証拠である。

- primary-sources.json: 閲覧した一次資料の版・URL・本文のSHA-256。外部Skillは全文同梱しない。
- lifecycle-final.json: 調整後の最終資材を一時環境で導入し、9手順を確認した。
- lifecycle.json: 実上流v1.1.1を読み取り専用の取得元にし、一時的なskills-dirで行った13手順。固定Releaseの更新確認のみ公開APIへ接続した。
- historical-receipts-verified.json: 固定したproposal.2の資材を使う旧比較の再照合。元の記録は上書きしていない。
- source-tests.log / self-test.log / bulk-test.log: 回帰試験の実結果。自己テストの通過は文章品質の証明ではない。

実PCの既存Skillと設定を検証のために更新していない。認証情報、個人設定の本文、内部思考の逐語記録は収録しない。完成稿と採点理由は比較のために保存する。


記録と主張範囲の独立監査は [実ハーネス報告](../../../design-research/yomiyasu-explanation-audit/report.md) に保存した。run 20261011T135446Z-083e3d55 は reviewed、Q1はpass。初回レビューの証拠IDの形式修正は保持し、文章の再生成や再採点をしていない。
