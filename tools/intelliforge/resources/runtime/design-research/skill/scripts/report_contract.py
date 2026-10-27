"""Reading/reuse eligibility for new reports; access does not prove understanding."""
from __future__ import annotations

from runtime import Blocked


def text(value):
    return isinstance(value, str) and bool(value.strip())


def active(state):
    return state.get('report_contract_version') in (1, 2)


def instruction(role, state):
    if not active(state):
        return ''
    common = ('\nREPORT CONTRACT: Read references/reporting.md for your responsibility. '
              'The final whole-report writer uses available kotonoha, otherwise yomiyasu; never install a writing skill. '
              'Content roles return faithful narrative fields without repeating that writing workflow. '
              'Keep original evidence, numbers, outcomes and uncertainty.\n')
    if role in {'producer-evidence', 'reviewer-dossier'}:
        common += ('Each candidate needs source_review={promising:boolean,reason:string,paper_reads:[],reuse:{...}}. '
                   'Read references/source-review.md for exact fields. Assess the selected candidate as promising. '
                   'Read promising papers completely, not just their abstracts/decisive extracts. '
                   'Record partial/unavailable reading truthfully and defer adoption of that candidate; other comparisons continue. '
                   'Prefer suitable existing OSS over unnecessary reimplementation. Never invent full reading or license clearance. '
                   'Unsupported findings remain unknown/hypothesis, not reported observations.\n')
    if state.get('original_first_contract_version') == 1:
        common += (' ORIGINAL-FIRST: Read references/original-first.md for this role. Originals and complete source reading '
                   'precede execution. Never replace an untried original with a simplified custom proxy. '
                   'Assets use parent-prepared runtimes through DR_RUNTIMES and the fixed model bridge; no child installs. '
                   'For adaptation, reuse exact baseline trials from DR_ORIGINAL_RESULTS and run only changed candidates. '
                   'Keep source_review.implementation origin, parent and differences. New variants need measured reasons. ')
        return common
    return common if role != 'producer-assets' else ''


