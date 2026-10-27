"""The preserved writing rules are checked against the immutable v3 archive."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest

if 'I' not in globals():
    spec=importlib.util.spec_from_file_location('flow_contract_installer',Path(__file__).resolve().parents[1]/'installer.py')
    I=importlib.util.module_from_spec(spec);sys.modules[spec.name]=I;spec.loader.exec_module(I)
    A=I.assets()


class FlowContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'kotonoha';self.root.mkdir()
        for name,raw in I.own_bundle('kotonoha','auto').items():
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        self.module=types.ModuleType('flow_rules')
        exec(compile(A['engine/flow_contract.py'],'flow_contract.py','exec'),self.module.__dict__)
        self.baseline=json.loads(A['evals/flow-v3-baseline.json'])

    def verify(self):return self.module.verify_flow(self.root,self.baseline)

    def test_full_v3_normative_blocks_and_local_links_are_preserved(self):
        self.assertEqual(self.verify()['preserved_resources'],9)

    def test_lost_negation_example_is_detected(self):
        p=self.root/'references/clarity.md'
        p.write_text(p.read_text(encoding="utf-8").replace('「増大を招かないとは言えない」は「増えることがある」','「増大を招かないとは言えない」は「増えない」'), encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(ValueError,'legacy rule changed'):self.verify()

    def test_lost_directness_example_and_missing_reference_are_detected(self):
        p=self.root/'references/directness.md';original=p.read_text(encoding="utf-8")
        p.write_text(original.replace('CPU環境は未評価です','CPU環境は評価済みです'), encoding="utf-8", newline="\n")
        with self.assertRaises(ValueError):self.verify()
        p.write_text(original, encoding="utf-8", newline="\n");(self.root/'references/review.md').unlink()
        with self.assertRaises((ValueError,FileNotFoundError)):self.verify()

    def test_workflow_cannot_silently_make_clarity_optional(self):
        p=self.root/'SKILL.md';p.write_text(p.read_text(encoding="utf-8").replace('を読み、meisekiの明晰化を先に適用する','を必要なら読み、明晰化は任意とする'), encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(ValueError,'legacy rule changed'):self.verify()

    def test_broken_new_reference_is_detected(self):
        p=self.root/'references/finish.md';p.write_text(p.read_text(encoding="utf-8")+'\n[詳細](missing.md)\n', encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(ValueError,'Broken maintained link'):self.verify()

    def test_mapping_cannot_relabel_rule_deletion_as_wiring(self):
        p=self.root/'FLOW.json';value=json.loads(p.read_text(encoding="utf-8"))
        value['preserved'][0]['replacements'].append(['原文','省略'])
        p.write_text(json.dumps(value), encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(ValueError,'approved wiring-only'):self.verify()

    def test_unknown_editorial_revision_cannot_bypass_rule_checks(self):
        p=self.root/'FLOW.json';value=json.loads(p.read_text(encoding="utf-8"))
        value['editorial_revision']='unreviewed'
        p.write_text(json.dumps(value), encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(ValueError,'Unknown editorial revision'):self.verify()

    def test_editorial_revision_cannot_authorize_a_new_meaning_change(self):
        p=self.root/'references/directness.md'
        p.write_text(p.read_text(encoding="utf-8").replace('「予定」を「実施済み」に変えない。','「予定」を「実施済み」に変える。'), encoding="utf-8", newline="\n")
        # Even updating the candidate's own digest cannot change the external allowlist.
        import hashlib
        manifest=self.root/'FLOW.json';value=json.loads(manifest.read_text(encoding="utf-8"))
        row=next(r for r in value['preserved'] if r['destination']=='references/directness.md')
        row['preserved_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(value), encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(ValueError,'legacy rule changed'):self.verify()

    def test_original_detail_and_deduplicated_wrappers_have_explicit_coverage(self):
        contract=json.loads((self.root/'FLOW.json').read_text(encoding="utf-8"))
        self.assertEqual({r['source'] for r in contract['deduplicated']},
                         {'references/paragraphs.md','references/directness.md','references/reader-review.md'})
        self.assertNotIn('references/long-form.md',list(I.own_bundle('kotonoha','auto')))



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':unittest.main()
