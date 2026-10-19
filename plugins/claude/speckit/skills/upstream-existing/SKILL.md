---
name: upstream-existing
description: "稼働中アプリのAs-Is、合意済み仕様、To-Beを分けて上流資料を整理する。明示呼び出し専用。"
disable-model-invocation: true
---
# upstream-existing

対象・目的はコマンド後の文章から読む。modeは`existing`に固定する。
共通CLI: `intelliforge kit-run speckit --agent claude --`

1. 対象境界・AGENTS.md・既存文書を確認し、doctorとoverviewで配置・状態を読む。
2. `flow --project <root> --mode existing --brief`を読み、今の段階の
   `../../assets/references/PHASES.md`を使う。CLI未配置・競合は停止して報告する。
3. 未準備ならattachの差分を示し、依頼範囲で適用する。正本と既存の合意を維持する。
   文書編集は依頼範囲内だけ。checkは監査から始め、変更の依頼がなければ書かない。
4. 目的→ニーズ→ストーリー→要件→設計→検証をIDで結び、現状・合意・提案を分ける。
   方式選択はRESEARCH_FIRST.md、要件の見直しはREASSESSMENT.mdを読む。
   不確実なコアロジックだけdesign-researchへ。必要な研究は設計確定前に実行する。
5. レビューはupstream-review、現在の明示承認の記録はupstream-approve。
   沈黙は承認にせず、古いreviewやstaleな下流項目を自動承認しない。
6. checkで点検する。確定を主張する場合だけ`gate --project <root> --write`を実行し、非ゼロは未完了とする。
   更新後は`overview --write`。読み取り依頼では書かず最新のoverviewを表示する。
最後は確認ページ1つと対象ID・確認箇所・承認待ち・次の操作を示す。
上流整理だけではアプリ実装・DB変更・デプロイを開始しない。計画と実行PASSを混同しない。
日本語は利用可能なkotonohaを優先し、未導入ならyomiyasu互換入口を使う。同じ原稿に両方を重ねず、意味・ID・数値・条件を保持する。

## 配布環境の呼び出し
このPluginの管理ソースは `tools/speckit-upstream/kit.json`。導入先は `intelliforge locate --only speckit --agent claude` で確認する。Pythonヘルパーは `intelliforge kit-run speckit --agent claude --tool <ファイル名> -- <引数>`、研究・UXハーネスは `intelliforge kit-run speckit --agent claude -- <引数>` から実行する。Windowsではこの入口を使い、Bashやpython3という実行名を前提にしない。
Claude Code対応は試験対応。実機未検証の機能を検証済みと扱わない。
