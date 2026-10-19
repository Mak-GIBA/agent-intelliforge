"""Exercise real setup/resume/publication with execution deliberately unavailable."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

SOURCE=Path(os.environ['CODEX_INTERFACE_SOURCE_ROOT']) if os.environ.get('CODEX_INTERFACE_SOURCE_ROOT') else None


@unittest.skipUnless(SOURCE,'Requires assembled runtime')
class SplitHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def execute(self,argv):
        code='''import harness,sys
from unittest.mock import patch
with patch.object(harness,'codex_capabilities',return_value={'ready':False,'errors':['Synthetic unavailable runtime']}):
    sys.exit(harness.execution(harness.parser().parse_args(sys.argv[1:])))
'''
        result=subprocess.run([sys.executable,'-B','-c',code,*argv,'--project',str(self.root)],
               env={**os.environ,'PYTHONPATH':str(SOURCE/'tools/design-research/skill/scripts')},capture_output=True,text=True,timeout=20)
        self.assertNotIn('Traceback',result.stderr,result.stderr)
        return result.returncode
    def test_new_topic_public_report_and_resume_share_the_same_local_run(self):
        self.assertEqual(self.execute(['research','--brief','Synthetic setup only','--slug','example']),2)
        local=self.root/'.artifacts/design-research/example';states=list(local.glob('runs/*/state.json'))
        self.assertEqual(len(states),1);self.assertTrue((self.root/'docs/design-research/example/report.md').is_file())
        self.assertFalse((self.root/'docs/design-research/example/runs').exists())
        self.assertEqual(self.execute(['resume',states[0].parent.name]),2)
        self.assertEqual(list(local.glob('runs/*/state.json')),states)
        self.assertNotIn('Source changed',states[0].read_text())
    def test_existing_topic_stays_in_legacy_location(self):
        legacy=self.root/'docs/design-research/old';legacy.mkdir(parents=True);(legacy/'design-research.md').write_text('Existing report')
        self.assertEqual(self.execute(['research','--brief','Synthetic setup','--slug','old']),2)
        self.assertTrue(list(legacy.glob('runs/*/state.json')))
        self.assertFalse((self.root/'.artifacts/design-research/old').exists())
    def test_new_and_old_completed_contexts_are_read_without_rewriting_history(self):
        self.execute(['research','--brief','Synthetic setup','--slug','example'])
        path=next((self.root/'.artifacts/design-research/example').glob('runs/*/state.json'))
        state=json.loads(path.read_text());state.update(status='research_complete',dossier={});path.write_text(json.dumps(state))
        before={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        code='''import reassessment,sys
from pathlib import Path
print(reassessment.load_previous(Path(sys.argv[1]),sys.argv[2],'example-reassess')['previous_state'])
'''
        r=subprocess.run([sys.executable,'-B','-c',code,str(self.root),str(path)],
            env={**os.environ,'PYTHONPATH':str(SOURCE/'tools/design-research/skill/scripts')},capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr);self.assertIn('.artifacts/design-research/example',r.stdout)
        self.assertEqual(before,{p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
    def test_unavailable_standalone_overview_remains_readonly(self):
        # Actual Codex failure never becomes execution success.
        self.assertEqual(self.execute(['research','--brief','Synthetic setup','--slug','unavailable']),2)
        before={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        sys.path.insert(0,str(SOURCE/'tools/design-research/skill/scripts'))
        from codex_interface import runs
        rows,warnings=runs(self.root)
        self.assertEqual(rows[0]['status'],'blocked');self.assertTrue(rows[0]['resume_eligible'])
        self.assertEqual(before,{p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
