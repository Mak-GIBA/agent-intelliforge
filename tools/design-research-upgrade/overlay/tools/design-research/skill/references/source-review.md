# 原典の精読とOSS再利用

新規のreport契約では、候補ごとの原典確認担当がcandidate.source_reviewを保存し、最終レビュー担当が原典と照合する。
推奨候補は必ずpromising=trueにする。有望候補を減らすために未確認を不適格へ読み替えない。

```json
{
  "promising": true,
  "reason": "この候補を詳しく調べる理由",
  "paper_reads": [{
    "source_id": "S1", "status": "complete",
    "sections": [{"section": "本文の実際の節名", "locator": "実際のページ/節", "summary": "確認した内容と判断への関係"}],
    "missing": [], "supplementary": "判断に関係する補遺の確認結果。不要ならその理由"
  }],
  "reuse": {"strategy": "not_applicable", "reason": "既存OSSの採用が対象でない理由"}
}
```

有望な論文は本文全体を読み、必要な補遺、表、式、図も確認する。sectionsには実際の主要節をすべて記録する。
短い理論論文へ架空の実験節を足さない。completeにはread_level=full_textと親のアクセス記録・ハッシュが必要。
URLから取得した本文・関連節は、親が応答本文をローカルへ保存し、original_pathとoriginal_sha256で固定する。
原文の取得・保存ができなければcompleteにしない。取得先が目次や概要なら、本文を得たことにはならない。
取得だけでは読了・解釈の正しさを証明できない。独立レビューで記録と原典の対応を確認する。
部分閲覧はpartial、取得不能はunavailableとし、missingに未確認箇所を書く。full_textを自動付与しない。
既存SOURCEのlocatorやread_levelは書き換えず、別の原典・読取範囲には新しいsource IDを登録する。
未確認の資料を根拠にreported/inferredの主張を作らず、unknown/hypothesisとする。
全文未確認の候補はprovisional/deferredで採用保留にできる。他候補の比較と研究の条件付き完了は続ける。

OSSを利用する候補はstrategyをdirect（直接利用）、wrapper、adapt（改変利用）から選び、次をreuseへ加える。

```json
{
  "strategy": "direct", "reason": "要件を満たし再実装が不要な理由",
  "source_ids": ["REPO1"], "version": "確認したtag/commit",
  "code_paths": ["実際に読んだ実装・呼出し先・関連テスト"],
  "api": "使うAPIと入出力", "tests": "読んだテストと実行済み/未実行の区別",
  "dependencies": "依存と環境条件", "integration": "組込み先・設定・接続方法",
  "license": {"status": "verified", "identifier": "確認したライセンス", "locator": "原典中の条件の場所"},
  "compatibility": "verified"
}
```

license.statusとcompatibilityはverified/unknown/incompatible。条件不明・不適合なら採用を保留する。
ライセンス名だけから全用途への適合を断定しない。互換性の確認範囲もintegrationへ記録する。
自作を選ぶ場合はcustomとし、既存OSSの直接利用・ラッパー・改変で不足する具体的理由をreasonへ書く。
既存OSSで要件を満たせるなら再利用を優先する。独自性そのものを採用理由にしない。
調査は採用方法の提案まで。対象アプリの依存追加・実装変更は実装依頼の範囲で行う。
PoCは既存の隔離・通信・許可・予算に従い、環境がなければ未実測とする。
原文・checkoutはローカル実行領域へ保持し、公開reportには分析・適用条件・参照先を載せる。
親が保存した外部資料の応答本文は、公開用Evidenceへ自動追加しない。外部原文を公開用local_pathへ登録しない。
