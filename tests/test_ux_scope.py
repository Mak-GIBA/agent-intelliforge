"""Focused checks must declare their limits without weakening full review."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(os.environ.get('UX_SCOPE_SOURCE', Path(__file__).resolve().parents[1] /
                             'tools/codex-ux-stack/skill/scripts/harness.py'))
spec = importlib.util.spec_from_file_location('ux_scope', SOURCE)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class ScopeTests(unittest.TestCase):
    def audit(self):
        return {'issues': [], 'friction': [], 'simplicity': {'regressed': False},
                'second_pass_complete': True,
                'coverage': [{'flow_id': 'save', 'viewport': viewport, 'state': 'normal',
                              'perspective': perspective, 'result': 'passed'}
                             for viewport, perspective in [('desktop', 'first_time'),
                                                           ('mobile', 'first_time'),
                                                           ('desktop', 'mistake')]]}

    def test_focused_parser_requires_explicit_scope_before_execution(self):
        args = h.parser().parse_args(['audit', '--url', 'http://localhost',
                                      '--profile', 'focused', '--focus', '表示名の保存'])
        self.assertEqual(args.profile, 'focused')
        self.assertEqual(args.focus, ['表示名の保存'])

    def test_focused_gate_uses_declared_viewports_and_no_external_comparison(self):
        plan = {'flows': [{'id': 'save', 'required': True, 'states': []}]}
        config = {'profile': 'focused', 'focus': ['表示名の保存'],
                  'viewports': ['desktop', 'mobile'], 'reference_urls': []}
        reasons = h.gate(self.audit(), plan, {'status': 'not_required'}, [{'passed': True}], config)
        self.assertEqual(reasons, [])

    def test_missing_profile_keeps_all_full_requirements(self):
        plan = {'flows': [{'id': 'save', 'required': True, 'states': []}]}
        reasons = h.gate(self.audit(), plan, {'status': 'not_required'}, [{'passed': True}])
        self.assertTrue(any('tablet' in x for x in reasons))
        self.assertIn('Reference comparison incomplete', reasons)
        self.assertIn('Second pass / four perspectives incomplete', reasons)

    def test_focused_cannot_skip_requested_references_or_major_issues(self):
        plan = {'flows': [{'id': 'save', 'required': True, 'states': []}]}
        config = {'profile': 'focused', 'focus': ['save'], 'viewports': ['desktop'], 'reference_urls': ['https://example.org']}
        audit = self.audit();audit['issues'] = [{'severity': 'High', 'status': 'open'}]
        reasons = h.gate(audit, plan, {'status': 'not_required'}, [{'passed': True}], config)
        self.assertIn('Critical/High issues remain', reasons)
        self.assertIn('Reference comparison incomplete', reasons)

    def test_role_prompt_contains_scope_and_evidence_copying_instructions(self):
        state = {'config': {'project': '/tmp/app', 'url': 'http://localhost',
                            'brief': '保存', 'reference_urls': [], 'profile': 'focused',
                            'focus': ['表示名'], 'viewports': ['mobile']},
                 'backend': 'local-playwright', 'fallback_reason': '', 'rules': []}
        with tempfile.TemporaryDirectory() as directory:
            prompt = h.role_prompt('reviewer', state, Path(directory))
        data = json.loads(prompt.split('\nINPUT:\n', 1)[1])
        self.assertEqual(data['review_scope']['viewports'], ['mobile'])
        self.assertNotIn('tablet 768x1024', prompt)
        self.assertIn('receipt', prompt)
        self.assertNotIn('cover the app, then revisit', prompt)

    def test_invalid_persisted_scope_is_not_silently_treated_as_full(self):
        for config in ({'profile':'focused'}, {'profile':'focused','focus':'save'},
                       {'profile':'unknown'}, {'viewports':['desktop']}):
            with self.subTest(config=config), self.assertRaises(h.Blocked):
                h.review_scope(config)

    def test_reference_role_keeps_external_pages_view_only(self):
        state={'config':{'project':'/tmp/app','url':'http://localhost','brief':'test','reference_urls':[]},
               'backend':'local-playwright','fallback_reason':'','rules':[]}
        with tempfile.TemporaryDirectory() as directory:
            prompt=h.role_prompt('references',state,Path(directory))
        self.assertNotIn('operate Tab/Enter/Escape',prompt)


if __name__ == '__main__':
    unittest.main()
