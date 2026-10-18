import contextlib
import io
import json
from pathlib import Path
import shutil
from test_workbench import Base,demo_records
from workbench.overview import overview,write,MARKER
from workbench.cli import main
from workbench.workflow import snapshot,run_gate,verify_gate,flow
from workbench.trace import documents,inspect
from workbench.common import load_project,WorkbenchError
from workbench.command_skills import COMMANDS,render_skill


class OverviewTests(Base):
    def snapshot_bytes(self):return {p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    def test_inspection_and_brief_modes_do_not_write(self):
        self.attach(docs_only=True);before=self.snapshot_bytes()
        data=overview(self.root);self.assertTrue(data['inspection_only']);self.assertEqual(data['research'],[])
        for mode in ('new','existing','change','bug','refactor','check'):
            self.assertEqual(main(['flow','--project',str(self.root),'--mode',mode,'--brief']),0)
        self.assertEqual(main(['overview','--project',str(self.root),'--json']),0)
        self.assertEqual(before,self.snapshot_bytes())
    def test_generated_navigation_does_not_invalidate_approvals_or_gate(self):
        self.legacy_layout=False
        self.attach(docs_only=True);self.write_records(demo_records())
        before=snapshot(self.root);gate=run_gate(self.root,True)
        write(self.root);path=self.root/'docs/upstream/README.md'
        self.assertTrue(path.read_text(encoding="utf-8").startswith(MARKER))
        self.assertNotIn(path,documents(self.root,load_project(self.root)))
        self.assertEqual(before,snapshot(self.root));self.assertEqual(gate['passed'],verify_gate(self.root)['passed'])
        self.assertNotIn('STALE_APPROVAL',self.codes())
        info=overview(self.root);self.assertTrue((self.root/info['review']['path']).is_file())
        p=self.root/'docs/upstream/requirements/demo.md';p.write_text(p.read_text(encoding="utf-8")+'\nchanged shared condition\n', encoding="utf-8", newline="\n")
        self.assertIn('STALE_APPROVAL',self.codes())
    def test_unmanaged_readme_is_preserved_and_included_in_scan(self):
        self.attach(docs_only=True);path=self.root/'docs/upstream/README.md';path.write_text('User-owned document', encoding="utf-8", newline="\n")
        self.assertIn(path,documents(self.root,load_project(self.root)))
        with self.assertRaises(WorkbenchError):write(self.root)
        self.assertEqual(path.read_text(encoding="utf-8"),'User-owned document')
    def test_all_eight_entries_and_mandatory_brief_are_bounded(self):
        self.assertEqual(len(COMMANDS),8)
        for name in COMMANDS:
            entry=render_skill(name,Path('/usr/bin/speckit-workbench'),Path('/runtime/assets'))
            self.assertLessEqual(len(entry),1500,name)
        self.assertLess(len(flow(self.root,'new',True)),1500)
        self.assertGreater(len(flow(self.root,'new')),len(flow(self.root,'new',True)))
    def test_mutation_refreshes_navigation_readonly_check_does_not(self):
        # Use the current compact attach, not Base's intentional legacy conversion.
        self.legacy_layout=False
        self.assertEqual(main(['attach','--project',str(self.root),'--system','APP','--docs-only','--apply']),0)
        path=self.root/'docs/upstream/README.md';self.assertTrue(path.is_file());before=self.snapshot_bytes()
        main(['check','--project',str(self.root)]);self.assertEqual(before,self.snapshot_bytes())
        main(['item','--project',str(self.root),'--type','goal','--id','APP-G1','--title','Test goal','--apply'])
        self.assertIn('APP-G1',path.read_text(encoding="utf-8"))

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
