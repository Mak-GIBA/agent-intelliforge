"""Portable ECC uses the same language routing and required TDD original."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from agent_intelliforge import ecc_port, runtime
from agent_intelliforge.catalog import ForgeError
import test_ecc_on_demand as fixtures


class PortableEccTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.bundle=self.root/'bundle';self.bundle.mkdir()
        for name in list(filter(None,fixtures.ecc.ENTRIES.values()))+['cpp-testing','react-testing']:
            path=self.root/'upstream/skills'/name/'SKILL.md';path.parent.mkdir(parents=True)
            path.write_text('---\nname: '+name+'\ndescription: Test workflow testing patterns\n---\nbody')

    def run_reader(self,*args):
        output=io.StringIO()
        with mock.patch.object(ecc_port,'verify'), mock.patch.object(runtime,'load',return_value=fixtures.ecc), contextlib.redirect_stdout(output):
            ecc_port.main(self.bundle,'codex',list(args))
        return json.loads(output.getvalue())

    def test_language_option_routes_without_cross_language_results(self):
        value=self.run_reader('search','testing','--language','typescript','--json')
        names=[row['name'] for row in value['matches']]
        self.assertIn('react-testing',names);self.assertNotIn('cpp-testing',names)
        with self.assertRaises(ForgeError):self.run_reader('search','testing','--language','unknown')

    def test_tdd_is_required_and_resolvable(self):
        self.assertEqual(self.run_reader('resolve','tdd-workflow','--json')['name'],'tdd-workflow')
        (self.root/'upstream/skills/tdd-workflow/SKILL.md').unlink()
        with self.assertRaises(ForgeError):self.run_reader('doctor','--json')

    def test_read_only_option_preserves_frozen_reader(self):
        self.assertEqual(self.run_reader('resolve','tdd-workflow','--no-refresh','--json')['name'],'tdd-workflow')
        self.assertTrue(self.run_reader('search','testing','--language','typescript','--no-refresh','--json')['matches'])

    def test_real_portable_ownership_rejects_changed_upstream(self):
        from agent_intelliforge.ownership import replace_tree
        data={p.relative_to(self.root/'upstream').as_posix():p.read_bytes()
              for p in (self.root/'upstream').rglob('*') if p.is_file()}
        import shutil
        shutil.rmtree(self.root/'upstream')
        replace_tree(self.root/'upstream',runtime.owner('ecc-upstream','codex'),data)
        with mock.patch.object(runtime,'load',return_value=fixtures.ecc),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ecc_port.main(self.bundle,'codex',['resolve','tdd-workflow','--no-refresh']),0)
            (self.root/'upstream/skills/python-patterns/SKILL.md').write_text('modified')
            with self.assertRaises(ForgeError):
                ecc_port.main(self.bundle,'codex',['resolve','tdd-workflow','--no-refresh'])
