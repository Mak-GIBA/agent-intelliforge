"""Check evaluation integrity; these tests do not score writing quality."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    p=ROOT/'evals'/name
    source=p.read_text(encoding="utf-8") if p.is_file() else A['evals/'+name].decode()
    module=types.ModuleType(name.removesuffix('.py'));module.__file__=str(p)
    exec(compile(source,str(p),'exec'),module.__dict__);return module

B=load('run_study.py')
with mock.patch.dict(sys.modules, {'run_study':B}):
    E=load('explanation_study.py')
with mock.patch.dict(sys.modules, {'run_study':B, 'explanation_study':E}):
    N=load('explanation_native.py')

class ExplanationEvidenceTests(unittest.TestCase):
    def rating(self, label='O001'):
        return dict(id=label,**{a:4 for a in E.AXES},meaning_errors=[],requester_residue=[],reason='素材の条件を保持。')
    def test_duplicate_and_missing_anonymous_scores_are_rejected(self):
        with self.assertRaises(ValueError):E.validate_ratings([self.rating(),self.rating()],['O001','O002'])
        with self.assertRaises(ValueError):E.validate_ratings([self.rating()],['O001','O002'])
    def test_invalid_scores_and_missing_rationale_are_rejected(self):
        row=self.rating();row['specificity']=True
        with self.assertRaises(ValueError):E.validate_ratings([row],['O001'])
        row=self.rating();row['reason']=''
        with self.assertRaises(ValueError):E.validate_ratings([row],['O001'])
    def test_critical_findings_are_not_lost_in_mean_scores(self):
        row=self.rating();row['meaning_errors']=['原因を捏造']
        E.validate_ratings([row],['O001']);self.assertTrue(row['meaning_errors'])
    def test_blind_grader_receives_material_but_no_arm_or_guide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'writing').mkdir()
            B.save(root/'writing/private-improved.json',{'task':'E01','arm':'improved','output':'完成した文章'})
            c={'tasks':[{'id':'E01','instruction':'自然な説明に','input':'提供された事実','requirements':['事実保持']} ]}
            prompt=E.grade_prompt(root,['O001'],{'O001':'private-improved.json'},c)
            self.assertIn('提供された事実',prompt);self.assertIn('完成した文章',prompt)
            self.assertNotIn('improved',prompt);self.assertNotIn('SKILL.md',prompt)
    def test_failed_trial_is_retained_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'writing').mkdir()
            B.save(root/'writing/E01-baseline-1.json',{'status':'timeout'})
            with mock.patch.object(B,'execute') as execute:
                self.assertEqual(E.write_one(root,{'task':'E01','arm':'baseline','repeat':1},{},[])[1],'retained_timeout')
                execute.assert_not_called()
    def test_reference_mention_and_partial_read_are_not_full_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'explanation.md';p.write_text('Reader questions and factual limits.\nSecond paragraph.\n', encoding="utf-8", newline="\n")
            echo={'command':'echo '+str(p),'exit_code':0,'aggregated_output':p.read_text(encoding="utf-8")}
            partial={'command':'head -n 1 '+str(p),'exit_code':0,'aggregated_output':'Reader questions and factual limits.'}
            full={'command':'cat '+str(p),'exit_code':0,'aggregated_output':p.read_text(encoding="utf-8")}
            self.assertFalse(N.full_reads([echo,partial],p));self.assertEqual(len(N.full_reads([full],p)),1)

    def test_input_mutation_stops_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'input.md').write_text('original', encoding="utf-8", newline="\n")
            c={'files':{'input.md':B.sha(b'original')}};E.verify_inputs(root,c)
            (root/'input.md').write_text('changed', encoding="utf-8", newline="\n")
            with self.assertRaises(ValueError):E.verify_inputs(root,c)


from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':unittest.main()
