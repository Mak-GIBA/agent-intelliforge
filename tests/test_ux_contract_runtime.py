from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
from test_ux_visual_contract import example

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ux_contract_runtime_test',ROOT/'tools/codex-ux-stack/skill/scripts/contract_runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
hspec=importlib.util.spec_from_file_location('ux_harness_contract_test',ROOT/'tools/codex-ux-stack/skill/scripts/harness.py')
h=importlib.util.module_from_spec(hspec);hspec.loader.exec_module(h)

class ContractRuntimeTests(unittest.TestCase):
    def test_harness_gate_does_not_accept_model_success_without_contract_receipts(self):
        audit={'issues':[],'friction':[],'simplicity':{'regressed':False},'second_pass_complete':True,
               'coverage':[{'flow_id':'J-doc','viewport':'desktop','state':'normal','result':'passed','perspective':p} for p in ['first_time','mistake']]}
        plan={'flows':[{'id':'J-doc','required':True,'states':['normal']}]}
        config={'profile':'focused','focus':['document'],'viewports':['desktop'],'reference_urls':[],'ux_contract_path':'design.json'}
        reasons=h.gate(audit,plan,{'status':'not_required'},[{'passed':True}],config)
        self.assertTrue(any('contract' in r.lower() for r in reasons),reasons)
    def fixture(self,root):
        (root/'index.html').write_text('fixture');p=root/'design.json';p.write_text(json.dumps(example()));run=root/'run';run.mkdir()
        return p,runtime.freeze(p,root,run)

    def test_human_edit_invalidates_the_frozen_design(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p,state=self.fixture(root);runtime.assert_current(state)
            p.write_text(p.read_text()+'\n')
            with self.assertRaises(runtime.ContractBlocked):runtime.assert_current(state)

    def test_missing_receipts_cannot_be_replaced_by_an_empty_or_successful_model_report(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,state=self.fixture(root);report=runtime.observations(state,root/'role',['desktop'])
            self.assertFalse(report['ready']);self.assertEqual(report['verified'],0);self.assertEqual(len(report['missing']),len(state['required_checks']))

    def test_planner_cannot_rename_or_drop_required_screens_and_journeys(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,state=self.fixture(root)
            with self.assertRaises(runtime.ContractBlocked):runtime.validate_plan({'screens':[{'id':'invented'}],'flows':[{'id':'renamed','required':True}]},state)
            runtime.validate_plan({'screens':[{'id':'S-list'},{'id':'S-detail'}],'flows':[{'id':'J-doc','required':True}]},state)

if __name__=='__main__':unittest.main()
