"""Presentation contracts; retrieval and state-machine contracts live separately."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import sys
from types import SimpleNamespace

SOURCE=Path(__file__).resolve().parents[1]/'tools/basic-memory-workgraph/hooks/basic_memory_workgraph.py'
spec=importlib.util.spec_from_file_location('prompt_hook',SOURCE)
hook=importlib.util.module_from_spec(spec);spec.loader.exec_module(hook)


class PromptTests(unittest.TestCase):
    def test_full_hook_character_budget_against_immediate_baseline(self):
        source=SOURCE.parent.parent
        path=source/'evaluation/measure_prompts.py'
        spec=importlib.util.spec_from_file_location('measure_fixture',path)
        measure=importlib.util.module_from_spec(spec);spec.loader.exec_module(measure)
        baseline=json.loads((SOURCE.parents[3]/'tests/fixtures/workgraph-prompt-v110.json').read_text())['before']
        # Character-only regression gate; actual tokenizer comparison is run separately.
        encoder=SimpleNamespace(encode=lambda text:text)
        with patch.dict(sys.modules,{'tiktoken':SimpleNamespace(get_encoding=lambda name:encoder)}):
            actual=measure.measure(source)
        for case in ('empty','found','unavailable','needs_context'):
            for phase in ('start','stop'):
                self.assertLessEqual(actual[case][phase]['characters'],baseline[case][phase]['characters']*.8)

    def test_projection_preserves_bodies_scope_warnings_and_does_not_change_source(self):
        body='---\ntype: correction\n---\nDo not summarize: scope and exceptions matter.\n'
        result={'status':'found','candidates':5,'notes':[{'id':'fixture:rule','project':'fixture','identifier':'rule',
            'fingerprint':'a'*64,'blocked':True,'title':'Scope','content':body,
            'metadata':{'scope':'reports','exceptions':'tutorials'},'warning':'Read full source','trust':'untrusted'}],
            'message':'Repeated instructions'}
        before=copy.deepcopy(result);value=hook.recall_view(result)
        self.assertEqual(result,before)
        self.assertEqual(value['notes'][0]['content'],body)
        self.assertEqual(value['notes'][0]['metadata'],result['notes'][0]['metadata'])
        self.assertTrue(value['notes'][0]['blocked'])
        self.assertEqual(value['notes'][0]['warning'],'Read full source')
        self.assertEqual(value['candidates'],5)
        for key in ('fingerprint','project','identifier','trust'):self.assertNotIn(key,value['notes'][0])

    def test_empty_and_error_statuses_never_collapse_to_no_results(self):
        for status in ('no_results','unavailable','needs_context'):
            self.assertEqual(hook.recall_view({'status':status,'notes':[],'candidates':0,'message':'verbose'}),{'status':status})

    def test_hook_header_repeats_neither_helper_nor_task(self):
        from unittest.mock import patch
        ticket='a'*64
        class Service:
            seed_query=staticmethod(lambda value:'purpose')
            def prepare(self,*args):return {'status':'no_results','notes':[],'candidates':0}
        with patch.object(hook,'recall_service',return_value=Service()),patch.object(hook,'ROOT',SOURCE.parent.parent):
            context=hook.retrieved_context({'prompt':'purpose'},Path(ticket+'.json'))
        self.assertEqual(context.count(ticket),1)
        self.assertEqual(context.count('workgraph_recall.py'),1)
        for command in ('prepare','select','check'):self.assertIn(command,context)
        self.assertIn('semantic',context)
        self.assertIn('no_results',context)
