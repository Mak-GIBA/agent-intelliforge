"""Synthetic published runs verify on clones and invalidate real approvals on tamper."""
import json
import shutil
from test_workbench import Base,demo_records
from workbench.published_evidence import export,verify,sha
from workbench.workspace_paths import topic_workspace
from workbench.design_quality import validate_binding,dependency_files,MARKER
from workbench.approval import create_review,approve
from workbench.overview import overview,write


class PortableBindingTests(Base):
    def setUp(self):
        super().setUp();self.legacy_layout=False;self.attach(docs_only=True)
        records=demo_records();records[-1]['links']['verifies'].append('APP-DES-001');self.write_records(records)
        self.workspace=topic_workspace(self.root,'example',True);run=self.workspace/'runs/FIXTURE';run.mkdir(parents=True)
        req=self.root/'docs/upstream/requirements.md';snap=run/'inputs/requirements.md';snap.parent.mkdir();snap.write_bytes(req.read_bytes())
        report=run/'reports/report.md';report.parent.mkdir();report.write_text('# Synthetic report\n[Receipt](../receipt.json)\n')
        output=run/'stdout.log';output.write_text('synthetic measured output\n')
        receipt=run/'receipt.json';receipt.write_text(json.dumps({'outputs':{'stdout':{'path':'runs/FIXTURE/stdout.log','sha256':sha(output.read_bytes())}}}))
        state={'schema_version':1,'run_id':'FIXTURE','status':'research_complete','config':{'mode':'research','slug':'example','project':str(self.root)},
               'workspace':str(self.workspace),'dossier':{'candidates':[{'id':'A'}]},
               'requirements_context':{'project_path':'docs/upstream/requirements.md','snapshot':'runs/FIXTURE/inputs/requirements.md','sha256':sha(snap.read_bytes())},
               'evidence':{'EV1':{'path':'runs/FIXTURE/receipt.json','sha256':sha(receipt.read_bytes())}}}
        (run/'state.json').write_text(json.dumps(state))
        self.exported=export(self.root,'example','FIXTURE',True,['APP-DES-001']);binding=self.exported['binding']
        binding['decisions']=[{'design_id':'APP-DES-001','candidate_id':'A','rationale':'Synthetic fixture only.'}]
        self.data={'schema_version':3,'runs':[binding],'uiux':{'applicable':False,'reason':'Fixture has no screens.','artifacts':[]}}
        self.doc=self.root/'docs/upstream/requirements/demo.md'
        diagrams=''.join(f'\n## Diagram {i}\n```mermaid\nflowchart LR\n A -->|data| B\n```\nSynthetic reading guide.\n' for i in range(3))
        self.doc.write_text(self.doc.read_text()+MARKER+'\n## フレームワーク\nSynthetic fixture.\n'+diagrams+'\n```design-research\n'+json.dumps(self.data)+'\n```\n')
        packet=create_review(self.root,'all',True);approve(self.root,packet['review_id'],[],'TEST','synthetic explicit approval',True,True)
    def test_clone_without_runtime_validates_design_and_evidence(self):
        clone=self.root.parent/'clone';shutil.copytree(self.root,clone,ignore=shutil.ignore_patterns('.artifacts'))
        dependencies=validate_binding(clone,self.data,{'APP-DES-001'},'docs/upstream/requirements.md')
        self.assertTrue(dependencies);self.assertFalse((clone/'.artifacts').exists())
        result=overview(clone);self.assertEqual(result['research_stage'],'integrated')
        self.assertTrue(result['research'][0]['exported'])
    def test_proof_change_stales_design_and_linked_verification(self):
        write(self.root);self.assertNotIn('STALE_APPROVAL',self.codes())
        package=self.root/self.exported['package'];out=package/'files/runs/FIXTURE/stdout.log';out.write_text('tampered')
        self.assertIn('STALE_APPROVAL',self.codes());self.assertIn('STALE_DEPENDENCY_APPROVAL',self.codes())
        self.assertIn(out,dependency_files(self.root,[self.doc]))
        with self.assertRaisesRegex(ValueError,'changed'):validate_binding(self.root,self.data,{'APP-DES-001'},'docs/upstream/requirements.md')
    def test_changed_requirement_rejects_frozen_input(self):
        (self.root/'docs/upstream/requirements.md').write_text('changed requirement')
        with self.assertRaisesRegex(ValueError,'stale'):validate_binding(self.root,self.data,{'APP-DES-001'},'docs/upstream/requirements.md')
    def test_missing_proof_blocks_and_does_not_rewrite_archives(self):
        before=(self.workspace/'runs/FIXTURE/state.json').read_bytes()
        package=self.root/self.exported['package'];(package/'files/runs/FIXTURE/stdout.log').unlink()
        with self.assertRaisesRegex(ValueError,'missing'):verify(package)
        self.assertEqual(before,(self.workspace/'runs/FIXTURE/state.json').read_bytes())
