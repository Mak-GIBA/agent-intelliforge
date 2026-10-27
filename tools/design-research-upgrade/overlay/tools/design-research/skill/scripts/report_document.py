"""Reader order for new runs; legacy rendering and factual records stay intact."""
from __future__ import annotations

import hashlib
import re

from execution_units import digest

HEADINGS = ('結論', '背景・課題と前提', '候補の調査と比較', '推奨方式と採用方法',
            '検証方法と結果', '限界・未確認事項と次の対応')
APPENDIX = '## 付録：出典・精読状況・実行記録'


def split_sections(lines):
    result = {}; current = ''; fenced = False
    for line in lines:
        if line.startswith(('```', '~~~')):
            fenced = not fenced
        if line.startswith('## ') and not fenced:
            current = line[3:]; result.setdefault(current, [])
        else:
            result.setdefault(current, []).append(line)
    return result


def substantive_signature(state):
    value = {k: state.get(k) for k in ('dossier', 'review', 'evaluation_summary',
                                            'expected_source', 'iteration', 'config')}
    if state.get('original_first_contract_version') == 1:
        value['original_first'] = state.get('original_first')
    return digest(value)


def body_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def body(text):
    return text.split('## 結論\n', 1)[1].split(APPENDIX, 1)[0].rstrip() if '## 結論\n' in text else ''


def editable_blocks(text):
    """Only narrative paragraphs are editable. Tables, headings, quotes and code are locked."""
    blocks = []; offset = 0; fenced = False
    for paragraph in re.split(r'(\n\s*\n)', text):
        start = offset; offset += len(paragraph)
        if not paragraph.strip():
            continue
        was_fenced = fenced; has_fence = False
        for line in paragraph.splitlines():
            if line.lstrip().startswith(('```', '~~~')):
                fenced = not fenced; has_fence = True
        if was_fenced or has_fence or any(re.match(r'^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s|[|>]|```|~~~|\$\$)', line)
                         for line in paragraph.splitlines()):
            continue
        if paragraph.strip().startswith(('採用判断:', '候補:', '対象版:', '実行ID:', '<!--')):
            continue
        blocks.append({'id': 'P' + str(len(blocks) + 1), 'text': paragraph, 'start': start, 'end': offset})
    return blocks


def nonempty_subsections(lines):
    out = []; fenced = False
    for i, line in enumerate(lines):
        if line.startswith(('```', '~~~')):
            fenced = not fenced
        if not fenced and re.match(r'^#{3,6} ', line):
            following = next((v for v in lines[i+1:] if v.strip()), '')
            heading = re.match(r'^(#{1,6}) ', following)
            if not following or (heading and len(heading[1]) <= len(line.split(' ', 1)[0])):
                continue
        out.append(line)
    return out


