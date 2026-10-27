"""Contract-2 invariants; synthetic prose does not measure model writing quality."""
import copy
import json
import unittest
from unittest.mock import patch

import test_stages as fixtures
import report_composition as c
import report_document as legacy
import report_polish
import report
import runtime as rt


class CompositionTests(unittest.TestCase):
    def setUp(self):
        fixtures.StageTests.setUp(self)
        self.state.update(report_contract_version=2, execution_contract_version=2,
                          dossier=copy.deepcopy(self.draft), review=copy.deepcopy(self.review))
        self.state['config'].update(brief='比較方式を検討する', allow_network=False, test_commands=[])
        self.state['report_finalization'] = {'target_status': 'research_complete',
                                           'science_sha256': legacy.substantive_signature(self.state)}
        self.pack = c.evidence_pack(self.state, '# 比較\n\n効果は未測定。\n')
        self.calls = []

    def candidate(self, pack=None):
        pack = pack or self.pack
        block = {'text': '効果は未測定であり、採用は保留する。', 'evidence_ids': ['dossier.decision'], 'asset_ids': []}
        value = {'status': 'proposed', 'reason': 'synthetic fixture', 'evidence_sha256': c.digest(pack),
                'title': '比較方式の設計調査', 'abstract': block,
                'sections': [{'heading': h, 'blocks': [copy.deepcopy(block)]} for h in c.HEADINGS]}
        value['sections'][1]['blocks'][0]['asset_ids'] = [a['id'] for a in pack['assets'] if a.get('required')]
        return value

    def invoke(self, role, schema, state, workspace, run_dir, validator):
        self.calls.append(role)
        task = state['report_task']
        if role == 'report-writer':
            pack = json.loads(__import__('pathlib').Path(task['evidence_file']['path']).read_text())
            value = self.candidate(pack)
        else:
            value = {'status': 'reviewed', 'reason': 'synthetic reader',
                     'evidence_sha256': task['evidence_sha256'], 'candidate_sha256': task['candidate_sha256'],
                     'accepted': True, 'issues': [], 'checks': {k: True for k in c.REVIEW['properties']['checks']['properties']}}
        validator(value, state)
        return value

    def finish(self, invoke=None):
        with patch.object(c, 'selected_entry', return_value=None):
            report_polish.finish(self.state, self.workspace, self.run, invoke or self.invoke)

    def test_full_structure_and_paragraphs_are_editable(self):
        value = self.candidate()
        value['sections'].reverse()
        value['sections'][0]['blocks'] *= 2
        c.validate_document(value, self.pack)
        self.assertIn('## '+c.HEADINGS[-1], c.render_document(value, self.pack))

    def test_wrong_denominator_and_unknown_support_rejected(self):
        for text, support in [('効果は99.9%である。', ['dossier.decision']),
                              ('効果は未測定。', ['unknown'])]:
            value = self.candidate(); value['abstract'].update(text=text, evidence_ids=support)
            with self.assertRaises(rt.Blocked): c.validate_document(value, self.pack)

    def test_existing_number_must_belong_to_the_cited_record(self):
        self.pack['records'].append({'id': 'other', 'value': {'denominator': 40}})
        value = self.candidate(); value['abstract']['text'] = '40件を比較した。'
        with self.assertRaisesRegex(rt.Blocked, 'denominator'): c.validate_document(value, self.pack)

    def test_semantic_review_cannot_accept_failed_scope_or_support(self):
        value = {'status': 'reviewed', 'reason': '', 'evidence_sha256': 'pack', 'candidate_sha256': 'candidate',
                 'accepted': True, 'issues': [], 'checks': {k: True for k in c.REVIEW['properties']['checks']['properties']}}
        for check in ('support', 'results', 'adoption', 'limits'):
            bad = copy.deepcopy(value); bad['checks'][check] = False
            with self.assertRaisesRegex(rt.Blocked, 'contradictory'): c.check_review(bad, 'pack', 'candidate')
        value['candidate_sha256'] = 'other'
        with self.assertRaisesRegex(rt.Blocked, 'stale'): c.check_review(value, 'pack', 'candidate')

    def test_missing_style_still_composes_and_preserves_science(self):
        before = legacy.substantive_signature(self.state)
        self.finish()
        self.assertEqual(self.calls, ['report-writer', 'report-reviewer'])
        self.assertEqual(self.state['report_polish']['status'], 'complete')
        report.publish(self.state, self.workspace, self.run)
        text = (self.workspace/'report.md').read_text()
        self.assertIn('## 要旨', text); self.assertIn('文章Skill: 未適用', text)
        self.assertEqual(before, legacy.substantive_signature(self.state))
        self.finish(lambda *a: self.fail('completed composition called a model'))

    def test_resume_only_retries_incomplete_reader(self):
        def timeout(role, *args):
            if role == 'report-reviewer': raise rt.Blocked('synthetic timeout')
            return self.invoke(role, *args)
        with self.assertRaises(rt.Blocked): self.finish(timeout)
        self.finish()
        self.assertEqual(self.calls.count('report-writer'), 1)
        self.assertEqual(self.state['report_polish']['status'], 'complete')

    def test_negative_or_unmeasured_overclaim_needs_repair_not_new_research(self):
        def reject(role, *args):
            v = self.invoke(role, *args)
            if role == 'report-reviewer':
                v.update(accepted=False, issues=['未測定の効果から優位性を主張しない'])
                v['checks']['results'] = False
            return v
        with self.assertRaisesRegex(rt.Blocked, 'one repair'): self.finish(reject)
        self.assertEqual(self.calls, ['report-writer', 'report-reviewer']*2)
        self.assertEqual(self.state['report_polish']['status'], 'rejected')

    def test_explicit_resume_after_rejection_keeps_prior_candidates_and_science(self):
        before = legacy.substantive_signature(self.state)
        def reject(role, *args):
            value = self.invoke(role, *args)
            if role == 'report-reviewer': value.update(accepted=False, issues=['説明が不足'])
            return value
        with self.assertRaises(rt.Blocked): self.finish(reject)
        previous = {p.name: p.read_bytes() for p in (self.run/'composition-v2').glob('candidate-*.md')}
        self.finish()
        self.assertEqual(self.state['report_polish']['cycle'], 1)
        for name, raw in previous.items(): self.assertEqual(raw, (self.run/'composition-v2'/name).read_bytes())
        self.assertEqual(before, legacy.substantive_signature(self.state))

    def test_immutable_approval_evidence_and_snapshot(self):
        for target in ('after', 'evidence', 'before'):
            with self.subTest(target=target):
                if self.state.get('report_polish', {}).get('status') != 'complete': self.finish()
                pol = self.state['report_polish']; p = self.workspace/pol['artifacts'][target]
                original = p.read_bytes(); p.write_text('changed')
                with self.assertRaises(rt.Blocked): c.assert_artifacts(self.state, self.workspace)
                p.write_bytes(original)
        self.state['report_polish']['approved_document'] += 'new text'
        with self.assertRaises(rt.Blocked): report.publish(self.state, self.workspace, self.run)

    def test_input_report_cannot_be_publication_target(self):
        self.state['sources']['BAD'] = {'original_path': str(self.workspace/'report.md')}
        with self.assertRaisesRegex(rt.Blocked, 'frozen source'): self.finish()
        self.assertFalse((self.run/'composition-v2').exists())
        before = (self.workspace/'report.md').read_bytes() if (self.workspace/'report.md').exists() else None
        with self.assertRaisesRegex(rt.Blocked, 'frozen source'):
            report.publish(self.state, self.workspace, self.run)
        after = (self.workspace/'report.md').read_bytes() if (self.workspace/'report.md').exists() else None
        self.assertEqual(before, after)

    def test_difference_has_explicit_units_and_rounding(self):
        d = c.difference('65.1', '52.7')
        self.assertEqual(d['value'], '12.4'); self.assertEqual(d['unit'], 'percentage points')
        self.assertEqual(c.difference('1.05', '0', places=1)['value'], '1.1')

    def test_v2_prompt_passes_pack_once_without_duplicate_dossier(self):
        from execution_units import select_inputs
        self.state['report_task'] = {'evidence_file': {'path': 'snapshot', 'sha256': 'hash'}}
        inputs = select_inputs('report-writer', self.state)
        self.assertNotIn('dossier', inputs); self.assertNotIn('review', inputs)
        self.assertIn('report_task', inputs)

    def test_export_restores_frozen_writing_and_root_links(self):
        from pathlib import Path
        style = self.project/'example-style'; (style/'references').mkdir(parents=True)
        (style/'SKILL.md').write_text('Read references/guide.md')
        (style/'references/guide.md').write_text('Synthetic writing guide')
        entry = {'name': 'kotonoha', 'path': str(style/'SKILL.md'),
                 'files': [{'path': str(style/'SKILL.md'), 'sha256': rt.sha256(style/'SKILL.md')}],
                 'scripts': str(style/'scripts'), 'runtime': str(style/'missing.json')}
        with patch.object(c, 'selected_entry', return_value=entry), patch.object(report_polish, 'lint', return_value={'status':'unavailable'}):
            report_polish.finish(self.state, self.workspace, self.run, self.invoke)
        self.state.update(status='research_complete', schema_version=1)
        report.publish(self.state, self.workspace, self.run)
        rt.atomic_json(self.run/'state.json', self.state)
        from published_evidence import closure, export, verify
        _, _, files = closure(self.workspace, self.state['run_id'])
        self.assertTrue(any(n.endswith('writing-skill/references/guide.md') for n in files))
        self.assertTrue(any(n.endswith('composition-v2/evidence.json') for n in files))
        result = export(self.project, 'demo', self.state['run_id'], True)
        import shutil
        clone = self.project.parent/'clone'; shutil.copytree(self.project/'docs', clone/'docs')
        verified = verify(clone/result['package'])
        self.assertEqual(set(files), set(verified['files']))
        # The same verifier ships in Upstream without Design Research imports.
        import subprocess, sys
        import published_evidence
        code = ('import importlib.util; '
                's=importlib.util.spec_from_file_location("standalone", '+repr(published_evidence.__file__)+'); '
                'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                'm.verify('+repr(str(clone/result['package']))+')')
        checked = subprocess.run([sys.executable, '-I', '-B', '-c', code], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)

        frozen = next(__import__('pathlib').Path(p) for p in self.state['unit_inputs'] if p.endswith('writing-skill/references/guide.md'))
        frozen.write_text('changed style input')
        with self.assertRaisesRegex(rt.Blocked, 'input changed'):
            c.assert_artifacts(self.state, self.workspace)

    def diagram_fixture(self):
        from readable_report import figure_lines
        figures = []
        for fid, kind in [('F1', 'overview'), ('F2', 'detail')]:
            f = {'id': fid, 'kind': kind, 'title': fid+'の処理', 'caption': '入力から出力への処理の流れ。実測結果を示さない。',
                 'reading_guide': '矢印は渡す情報を表す。', 'alt': '入力から処理を経て出力へ渡す。',
                 'nodes': [{'id': 'Input', 'label': '入力'}, {'id': 'Core', 'label': '処理'}],
                 'edges': [{'from': 'Input', 'to': 'Core', 'label': '入力データ'}]}
            if kind == 'detail': f.update(parent_figure='F1', expanded_component='Core')
            figures.append(f)
        self.state['config']['reader_friendly'] = True
        self.state['report_diagram_contract_version'] = 1
        self.state['dossier']['reader_guide'] = {'diagram_source': 'reader-guide', 'figures': figures}
        reference = '# 比較\n\n'+'\n'.join(line for i,f in enumerate(figures,1) for line in figure_lines(f,i,direction='TD' if f['kind']=='detail' else 'LR'))
        return figures, reference

    def test_diagram_and_explanations_are_one_required_asset(self):
        figures, reference = self.diagram_fixture()
        pack = c.evidence_pack(self.state, reference)
        self.assertEqual(len(pack['assets']), 2)
        self.assertEqual([a['figure_id'] for a in pack['assets']], ['F1', 'F2'])
        self.assertIn('flowchart LR', pack['assets'][0]['text'])
        self.assertIn('flowchart TD', pack['assets'][1]['text'])
        text = c.render_document(self.candidate(pack), pack)
        for a,f in zip(pack['assets'], figures):
            self.assertIn(f['caption'], a['text']); self.assertIn(f['reading_guide'], a['text'])
            self.assertIn(f['alt'], a['text']); self.assertEqual(text.count(a['text']),1)
        self.assertLess(text.index('```mermaid'), text.index('## 結果'))

    def test_required_diagram_cannot_be_omitted_duplicated_or_put_in_abstract(self):
        _, reference = self.diagram_fixture(); pack = c.evidence_pack(self.state, reference)
        for change in ('omit', 'duplicate', 'abstract'):
            value = self.candidate(pack)
            ids = value['sections'][1]['blocks'][0]['asset_ids']
            if change == 'omit': ids.pop()
            elif change == 'duplicate': ids.append(ids[0])
            else: value['abstract']['asset_ids'] = ids[:]
            with self.subTest(change=change), self.assertRaisesRegex(rt.Blocked, 'diagram'):
                c.validate_document(value, pack)

    def test_missing_caption_or_figure_is_rejected_before_freezing(self):
        figures, reference = self.diagram_fixture()
        reference = reference.replace(figures[0]['caption'], '', 1)
        with self.assertRaisesRegex(rt.Blocked, 'explanation missing'):
            c.evidence_pack(self.state, reference)

    def test_saved_v2_without_flag_keeps_identical_asset_representation(self):
        _, reference = self.diagram_fixture()
        for flag in (None, 0):
            self.state['report_diagram_contract_version'] = flag
            pack = c.evidence_pack(self.state, reference)
            self.assertNotIn('diagram_contract_version', pack)
            self.assertEqual(pack['assets'], c.extract_assets(reference))
            self.assertTrue(all(set(a)=={'id','text'} for a in pack['assets']))
            c.validate_document(self.candidate(pack), pack)

    def test_legacy_diagram_direction_stays_horizontal(self):
        import readable_report
        _, reference = self.diagram_fixture()
        guide = self.state['dossier']['reader_guide']
        guide.update(purpose='synthetic purpose', scope='synthetic scope', takeaway='unmeasured',
                     walkthrough='synthetic example', glossary='synthetic terms', limitations='unmeasured')
        with patch.object(readable_report, 'quality_issues', return_value=[]):
            self.state.pop('report_diagram_contract_version')
            previous = '\n'.join(readable_report.sections(self.state))
            self.state['report_diagram_contract_version'] = 1
            current = '\n'.join(readable_report.sections(self.state))
        self.assertEqual(previous.count('flowchart LR'), 2)
        self.assertNotIn('flowchart TD', previous)
        self.assertEqual(current.count('flowchart LR'), 1)
        self.assertEqual(current.count('flowchart TD'), 1)

    def test_new_contract_does_not_invent_diagrams_for_audit(self):
        self.state['report_diagram_contract_version'] = 1
        self.state['config'].update(mode='audit', reader_friendly=True)
        pack = c.evidence_pack(self.state, '# 検証\n\n実施済みの確認のみ。')
        self.assertEqual(pack['assets'], [])
        c.validate_document(self.candidate(pack), pack)

    def test_proposed_method_svg_retains_caption_explanation_and_editable_source(self):
        from test_narrow_method_scope import fixture
        import proposal_report
        self.state['dossier'] = fixture()
        self.state['config'].update(reader_friendly=True, report_profile='proposed-method')
        self.state['report_diagram_contract_version'] = 1
        self.state['dossier']['reader_guide'] = {'diagram_source':'proposed-method','figures':[]}
        reference = '\n'.join(proposal_report.render_chapter(self.state['dossier'], self.workspace, self.run/'figures'))
        pack = c.evidence_pack(self.state, reference)
        diagrams = [a for a in pack['assets'] if a.get('required')]
        self.assertEqual(len(diagrams), 3)
        for a in diagrams:
            self.assertIn('.svg)', a['text']); self.assertIn('.json)', a['text'])
            self.assertIn('**図', a['text'])
        c.validate_document(self.candidate(pack), pack)
        self.state['report_finalization']['science_sha256'] = legacy.substantive_signature(self.state)
        self.finish()
        self.state.update(status='research_complete', schema_version=1)
        report.publish(self.state, self.workspace, self.run)
        rt.atomic_json(self.run/'state.json', self.state)
        from published_evidence import closure
        _, _, files = closure(self.workspace, self.state['run_id'])
        self.assertTrue(any(n.endswith('.svg') for n in files))
        self.assertTrue(any(n.endswith('.json') and 'figures/' in n for n in files))

    def test_legacy_paragraph_flow_remains_separate(self):
        self.state['report_contract_version'] = 1
        with patch.object(report_polish, 'resolve_entry', return_value=None):
            report_polish.finish(self.state, self.workspace, self.run, self.invoke)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.state['report_polish']['status'], 'skipped_unavailable')
        for version in (None, 0):
            self.state['report_contract_version'] = version
            report.publish(self.state, self.workspace, self.run)
            self.assertIn('## 結論と確認してほしいこと', (self.workspace/'report.md').read_text())


if __name__ == '__main__': unittest.main()
