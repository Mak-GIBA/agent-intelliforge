---
name: ux-visual-design
description: ユーザーの目的から導線図・ワイヤーフレーム・UI設計を作り、人間の編集をローカルの設計契約へ反映する。複数画面のUX設計、導線の可視化、Whimsical・Figmaとの共同編集で使う。小さな文言やCSSだけの修正に全体設計を要求しない。
---

# UXを可視化して実装へつなぐ

ユーザーが何を達成したいかを、画面・操作・状態と対応付ける。図だけで完成とせず、
実装と実操作まで追える設計契約を残す。既存の構成・デザインシステム・依頼範囲を優先する。

## 作業の入口

1. 依頼、既存アプリと上流資料、利用者、利用状況、達成条件を読む。渡された設計メモを再利用する。
   対象・属性・操作・関係を整理し、固定手順にはタスク指向の構成も検討する。
   OOUIの判断は利用可能なooui-designの参照資料を使い、同じ処理を呼び戻して循環させない。
2. シナリオとジャーニー、情報のまとまり、画面、遷移、入力保持、エラー・取消・中断・復旧を決める。
   正式な要件と提案・未確認を分ける。IDは既存仕様とハーネスのscreen/flow IDを優先する。
3. [設計契約と共同編集](references/contract.md)に沿い、JSONと編集可能な導線図・ワイヤーフレームを作る。
   軽微な修正では既存契約の影響箇所だけを扱い、契約がないだけで資料一式を要求しない。
4. 外部キャンバスを使う場合は[接続と対象範囲](references/mcp.md)を読む。実行時のツール一覧とスキーマを確認する。
   外部MCPがなければMermaid・SVG・HTMLプレビューを使って続ける。
5. [UI設計と引き継ぎ](references/design.md)に沿い、実装可能な画面、部品、状態、レスポンシブを設計する。
   新規・大幅変更では成果物のリンクと判断理由を提示する。実装まで依頼済みなら確認可能な状態を残して進める。
   任意の追加質問や未認証の外部ツールだけを理由に実装を止めない。
6. 実装前に人間の編集を読み直し、三者差分を契約へ反映する。競合を隠して上書きせず、必要な一点だけ確認する。
   人間の承認を受けていない版を「承認済み」と記録しない。
7. Product Design／Build Web Apps等の利用可能な実装Skillへ、契約、画面・操作ID、デザイン、必要な状態、
   未決事項を渡す。実装を依頼されていない場合は設計までに留める。
8. 実装後はux-gan-harnessへ同じ契約を渡し、実画面・操作・必要なテストと照合する。
   修正の申告、図の存在、構造検査だけでタスク達成や使いやすさを認定しない。

## ローカルの操作

契約の既定位置は`docs/ux/design-contract.json`。同等の既存資料があれば再利用する。
`<skill-dir>`はこのSkillの実際の配置先へ置き換える。

```bash
python3 <skill-dir>/scripts/ux_contract.py validate --contract docs/ux/design-contract.json --project .
python3 <skill-dir>/scripts/ux_contract.py export --contract docs/ux/design-contract.json --design docs/ux/visual
python3 <skill-dir>/scripts/ux_contract.py import --contract docs/ux/design-contract.json --design docs/ux/visual/wireframes.svg
python3 <skill-dir>/scripts/design_mcp.py doctor --providers whimsical,figma
```

`import`は既定で提案だけを返す。依頼範囲内の変更を反映する場合は`--apply`を付ける。
共有済みの成果物や別の利用者の編集を、再生成で消さない。
設計だけの段階では`validate`の`--project`を省略する。実装済みの対応ファイルも確認するときに付ける。
自動出力は構造のプレビューである。入力部品、情報の優先順位、各状態の表示を補い、主要画面を作り込む。

## 報告

目的、主要経路、採用理由、成果物、確認した操作、残る不一致を短く伝える。
自動チェック、モデルによる画像評価、実MCPの操作、人間による利用評価を区別する。
外部ツールが使えない場合は理由と代替成果物を示し、モックの成功を実接続として記載しない。