def assemble(state, original, workspace):
    """Reorder existing, evidence-bearing sections rather than regenerating their facts."""
    sections = split_sections(original); dossier = state.get('dossier') or {}
    plan = state.get('plan', {}); guide = dossier.get('reader_guide', {})
    decision = dossier.get('decision') or state.get('draft_conclusion') or {}
    mode = state['config']['mode']; selected = decision.get('candidate_id')
    candidates = {c['id']: c for c in dossier.get('candidates', [])}
    reviewed = state.get('review') or {}
    rationale = decision.get('rationale') or reviewed.get('reason')
    conclusion = [rationale or '調査・検証は途中です。結論はまだ確定していません。', '']
    if mode != 'research' and reviewed:
        checks = reviewed.get('checks', [])
        conclusion += ['確認結果: ' + ' / '.join(label + ' ' + str(sum(c['result'] == result for c in checks)) + '件'
                         for result, label in [('pass', '合格'), ('fail', '不合格'), ('unknown', '未確認')]), '']
        conclusion += ['- ' + i['id'] + ': ' + i['title'] for i in reviewed.get('issues', [])
                       if i['status'] != 'resolved']
    if selected:
        conclusion += ['候補: ' + candidates.get(selected, {}).get('name', selected),
                       '採用判断: ' + {'proposed': '採用を提案', 'provisional': '条件付き・採用保留',
                                   'deferred': '採用保留', 'accepted': '承認記録あり'}.get(decision.get('status'), '未確定'), '']
    conclusion += [str(s) for s in decision.get('unresolved', [])]
    background = [plan.get('goal') or state['config']['brief'], '',
                  '基準案: ' + plan.get('baseline', '未確認'), '', dossier.get('scope', ''), '']
    if dossier.get('constraints'):
        background += ['### 比較で維持する条件', '',
                       *['- ' + c['text'] for c in dossier['constraints']], '']
    if guide:
        background += ['### 入出力の具体例', '', guide.get('walkthrough', ''), '',
                       '### 用語と前提', '', guide.get('glossary', ''), '']
    compare = []; method = []; verification = []; appendix = []
    old_compare = sections.get('背景・課題と比較対象', sections.get('調査・比較・検証', []))
    split = next((i for i, s in enumerate(old_compare) if s in {'### 主張と根拠', '### 確認結果'}), len(old_compare))
    first = next((i for i, s in enumerate(old_compare[:split]) if s == '### 候補の比較'), split)
    compare += old_compare[first:split]
    for c in dossier.get('candidates', []):
        compare += ['### ' + c['name'], '', c.get('summary', ''), '']
    verification += old_compare[split:]
    method += sections.get('提案手法', [])
    if guide.get('diagram_source') != 'proposed-method':
        method += sections.get('全体像から詳細へ', [])
    method += sections.get('変更と再検証', [])
    for c in dossier.get('candidates', []):
        review = c.get('source_review', {}); reuse = review.get('reuse', {})
        if reuse:
            method += ['### ' + c['name'] + 'の採用方法', '',
                       '利用形態: ' + {'direct': '直接利用', 'wrapper': 'ラッパー経由', 'adapt': '改変利用',
                                   'custom': '自作', 'not_applicable': '対象外'}.get(reuse.get('strategy'), '未確認'), '',
                       reuse.get('reason', ''), '']
            for key, label in [('version', '対象版'), ('api', '利用API'), ('integration', '組込み方法'),
                               ('dependencies', '依存と環境'), ('tests', 'テストの確認範囲')]:
                if reuse.get(key):
                    method += [label + ': ' + reuse[key], '']
    for name in ('主要指標と具体的な差', '効果の測定状況', '実験設定・結果・根拠'):
        if sections.get(name):
            verification += ['### ' + name, '', *sections[name]]
    limits = [str(x) for x in dossier.get('limitations', [])] + list(decision.get('unresolved', []))
    if guide.get('limitations'):
        limits += [guide['limitations']]
    if decision.get('revisit_when'):
        limits += ['### 判断を見直す条件', '', *['- ' + x for x in decision['revisit_when']]]
    if not limits:
        limits = ['確認できた範囲は上記の検証結果に限られます。']
    for key in ('この研究が担当するコアロジック',):
        background += sections.get(key, [])
    compare += sections.get('前回からの変更と再検討', [])
    for source in dossier.get('sources', []):
        link = source.get('local_path') or source.get('url')
        appendix += [f"- [{source['id']}: {source['title']}]({link}) / {source.get('read_level', '未確認')}"]
    for c in dossier.get('candidates', []):
        review = c.get('source_review', {})
        if review:
            appendix += ['', '### ' + c['name'] + 'の精読記録', '', review.get('reason', '')]
        for read in review.get('paper_reads', []):
            appendix += ['', f"{read['source_id']}: {read['status']}", '']
            for s in read.get('sections', []):
                appendix += [f"- {s['section']} / {s['locator']}: {s['summary']}"]
            appendix += ['未確認: ' + '; '.join(read.get('missing', [])), read.get('supplementary', '')]
    holds = state.get('candidate_adoption_holds', {})
    for cid, reasons in holds.items():
        if reasons:
            limits += ['', candidates.get(cid, {}).get('name', cid) + 'の採用保留理由:',
                       *['- ' + reason for reason in reasons]]
    if state.get('units'):
        appendix += ['', '### 保存した工程', '', '| 工程 | 状態 |', '|---|---|']
        appendix += [f"| {u['id']} | {u['status']} |" for u in state['units'].values()]
    appendix += ['', *sections.get('停止した処理と検証の実行状況', []),
                 *sections.get('限界・次の実験と再現性', sections.get('残る確認と実行記録', []))]
    # Preserve future extension sections in the appendix instead of silently losing evidence.
    known = {'', '結論と確認してほしいこと', '要旨と現時点の結論', '保存した工程と残る作業',
             '背景・課題と比較対象', '調査・比較・検証', '提案手法', '全体像から詳細へ', '変更と再検証',
             '主要指標と具体的な差', '効果の測定状況', '実験設定・結果・根拠', 'この研究が担当するコアロジック',
             '前回からの変更と再検討', '停止した処理と検証の実行状況', '限界・次の実験と再現性',
             '残る確認と実行記録', 'はじめて読む方へ'}
    for name, content in sections.items():
        if name not in known:
            appendix += ['### ' + name, '', *content]
    parts = [(HEADINGS[0], conclusion), (HEADINGS[1], background)]
    if compare:
        parts.append((HEADINGS[2], compare))
    if method:
        parts.append((HEADINGS[3] if mode == 'research' else '改善方針と実施した変更', method))
    if verification:
        parts.append((HEADINGS[4], verification))
    parts.append((HEADINGS[5], limits))
    narrative = '\n'.join(x for title, content in parts for x in ['## ' + title, '', *nonempty_subsections(content), '']).rstrip() + '\n\n'
    pol = state.get('report_polish', {})
    if pol.get('status') == 'complete':
        if pol.get('science_sha256') != substantive_signature(state) or pol.get('base_sha256') != body_hash(body(narrative)):
            from runtime import Blocked
            raise Blocked('Report polish: approved text no longer matches the reviewed evidence')
        narrative = pol['approved_body']
    header = [original[0], '# ' + ('研究報告書' if mode == 'research' else '検証・改善報告書'), '',
              f"実行ID: {state['run_id']} / 状態: {state['status']} / 反復: {state['iteration']}",
              '対象版: ' + (state['expected_source']['head'] or 'Git管理なし'), '']
    if pol.get('status') == 'skipped_unavailable':
        header += ['文章の仕上げ: 未実施（kotonoha・yomiyasu未導入）。', '']
    elif pol.get('status') not in {'complete', 'not_required'}:
        header += ['草稿：文章の最終確認は未完了です。', '']
    return header + narrative.splitlines() + ['', APPENDIX, '', *appendix]
