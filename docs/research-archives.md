# 検証記録のアーカイブ

研究・文章評価の要約と限界は、このリポジトリの検証ガイドに残しています。過去の実行状態、入力の複製、完成稿、評定、旧版資材は、必要なときに取得できるアーカイブへ移しました。通常のインストールやテストでは取得しません。

[English](en/research-archives.md) · [開発ガイド](development.md) · [アーカイブ台帳](research-archives.json)

## 保存した記録

[2026-10-27のアーカイブ](https://github.com/Mak-GIBA/agent-intelliforge/releases/tag/research-archive-20261027-871cb8ad)は、commit `871cb8adf0f7c278d22c72c4fbb21fadc5882f72` の2,414ファイルを、元の内容・相対パス・ライセンス表示のまま保存しています。圧縮後は約12.3 MiBです。要約などを除く2,254ファイル、約59.9 MiBを日常のGit管理から外しました。

対象はResearchの過去の実行記録、kotonohaの評価記録と旧版の評価資材です。成功・失敗・保留の記録をまとめて保存しており、今回の移送でモデルを再実行したり、結果を再評定したりしていません。

台帳にアーカイブのSHA-256、元commit、収録数を記録しています。アーカイブ内の`inventory.json`には各ファイルのSHA-256・サイズ・元のモードがあります。これは内容の一致を検査するための情報で、人による承認や文章品質の証明ではありません。

## 取得・検証・復元

Python 3.11以上で、リポジトリのルートから実行します。検証だけなら次のコマンドで取得し、圧縮ファイルと収録ファイルの全件を照合できます。

```bash
python scripts/research_archive.py verify
```

内容を読むときは、まだ存在しないディレクトリを指定して復元します。既存のディレクトリやファイルを上書きしません。復元先の中に、元の`docs/`・`tools/`からの配置ができます。

```bash
python scripts/research_archive.py restore --destination .artifacts/evidence-archives/20261027
```

オフラインでは、Releaseから取得済みのファイルを指定します。`--archive`は`verify`と`restore`の両方で使えます。複数のアーカイブを登録した場合は`--id`で選びます。

```bash
python scripts/research_archive.py verify --archive /path/to/research-archive-20261027-871cb8ad.tar.gz
```

復元した記録は、条件・出力・評定を読み直すために使えます。旧版の評価プログラムを再実行するときは、その記録が示す元commit・依存・モデル条件を別途そろえてください。復元コマンドはモデルや外部サービスを起動しません。元の文書中の詳細リンクは、必要に応じて元commit上のファイルやディレクトリを指しています。

たとえば4.1.1の再照合では、`--native`へ復元先の`docs/codex-yomiyasu/evidence/editorial-v411`を渡します。基準版の資材と現在の資材は、[当時の条件](codex-yomiyasu/evidence/editorial-v411/README.md)に従って用意します。

## Gitに残すもの

通常のオフラインテストが使うECCの記録、規範保持の基準データ、スキーマ移行資料、上流原典・ライセンスは残しています。生成Plugin、単体インストーラー、配布用runtimeも維持しています。アーカイブを取得しなくても、それらの導入・自己テストを使えます。

新しい大量の実行記録は作業用ディレクトリへ出し、検証ガイドには条件・結果・限界と必要な証拠の所在を残してください。CIの`check-tree`は、移送済みの領域が再び追跡対象へ入ることを拒否します。過去のGit履歴は保持しているため、現行ツリーの軽量化と、全履歴のclone容量は別です。
