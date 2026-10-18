"""Portable synthetic evidence: no model calls or real study claims."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'overlay/tools/design-research/skill/scripts'))
from workspace_paths import topic_workspace,state_paths,state_identity
from published_evidence import export,verify,sha


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'source';self.root.mkdir()
        self.workspace=topic_workspace(self.root,'example',create=True)
        self.run=self.workspace/'runs/FIXTURE';self.run.mkdir(parents=True)
        self.write('runs/FIXTURE/stdout.log',b'actual synthetic output\n')
        self.write('runs/FIXTURE/stderr.log',b'')
        receipt={'outputs':{name:{'path':f'runs/FIXTURE/{name}.log','sha256':sha((self.run/(name+'.log')).read_bytes())} for name in ('stdout','stderr')},'artifacts':[]}
        raw=json.dumps(receipt).encode();self.write('runs/FIXTURE/receipt.json',raw)
        self.write('runs/FIXTURE/reports/report.md',b'# Synthetic test report\n[Receipt](../receipt.json)\n')
        self.state={'schema_version':1,'run_id':'FIXTURE','status':'research_complete','config':{'mode':'research','slug':'example','project':str(self.root)},
                    'workspace':str(self.workspace),'dossier':{'candidates':[{'id':'A'}]},
                    'evidence':{'EV1':{'path':'runs/FIXTURE/receipt.json','sha256':sha(raw)}}}
        self.write('runs/FIXTURE/state.json',json.dumps(self.state).encode())
    def write(self,name,raw):
        p=self.workspace/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    def snapshot(self):return {p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    def test_new_layout_and_legacy_are_discovered_without_moving_history(self):
        old=self.root/'docs/design-research/old';old.mkdir(parents=True);(old/'keep').write_bytes(b'keep')
        self.assertEqual(topic_workspace(self.root,'old',True),old)
        self.assertEqual(state_paths(self.root),[self.run/'state.json'])
        self.assertEqual(state_identity(self.root,self.run/'state.json'),('example','FIXTURE'))
        self.assertEqual((old/'keep').read_bytes(),b'keep')
    def test_preview_is_readonly(self):
        before=self.snapshot();result=export(self.root,'example','FIXTURE')
        self.assertFalse(result['applied']);self.assertEqual(before,self.snapshot())
    def test_clone_without_runtime_retains_receipts_and_needed_logs(self):
        result=export(self.root,'example','FIXTURE',True,['SYS-D1'])
        clone=Path(self.tmp.name)/'clone';shutil.copytree(self.root/'docs',clone/'docs')
        package=clone/result['package'];verified=verify(package)
        self.assertIn('runs/FIXTURE/stdout.log',verified['files'])
        self.assertIn('runs/FIXTURE/stderr.log',verified['files'])
        self.assertEqual(verified['related_ids'],['SYS-D1'])
        self.assertFalse((clone/'.artifacts').exists())
    def test_tampered_output_blocks_before_export(self):
        self.write('runs/FIXTURE/stdout.log',b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):export(self.root,'example','FIXTURE',True)
        self.assertFalse((self.root/'docs/design-research/example/evidence/FIXTURE').exists())
    def test_missing_log_is_not_silently_dropped(self):
        (self.run/'stdout.log').unlink()
        with self.assertRaisesRegex(ValueError,'missing'):export(self.root,'example','FIXTURE')
    def test_tampering_and_manifest_dependency_omission_block_verification(self):
        result=export(self.root,'example','FIXTURE',True);package=self.root/result['package']
        manifest=package/'manifest.json';m=json.loads(manifest.read_text());del m['files']['runs/FIXTURE/stderr.log'];manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'omits'):verify(package)
    def test_absolute_frozen_unit_input_remains_portable(self):
        p=self.run/'inputs/task.json';p.parent.mkdir();p.write_bytes(b'{"synthetic": true}')
        self.state['unit_inputs']={str(p):sha(p.read_bytes())}
        self.write('runs/FIXTURE/state.json',json.dumps(self.state).encode())
        result=export(self.root,'example','FIXTURE',True)
        self.assertIn('runs/FIXTURE/inputs/task.json',verify(self.root/result['package'])['files'])
    def test_existing_package_is_immutable(self):
        result=export(self.root,'example','FIXTURE',True,['SYS-D1']);before=self.snapshot()
        export(self.root,'example','FIXTURE',True,['SYS-D1']);self.assertEqual(before,self.snapshot())
        with self.assertRaisesRegex(ValueError,'immutable'):export(self.root,'example','FIXTURE',True,['SYS-D2'])
    def test_ignore_configuration_is_preserved(self):
        other=Path(self.tmp.name)/'ignore';other.mkdir();(other/'.gitignore').write_text('user-rule\n')
        topic_workspace(other,'a',True);topic_workspace(other,'b',True)
        self.assertEqual((other/'.gitignore').read_text(),'user-rule\n/.artifacts/design-research/\n')

if __name__=='__main__':unittest.main()
