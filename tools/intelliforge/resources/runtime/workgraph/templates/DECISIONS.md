# 案件の判断を残す

`decision=scoped`では、案件内で後から理由を確認する価値がある選択を`codex/decisions/`へ残す。案件を超える一般化は不要。通常の作業指示、TODO、進捗、根拠のない提案だけでは保存しない。

`type: decision`、`scope: project`、`repository`、`actor: user|agent|team`、`status: proposed|decided|superseded`を付ける。判断した人と保存したエージェントを混同しない。`verification: unknown|partial|verified`と`acceptance: unknown|accepted|rejected`は独立して扱い、指示だけを有効性の証明にしない。

背景・選んだ案・代替案・理由・影響・見直す条件・根拠を短く記す。未検証の影響は予想として書く。保存ヘルパーはリポジトリの識別子を付ける。別案件の判断は参照例にはなるが、その案件の運用規則として自動採用しない。リモート名を変えた場合や識別子が不明な旧ノートは、同一案件かを確認する。

同じ判断への新しい根拠や条件変更は、既存内容と例外を残して更新する。方針の撤回は、元の判断がなかったことにせず、変更理由を記す。公開・共有・学習利用は別の許可が必要。自動保存ではprivate/excluded/pendingとし、既存ノートを一括移行しない。
