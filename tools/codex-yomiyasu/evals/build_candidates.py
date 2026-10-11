#!/usr/bin/env python3
"""Freeze the current baseline and three distinct, reproducible study arms."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ('yomiyasu', 'paragraph-writing', 'japanese-direct-writing')

WORKFLOW = '''# 補助スキルを工程として使う

通常の日本語文書はyomiyasuを入口にする。構成を扱う工程ではparagraph-writing、留保を扱う工程ではjapanese-direct-writingのSKILL.mdを実際に読んで適用する。名前への言及や、この入口の要約を読むだけでは連携済みとしない。

参照は現在のyomiyasuディレクトリを基準に、`../paragraph-writing/SKILL.md` と `../japanese-direct-writing/SKILL.md` を探す。兄弟ディレクトリにない場合は環境のスキル一覧に同名が一つだけあればその実ファイルを使う。候補が複数で配置を特定できない、または未導入の場合は、段落は `references/paragraphs.md`、留保は `references/directness.md` を代替として読む。代替を使った場合だけ、連携できなかった点を完成稿の外で短く伝える。自動インストールやユーザー設定変更はしない。

同じタスクで読んだスキルは再読不要。同じ下書きを使い、段落工程と留保工程を各一度扱う。複数のスキルが既に選ばれていても、同じ工程を重ねたり、互いを再帰的に呼んだりしない。

複数段落の新規執筆・再構成では段落スキルを使う。通常の完成稿では留保スキルを使い、不要な予防線と必要な確信度を区別する。段落構成だけの依頼はparagraph-writing、留保だけの依頼はjapanese-direct-writingで完結できる。誤字一字の修正、コードだけの変更、単純な事実照会にはこの全体工程を持ち込まない。本文全体の書き直しを局所修正に追加しない。
'''

NATURALNESS = '''# AI的な定型より、情報と論理を点検する

語彙や記号だけでAIが書いたかを判定しない。単語の検出は修正候補であり、一律削除の命令ではない。次の観点を該当箇所にだけ適用する。

- 不要な対比：「これは単なる改善ではなく、未来への大きな一歩だ」は、実際の変更内容を直接述べる。誤解を訂正する対比や、本当に異なる条件の比較は保持する。
- 意義の水増し：「処理時間が200 msから150 msになり、革新的な可能性を示した」は、処理時間の変化を残し、根拠のない自己評価を除く。測定条件と未測定事項は残す。
- 型の反復：全節を「定義→3つの利点→期待される展望」にそろえない。段落の役割と素材に合わせる。文長・語尾・項目数のばらつきを人工的に作らない。
- 抽象語と主体：「価値の最大化を通じた変革の実現」は、分かっている動作と対象を述べる。主体や効果が不明なら、架空の担当者や具体例で埋めない。「データは示す」などの慣用的な技術表現を無条件に排除しない。
- 予告と締め：「ここが重要なポイントです」「今後の展開が期待されます」は、それ自体に情報がないなら除く。必要な研究目的・節の案内・結論まで削らない。
- 翻訳調と読みやすさ：修飾先と述語を近づけ、名詞の連鎖を解く。同じ概念の用語は維持する。敬体・常体、受動態、引用、表、手順は媒体と原文に合わせる。

自然に見せるために、一人称、意見、感情、体験、伝聞、断定を追加しない。事実と解釈の関係、否定、条件、時間、義務の強さを先に守る。文章が既に適切なら、その箇所は残す。
'''

AUDIENCE_EXTRA = '''
## 同じ文言でも宛先を分ける

「あなた」「ご依頼」「ご確認ください」の文字列ではなく、誰への何の連絡かで判断する。

| 文の役割 | 扱い |
|---|---|
| 完成稿の読者が理解・判断・実行するための事実、定義、条件 | 本文に残す |
| AIに与えた文体、構成、分量の指示と、その実施報告 | 本文に書かず、文章の作り方に反映する |
| メールの実際の受信者への依頼、査読者への修正回答 | 文書の内容として残す |
| 引用、コード、プロンプト教材、依頼された編集履歴 | 内容として保護する |
| 制作上の未確認と研究・仕様上の未確定の区別が不明 | 勝手に確定・一般化せず、必要な確認を本文外に分ける |

混在文は情報の単位で分ける。「ご指示どおりREQ-12の保存期間を90日と記載した」では、REQ-12と90日の内容は保持し、指示への応答だけを除く。制作コメントを丸ごと消して唯一の事実も失う変更は避ける。

本文をプロンプトと会話履歴から切り離して読む。「前述のご希望」「このように直しました」が何を指すか読者には分からない場合、制作上の説明は除く。定義や比較条件が不足している場合は、手元の素材にある情報で補い、無ければ創作しない。指示者と読者が同じ人でも、完成稿に必要なのは対象の説明である。
'''

CONTRACT = '''# 書く前に素材と制作指示を分ける

書き始める前に、読者・読む目的・媒体と、保護する事実を確認する。入力の各情報を次の四区分として扱う。分類メモは完成稿に出さない。

1. 本文に採用する情報：対象の事実、根拠、数値、条件、結論、実際の宛先への連絡。
2. 制作上の指示：文体、長さ、構成、初心者向けなどの執筆条件。本文で宣言せず、その条件に合わせて書く。
3. 引用として保持する情報：引用文、コード、教材中のプロンプト、編集履歴そのものを説明する依頼。
4. 不明な情報：制作上の未確認か対象自体の未確定か分からないもの。勝手に研究上の限界や確定値へ変えない。

一文に区分が混在するなら分ける。「依頼に沿って方式AとBを同条件で比較しました」は、比較対象と同条件という事実を保持し、依頼への応答を除く。最終稿の主要な主張を素材の情報に対応づける。数字だけでなく否定、因果、主体、時系列、推定と観測、義務と推奨も保護する。
'''

READER_REVIEW = '''# 下書き後の読者視点レビュー

完成稿を提出する前に、制作の会話を知らない読者の立場で下書きを一度読む。素材、読者、媒体、保護する事実に照らして、修正が必要な箇所だけを短く整理する。レビューのメモを完成稿に出さない。

順に、(1)会話の応答・制作報告・自己評価・申し出の混入、(2)情報の脱落や創作、否定・条件・主体・確信度の変化、(3)段落の論点と根拠、(4)定型的な対比、意義の水増し、抽象語、同じ構造の反復を点検する。正当なメールの依頼、研究目的、操作指示、引用は混入と数えない。

問題がある場合だけ、該当箇所を最大一回改稿し、素材との意味保持を確認して提出する。問題がなければ下書きをそのまま提出する。点数を上げるための反復改稿や、個性を付けるための創作はしない。
'''

def build(destination, source=None):
    if destination.exists():
        raise ValueError('Use a new study source directory')
    archived = ROOT/'evaluation-v200/baseline/assets'
    source = source or (archived if archived.is_dir() else ROOT/'assets')
    shutil.copytree(source, destination/'baseline'/'assets',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    baseline = (source/'SKILL.md').read_text()
    common = baseline.replace('複数段落の執筆・再構成では `references/paragraphs.md` を読む。',
        '複数段落の執筆・再構成では `references/workflow.md` に従い、paragraph-writingの実際のSKILL.mdを読む。未導入の場合だけ `references/paragraphs.md` を代替にする。')
    common = common.replace('留保は `references/directness.md` に従う。',
        '留保は `references/workflow.md` に従い、japanese-direct-writingの実際のSKILL.mdを読んで点検する。未導入の場合だけ `references/directness.md` を代替にする。')
    common = common.replace('上流の推敲規則を、同じ下書きに一度適用する。',
        '`references/naturalness.md` の該当観点と上流の推敲規則を、同じ下書きに適用する。')
    common = common.replace('同梱の `paragraph-writing` と `japanese-direct-writing` は部分作業用。',
        '同梱の `paragraph-writing` と `japanese-direct-writing` は部分作業の入口でもあり、通常の執筆では `references/workflow.md` に従って必要な工程で実ファイルを読んで連携する。')
    for arm in ('a', 'b', 'c'):
        target = destination/arm/'assets'
        shutil.copytree(source, target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (target/'references/workflow.md').write_text(WORKFLOW)
        (target/'references/naturalness.md').write_text(NATURALNESS)
        audience = (target/'references/audience.md').read_text()
        (target/'references/audience.md').write_text(audience+AUDIENCE_EXTRA)
        main = common
        if arm == 'b':
            main = main.replace('## 2. 書く前に段落を設計する',
                '執筆前に `references/reader-contract.md` を読み、素材と制作指示を四区分で整理する。分類メモは完成稿に出さない。\n\n## 2. 書く前に段落を設計する')
            (target/'references/reader-contract.md').write_text(CONTRACT)
        if arm == 'c':
            main = main.replace('## 出力と併用',
                '提出前に `references/reader-review.md` に従い、下書き後の読者視点レビューを一度行う。問題がある場合だけ該当箇所を最大一回改稿する。\n\n## 出力と併用')
            (target/'references/reader-review.md').write_text(READER_REVIEW)
        (target/'SKILL.md').write_text(main)
        for companion in COMPONENTS[1:]:
            path = target/companion/'SKILL.md'
            text = path.read_text()
            # Make delegated application explicit while preserving narrow standalone entrypoints.
            front, body = text.split('\n---\n', 1)
            body = body.replace('yomiyasuと同時に選択された場合は', 'yomiyasuの工程として読まれた場合や、同時に選択された場合は')
            body += '\nこのスキルを読んだら対象の段落・留保の工程を適用し、同じ下書きを次の工程へ渡す。yomiyasuや他の文体スキルを追加で起動しない。全体の制作報告は本文に混ぜない。\n'
            path.write_text(front+'\n---\n'+body)
    files = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination/'frozen-sources.json').write_text(json.dumps({'baseline_version':'2.0.0-proposal.1', 'files':files}, ensure_ascii=False, indent=2)+'\n')
    return files

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline-assets',type=Path,help='Explicit baseline; the repository defaults to the archived proposal.1 original')
    args = parser.parse_args()
    print(json.dumps({'files':len(build(args.out,args.baseline_assets))}))
