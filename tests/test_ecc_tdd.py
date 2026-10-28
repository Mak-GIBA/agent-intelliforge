"""Runtime binding, version-one migration, and multilingual routing contracts."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import unittest
from unittest import mock
import test_ecc_on_demand as fixtures
ecc = fixtures.ecc


class TddMigrationTests(unittest.TestCase):
    setUp = fixtures.ManagerTest.setUp

    def legacy_state(self):
        self.manager.apply()
        state = self.manager.state()
        for path in list(state['files']):
            if '/ecc-tdd/' in path or path.endswith('/catalog.json'):
                Path(path).unlink(); del state['files'][path]
        root = self.skills_root/'ecc-tdd'
        if root.exists():
            (root/'agents').rmdir(); root.rmdir()
        state['version'] = 1
        state.pop('python_executable', None)
        state.pop('catalog_snapshot', None)
        state.pop('entrypoints', None)
        self.manager.state_path.write_text(json.dumps(state))
        return state

    def test_upgrade_four_entries_preserves_configuration_and_restore(self):
        old = self.legacy_state()
        before = self.config.read_bytes()
        self.manager.apply()
        state = self.manager.state()
        self.assertEqual(state['version'], 2)
        self.assertIn('ecc-tdd', state['entrypoints'])
        self.assertEqual(state['backup'], old['backup'])
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(self.manager.apply()['changed_files'], 0)
        self.manager.restore()
        self.assertFalse((self.skills_root/'ecc-tdd').exists())

    def test_new_unmanaged_tdd_entry_blocks_migration_without_writes(self):
        self.legacy_state()
        target = self.skills_root/'ecc-tdd'; target.mkdir()
        (target/'SKILL.md').write_text('user content')
        before = self.manager.state_path.read_bytes(), self.config.read_bytes()
        with self.assertRaises(ecc.ManagementError): self.manager.apply()
        self.assertEqual(before, (self.manager.state_path.read_bytes(), self.config.read_bytes()))
        self.assertEqual((target/'SKILL.md').read_text(), 'user content')

    def test_failed_upgrade_rolls_back_old_state_and_entries(self):
        self.legacy_state()
        before = {p:p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        write = ecc.atomic_write
        def fail(path, *args, **kwargs):
            if path == self.skills_root/'ecc-tdd/agents/openai.yaml': raise OSError('fixture disk failure')
            return write(path, *args, **kwargs)
        with mock.patch.object(ecc, 'atomic_write', side_effect=fail):
            with self.assertRaises(OSError): self.manager.apply()
        self.assertEqual(before, {p:p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
        self.assertFalse((self.skills_root/'ecc-tdd').exists())

    def test_missing_tdd_original_preserves_legacy_installation(self):
        self.legacy_state()
        before = self.config.read_bytes(), self.manager.state_path.read_bytes()
        self.codex.originals = [row for row in self.originals if row['name'] != 'ecc:tdd-workflow']
        with self.assertRaisesRegex(ecc.ManagementError, 'missing'):
            self.manager.apply()
        self.assertEqual(before, (self.config.read_bytes(), self.manager.state_path.read_bytes()))

    def test_restore_legacy_state_does_not_require_a_fifth_entry(self):
        self.legacy_state()
        self.assertEqual(self.manager.restore()['status'], 'restored')

    def test_installed_lookup_works_without_any_codex_executable(self):
        self.manager.apply()
        command = (self.skills_root/'ecc-tdd/SKILL.md').read_text().split('`')[1]
        args = shlex.split(command)
        args[args.index('--codex')+1] = '/missing/codex'
        result = subprocess.run(args, env={**os.environ,'PATH':'/missing'}, cwd=self.root,
                                text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['name'],'tdd-workflow')

    def test_snapshot_lookup_never_starts_codex_and_detects_changed_original(self):
        self.manager.apply()
        self.codex.calls.clear()
        self.assertIn('tdd-workflow', [s['name'] for s in self.manager.read_snapshot()])
        self.assertEqual(self.codex.calls, [])
        Path(self.originals[0]['path']).write_text('modified original')
        with self.assertRaisesRegex(ecc.ManagementError, 'changed or missing'):
            self.manager.read_snapshot()

    def test_installed_tdd_command_does_not_depend_on_python3_path(self):
        self.manager.apply()
        command = (self.skills_root/'ecc-tdd/SKILL.md').read_text().split('`')[1]
        args = shlex.split(command)
        self.assertEqual(args[0], os.path.abspath(sys.executable))
        # The bound runtime starts even when no python3 can be found in PATH.
        result = subprocess.run(args[:3]+['--help'], env={**os.environ,'PATH':'/missing'},
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skills = [{'name':n,'description':'Test workflow and testing patterns'} for n in
                       ('tdd-workflow','python-testing','react-testing','golang-testing',
                        'rust-testing','cpp-testing','csharp-testing')]

    def test_language_filter_including_punctuation_and_aliases(self):
        for language, expected in [('Python','python-testing'),('TypeScript','react-testing'),
                                   ('Go','golang-testing'),('Rust','rust-testing'),
                                   ('C++','cpp-testing'),('C#','csharp-testing')]:
            with self.subTest(language=language):
                found = ecc.search_catalog(self.skills,'testing',self.root,language=language)
                self.assertIn(expected,[s['name'] for s in found])
                self.assertFalse({s['name'] for s in found}-{'tdd-workflow',expected})

    def test_nearest_project_wins_over_monorepo_root(self):
        (self.root/'pyproject.toml').write_text('[project]\nname="root"')
        package=self.root/'web';package.mkdir();(package/'tsconfig.json').write_text('{}')
        found=ecc.search_catalog(self.skills,'testing',package)
        self.assertIn('react-testing',[s['name'] for s in found])
        self.assertNotIn('python-testing',[s['name'] for s in found])

    def test_explicit_skill_and_language_common_tdd_remain_available(self):
        self.assertEqual(ecc.search_catalog(self.skills,'tdd-workflow',self.root,language='go')[0]['name'],'tdd-workflow')
        self.assertIn('tdd-workflow',[s['name'] for s in ecc.search_catalog(self.skills,'TDD テスト',self.root,language='go')])
        with self.assertRaises(ecc.ManagementError): ecc.search_catalog(self.skills,'testing',self.root,language='unknown-language')
