# UX画面品質の比較データ

[2026-10-31の報告](../../../docs/design-research/uiux-skill-quality/report.md)は、
文書管理・設定フォーム・公開ページを同条件で生成し、画像の独立評価と実操作を分けた比較です。
全文のスキル置換は採用条件を満たさず、既存入口を維持しました。

```bash
python3 tools/codex-ux-stack/evals/verify_quality.py \
  docs/design-research/uiux-skill-quality/evidence/benchmark
```

このコマンドはハッシュ、操作証拠、匿名評価の集計を確認します。モデルを呼ばず、ファイルを変更しません。
検証素材・指示・条件はevaluation-contract.json、スキルの実験用原稿はsnapshots、
生成ページはpages、画面はscreens、採点はratingsに保存しています。
新しいモデル比較を行う場合は、評価条件と上限を先に固定し、既存の結果を上書きしないでください。