def assess(dossier, state, *, require_all=True, verify_access=True, for_trial=False):
    """Return candidate holds; malformed assessments fail, incomplete reading defers adoption."""
    if not active(state) or state['config']['mode'] != 'research':
        return {}
    sources = {s['id']: s for s in dossier['sources']}
    selected = dossier['decision'].get('candidate_id')
    holds = {}
    for candidate in dossier['candidates']:
        cid = candidate['id']; review = candidate.get('source_review')
        if not isinstance(review, dict):
            if require_all:
                raise Blocked('Source review: candidate ' + cid + ' needs source_review')
            continue
        if not isinstance(review.get('promising'), bool) or not text(review.get('reason')):
            raise Blocked('Source review: promising and reason are required: ' + cid)
        if cid == selected and not review['promising']:
            raise Blocked('Source review: selected candidate must be promising: ' + cid)
        reads = review.get('paper_reads'); reuse = review.get('reuse')
        if not isinstance(reads, list) or not isinstance(reuse, dict):
            raise Blocked('Source review: paper_reads and reuse are required: ' + cid)
        linked = {e['source_id'] for claim in dossier['claims']
                  if claim['id'] in {i for row in dossier['comparison'] if row['candidate_id'] == cid
                                     for i in row.get('claim_ids', [])}
                  for e in claim['evidence'] if e['relation'] == 'supports'}
        if cid == selected:
            linked |= {e['source_id'] for claim in dossier['claims']
                       if claim['id'] in dossier['decision'].get('claim_ids', [])
                       for e in claim['evidence'] if e['relation'] == 'supports'}
        if state.get('original_first_contract_version') == 1:
            linked |= set(review.get('implementation',{}).get('source_ids',[]))
        paper_ids = {sid for sid in linked if sources.get(sid, {}).get('source_type') in {'paper', 'preprint'}}
        indexed = {}; reasons = []
        for read in reads:
            sid = read.get('source_id') if isinstance(read, dict) else None
            if not isinstance(sid, str) or sid not in sources or sources[sid].get('source_type') not in {'paper', 'preprint'} or sid in indexed:
                raise Blocked('Source review: paper reading has unknown/duplicate source: ' + str(sid))
            indexed[sid] = read
            if not isinstance(read.get('status'), str) or read['status'] not in {'complete', 'partial', 'unavailable'}:
                raise Blocked('Source review: invalid reading status: ' + sid)
            if not isinstance(read.get('sections'), list) or not isinstance(read.get('missing'), list):
                raise Blocked('Source review: sections/missing arrays are required: ' + sid)
            if not all(text(v) for v in read['missing']):
                raise Blocked('Source review: missing material must be named: ' + sid)
            for section in read['sections']:
                if not isinstance(section, dict) or any(not text(section.get(k))
                                                       for k in ('section', 'locator', 'summary')):
                    raise Blocked('Source review: section, locator and summary are required: ' + sid)
            access = state.get('sources', {}).get(sid, {})
            evidence = state.get('evidence', {}).get(access.get('evidence_id'), {})
            if read['status'] == 'complete':
                if (sources[sid].get('read_level') != 'full_text' or not read['sections'] or read['missing']
                        or not text(read.get('supplementary'))
                        or (verify_access and (access.get('status') not in {'local', 'retrieved'}
                            or (access.get('status') == 'retrieved' and
                                (not access.get('original_path') or not access.get('original_sha256')))
                            or not evidence.get('sha256')))):
                    raise Blocked('Source review: full reading needs full_text, sections, supplements and access evidence: ' + sid)
            elif not read['missing']:
                raise Blocked('Source review: incomplete reading must identify missing material: ' + sid)
        if review['promising']:
            for sid in sorted(paper_ids | set(indexed)):
                if indexed.get(sid, {}).get('status') != 'complete':
                    reasons.append('論文の全文確認が未完了: ' + sid)
        strategy = reuse.get('strategy')
        if not isinstance(strategy, str) or strategy not in {'direct', 'wrapper', 'adapt', 'custom', 'not_applicable'}:
            raise Blocked('Source review: invalid reuse strategy: ' + cid)
        if not text(reuse.get('reason')):
            raise Blocked('Source review: explain reuse/custom choice: ' + cid)
        if strategy in {'direct', 'wrapper', 'adapt'}:
            ids = reuse.get('source_ids', [])
            if not isinstance(ids, list) or not ids or any(not isinstance(s, str) or sources.get(s, {}).get('source_type') != 'repository' for s in ids):
                raise Blocked('Source review: OSS adoption needs repository sources: ' + cid)
            for key in ('version', 'api', 'tests', 'dependencies', 'integration'):
                if not text(reuse.get(key)):
                    raise Blocked('Source review: OSS needs ' + key + ': ' + cid)
            if not isinstance(reuse.get('code_paths'), list) or not reuse['code_paths'] or not all(text(p) for p in reuse['code_paths']):
                raise Blocked('Source review: OSS needs reviewed code_paths: ' + cid)
            license = reuse.get('license', {})
            if not isinstance(license, dict) or not isinstance(license.get('status'), str) or license['status'] not in {'verified', 'unknown', 'incompatible'}:
                raise Blocked('Source review: license status is required: ' + cid)
            if license['status'] == 'verified' and any(not text(license.get(k)) for k in ('identifier', 'locator')):
                raise Blocked('Source review: verified license needs identifier and locator: ' + cid)
            if license['status'] != 'verified':
                reasons.append('OSSの利用条件が未確認または不適合')
            for sid in ids:
                access = state.get('sources', {}).get(sid, {})
                if access.get('status') not in {'local', 'retrieved'}:
                    reasons.append('OSSの原典にアクセスできていない: ' + sid)
                elif access.get('status') == 'retrieved' and (not access.get('original_path') or not access.get('original_sha256')):
                    reasons.append('OSSの確認対象の原文が保存されていない: ' + sid)
            if not isinstance(reuse.get('compatibility'), str) or reuse['compatibility'] not in {'verified', 'unknown', 'incompatible'}:
                raise Blocked('Source review: compatibility is required: ' + cid)
            if reuse['compatibility'] != 'verified' and not (for_trial and reuse['compatibility']=='unknown'):
                reasons.append('OSSの互換性が未確認または不適合')
        holds[cid] = reasons
    if (require_all and dossier['decision']['status'] in {'proposed', 'accepted'} and holds.get(selected)):
        raise Blocked('Source review: adoption must be provisional/deferred: ' + '; '.join(holds[selected]))
    return holds

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
