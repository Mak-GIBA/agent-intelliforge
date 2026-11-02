from pathlib import Path
import importlib.util
import json
import tempfile
import unittest
import hashlib
import subprocess
from unittest.mock import patch
from test_ux_gan_harness import png
from test_ux_visual_contract import example

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ux_contract_runtime_test',ROOT/'tools/codex-ux-stack/skill/scripts/contract_runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
hspec=importlib.util.spec_from_file_location('ux_harness_contract_test',ROOT/'tools/codex-ux-stack/skill/scripts/harness.py')
h=importlib.util.module_from_spec(hspec);hspec.loader.exec_module(h)

class ContractRuntimeTests(unittest.TestCase):
    def test_unavailable_vendor_listing_keeps_local_browser_fallback(self):
        with patch.object(h,'command',return_value=subprocess.CompletedProcess(['codex'],1,'','unavailable')):
            backend,reason=h.select_backend({'browser':'auto'})
        self.assertEqual(backend,'local-playwright');self.assertIn('inspection',reason.lower())
    def test_concurrent_edit_during_freeze_cannot_change_approval_behind_the_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p,_=self.fixture(root);engine=runtime.helper();original=engine.require
            def require(value,project=None):
                changed=json.loads(p.read_text());changed['approval']={'status':'approved','source':'concurrent edit'};p.write_text(json.dumps(changed))
                return original(value,project)
            with patch.object(runtime,'helper',return_value=engine),patch.object(engine,'require',side_effect=require),self.assertRaises(runtime.ContractBlocked):runtime.freeze(p,root,root/'run')
    def test_approved_design_needs_a_frozen_reference_and_detects_its_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p,state=self.fixture(root);c=json.loads(p.read_text());c['approval']={'status':'approved','source':'test user approval'}
            p.write_text(json.dumps(c));state=runtime.freeze(p,root,root/'run')
            self.assertEqual(runtime.observations(state,root/'role',['desktop'])['design_reference_status'],'missing')
            image=root/'approved.png';image.write_bytes(png());c['artifacts']=[{'id':'D-main','provider':'local','url':'approved.png','file_id':'local','bindings':{'S-list':'list'},'snapshot':{'path':'approved.png','sha256':hashlib.sha256(image.read_bytes()).hexdigest()}}]
            p.write_text(json.dumps(c));state=runtime.freeze(p,root,root/'run');self.assertEqual(runtime.context(state)['design_references'][0]['id'],'D-main')
            image.write_bytes(image.read_bytes()+b'human edit')
            with self.assertRaises(runtime.ContractBlocked):runtime.assert_current(state)
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
