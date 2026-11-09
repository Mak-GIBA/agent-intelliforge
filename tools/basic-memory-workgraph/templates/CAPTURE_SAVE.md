# 保存して確認する

自動保存では、フックに示された`workgraph_capture.py`を使う。呼び出せない`bm_write`を待たず、設定で検証済みのBasic Memory CLIへ渡す。エージェントが採用基準・事実・重複の意味を判断し、ヘルパーがモード・範囲・競合・読み戻しを確認する。機械検査だけで意味や満足を保証しない。

1. memory-policy.mdを読み、候補に応じてCORRECTIONS.md、CAPTURE.mdとAUDIT.md、DECISIONS.md、SKILL_REVIEW.mdを参照する。複数種類への重複保存や、過去会話の一括保存をしない。
2. 秘密・不要な個人情報を除いた候補JSONを用意する。`prepare --input <JSONファイル>`は読み取りだけ。本文と同じ概念の短い検索語を使う。検索失敗は該当なしではない。候補が多すぎる場合は検索語を絞る。
3. 返された全matchesの本文を読み、`distinct`・`duplicate`・`update`と理由を判断する。`review`はその候補・検索結果・設定に結び付く。必要なら検索語を変えてprepareし直す。
4. `apply --input <候補> --review <値> --decisions <JSON配列またはファイル> --ticket <今回の値> --token <今回の値> --mode implementation`を実行する。更新は同一primaryProjectの対象だけ。共有済み・学習許可済みノートはこの経路で更新しない。
5. 結果を確認し、最終回答前に`finish --outcome complete|no_candidate|out_of_scope|pending|failed`を一度実行する。ticket/token/modeはapplyと同じ。フックのfinishコマンドへoutcomeを追記する。Plan/read-onlyではapply・finish・armを行わない。

候補の基本形（説明用。実際の根拠と本文へ置き換える）:

```json
{"kind":"validation","query":"回復手順 特定の失敗条件","action":"create","admission":{"transfer":"別案件での具体的な利用","utility":"避けられる失敗","evidence":"実際の確認と範囲","durability":"適用条件・例外・再確認条件","added_value":"既存資料だけでは分からない組合せの発見"},"note":"---\ntitle: 条件に応じた回復手順\ntype: validation\n---\n\n## Observations\n- [trigger] 適用条件。\n- [procedure] 確認した操作と理由。\n- [evidence] 実際に確認した性質。\n- [limits] 例外と未確認の範囲。\n"}
```

`rule/workflow/validation`のadmissionは上記5項目。将来の明示的な好みだけは、`category: future_preference`と`context/instruction/evidence/exceptions`を使える。

`correction`: `context/mismatch/requested/evidence`。`decision`: `context/actor/choice/alternatives/rationale/consequences/revisit/evidence`。判断の8項目は本文のDecision節にも保存する。`case`: `context/reusable_feature/evidence/limits`と、CAPTURE.mdに従うv2本文。未完了でもprogressive基準を満たせば保存できる。

全ノートに検索用`## Observations`を置く。関係を付ける場合だけ`## Relations`に`- learned_from [[実在する参照先]]`等を書く。独立して必要な既存ノートだけに結び付け、リンクのためのノートを作らない。

更新は`action: update`、`target: prepareで確認したpermalink`、`change_evidence: 新しい根拠`と、無関係な既存内容を残した本文を指定する。各matchの判定は`{"id":"project:permalink","decision":"update","reason":"同一対象への新しい根拠"}`の配列。内容・検索結果・設定が変わったらレビューをやり直す。

`saved/updated`は書き込み後の本文・設定・構造を読み戻せた状態。`duplicate`は同じ情報のため書かない判断。CLIがエラーでも保存済みの場合があるため、自動再試行せず読み戻す。読み戻し不能はfailedであり保存成功と報告しない。終了時に参照先の指紋も再確認する。同じノートを複数回更新した場合は最後の検証済み更新の指紋を使い、その後の外部改変は失敗として検出する。部分保存を見落として作り直さない。

`complete`は全候補の保存または重複確認を終えた場合。候補なしは`no_candidate`、候補が基準外なら`out_of_scope`、未処理なら`pending`、処理失敗なら`failed`。未評価を候補なしと扱わない。pending/failedだけStopで一度再確認でき、継続ターンから再びarmしない。トークンは認証境界ではなく、そのターンの実装モード申告を照合するもの。

`status`は保存内容を出さず、結果別件数と診断上限を返す。診断はprivateの列挙値・不透明な参照のみ、最大64件・14日。Planや中断で申告のないターンは保存漏れと断定しない。一時レシートは作業場所の`.workgraph-capture/`に置き、Git対象外とする。最終状態の診断とレシートを長期メモリーへ転記しない。
