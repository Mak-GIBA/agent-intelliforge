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

## 1.4.0の追加方式と複数画面の比較

[実装と検証結果](../../../docs/codex-ux-stack/verification-1.4.0.md)で、文書管理・設定・LP・申込の
旧新版比較、評価コードの補正、時間切れ、局所的な修正反復、未認証の外部MCPを分けて報告しています。

| 条件の正本 | 実行するコード |
|---|---|
| `visual-design-contract.json` | `visual_benchmark.py`で16成果物の生成と独立採点 |
| `stable-observation-contract.json` | `visual_operations.cjs --stable-frames`で同じ成果物の静止画・操作を再観測 |
| `visual-repair-contract.json` | `visual_repair.py`で同じ回帰を入れた旧新版の修正反復 |
| `local-workflow-contract.json` | `local_workflow.py`でDesktopの2画面試作を局所検証 |
| `local-recovery-contract.json` | `local_recovery.py`で失敗記録を残して読み取り専用レビューを確認 |

```bash
python3 tools/codex-ux-stack/evals/visual_benchmark.py prepare --output /private/comparison
python3 tools/codex-ux-stack/evals/visual_benchmark.py generate --output /private/comparison
node tools/codex-ux-stack/evals/visual_operations.cjs /private/comparison/generation/<trial> <case> --stable-frames
python3 tools/codex-ux-stack/evals/visual_benchmark.py ratings --output /private/comparison --stable-frames
```

操作は各成果物へ実行してから採点します。ブラウザーには `UX_GAN_RUNTIME`、追加のaxe診断には
`UX_AXE_RUNTIME` を指定します。`visual_accessibility.cjs --stable-frames` はaxeの補助診断です。
採点は固定した8対に対して一度ずつ実行し、時間切れは欠測として残します。未完了のモデル実行を
正常終了へ置き換えたり、失敗した版だけを生成し直したりしません。

モデル実行は正規認証と予算を使います。すべての段階で同じ出力先の累積240分を共有し、
別の評価プロセスを同時実行しないでください。生成内の並列処理は同じロックで予約を管理します。
外部MCPを使った設計・費用は未測定です。固定のソースSHAは今回の比較条件であり、現在の正本ではありません。
