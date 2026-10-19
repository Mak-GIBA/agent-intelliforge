---
name: design-research
description: Research and improve the core logic contributing to a project's main goal by comparing methods, algorithms and agent designs with multiple primary sources and bounded experiments. Run the installed GAN harness for evidence-based checks and requested improvements, including backend behavior. Use for コアロジックの改善, 技術選定, 研究・比較・評価, バックエンドの検証・改善, or explicit $design-research. UI visual review uses the separate UX workflow.
---

# Design Research

`$design-research`を入口に、依頼と既存記録から必要な工程を選ぶ。
`DR_GAN_CHILD=1`では渡された役割と参照だけを扱い、別ハーネスやMemory書込を開始しない。

1. 対象の境界・AGENTS.md・正本・現在の依頼範囲を確認する。
   `scripts/workflow_overview.py --project <root>`で状態を読む。確認だけなら書かず実行しない。
2. 単一方式はresearch、完了研究の条件変更はreassess、中断した同条件はresume。
   全体の要求・設計はUpstreamへ戻し、不確実なコアロジックを研究テーマとして分解する。
   複数候補・複数runは明示選択し、最新日時で決めない。計画だけの依頼は計画で止める。
3. 実行時に[工程と停止境界](references/workflow-guide.md)と
   [保存単位](references/execution-units.md)を読む。
   `scripts/codex_interface.py prepare`で入力とハッシュを確認し、同じ選択でrunする。
   実際の`gan-harness.sh`のrun ID・状態・結果を報告する。文章のレビューで実行を代替しない。
4. 効果・精度・性能を測るときは[評価契約](references/effectiveness-evaluation.md)を読み、
   実験前に主要指標・基準案・同一入力・採点・採用条件を固定する。
   文献・設計調査は未測定の効果を明記し、条件付きの結論にする。改善なしも結果として残す。
5. 約5候補を目安に一次資料、必要な数式・図解・反証条件を比較する。少数なら理由を記録する。
   提案手法の詳細設計が必要なら[提案手法](references/proposed-method-report.md)、
   条件変更なら[再検討](references/reassessment.md)、複数テーマなら[研究計画](references/workstreams.md)を読む。
   詳細な実行・証拠・役割契約は[実行契約](references/advanced-contracts.md)の該当節を使う。
6. 最小設計→実行資材→実測・採点→原典確認→結論・説明→独立レビューを保存する。
   必須単位が残る間は全体を完了としない。入力は通常16 KiB以内、超過は全文・ハッシュ付き参照へ。
   同一projectのロック・時間上限・sandbox・ネット利用・実装変更の境界を守る。

新規テーマの報告書は`docs/design-research/<topic>/report.md`、図は同じ場所の`figures/`。
完全な実行記録は`.artifacts/design-research/<topic>/`に保存しGitから除外する。
既存テーマは元の保存先を維持する。採用時は[証拠の固定](references/published-evidence.md)を読み、設計に採用するrunだけ
`gan-harness.sh export-evidence --project <root> --topic <topic> --run-id <ID>`で確認し、
`--apply`で`docs/design-research/<topic>/evidence/<ID>/`へ必要な証拠を固定する。
`verify-evidence --package <path>`はclone後も検証できる。必要なログを省かない。
Upstreamは出力されたv3 bindingを要件・設計IDに結び、統合結果と未確認事項を別に記録する。
文書更新後は`overview --write`で確認ページを更新し、最後はそのリンクと対象ID・次の操作を示す。
記録の整合性は科学的な有効性やユーザー承認の証明ではない。未実行・失敗・不明点を保持する。
日本語は利用可能なkotonohaを優先し、未導入ならyomiyasu互換入口を使う。同じ原稿に両方を重ねず、なければ追加導入せず続行する。公開済みの台帳・ログ・保存版は保持する。
