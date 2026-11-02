# 設計MCPの使い方

2026-11-02に公式資料を確認。実行時の一覧・入力スキーマ・権限を優先する。

| Provider | Remote MCP | 主な役割 |
|---|---|---|
| Whimsical | https://mcp.whimsical.com/mcp | 導線、分岐、ワイヤーフレーム、配置と接続の編集 |
| Figma | https://mcp.figma.com/mcp | FigJam、画面・部品・変数、デザインシステム、実装との往復 |

- [Whimsical設定](https://whimsical.com/integrations/codex)、[ツールと変更点](https://whimsical.com/learn/ai/mcp-tools)
- [Figma設定](https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/)、[ツール](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/)、[編集条件](https://developers.figma.com/docs/figma-mcp-server/write-to-canvas/)
- [CodexのMCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)、[App Server](https://learn.chatgpt.com/docs/app-server)

## 接続・認証・機能

外部MCPの追加は明示選択時だけ。既存の別名・設定・無効化を保持する。
OAuthは`codex mcp login <登録名>`で利用者が正規フローを完了する。トークンの貼り付け・転記を求めない。
doctorは登録、接続、認証、公開機能、対象への権限を区別する。登録や一覧だけでは編集権限を認定しない。
Figmaの編集はプラン・席・ファイル権限にも依存する。

`design_mcp.py catalog --providers figma`で入力スキーマを確認できる。認証・承認情報はネイティブCodexが扱う。
Whimsicalでは古いgenerate系と現在のcreate_file/add_board_content等が併記される場合がある。
Figmaでもuse_figma、generate_figma_design、html_to_figma等の有無を確認し、ない機能を仮定しない。

## 作成・編集

1. 指定されたファイル・ボード・ノード、または新規作成の場所と目的を特定する。
   接続しただけで既存の別ファイルを編集しない。調査だけなら読み取りに留める。
2. 現在の内容を読み、契約のUX IDと対象node ID、変更内容を短い操作案へ対応付ける。
3. 利用可能なネイティブMCPツールで実行する。Figmaのコードによるcanvas編集は、利用可能なら公式figma-use等の
   Skillを読み、対象ファイル・フレームを明示する。汎用CLIヘルパーは任意のJavaScriptを代理実行しない。
4. 編集後の構造と画像を読み直し、ID・URLを記録する。失敗後は実状態を確認してから再実行し、
   同じファイルや部品を重複作成しない。承認要求や403を回避する設定変更はしない。
5. 構造を交換JSONへ整理し、三者差分を確認して取り込む。外部側で原子的な版指定が使えない場合は、
   同時編集の完全な排他を保証せず、直前・直後の確認と競合の報告で扱う。

file_idを持つ単純な呼び出しは`design_mcp.py call --providers figma --request <JSON>`からも行える。
JSONは`tool`、`arguments`、`target: {file_id,url}`を持つ。書き込みは`--apply`が必要。
対象を結び付けられない作成・コード編集や追加承認が必要な操作はホストのMCP／公式Skillへ渡す。

## 利用不能時

未登録、未認証、権限不足、接続失敗、未対応機能を区別して伝える。
Mermaid、SVG、ローカルプレビューを生成し、認証以外の作業を続ける。
モックやローカルMCP fixtureの成功を、Whimsical/Figmaの実操作成功と記載しない。
Stitch・tldraw・Penpotは拡張候補であり、標準設定へ自動追加しない。
