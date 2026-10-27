"""Keep entry instructions short; retain detailed contracts as phase references."""
from pathlib import Path
import re


def apply(repo):
    skill=repo/'tools/design-research/skill'
    original=(skill/'SKILL.md').read_text('utf-8')
    original=original.replace('available yomiyasu','available kotonoha (or yomiyasu as a compatibility fallback)')
    original=original.replace('If yomiyasu is unavailable','If neither writing entry is available')
    front=re.match(r'---\n.*?\n---\n',original,re.S).group()
    advanced=re.sub(r'(\]\()(?=(?:references|scripts|templates|agents)/)',r'\1../',original[len(front):])
    advanced = ('新規runのreport_contract_version=2と保存済みのversion=1では[報告工程](reporting.md)と'
                '[原典確認](source-review.md)を適用する。以下の旧執筆推奨は旧run向けの互換契約として残す。\n\n' + advanced)
    (skill/'references/advanced-contracts.md').write_text(advanced,encoding='utf-8')
    (skill/'SKILL.md').write_text(front+'''
# Design Research

`$design-research`を入口に、依頼と既存記録から必要な工程を選ぶ。
`DR_GAN_CHILD=1`では渡された役割と参照だけを扱い、別ハーネスやMemory書込を開始しない。

1. 対象の境界・AGENTS.md・正本・現在の依頼範囲を確認する。
   `scripts/workflow_overview.py --project <root>`で状態を読む。確認だけなら書かず実行しない。
2. 単一方式はresearch、完了研究の条件変更はreassess、中断した同条件はresume。
   全体の要求・設計はUpstreamへ戻し、不確実なコアロジックを研究テーマとして分解する。
   複数候補・複数runは明示選択し、最新日時で決めない。計画だけの依頼は計画で止める。
3. 実行時に[工程と停止境界](references/workflow-guide.md)と
   [保存単位](references/execution-units.md)を読む。
   `scripts/codex_interface.py prepare`で入力とハッシュを確認し、同じ選択でrunする。
   実際の`gan-harness.sh`のrun ID・状態・結果を報告する。文章のレビューで実行を代替しない。
4. 効果・精度・性能を測るときは[評価契約](references/effectiveness-evaluation.md)を読み、
   実験前に主要指標・基準案・同一入力・採点・採用条件を固定する。
   文献・設計調査は未測定の効果を明記し、条件付きの結論にする。改善なしも結果として残す。
5. 約5候補を目安に一次資料、必要な数式・図解・反証条件を比較する。少数なら理由を記録する。
   提案手法の詳細設計が必要なら[提案手法](references/proposed-method-report.md)、
   条件変更なら[再検討](references/reassessment.md)、複数テーマなら[研究計画](references/workstreams.md)を読む。
   詳細な実行・証拠・役割契約は[実行契約](references/advanced-contracts.md)の該当節を使う。
6. 原典確認→公式実装・原手法の検証→必要な適応・改変→再比較→独立レビュー→全文推敲を保存する。
   新規研究は[原形からの検証](references/original-first.md)に従い、近似PoCで原手法の検証を代用しない。
   必須単位が残る間は全体を完了としない。入力は通常16 KiB以内、超過は全文・ハッシュ付き参照へ。
   同一projectのロック・時間上限・sandbox・ネット利用・実装変更の境界を守る。

新規テーマの報告書は`docs/design-research/<topic>/report.md`、図は同じ場所の`figures/`。
完全な実行記録は`.artifacts/design-research/<topic>/`に保存しGitから除外する。
既存テーマは元の保存先を維持する。採用時は[証拠の固定](references/published-evidence.md)を読み、設計に採用するrunだけ
`gan-harness.sh export-evidence --project <root> --topic <topic> --run-id <ID>`で確認し、
`--apply`で`docs/design-research/<topic>/evidence/<ID>/`へ必要な証拠を固定する。
`verify-evidence --package <path>`はclone後も検証できる。必要なログを省かない。
Upstreamは出力されたv3 bindingを要件・設計IDに結び、統合結果と未確認事項を別に記録する。
文書更新後は`overview --write`で確認ページを更新し、最後はそのリンクと対象ID・次の操作を示す。
記録の整合性は科学的な有効性やユーザー承認の証明ではない。未実行・失敗・不明点を保持する。
新規runは固定した根拠から論文型の技術報告を構成し、全文にkotonohaを適用して意味を独立確認する。詳細は[報告工程](references/reporting.md)に従う。
有望な論文の全文確認とOSS再利用の判断は[原典確認](references/source-review.md)で記録する。
未読・利用条件不明の候補は採用保留にする。日本語Skillがなければ未適用を明記して完了できる。
公開済みの台帳・ログ・保存版は保持する。
''',encoding='utf-8')
    upstream=repo/'tools/speckit-upstream'
    p=upstream/'workbench/command_skills.py';text=p.read_text('utf-8')
    # Preserve catalog, metadata, invocation policy and descriptive routing.
    start=text.index('def render_skill(');end=text.index('\ndef metadata(',start)
    text=text[:start]+'''def render_skill(name: str, command: Path, assets: Path) -> str:
    mode,desc=COMMANDS[name];cli=shlex.quote(str(command))
    base=_frontmatter(name,desc)+f"# {name}\\n\\n対象・目的はコマンド後の文章から読む。modeは`{mode}`に固定する。\\n共通CLI: `{cli}`\\n"
    if mode=='review':
        return base+f"""
`doctor`と`overview`で対象を確認し、`approval-plan`で未承認・staleのIDを読む。
`review --project <root> --checkpoint next --write`で本文とIDを固定する。
対象ID・要旨・未解決事項・共通条件・固定レビューのリンクを提示する。
どのIDを承認・修正するか確認する。明示承認までapproveは実行しない。
沈黙や過去の一般的なOKを今回の承認に使わない。review作成自体は承認ではない。
詳しい確認手順: `{assets}/references/PHASES.md`のレビュー節。
最後は確認ページへのリンク1つと今回の対象IDを示す。
"""
    if mode=='approve':
        return base+f"""
現在のユーザー発言が具体的なreviewのIDを明示承認した場合だけ記録する。
`review --latest`を読む。指定されたreview_idを優先し、曖昧なら確認する。
`approve --review <ID> --id <item> --by <label> --reference <今回の発言>`をdry-runする。
一致を確認して`--apply`。全部承認はこのreview全体への明示承認がある場合だけ。
checkとapproval-planを再確認する。STALE系は再レビューし、自動再承認しない。
STALE_REVIEW等は再レビューへ戻す。記録は本人性の暗号認証ではない。未適用なら未記録と報告する。
詳しい手順: `{assets}/references/PHASES.md`の承認節。
最後は確認ページと記録したID・承認状態を示す。
"""
    return base+f"""
1. 対象境界・AGENTS.md・既存文書を確認し、doctorとoverviewで配置・状態を読む。
2. `flow --project <root> --mode {mode} --brief`を読み、今の段階の
   `{assets}/references/PHASES.md`を使う。CLI未配置・競合は停止して報告する。
3. 未準備ならattachの差分を示し、依頼範囲で適用する。正本と既存の合意を維持する。
   文書編集は依頼範囲内だけ。checkは監査から始め、変更の依頼がなければ書かない。
4. 目的→ニーズ→ストーリー→要件→設計→検証をIDで結び、現状・合意・提案を分ける。
   方式選択はRESEARCH_FIRST.md、要件の見直しはREASSESSMENT.mdを読む。
   不確実なコアロジックだけdesign-researchへ。必要な研究は設計確定前に実行する。
5. レビューはupstream-review、現在の明示承認の記録はupstream-approve。
   沈黙は承認にせず、古いreviewやstaleな下流項目を自動承認しない。
6. checkで点検する。確定を主張する場合だけ`gate --project <root> --write`を実行し、非ゼロは未完了とする。
   更新後は`overview --write`。読み取り依頼では書かず最新のoverviewを表示する。
最後は確認ページ1つと対象ID・確認箇所・承認待ち・次の操作を示す。
上流整理だけではアプリ実装・DB変更・デプロイを開始しない。計画と実行PASSを混同しない。
日本語は利用可能なkotonohaを優先し、未導入ならyomiyasu互換入口を使う。同じ原稿に両方を重ねず、意味・ID・数値・条件を保持する。
"""

''' +text[end:]
    p.write_text(text,encoding='utf-8')
    # The generic entry routes to existing commands instead of repeating their steps.
    p=upstream/'assets/skill/SKILL.md';original=p.read_text('utf-8')
    front=re.match(r'---\n.*?\n---\n',original,re.S).group()
    p.write_text(front+'''
# SpecKit Workbench

新規はupstream-new、現状整理はupstream-existing、変更はupstream-change、
不具合はupstream-bug、設計改善はupstream-refactor、点検はupstream-checkを使う。
レビューはupstream-review、明示承認の記録はupstream-approve。
CLI: `@COMMAND@`。まず`doctor`と`overview --project <root>`で対象と状態を確認する。
手順は`flow --mode <mode> --brief`と`@ASSETS@/references/PHASES.md`の該当段階を読む。
依頼範囲と既存AGENTS.mdを守る。構造検査・研究実行・ユーザー承認・アプリ動作を区別する。
''',encoding='utf-8')
