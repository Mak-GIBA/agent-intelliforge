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
        return {'status': 'proposed', 'reason': 'synthetic fixture', 'evidence_sha256': c.digest(pack),
                'title': '比較方式の設計調査', 'abstract': block,
                'sections': [{'heading': h, 'blocks': [copy.deepcopy(block)]} for h in c.HEADINGS]}

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
