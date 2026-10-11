"""Offline checks for the evidence boundary, not assertions of prose quality."""
import importlib.util
import builtins
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    path=ROOT/'evals'/name
    if path.is_file():
        spec=importlib.util.spec_from_file_location(name.removesuffix('.py'),path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    # Standalone --self-test supplies the bundle without extracting it.
    module=types.ModuleType(name.removesuffix('.py'));module.__file__=str(path)
    exec(compile(A['evals/'+name],str(path),'exec'),module.__dict__);return module

S=load('run_study.py')
M=load('summarize_study.py')

class EvidenceTests(unittest.TestCase):
    def test_self_tests_do_not_require_the_python311_toml_module(self):
        original=builtins.__import__
        def importing(name,*args,**kwargs):
            if name=='tomllib':raise ModuleNotFoundError(name)
            return original(name,*args,**kwargs)
        with mock.patch.object(builtins,'__import__',side_effect=importing):
            module=load('run_study.py')
            self.assertTrue(callable(module.read_receipts))
            with self.assertRaisesRegex(ValueError,'Study preparation requires Python 3.11'):
                module.prepare(None,None,None)
    def test_mention_and_partial_read_are_not_application(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills=Path(tmp)
            for name in ('yomiyasu','paragraph-writing','japanese-direct-writing'):
                path=skills/name;path.mkdir();(path/'SKILL.md').write_text('---\nname: '+name+'\n---\nMeaning-preserving workflow.\n')
            path=skills/'paragraph-writing/SKILL.md'
            mention={'command':'echo paragraph-writing/SKILL.md','aggregated_output':path.read_text(),'exit_code':0}
            partial={'command':'head -n 2 '+str(path),'aggregated_output':'---\nname: paragraph-writing\n','exit_code':0}
            full={'command':'cat '+str(path),'aggregated_output':path.read_text(),'exit_code':0}
            self.assertEqual(S.read_receipts([mention,partial],skills),{})
            self.assertEqual(set(S.read_receipts([full],skills)),{'paragraph-writing'})
            self.assertEqual(len(S.read_receipts([full,full],skills)['paragraph-writing']),2)
    def test_execution_failure_stays_a_failed_trial_and_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'native/N1-a-1.json';target.parent.mkdir()
            target.write_text(json.dumps({'status':'timeout'}))
            self.assertEqual(S.generate_job(root,'native',{'task':'N1','arm':'a','repeat':1},{},{}),('N1-a-1','retained_timeout'))
    def test_contract_rejects_changed_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'sources';source.mkdir();file=source/'SKILL.md';file.write_text('frozen')
            contract={'source_hashes':{'files':{'SKILL.md':S.sha(file.read_bytes())}},'upstream_hashes':{}}
            locations={'sources':str(source),'upstream':str(root)}
            S.check_sources(contract,locations)
            file.write_text('changed')
            with self.assertRaisesRegex(ValueError,'Frozen'):S.check_sources(contract,locations)
    def test_timeout_is_missing_evidence_not_a_prose_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'writing').mkdir();(root/'writing-grades').mkdir()
            for name,status in [('done.json','completed'),('missing.json','timeout')]:
                (root/'writing'/name).write_text(json.dumps({'arm':'b','status':status,'elapsed_seconds':1,
                    'usage':{'input_tokens':10,'output_tokens':10} if status=='completed' else None}))
            row={'output_file':'done.json','meaning_errors':[],'requester_residue':[],
                 'paragraph':4,'naturalness':4,'reader_fit':4}
            (root/'writing-grades/unit.json').write_text(json.dumps({'status':'completed','ratings':[row]}))
            result=M.summarize(root)['conditions']['b']
            self.assertEqual(result['primary_fraction'],1)
            self.assertEqual(result['delivered_pass_fraction'],0.5)
            self.assertEqual(result['meaning_error_outputs'],0)
    def test_mean_score_cannot_hide_a_meaning_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'writing').mkdir();(root/'writing-grades').mkdir();(root/'native').mkdir()
            ratings=[]
            for i in range(24):
                name=f'W{i:02}-a-1.json'
                (root/'writing'/name).write_text(json.dumps({'arm':'a','status':'completed','elapsed_seconds':1,'usage':{'input_tokens':10,'output_tokens':10}}))
                ratings.append({'output_file':name,'meaning_errors':['Negation removed'] if i==0 else [],'requester_residue':[],
                                'paragraph':4,'naturalness':4,'reader_fit':4})
            (root/'writing-grades/B01.json').write_text(json.dumps({'status':'completed','ratings':ratings}))
            for i in range(8):
                (root/'native'/f'N{i}-a-1.json').write_text(json.dumps({'arm':'a','status':'completed','route_pass':True}))
            result=M.summarize(root)
            self.assertIsNone(result['selected']);self.assertEqual(result['conditions']['a']['meaning_error_outputs'],1)

if __name__=='__main__':unittest.main()
