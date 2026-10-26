"""Report/publication invariants; fixture choices are not model-quality measurements."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_stages as fixtures
import harness as h
import runtime as rt
import report
import report_contract as contract
import report_document as document
import report_polish as polish
import test_bounded_pipeline as pipeline


def assessment(promising=True):
    return {'promising': promising, 'reason': 'Scope is a synthetic comparison fixture',
            'paper_reads': [], 'reuse': {'strategy': 'not_applicable', 'reason': 'No external code adopted'}}


class ReportTests(unittest.TestCase):
    def setUp(self):
        fixtures.StageTests.setUp(self)
        self.state.update(execution_contract_version=2, report_contract_version=1,
                          dossier=copy.deepcopy(self.draft), review=copy.deepcopy(self.review))
        self.state['config'].update(brief='既存方式を比較する', allow_network=False, test_commands=[])
        for c in self.state['dossier']['candidates']:
            c['source_review'] = assessment()
        self.state['dossier']['decision']['rationale'] = '同じ入力で候補を比較しました。効果は未測定です。'

    def finalization(self):
        self.state['report_finalization'] = {'target_status': 'research_complete',
                                             'science_sha256': document.substantive_signature(self.state)}

    def test_reader_order_preserves_results_and_moves_process_into_appendix(self):
        self.state['units'] = {'unit': {'id': 'unit', 'status': 'complete', 'required': True}}
        report.publish(self.state, self.workspace, self.run)
        text = (self.workspace/'report.md').read_text()
        self.assertLess(text.index('## 結論'), text.index('## 背景'))
        self.assertLess(text.index('## 候補の調査'), text.index('## 検証方法'))
        self.assertLess(text.index('## 限界'), text.index('### 保存した工程'))
        self.assertIn('主要効果は未測定', text)
        self.assertIn('synthetic design fixture', text)
        self.assertIn('### Aの採用方法', text)
        self.assertNotIn('## はじめて読む方へ', text)
        self.assertEqual(self.state['dossier'], json.loads((self.workspace/'.internal/evidence.json').read_text()))

    def test_old_report_layout_remains_unchanged(self):
        self.state.pop('report_contract_version')
        report.publish(self.state, self.workspace, self.run)
        text = (self.workspace/'report.md').read_text()
        self.assertIn('## 結論と確認してほしいこと', text)
        self.assertNotIn(document.APPENDIX, text)

    def test_audit_and_fix_reports_keep_actual_checks_without_inventing_research(self):
        self.state.pop('dossier'); self.state.pop('evaluation_contract_version')
        self.state['review']['dossier_json'] = ''
        for mode in ('audit', 'run'):
            self.state['config']['mode'] = mode
            report.publish(self.state, self.workspace, self.run)
            text = (self.workspace/'report.md').read_text()
            self.assertIn('synthetic design fixture', text)
            self.assertIn('unknown', text)
            self.assertNotIn('## 候補の調査', text)
            self.assertNotIn('## 推奨方式', text)
            self.assertIn('未確認 1件', text)
            self.assertNotIn('結論はまだ確定していません', text)

    def test_empty_claim_chapter_is_omitted_without_losing_actual_checks(self):
        report.publish(self.state, self.workspace, self.run)
        text = (self.workspace/'report.md').read_text()
        self.assertNotIn('### 主張と根拠', text)
        self.assertIn('synthetic design fixture', text)
        self.assertEqual(text.count('synthetic test'), 1)

    def test_proposed_method_figures_and_algorithm_remain_inside_adoption_chapter(self):
        raw = ['<!-- Generated -->', '# 研究報告書', '## 結論と確認してほしいこと',
               '## 提案手法', '### アルゴリズム', '```python', 'print(42)', '```',
               '![図](figures/overview.svg)', '## 実験設定・結果・根拠',
               '### 実験', '実行は未実施。', '## 残る確認と実行記録', '次の検証が必要。']
        text = '\n'.join(document.assemble(self.state, raw, self.workspace))
        start = text.index('## 推奨方式'); end = text.index('## 検証方法')
        self.assertIn('![図](figures/overview.svg)', text[start:end])
        self.assertIn('print(42)', text[start:end])
        self.assertIn('実行は未実施。', text[end:])

    def test_child_prompts_explicitly_receive_writing_and_reading_contract(self):
        for role in ['producer-reader', 'producer-method', 'producer-evidence', 'reviewer-dossier']:
            text = h.role_prompt(role, self.state, self.run/'child')
            self.assertIn('kotonoha', text)
            self.assertIn('references/reporting.md', text)
        text = h.role_prompt('producer-evidence', self.state, self.run/'child')
        self.assertIn('source_review', text)
        self.assertNotIn('kotonoha', h.role_prompt('producer-assets', self.state, self.run/'assets'))

    def test_self_contained_writing_entry_resolves_without_yomiyasu(self):
        import os
        skill=self.project/'.agents/skills/kotonoha'
        (skill/'scripts').mkdir(parents=True)
        (skill/'references').mkdir()
        (skill/'SKILL.md').write_text('Self-contained writing fixture')
        (skill/'scripts/writing_lint.py').write_text('# synthetic helper')
        (skill/'references/file-review.md').write_text('File review fixture')
        with patch.dict(os.environ,{'CODEX_HOME':str(self.project/'.empty-codex')}),patch.object(polish.Path,'home',return_value=self.project/'.empty-home'):
            entry=polish.resolve_entry(self.project)
        self.assertEqual(entry['name'],'kotonoha')
        self.assertEqual(entry['scripts'],str(skill/'scripts'))
        self.assertEqual({r['path'] for r in entry['files']},{str(skill/'SKILL.md'),str(skill/'references/file-review.md')})

    def paper(self, status='partial'):
        d = self.state['dossier']; d['decision']['candidate_id'] = 'B'
        d['sources'] = [{'id': 'PAPER', 'title': 'Fixture paper', 'source_type': 'paper', 'read_level': 'full_text'}]
        d['claims'] = [{'id': 'C1', 'evidence': [{'source_id': 'PAPER', 'relation': 'supports'}]}]
        d['comparison'][1]['claim_ids'] = ['C1']
        read = {'source_id': 'PAPER', 'status': status, 'sections': [],
                'missing': ['本文の結果と限界'], 'supplementary': '未確認'}
        d['candidates'][1]['source_review']['paper_reads'] = [read]
        return d, read

    def test_partial_paper_defers_only_affected_candidate(self):
        d, _ = self.paper()
        holds = contract.assess(d, self.state)
        self.assertTrue(holds['B']); self.assertFalse(holds['A'])
        d['decision']['status'] = 'proposed'
        with self.assertRaisesRegex(rt.Blocked, 'provisional/deferred'):
            contract.assess(d, self.state)
        d['decision'].update(status='provisional', candidate_id='A')
        self.assertTrue(contract.assess(d, self.state)['B'])

    def test_complete_reading_cannot_be_claimed_without_access_and_coverage(self):
        d, read = self.paper('complete')
        with self.assertRaisesRegex(rt.Blocked, 'full reading needs'):
            contract.assess(d, self.state)

        read.update(sections=[{'section': '本文', 'locator': 'pp.1-4', 'summary': 'Fixture mechanism and limitations'}],
                    missing=[], supplementary='この短い文献には補遺がないことを確認した')
        self.state['sources']['PAPER'] = {'status': 'retrieved', 'evidence_id': 'EV', 'original_sha256': 'fixture-content-hash'}
        self.state['evidence']['EV'] = {'sha256': 'fixture-access-hash'}
        with self.assertRaisesRegex(rt.Blocked, 'full reading needs'):
            contract.assess(d, self.state)
        self.state['sources']['PAPER']['original_path'] = 'runs/fixture/sources/paper.body'
        self.assertFalse(contract.assess(d, self.state)['B'])
        d['sources'][0]['read_level'] = 'abstract'
        with self.assertRaisesRegex(rt.Blocked, 'full reading needs'):
            contract.assess(d, self.state)

    def test_candidate_format_precedes_parent_access_but_final_review_requires_it(self):
        d, read = self.paper('complete')
        read.update(sections=[{'section': '本文', 'locator': 'pp.1-4', 'summary': 'Synthetic full-text reading'}],
                    missing=[], supplementary='No supplement exists in this synthetic fixture')
        self.assertFalse(contract.assess(d, self.state, require_all=False, verify_access=False)['B'])
        with self.assertRaisesRegex(rt.Blocked, 'full reading needs'):
            contract.assess(d, self.state)
        read['sections'] = []
        with self.assertRaisesRegex(rt.Blocked, 'full reading needs'):
            contract.assess(d, self.state, require_all=False, verify_access=False)

    def test_direct_oss_reuse_needs_version_code_license_and_compatibility(self):
        d = self.state['dossier']; d['decision']['candidate_id'] = 'B'
        d['sources'] = [{'id': 'OSS', 'source_type': 'repository'}]
        reuse = {'strategy': 'direct', 'reason': '既存のAPIで要件を満たす', 'source_ids': ['OSS'],
                 'version': 'fixture-ref', 'code_paths': ['lib.py', 'test_lib.py'], 'api': 'call(input)',
                 'tests': 'テストを読んだ。未実行', 'dependencies': 'Python標準ライブラリ',
                 'integration': '対象処理からcallを呼ぶ', 'license': {'status': 'unknown'},
                 'compatibility': 'unknown'}
        d['candidates'][1]['source_review']['reuse'] = reuse
        self.assertGreaterEqual(len(contract.assess(d, self.state)['B']), 2)
        self.state['sources']['OSS'] = {'status': 'retrieved', 'original_path': 'runs/fixture/sources/code.body',
                                        'original_sha256': 'fixture-code-hash'}
        reuse.update(license={'status': 'verified', 'identifier': 'fixture license', 'locator': 'LICENSE'},
                     compatibility='verified')
        self.assertFalse(contract.assess(d, self.state)['B'])
        reuse.pop('version')
        with self.assertRaisesRegex(rt.Blocked, 'version'):
            contract.assess(d, self.state)

    def test_malformed_nested_assessment_is_repairable_not_a_python_type_error(self):
        for bad in [None, {}, [], 0]:
            d = copy.deepcopy(self.state['dossier'])
            d['candidates'][0]['source_review']['reuse']['strategy'] = bad
            with self.assertRaises(rt.Blocked): contract.assess(d, self.state)

    def test_source_original_is_private_hashed_and_mutation_is_detected(self):
        import evidence
        import io
        response = io.BytesIO(b'Entire synthetic primary source. Not an actual paper.')
        response.geturl = lambda: 'https://example.org/paper'
        response.headers = {'Content-Type': 'text/plain'}
        opener = unittest.mock.Mock(); opener.open.return_value = response
        source = {'id': 'PAPER', 'title': 'Synthetic source', 'url': 'https://example.org/paper',
                  'locator': 'entire text', 'read_level': 'full_text'}
        dest = self.run/'sources/source.json'
        with patch.object(evidence, 'public_url'), patch.object(evidence.urllib.request, 'build_opener', return_value=opener):
            receipt = evidence.source_receipt(source, dest, True, archive_body=True)
        original = dest.with_suffix('.body')
        self.assertEqual(receipt['original_sha256'], rt.sha256(original))
        self.state['sources']['PAPER'] = {**receipt, 'original_path': original.relative_to(self.workspace).as_posix()}
        evidence.assert_records(self.state, self.workspace)
        original.write_text('altered')
        with self.assertRaisesRegex(rt.Blocked, 'original changed'):
            evidence.assert_records(self.state, self.workspace)

    def test_narrative_patch_cannot_change_facts_links_ids_or_structure(self):
        original = '方式Aの正解率は82%、方式Bは86%です。[S1](source.md)を参照します。'
        task = {'body': original, 'base_sha256': document.body_hash(original),
                'editable_blocks': document.editable_blocks(original)}
        value = {'base_sha256': task['base_sha256'], 'replacements': [{'id': 'P1', 'text': original}]}
        self.assertEqual(polish.apply_patch(value, task, self.state), original)
        for bad in [original.replace('82', '86').replace('86%です', '82%です'),
                    original.replace('source.md', 'other.md'), '## 新しい結論\n' + original]:
            value['replacements'][0]['text'] = bad
            with self.assertRaises(rt.Blocked): polish.apply_patch(value, task, self.state)
        value['base_sha256'] = 'stale'
        with self.assertRaisesRegex(rt.Blocked, 'stale'): polish.apply_patch(value, task, self.state)

    def entry(self):
        return {'name': 'kotonoha', 'path': '/fixture/SKILL.md', 'files': [],
                'runtime': str(self.project/'absent-settings'), 'scripts': str(self.project/'absent-scripts')}

    def invoke(self, calls, fail_review=False, refuse=False):
        def run(role, schema, state, workspace, run_dir, validator=None):
            calls.append(role); task = state['report_task']
            if role == 'report-writer':
                result = {'status': 'proposed', 'reason': 'fixture whole-document edit',
                          'base_sha256': task['base_sha256'], 'replacements': []}
            else:
                if fail_review and calls.count(role) == 1: raise rt.Blocked('fixture timeout')
                result = {'status': 'reviewed', 'reason': 'fixture comparison', 'base_sha256': task['base_sha256'],
                          'accepted': not refuse, 'issues': ['確信度が変わった'] if refuse else []}
            h.validate_shape(result, schema)
            if validator: validator(result, state)
            return result
        return run

    def test_missing_writing_skill_completes_with_visible_notice(self):
        self.finalization()
        with patch.object(polish, 'resolve_entry', return_value=None):
            polish.finish(self.state, self.workspace, self.run, self.invoke([]))
        report.publish(self.state, self.workspace, self.run)
        self.assertEqual(self.state['report_polish']['status'], 'skipped_unavailable')
        self.assertIn('未実施（kotonoha・yomiyasu未導入）', (self.workspace/'report.md').read_text())

    def test_semantic_rejection_is_not_overruled_by_matching_tokens(self):
        self.finalization(); calls = []
        with patch.object(polish, 'resolve_entry', return_value=self.entry()):
            with self.assertRaisesRegex(rt.Blocked, 'one repair'):
                polish.finish(self.state, self.workspace, self.run, self.invoke(calls, refuse=True))
        self.assertEqual(calls.count('report-writer'), 2)
        self.assertEqual(self.state['report_polish']['status'], 'rejected')

    def test_resume_reuses_writer_and_final_text_is_bound_to_evidence_and_artifacts(self):
        self.finalization(); calls = []; before = copy.deepcopy(self.state['dossier'])
        with patch.object(polish, 'resolve_entry', return_value=self.entry()):
            with self.assertRaisesRegex(rt.Blocked, 'timeout'):
                polish.finish(self.state, self.workspace, self.run, self.invoke(calls, fail_review=True))
            polish.finish(self.state, self.workspace, self.run, self.invoke(calls))
        self.assertEqual(calls.count('report-writer'), 1)
        self.assertEqual(self.state['dossier'], before)
        report.publish(self.state, self.workspace, self.run)
        self.assertNotIn('草稿：文章の最終確認', (self.workspace/'report.md').read_text())
        rationale = self.state['dossier']['decision']['rationale']
        self.state['dossier']['decision']['rationale'] = 'altered scientific result'
        with self.assertRaisesRegex(rt.Blocked, 'reviewed evidence'):
            report.publish(self.state, self.workspace, self.run)
        self.state['dossier']['decision']['rationale'] = rationale
        artifact = self.workspace/self.state['report_polish']['artifacts']['after']
        artifact.write_text('tampered')
        with self.assertRaisesRegex(rt.Blocked, 'artifact changed'):
            report.publish(self.state, self.workspace, self.run)

    def test_code_and_tables_are_never_editable_blocks(self):
        text = '```python\nprint(1)\n```\n\n文章を整えます。\n\n| 表 |\n|---|\n| 値 |'
        self.assertEqual([b['text'] for b in document.editable_blocks(text)], ['文章を整えます。'])

    def test_full_pipeline_finalizes_without_reexecuting_scientific_work_on_resume(self):
        case = pipeline.BoundedPipelineTests(); case.setUp(); self.addCleanup(case.doCleanups)
        case.state['report_contract_version'] = 1
        case.state['config']['brief'] = '既存方式と候補の比較'
        for c in case.draft['candidates']: c['source_review'] = assessment()
        case.design['dossier_json'] = json.dumps(case.draft)
        original = case.workspace/'synthetic-paper.txt'
        original.write_text('Entire synthetic primary source; no real research finding.')
        descriptor = {'id': 'NEWPAPER', 'title': 'Synthetic paper', 'url': '',
                      'path': 'synthetic-paper.txt', 'locator': 'entire text', 'read_level': 'full_text'}
        seen = []
        def replies(role, state):
            if role.startswith('report-'):
                if role == 'report-reviewer' and seen.count('report-reviewer') == 0:
                    seen.append(role); raise rt.Blocked('finalization interrupted')
                seen.append(role); task = state['report_task']
                if role == 'report-writer':
                    return {'status': 'proposed', 'reason': 'fixture edit', 'base_sha256': task['base_sha256'], 'replacements': []}
                return {'status': 'reviewed', 'reason': 'fixture review', 'base_sha256': task['base_sha256'],
                        'accepted': True, 'issues': []}
            value = case.default_reply(role, state)
            if role == 'producer-evidence' and state['unit_task']['candidate_id'] == 'B':
                # A newly discovered original is first registered after this
                # candidate's format gate, before the final access check.
                patch_value = json.loads(value['patch_json'])
                patch_value['sources'] = [{'id': 'NEWPAPER', 'title': descriptor['title'], 'source_type': 'paper',
                    'local_path': descriptor['path'], 'read_level': 'full_text', 'peer_review_status': 'unverified',
                    'retrieved_at': '2026-10-21', 'study_id': 'synthetic-fixture', 'correction_status': 'not_checked'}]
                patch_value['candidate']['source_review']['paper_reads'] = [{'source_id': 'NEWPAPER',
                    'status': 'complete', 'sections': [{'section': 'entire text', 'locator': 'line 1',
                    'summary': 'Synthetic source only'}], 'missing': [], 'supplementary': 'No supplement in fixture'}]
                value.update(patch_json=json.dumps(patch_value), sources=[descriptor])
            return value
        with patch.object(polish, 'resolve_entry', return_value=self.entry()):
            with self.assertRaisesRegex(rt.Blocked, 'interrupted'): case.drive(replies)
            scientific_calls = [x for x in case.calls if not x[1].startswith('report-')]
            case.drive(replies)
        self.assertEqual([x for x in case.calls if not x[1].startswith('report-')], scientific_calls)
        self.assertEqual(case.state['status'], 'research_complete')
        self.assertEqual(seen.count('report-writer'), 1)
        self.assertEqual(case.state['report_polish']['status'], 'complete')
        self.assertEqual(case.state['sources']['NEWPAPER']['status'], 'local')

    def test_export_requires_the_final_writing_artifacts(self):
        self.finalization()
        with patch.object(polish, 'resolve_entry', return_value=self.entry()):
            polish.finish(self.state, self.workspace, self.run, self.invoke([]))
        self.state.update(status='research_complete', schema_version=1)
        private = self.run/'sources/private.body'; private.parent.mkdir(exist_ok=True); private.write_bytes(b'private original')
        self.state['sources']['PRIVATE'] = {'original_path': private.relative_to(self.workspace).as_posix(),
                                           'original_sha256': rt.sha256(private)}
        report.publish(self.state, self.workspace, self.run)
        rt.atomic_json(self.run/'state.json', self.state)
        from published_evidence import closure
        _, _, files = closure(self.workspace, self.state['run_id'])
        self.assertNotIn(private.relative_to(self.workspace).as_posix(), files)
        for rel in self.state['report_polish']['artifacts'].values(): self.assertIn(rel, files)
        from published_evidence import export, verify
        import shutil
        result = export(self.project, 'demo', self.state['run_id'], True)
        clone = self.project.parent/'clone'; shutil.copytree(self.project/'docs', clone/'docs')
        verified = verify(clone/result['package'])
        for rel in self.state['report_polish']['artifacts'].values(): self.assertIn(rel, verified['files'])
        (self.workspace/self.state['report_polish']['artifacts']['before']).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            closure(self.workspace, self.state['run_id'])


if __name__ == '__main__': unittest.main()
