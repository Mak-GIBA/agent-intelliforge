# 設計契約と共同編集

契約はJSONで保持する。`assets/contract.schema.json`は構造、`ux_contract.py validate`はID・参照・状態・
実装対応も検査する。`assets/document-example.json`は架空の例であり、実案件の要件ではない。

| 項目 | 内容 |
|---|---|
| schema_version / revision | 形式の版と設計の版 |
| project | 利用者・利用状況・目的・対象・属性・操作・関係。根拠がない事業判断は補わない |
| journeys | Journey ID、目的、Action IDの順序、必須かどうか |
| screens | Screen ID、表示名、目的、ローカルルート、状態、実装対応、任意の配置 |
| actions | Action ID、対象画面、表示名、click/fill/select/press、selectorまたはrole/name |
| transitions | 操作、遷移元と先の画面・状態、条件、エラー時の先、保持する入力・選択 |
| requirements | 要件、Journey ID、必須かどうか、受け入れ条件 |
| artifacts | provider、外部URL・file_id、UX IDと外部node IDのbindings、確認済みスナップショット |
| approval | not_requested / presented / approved / needs_review / delegatedとその根拠 |

承認済みの外観を照合する場合は、artifactに `revision` と
`snapshot: {path: "docs/ux/approved.png", sha256: "<PNGのSHA-256>"}` を追加する。
pathはプロジェクト内の相対パス。ハーネスは画像と契約の両方を固定して独立レビューへ渡す。
approvedなのに参照画像がない場合は、外観の整合を未検証としてrunを合格にしない。
参照画像の存在は外観が一致した証拠ではなく、実画面との具体的な比較は別に必要となる。

受け入れ条件は固有ID、画面、状態、検査種別、locator、expectedを持つ。
種別はvisible、text、value、checked、focused、accessible_name、url。
実行するJavaScriptやシェルを埋め込まない。エラーと再試行、戻ると入力保持など、
達成条件を観測できる検査を明示する。業務上の条件は文章と実操作の根拠も残す。
入力部品は各screenの`fields: [{id,label,type}]`で宣言できる。typeはtext/search/email/number/textarea/select/checkbox。
selectの候補は`options`へ置く。`state_messages`で状態の表示を指定する。
保持する内部値をすべて入力欄として表示しない。設計段階の検証では`--project`を省略し、実装後に指定する。

## 編集を取り込む

- 設計・実装・レビューの前に対応する外部ファイルとローカル成果物を読み直す。常時同期は不要。
- SVGの画面・操作IDとメタデータ、MermaidのIDと`ux-base`行を保持する。タイトル、位置、サイズ、
  接続先・条件の変更を取り込める。対応不明のノードや構文はマッピングを確認する。
- JSON交換は`{"base": 前回の契約, "contract": 編集後の契約}`とする。Whimsical/Figmaの読み取り結果を
  この形へ整理し、元のID・URL・版またはハッシュを保持する。画像だけで遷移の意味を確定しない。
- 前回・現在のローカル・外部編集の三者を照合する。独立した変更は統合し、同じ項目の変更・削除競合は残す。
  図形の移動を業務要件の変更と同一視しない。承認後に内容が変わった版は再確認の対象とする。
- 提案を確認してから`import --apply`する。実装まで依頼済みで競合がなければ反映のたびに承認待ちを増やさない。
- 出力manifestは所有するファイルのハッシュを記録する。手動編集があれば再生成で上書きせず、先に取り込む。

同じScreen/Journey IDをハーネスへ渡す。コードの変更ハッシュは再確認のきっかけであり、それだけでUXの
不一致や一致を断定しない。契約の整合性、実装の存在、実操作、見た目、認知負荷、人間の承認は別の確認である。
# ブラウザーとの照合

`ux-gan-harness ... --ux-contract docs/ux/design-contract.json` は実装ファイルも確認して契約を固定する。
各画面・状態に到達したら `ux_check_contract(screen_id,state)`、宣言した操作の直後には
`transition_id` も指定する。正常経路だけでなく `T-id__on_error` も必須になる。
ホストは操作元・操作対象・遷移先・ルート・状態の受け入れ条件をブラウザー証拠と照合する。
状態ごとに実際に観測できる受け入れ条件を記載する。状態の名前だけでは合格にならない。

`retained_fields` は保持すべき実入力のIDで、`fields[].locator` があれば優先し、なければ
DOMの同名IDまたは `data-field` を使う。別画面で入力欄が外れる場合は、戻って再出現した時に
値を照合する。比較元を観測できない値、再表示されなかった値は未検証のまま残す。
各遷移に `T-id__retain_<field>` のチェックが追加され、未検証・不一致ならrunは合格しない。
これは自動操作とAIレビューであり、人間のユーザビリティテストの結果ではない。
