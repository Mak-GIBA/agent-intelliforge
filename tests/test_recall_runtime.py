"""Recall must use a working YAML runtime, independently of the launch shell."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/basic-memory-workgraph'
spec = importlib.util.spec_from_file_location('runtime_under_test', SOURCE / 'recall_runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RecallRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.codex = self.home / 'codex with spaces'
        self.policy = self.codex / 'basic-memory-workgraph'
        self.policy.mkdir(parents=True)
        self.env = {**os.environ, 'HOME': str(self.home), 'CODEX_HOME': str(self.codex)}
        for name in ('BM_RECALL_CLI', 'BM_RECALL_PYTHON'):
            self.env.pop(name, None)

    def test_configuration_pins_usable_python_without_explicit_cli(self):
        result = subprocess.run([sys.executable, str(SOURCE / 'configure_workgraph.py'),
                                 '--codex-dir', str(self.codex)], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads((self.policy / 'config.json').read_text())
        self.assertTrue(Path(config.get('recallPython', '')).is_file(), config)
        command = json.loads((self.codex / 'hooks.json').read_text())['hooks']['UserPromptSubmit'][0]['hooks'][0]['command']
        self.assertEqual(shlex.split(command)[0], config['recallPython'])
        self.assertEqual(subprocess.run([config['recallPython'], '-c',
                                        "import yaml; assert yaml.safe_load('ok: true')['ok']"],
                                       capture_output=True).returncode, 0)

    def test_doctor_reports_missing_yaml_even_without_a_cloud_cli(self):
        (self.policy / 'config.json').write_text('{}')
        result = subprocess.run([sys.executable, '-S', str(SOURCE / 'workgraph_recall.py'),
                                 '--codex-dir', str(self.codex), 'doctor'],
                                env=self.env, capture_output=True, text=True)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'unavailable')
        self.assertFalse(report['runtime']['yaml'])
        self.assertIn('repair', report)
        self.assertNotEqual(result.returncode, 0)

    def test_wrong_interpreter_restarts_saved_runtime_and_searches_without_writes(self):
        registry = self.home / 'registry'
        registry.mkdir()
        memory = self.home / 'memory'
        memory.mkdir()
        (memory / 'example.md').write_text('---\ntype: rule\ntitle: Recall fixture\n---\nRecall runtime verification')
        (registry / 'config.json').write_text(json.dumps({'projects': {'fixture': str(memory)}}))
        (self.codex / 'basic-memory.json').write_text(json.dumps({'basicMemory': {'primaryProject': 'fixture'}}))
        (self.policy / 'config.json').write_text(json.dumps({'recallPython': sys.executable}))
        before = {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, '-S', str(SOURCE / 'workgraph_recall.py'),
                                 '--codex-dir', str(self.codex), 'prepare', '--ticket', 'c'*64,
                                 '--query', 'runtime', '--cwd', str(self.home), '--mode', 'plan'],
                                env={**self.env, 'BASIC_MEMORY_CONFIG_DIR': str(registry),
                                     'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'found')
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()})

    def test_missing_yaml_search_returns_unavailable_with_repair_guidance(self):
        registry = self.home / 'registry'
        registry.mkdir()
        memory = self.home / 'memory'
        memory.mkdir()
        (registry / 'config.json').write_text(json.dumps({'projects': {'fixture': str(memory)}}))
        (self.codex / 'basic-memory.json').write_text('{"basicMemory":{"primaryProject":"fixture"}}')
        (self.policy / 'config.json').write_text('{}')
        result = subprocess.run([sys.executable, '-S', str(SOURCE / 'workgraph_recall.py'),
                                 '--codex-dir', str(self.codex), 'prepare', '--ticket', 'a'*64,
                                 '--query', 'runtime', '--cwd', str(self.home)],
                                env={**self.env, 'BASIC_MEMORY_CONFIG_DIR': str(registry)},
                                capture_output=True, text=True)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'unavailable')
        self.assertEqual(report['error'], 'missing_pyyaml')
        self.assertIn('--update', report['repair'])
        self.assertFalse((self.home / '.workgraph-recall').exists())

    def test_explicit_invalid_runtime_preserves_settings(self):
        (self.policy / 'config.json').write_text('{"custom":42}')
        before = (self.policy / 'config.json').read_bytes()
        result = subprocess.run([sys.executable, str(SOURCE / 'configure_workgraph.py'),
                                 '--codex-dir', str(self.codex)],
                                env={**self.env, 'BM_RECALL_PYTHON': str(self.home / 'missing')},
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.policy / 'config.json').read_bytes(), before)
        self.assertFalse((self.codex / 'hooks.json').exists())


class RuntimeSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def working_probe(self, working):
        return lambda path: {'python': str(Path(path).absolute()), 'yaml': str(path) in working}

    def test_saved_runtime_precedes_discovery_and_keeps_venv_symlink(self):
        python = self.root / 'saved/python'
        python.parent.mkdir()
        python.symlink_to(sys.executable)
        with patch.object(runtime, 'probe', side_effect=self.working_probe({str(python)})), \
             patch.object(runtime.shutil, 'which', return_value=None):
            result = runtime.select({'recallPython': str(python)}, self.root)
        self.assertEqual(result['python'], str(python))

    def test_explicit_invalid_python_does_not_fall_back(self):
        with patch.object(runtime, 'probe', return_value={'yaml': False}), \
             self.assertRaisesRegex(ValueError, 'BM_RECALL_PYTHON'):
            runtime.select({}, self.root, explicit_python=self.root / 'missing')

    def test_discovery_checks_resolved_cli_environment_without_executing_cli(self):
        tools = self.root / 'tools'
        tools.mkdir()
        python = tools / 'python3'
        python.touch()
        cli = tools / 'bm'
        cli.touch()
        alias = self.root / 'bm'
        alias.symlink_to(cli)
        with patch.object(runtime.shutil, 'which', side_effect=lambda name: str(alias) if name == 'bm' else None), \
             patch.object(runtime, 'probe', side_effect=self.working_probe({str(python)})):
            self.assertEqual(runtime.select({}, self.root)['python'], str(python))

    def test_explicit_cli_without_working_python_does_not_fall_back(self):
        with patch.object(runtime, 'cli_path', return_value=self.root / 'bm'), \
             patch.object(runtime, 'probe', return_value={'yaml': False}), \
             self.assertRaisesRegex(ValueError, 'Selected Basic Memory'):
            runtime.select({}, self.root, explicit_cli='bm')

    def test_readonly_selection_never_provisions(self):
        with patch.object(runtime, 'select', return_value=None), \
             patch.object(runtime, 'provision', side_effect=AssertionError('unexpected provisioning')):
            self.assertIsNone(runtime.ensure(self.root, config={}))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_provision_refuses_unmanaged_or_linked_directory(self):
        directory = self.root / 'runtime'
        directory.mkdir()
        (directory / 'user-data').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'Unmanaged'):
            runtime.provision(directory, SOURCE / 'requirements-export.txt')
        alias = self.root / 'linked'
        alias.symlink_to(directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Linked'):
            runtime.provision(alias, SOURCE / 'requirements-export.txt')
        self.assertEqual((directory / 'user-data').read_text(), 'keep')

    def test_failed_pip_preserves_existing_runtime(self):
        directory = self.root / 'runtime'
        directory.mkdir()
        (directory / '.workgraph-runtime.json').write_text(json.dumps({'owner': runtime.OWNER}))
        (directory / 'keep').write_text('existing')
        with patch.object(runtime, 'probe', return_value={'yaml': False}), \
             patch.object(runtime.venv, 'EnvBuilder') as builder, \
             patch.object(runtime.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)), \
             self.assertRaisesRegex(ValueError, 'Could not prepare'):
            runtime.provision(directory, SOURCE / 'requirements-export.txt')
        self.assertEqual((directory / 'keep').read_text(), 'existing')
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['runtime'])

    def test_runtime_is_provisioned_once_and_reused(self):
        directory = self.root / 'runtime'
        def create(stage):
            python = runtime.python_in(stage)
            python.parent.mkdir(parents=True)
            python.touch()
        with patch.object(runtime.venv, 'EnvBuilder') as builder, \
             patch.object(runtime.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as pip, \
             patch.object(runtime, 'probe', side_effect=lambda p: {'yaml': Path(p).exists(), 'python': str(p)}):
            builder.return_value.create.side_effect = create
            first = runtime.provision(directory, SOURCE / 'requirements-export.txt')
            second = runtime.provision(directory, SOURCE / 'requirements-export.txt')
        self.assertEqual(first, second)
        self.assertEqual(pip.call_count, 1)
        self.assertEqual(json.loads((directory / '.workgraph-runtime.json').read_text())['owner'], runtime.OWNER)

    def test_concurrent_unmanaged_directory_is_preserved(self):
        directory = self.root / 'runtime'
        def create(stage):
            python = runtime.python_in(stage)
            python.parent.mkdir(parents=True)
            python.touch()
            directory.mkdir()
            (directory / 'user-data').write_text('keep')
        with patch.object(runtime.venv, 'EnvBuilder') as builder, \
             patch.object(runtime.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
             patch.object(runtime, 'probe', return_value={'yaml': True}), \
             self.assertRaisesRegex(ValueError, 'changed during preparation'):
            builder.return_value.create.side_effect = create
            runtime.provision(directory, SOURCE / 'requirements-export.txt')
        self.assertEqual((directory / 'user-data').read_text(), 'keep')
