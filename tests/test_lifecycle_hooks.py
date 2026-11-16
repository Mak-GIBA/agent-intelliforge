"""Install and exercise bounded native lifecycle hooks without a plugin cold start."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import types
import signal
import unittest
from unittest import mock

try:
    import tomllib
except ImportError:
    import tomli as tomllib

SOURCE = Path(__file__).resolve().parents[1] / 'tools/basic-memory-workgraph'
sys.path.insert(0, str(SOURCE))
import configure_workgraph as configuration

NATIVE = 'codex@basic-memory:hooks/hooks.json:session_start:0:0'


class LifecycleInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.codex = Path(self.tmp.name) / "codex ' with spaces"
        self.codex.mkdir()
        self.settings = self.codex / 'config.toml'
        self.original = 'model = "fixture"\n# keep this comment\n[features]\nhooks = true\n'
        self.original += '\n[hooks.state.' + json.dumps(NATIVE) + ']\ntrusted_hash = "fixture"\nenabled = true # keep reason\n'
        self.settings.write_text(self.original)
        sibling = {'type': 'command', 'command': 'other-startup'}
        (self.codex / 'hooks.json').write_text(json.dumps({'hooks': {'SessionStart': [{'hooks': [sibling]}]}}))

    def configure(self):
        with mock.patch.object(configuration, 'recall_environment', return_value={'python': sys.executable}):
            configuration.configure(self.codex)

    def test_install_replaces_native_startup_and_keeps_other_hooks(self):
        self.configure()
        hooks = json.loads((self.codex / 'hooks.json').read_text())['hooks']
        commands = [entry['command'] for group in hooks['SessionStart'] for entry in group['hooks']]
        self.assertIn('other-startup', commands)
        self.assertTrue(any(command.endswith(' session-start') for command in commands), commands)
        self.assertTrue(any(entry['command'].endswith(' pre-compact') for group in hooks['PreCompact'] for entry in group['hooks']))
        self.assertFalse(tomllib.loads(self.settings.read_text())['hooks']['state'][NATIVE]['enabled'])
        self.assertIn('# keep this comment', self.settings.read_text())
        self.assertIn('# keep reason', self.settings.read_text())

    def test_second_install_is_idempotent_and_uninstall_restores_native(self):
        self.configure()
        first = (self.codex / 'hooks.json').read_bytes()
        self.configure()
        self.assertEqual(first, (self.codex / 'hooks.json').read_bytes())
        removal = subprocess.run(['bash', str(SOURCE / 'remove_workgraph_hooks.sh')],
                                 env={**os.environ, 'CODEX_HOME': str(self.codex)}, capture_output=True, text=True)
        self.assertEqual(removal.returncode, 0, removal.stderr)
        self.assertTrue(tomllib.loads(self.settings.read_text())['hooks']['state'][NATIVE]['enabled'])
        hooks = json.loads((self.codex / 'hooks.json').read_text())['hooks']
        self.assertEqual(hooks['SessionStart'][0]['hooks'][0]['command'], 'other-startup')
        self.assertNotIn('PreCompact', hooks)

    def test_explicitly_disabled_native_stays_disabled(self):
        self.settings.write_text(self.original.replace('enabled = true', 'enabled = false'))
        self.configure()
        hooks = json.loads((self.codex / 'hooks.json').read_text())['hooks']
        commands = [entry['command'] for group in hooks['SessionStart'] for entry in group['hooks']]
        self.assertFalse(any(command.endswith(' session-start') for command in commands))

    def test_uninstall_uses_saved_runtime_when_system_python_has_no_toml(self):
        self.configure()
        binary = Path(self.tmp.name) / 'system-bin'
        binary.mkdir()
        shim = binary / 'without_toml.py'
        shim.write_text(
            'import builtins, sys\n'
            'original = builtins.__import__\n'
            'def limited(name, *args, **kwargs):\n'
            ' if name in ("tomllib", "tomli"): raise ModuleNotFoundError(name)\n'
            ' return original(name, *args, **kwargs)\n'
            'builtins.__import__ = limited\n'
            'sys.argv = sys.argv[1:]\n'
            'exec(compile(sys.stdin.read(), "<system-python>", "exec"))\n')
        launcher = binary / 'python3'
        launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(shim)) + ' "$@"\n')
        launcher.chmod(0o755)
        env = {key: value for key, value in os.environ.items() if key not in ('BM_RECALL_PYTHON', 'PYTHON_BIN')}
        env.update(CODEX_HOME=str(self.codex), PATH=str(binary) + os.pathsep + os.environ['PATH'])
        removal = subprocess.run(['bash', str(SOURCE / 'remove_workgraph_hooks.sh')], env=env, capture_output=True, text=True)
        self.assertEqual(removal.returncode, 0, removal.stderr)
        self.assertTrue(tomllib.loads(self.settings.read_text())['hooks']['state'][NATIVE]['enabled'])
        self.assertFalse((self.codex / 'basic-memory-workgraph').exists())
        hooks = json.loads((self.codex / 'hooks.json').read_text())['hooks']
        self.assertEqual(hooks['SessionStart'][0]['hooks'][0]['command'], 'other-startup')

    def test_invalid_toml_makes_no_installation_changes(self):
        self.settings.write_text('[broken')
        before = {p.relative_to(self.codex): p.read_bytes() for p in self.codex.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError):
            self.configure()
        self.assertEqual(before, {p.relative_to(self.codex): p.read_bytes() for p in self.codex.rglob('*') if p.is_file()})

    def test_missing_saved_runtime_preserves_installation_until_explicit_override(self):
        self.configure()
        config = self.codex / 'basic-memory-workgraph/config.json'
        settings = json.loads(config.read_text())
        settings['recallPython'] = str(Path(self.tmp.name) / 'missing-python')
        config.write_text(json.dumps(settings))
        before = {p.relative_to(self.codex): p.read_bytes() for p in self.codex.rglob('*') if p.is_file()}
        env = {key: value for key, value in os.environ.items() if key not in ('BM_RECALL_PYTHON', 'PYTHON_BIN')}
        env['CODEX_HOME'] = str(self.codex)
        removal = subprocess.run(['bash', str(SOURCE / 'remove_workgraph_hooks.sh')], env=env, capture_output=True, text=True)
        self.assertNotEqual(removal.returncode, 0)
        self.assertIn('BM_RECALL_PYTHON', removal.stderr)
        self.assertEqual(before, {p.relative_to(self.codex): p.read_bytes() for p in self.codex.rglob('*') if p.is_file()})
        removal = subprocess.run(['bash', str(SOURCE / 'remove_workgraph_hooks.sh')],
            env={**env, 'BM_RECALL_PYTHON': sys.executable}, capture_output=True, text=True)
        self.assertEqual(removal.returncode, 0, removal.stderr)
        self.assertTrue(tomllib.loads(self.settings.read_text())['hooks']['state'][NATIVE]['enabled'])
        self.assertFalse((self.codex / 'basic-memory-workgraph').exists())


class LifecycleRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        spec = importlib.util.spec_from_file_location('lifecycle_runtime', SOURCE / 'hooks/basic_memory_workgraph.py')
        self.hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.hook)
        self.hook.ROOT = self.root
        (self.root / 'config.json').write_text(json.dumps({'recallCli': [sys.executable, '-c',
            'import sys;sys.stdin.read();print("NATIVE_BRIEF_OK")']}))

    def invoke(self, action='session-start'):
        output = io.StringIO()
        with mock.patch('sys.argv', ['hook', action]), mock.patch('sys.stdin', io.StringIO('{"source":"startup"}')), contextlib.redirect_stdout(output):
            self.hook.main()
        return output.getvalue()

    def test_native_success_is_forwarded_for_both_lifecycle_events(self):
        for action in ('session-start', 'pre-compact'):
            with self.subTest(action=action):
                self.assertEqual(self.invoke(action).strip(), 'NATIVE_BRIEF_OK')

    def test_timeout_returns_unavailable_and_kills_children(self):
        (self.root / 'config.json').write_text(json.dumps({'recallCli': [sys.executable, '-c',
            'import time;time.sleep(10)']}))
        with mock.patch.object(self.hook, 'HOOK_TIMEOUT_SECONDS', .15):
            started = time.monotonic()
            result = self.invoke()
        self.assertLess(time.monotonic() - started, 1)
        self.assertIn('unavailable', result)
        self.assertIn('deadline_exceeded', result)
        self.assertEqual(json.loads(result)['hookSpecificOutput']['hookEventName'], 'SessionStart')

    def test_failed_native_does_not_expose_backend_errors(self):
        (self.root / 'config.json').write_text(json.dumps({'recallCli': [sys.executable, '-c',
            'import sys;print("private-backend-error",file=sys.stderr);sys.exit(1)']}))
        result = self.invoke()
        self.assertIn('unavailable', result)
        self.assertNotIn('private-backend-error', result)

    def test_compaction_empty_success_is_not_a_failure(self):
        (self.root / 'config.json').write_text(json.dumps({'recallCli': [sys.executable, '-c', 'pass']}))
        self.assertEqual(self.invoke('pre-compact').strip(), '')

    def test_lifecycle_deadline_without_posix_alarm(self):
        (self.root / 'config.json').write_text(json.dumps({'recallCli': [sys.executable, '-c', 'import time;time.sleep(10)']}))
        with mock.patch.object(self.hook, 'signal', types.SimpleNamespace(SIGKILL=signal.SIGKILL)), mock.patch.object(self.hook, 'HOOK_TIMEOUT_SECONDS', .1):
            result = self.invoke()
        self.assertIn('deadline_exceeded', result)

    def test_explicit_plan_does_not_start_native_capture(self):
        with mock.patch('sys.argv', ['hook', 'session-start']), mock.patch('sys.stdin', io.StringIO('{"permission_mode":"plan"}')), mock.patch.object(self.hook.subprocess, 'Popen') as child, contextlib.redirect_stdout(io.StringIO()) as output:
            self.hook.main()
        child.assert_not_called()
        self.assertIn('read_only', output.getvalue())
        self.assertFalse((self.root / 'hook-diagnostics.jsonl').exists())

    @unittest.skipUnless(Path('/proc').is_dir(), 'Linux process-lifetime assertion')
    def test_timeout_kills_descendant_even_if_native_parent_already_exited(self):
        pidfile = self.root / 'child-pid'
        code = ('import subprocess,sys;from pathlib import Path;'
                'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(10)"]);'
                f'Path({str(pidfile)!r}).write_text(str(p.pid))')
        (self.root / 'config.json').write_text(json.dumps({'recallCli': [sys.executable, '-c', code]}))
        with mock.patch.object(self.hook, 'HOOK_TIMEOUT_SECONDS', .6):
            result = self.invoke()
        self.assertTrue(pidfile.exists(), 'Fixture must spawn the descendant before the deadline')
        child = int(pidfile.read_text())
        try:
            self.assertIn('deadline_exceeded', result)
            for _ in range(20):
                status = Path('/proc') / str(child) / 'stat'
                if not status.exists() or status.read_text().split()[2] == 'Z':
                    break
                time.sleep(.01)
            else:
                self.fail('Native parent exited, but its descendant survived the hook deadline')
        finally:
            try:os.kill(child, signal.SIGKILL)
            except ProcessLookupError:pass


if __name__ == '__main__':
    unittest.main()
