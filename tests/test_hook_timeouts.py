"""Bound hook latency without recording prompts or changing read-only state."""
import contextlib
import fcntl
import importlib.util
import io
import json
import signal
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / 'tools/basic-memory-workgraph'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HookTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.hook = load('timeout_hook', SOURCE / 'hooks/basic_memory_workgraph.py')
        self.hook.ROOT = self.root
        (self.root / 'config.json').write_text('{"mode":"smart"}')
        (self.root / 'memory-policy.md').write_text('fixture policy')
        self.event = {'session_id': 'fixture', 'turn_id': 'turn', 'cwd': str(self.root),
                      'prompt': 'private fixture prompt must not be logged'}

    def invoke(self, event=None, action='recall'):
        output = io.StringIO()
        with mock.patch('sys.argv', ['hook', action]), mock.patch('sys.stdin', io.StringIO(json.dumps(event or self.event))), contextlib.redirect_stdout(output):
            self.hook.main()
        return json.loads(output.getvalue())

    def test_busy_state_lock_returns_unavailable_and_preserves_state(self):
        state = self.hook.state_path(self.event)
        state.parent.mkdir()
        state.write_text('{"preserve":true}')
        with (state.parent / '.lock').open('w+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            # A safety alarm stops the old implementation hanging this test.
            previous = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(AssertionError('unbounded lock wait')))
            signal.setitimer(signal.ITIMER_REAL, 2)
            started = time.monotonic()
            try:
                result = self.invoke()
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous)
        self.assertLess(time.monotonic() - started, 1.8)
        self.assertIn('unavailable', result['hookSpecificOutput']['additionalContext'])
        self.assertEqual(json.loads(state.read_text()), {'preserve': True})

    def test_whole_hook_deadline_interrupts_a_stalled_reader(self):
        with mock.patch.object(self.hook, 'HOOK_TIMEOUT_SECONDS', .08, create=True), mock.patch.object(self.hook, 'evaluate', side_effect=lambda *_: time.sleep(.3)):
            started = time.monotonic()
            result = self.invoke()
        self.assertLess(time.monotonic() - started, .25)
        self.assertIn('unavailable', result['hookSpecificOutput']['additionalContext'])
        records = [json.loads(line) for line in (self.root / 'hook-diagnostics.jsonl').read_text().splitlines()]
        self.assertEqual(records[-1]['status'], 'deadline_exceeded')
        self.assertNotIn('private fixture', json.dumps(records))

    def test_diagnostic_log_is_bounded_and_private(self):
        with mock.patch.object(self.hook, 'evaluate', return_value={}):
            self.invoke()
            path = self.root / 'hook-diagnostics.jsonl'
            self.assertTrue(path.is_file())
            path.write_text('x' * 65536)
            self.invoke()
        self.assertLess(path.stat().st_size, 65536)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(path.read_text().splitlines()[-1])['status'], 'complete')

    def test_explicit_plan_never_creates_state_or_logs(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with mock.patch.object(self.hook, 'retrieved_context', return_value='Read-only fixture'):
            self.invoke({**self.event, 'permission_mode': 'plan'})
            self.invoke({**self.event, 'permission_mode': 'plan'}, 'save')
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_runtime_reexec_preserves_event_input(self):
        hooks = self.root / 'codex/hooks'
        hooks.mkdir(parents=True)
        installed = hooks / 'basic_memory_workgraph.py'
        installed.write_bytes((SOURCE / 'hooks/basic_memory_workgraph.py').read_bytes())
        policy = hooks.parent / 'basic-memory-workgraph'
        policy.mkdir()
        (policy / 'config.json').write_text('{"mode":"smart"}')
        (policy / 'memory-policy.md').write_text('fixture policy')
        (policy / 'recall_runtime.py').write_text(
            "import os,sys\n"
            "def reexec_if_needed(*args, **kwargs):\n"
            " if not os.environ.get('_WORKGRAPH_RECALL_REEXEC'):\n"
            "  os.execve(sys.executable,[sys.executable,*sys.argv],{**os.environ,'_WORKGRAPH_RECALL_REEXEC':'1'})\n")
        env = {k: v for k, v in os.environ.items() if k not in ('_WORKGRAPH_RECALL_REEXEC', '_WORKGRAPH_HOOK_DEADLINE')}
        result = subprocess.run([sys.executable, '-B', str(installed), 'recall'],
                                input=json.dumps({**self.event, 'permission_mode': 'plan'}),
                                env=env, capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('hookSpecificOutput', json.loads(result.stdout))

    def test_stop_lock_timeout_does_not_delete_pending_capture(self):
        state = self.hook.state_path(self.event)
        state.parent.mkdir()
        original = '{"armed":true,"capture_pending":true}'
        state.write_text(original)
        with (state.parent / '.lock').open('w+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            result = self.invoke(action='save')
        self.assertIn('lock_timeout', result['systemMessage'])
        self.assertEqual(state.read_text(), original)

    def test_application_lock_timeout_preserves_pending_state(self):
        state = self.hook.state_path(self.event)
        state.parent.mkdir()
        original = '{"armed":true,"capture_pending":true}'
        state.write_text(original)
        service = mock.Mock()
        service.stop.side_effect = TimeoutError('fixture application lock')
        with mock.patch.object(self.hook, 'recall_service', return_value=service):
            result = self.invoke(action='save')
        self.assertTrue(state.exists(), 'Failed application check must not consume pending capture')
        self.assertEqual(state.read_text(), original)
        self.assertIn('lock_timeout', result['systemMessage'])

    def test_whole_deadline_also_covers_runtime_binding(self):
        runtime = self.root / 'recall_runtime.py'
        runtime.write_text('import time\ndef reexec_if_needed(*args,**kwargs): time.sleep(.3)\n')
        with mock.patch.object(self.hook, 'HOOK_TIMEOUT_SECONDS', .08):
            started = time.monotonic()
            result = self.invoke()
        self.assertLess(time.monotonic() - started, .25)
        self.assertIn('runtime_binding', result['hookSpecificOutput']['additionalContext'])

    def test_deadline_kills_stalled_external_command(self):
        child = None
        real_popen = subprocess.Popen
        def capture_child(*args, **kwargs):
            nonlocal child
            child = real_popen(*args, **kwargs)
            return child
        def stalled(*_):
            subprocess.run([sys.executable, '-c', 'import time; time.sleep(10)'], capture_output=True)
        with mock.patch.object(self.hook, 'HOOK_TIMEOUT_SECONDS', 1), mock.patch.object(self.hook, 'bind_runtime'), mock.patch.object(self.hook, 'evaluate', side_effect=stalled), mock.patch('subprocess.Popen', side_effect=capture_child):
            result = self.invoke()
        self.assertIn('deadline_exceeded', result['hookSpecificOutput']['additionalContext'])
        self.assertIsNotNone(child.poll())


class RecallDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.recall = load('timeout_recall', SOURCE / 'workgraph_recall.py')

    def test_empty_local_scan_must_not_report_success_after_deadline(self):
        reader = self.recall.RegisteredReader([])
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(reader, 'local_root', return_value=Path(directory)):
            with self.assertRaises((TimeoutError, ValueError)):
                reader.documents('fixture', time.monotonic() - 1)

    def test_repository_probe_uses_remaining_budget(self):
        with mock.patch.object(self.recall.subprocess, 'run') as run:
            with self.assertRaises(TimeoutError):
                self.recall.repository_scope(Path.cwd(), deadline=time.monotonic() - 1)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
