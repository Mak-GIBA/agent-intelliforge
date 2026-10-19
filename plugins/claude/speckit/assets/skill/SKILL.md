---
name: speckit-workbench
description: "新規開発・既存アプリの後付け仕様整理・機能変更・不具合修正・リファクタリングで、目的から要求、ユーザーストーリー、設計、検証を構造化して残す。SpecKitを利用する。一般的な文章の推敲や簡単な質問には使わない。"
---

# SpecKit Workbench

新規はupstream-new、現状整理はupstream-existing、変更はupstream-change、
不具合はupstream-bug、設計改善はupstream-refactor、点検はupstream-checkを使う。
レビューはupstream-review、明示承認の記録はupstream-approve。
CLI: `@COMMAND@`。まず`doctor`と`overview --project <root>`で対象と状態を確認する。
手順は`flow --mode <mode> --brief`と`@ASSETS@/references/PHASES.md`の該当段階を読む。
依頼範囲と既存AGENTS.mdを守る。構造検査・研究実行・ユーザー承認・アプリ動作を区別する。
