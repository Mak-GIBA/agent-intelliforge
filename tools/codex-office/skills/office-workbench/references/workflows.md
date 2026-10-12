# 閲覧・編集手順

以下はローカルCLI。ユーザーが毎回入力する必要はなく、CodexがSkillから利用する。
引数のパスはすべて引用符で囲む。実際の編集範囲と出力名は依頼から確定する。

## Wordの部分修正

```bash
office-workbench inspect original.docx --output before.json
office-workbench render original.docx --out-dir before-pages
office-workbench prepare original.docx --output edited.docx
office-workbench officecli view edited.docx outline
office-workbench officecli get edited.docx /body --depth 2 --json
office-workbench officecli help docx paragraph
# 実在するパスを確認してから、例:
office-workbench officecli set edited.docx '/body/p[3]' --find '旧文' --replace '新文'
office-workbench officecli get edited.docx '/body/p[3]' --depth 2 --json
office-workbench officecli validate edited.docx
office-workbench verify-copy edited.docx
office-workbench compare original.docx edited.docx --require-media-preserved --output diff.json
office-workbench render edited.docx --out-dir after-pages
office-workbench verify-renders after-pages
```

`/body/p[3]`は例。文字列置換後も文字種別フォント、run書式、ページ数、ヘッダー・脚注・コメント等を確認する。
`python-docx`で段落全体の`.text`を上書きするとrunの書式を失うことがある。単純な全文再生成に逃げない。
画像を保持する要求がなければ `--require-media-preserved` は不要。図の変更を依頼された仕事を誤って失敗にしない。

## PowerPointの指定スライドだけ修正

```bash
office-workbench prepare original.pptx --output edited.pptx
office-workbench officecli get edited.pptx '/slide[4]' --depth 2 --json
office-workbench officecli help pptx shape
# 実在するshapeのIDやpathで編集する。
office-workbench officecli validate edited.pptx
office-workbench compare original.pptx edited.pptx --require-media-preserved \
  --allowed-part ppt/slides/slide4.xml --output diff.json
office-workbench render edited.pptx --out-dir all-slides
```

対象外のpart変更が検出された場合は理由を確認する。必要な`docProps`変更を許す場合も説明してallowlistへ追加する。
PPTXは画像だけではなく図形・コネクタ・チャート・マスター・テーマ・ノートから成る。画像hash一致だけでは「原図そのまま」とは言わない。
OfficeCLIのヘッドレスブラウザーを使う場合は `--engine officecli --pages 4` を明示する。この方法は要求ページだけのプレビューで、Word全ページを検査したことにはならない。

## PDFを図表込みで読む

```bash
office-workbench inspect paper.pdf --output structure.json
office-workbench extract paper.pdf --pages 1-10 --output text.md
office-workbench render paper.pdf --pages 1-10 --out-dir pages
office-workbench pdf-tables paper.pdf --pages 3-5 --output tables.json
```

ページは1始まり。全文依頼では残りのページを区切って続ける。表抽出が空でも表が存在しないとは限らない。
OCRは標準では実行しない。画像ページはCodexで視認し、必要なときだけOCRの導入・実行を合意する。

## PDFのページ操作

```bash
office-workbench pdf-select input.pdf --pages 1,3-5 --output selected.pdf
office-workbench pdf-rotate input.pdf --pages 2 --angle 90 --output rotated.pdf
office-workbench pdf-merge first.pdf second.pdf --output merged.pdf
```

署名・フォーム・ブックマークの完全な保持は対象外。必要なら専用処理と別検証を行う。
隠蔽用の白い図形はredactionではない。個人情報削除や任意のPDF本文編集はこのページ操作だけで済ませない。

## 技術的な構造確認と見た目は別

- `validate`: OfficeCLIのOpenXML構造検査。
- `compare`: パッケージpart、原画像byte、枚数などの差。
- `verify-copy`: 元ファイルが準備時から変わっていないか。
- `verify-renders`: 作成された画像が最新のファイルに対応しているか。
- **どれも自然言語の内容とレイアウトを採点する関数ではない。画像は別に開いて確認する。**

## ブラウザー・Officeの差

LibreOfficeとOfficeCLIの描画はMicrosoft Officeと同じではない。
複雑な変更履歴、SmartArt、OLE、数式、特殊フォント、PowerPointアニメーション、マスターは対象Officeでの確認を残す。
LibreOfficeは一時コピーをPDFへ変換するだけに使い、原本をOffice形式で保存し直さない。
PNGだけで確認できない変更履歴やコメントの残存はXML構造・アプリ本体でも別に確認する。
