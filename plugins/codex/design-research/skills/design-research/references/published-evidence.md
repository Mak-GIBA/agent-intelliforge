# 採用した研究の証拠を固定する

研究完了と設計への採用は別の段階です。まず要件・候補・run IDを選び、対象プロジェクトで次を実行します。複数の完了runから日時で自動選択しません。

```bash
bash <skill>/scripts/gan-harness.sh export-evidence \
  --project . --topic <topic> --run-id <ID> --related-id <design-ID>
# プレビューした同じ選択で適用する
bash <skill>/scripts/gan-harness.sh export-evidence \
  --project . --topic <topic> --run-id <ID> --related-id <design-ID> --apply
```

`docs/design-research/<topic>/evidence/<ID>/`へ固定報告と必要な依存ファイルをコピーします。元のrunは変更しません。manifestはソースの版、関連ID、各ファイルのハッシュを持ちます。receiptが必要とするログ・生成結果・評価入力も残し、欠落やハッシュ不一致は出力を止めます。既存パッケージは同じ内容でのみ再利用できます。

出力の`binding`をdesign.mdの各runへコピーし、既存の計画・統合フィールドと候補の選定理由を維持して、トップの`schema_version`を3にします。以下の山括弧の値は出力された実際の値で置き換えます。

```json
{
  "schema_version": 3,
  "workstream_plan": {"path": ".specify/workbench/research-plan.json", "sha256": "<plan hash>"},
  "runs": [{
    "workstream_id": "<workstream ID>",
    "state": "<binding.state>",
    "report": "<binding.report>",
    "state_sha256": "<binding.state_sha256>",
    "report_sha256": "<binding.report_sha256>",
    "evidence_manifest": "<binding.evidence_manifest>",
    "evidence_manifest_sha256": "<binding.evidence_manifest_sha256>",
    "decisions": [{"design_id": "<design ID>", "candidate_id": "<candidate ID>", "rationale": "根拠と限界を踏まえた採用理由"}]
  }],
  "standard_decisions": [],
  "integration": {
    "status": "planned", "rationale": "全体で検証する理由",
    "selected_combination": "選定した組合せ", "tradeoffs": "全体の制約と両立条件",
    "verification_ids": ["<verification ID>"], "artifacts": []
  },
  "uiux": {"applicable": false, "reason": "画面設計の適用範囲", "artifacts": []}
}
```

計画を持たない単独研究の結合ではworkstream_plan・workstream_id・standard_decisions・integrationを省けます。計画がある場合は研究計画の参照資料（Design Researchのworkstreams.md、UpstreamのRESEARCH_WORKSTREAMS.md）に従い、全テーマと標準実装の対応・統合条件を維持します。既存のv1/v2 bindingは変更せず引き続き使用できます。

```bash
bash <skill>/scripts/gan-harness.sh verify-evidence --package <evidence-directory>
```

この検証はローカルの実行記録がないcloneでも動きます。存在・ハッシュ・依存の完備を確認するもので、科学的な妥当性や本人性・ユーザー承認を認証しません。上流のv3設計の承認とgateには証拠の実際のハッシュが含まれます。証拠が変わると再レビューが必要です。確認ページをoverview --writeで更新し、正本と固定報告からユーザーが判断できるようにします。
