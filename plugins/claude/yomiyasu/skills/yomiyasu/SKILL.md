---
name: yomiyasu
description: 既存の /yomiyasu:yomiyasu 呼び出し用の互換入口。日本語執筆・推敲の通常の入口はkotonoha。
disable-model-invocation: true
---

# yomiyasu — kotonoha互換入口

`references/workflow.md` を読んで同じ共通フローを使う。meisekiで明晰化し、yomiyasuで自然さを仕上げる。kotonohaを既に適用している場合は同じ工程を繰り返さない。上流原本は `upstream/` に変更せず保持する。

検査は `intelliforge kit-run yomiyasu --agent claude --tool writing_lint.py -- <原稿> [--before <原稿>]`。Python・Node.jsは導入時に準備した専用環境を使う。
Claude Code対応は試験対応。実機未検証の機能を検証済みと扱わない。
