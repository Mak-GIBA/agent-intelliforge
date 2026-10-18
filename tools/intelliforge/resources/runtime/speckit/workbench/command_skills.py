"""Explicitly invoked, fixed workflow entry points. These are not OS security rules."""
from __future__ import annotations
import json, shlex
from pathlib import Path

COMMANDS = {
    'upstream-new': ('new', '新規アプリ・機能の目的、要求、ストーリー、設計、検証計画を構造化する'),
    'upstream-existing': ('existing', '稼働中アプリのAs-Is、合意済み仕様、To-Beを分けて上流資料を整理する'),
    'upstream-change': ('change', '仕様変更の理由と既存要件・設計・テストへの影響を整理する'),
    'upstream-bug': ('bug', '不具合の期待挙動、再現条件、対象要件、修正設計、回帰検証計画を整理する'),
    'upstream-refactor': ('refactor', '挙動維持の条件、品質改善の目的、設計変更、移行・回帰検証計画を整理する'),
    'upstream-check': ('check', '上流文書の内容をレビューし、参照・網羅性をCLIで検査する'),
    'upstream-review': ('review', '次の承認チェックポイントを固定し、ユーザーが確認するreview packetを作る'),
    'upstream-approve': ('approve', '明示されたreviewとIDだけをhash-bound approvalとして記録する'),
}


def _frontmatter(name:str,desc:str)->str:
    return f'''---\nname: {name}\ndescription: {json.dumps(desc + '。明示呼び出し専用。', ensure_ascii=False)}\n---\n'''


def render_skill(name: str, command: Path, assets: Path) -> str:
    mode,desc=COMMANDS[name];cli=shlex.quote(str(command))
    base=_frontmatter(name,desc)+f"# {name}\n\n対象・目的はコマンド後の文章から読む。modeは`{mode}`に固定する。\n共通CLI: `{cli}`\n"
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
日本語の文書は利用可能なyomiyasuで仕上げ、意味・ID・数値・条件を保持する。
"""


def metadata(name: str, desc: str) -> str:
    return ('interface:\n'
            f'  display_name: {json.dumps(name)}\n'
            f'  short_description: {json.dumps(desc, ensure_ascii=False)}\n'
            f'  default_prompt: {json.dumps("$"+name, ensure_ascii=False)}\n'
            'policy:\n  allow_implicit_invocation: false\n')

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
