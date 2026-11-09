import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from test_ux_gan_harness import h, png


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        (self.directory/'screenshots').mkdir()
        self.context = {'run_id': 'test', 'role': 'reviewer', 'iteration': 0, 'source': 'source-a',
                        'scope': 'scope-a', 'browser': 'local-playwright'}
        h.atomic_json(self.directory/'checkpoint-context.json', self.context)

    def tearDown(self):
        self.temp.cleanup()

    def watch(self, record=None):
        def evidence(result):
            return h.validated_evidence(result, self.directory, 'local-playwright', self.directory,
                                        'test', archive=False)
        return h.role_checkpoint.Progress(self.directory, self.context, h.AUDIT_SCHEMA,
                                          h.validate_schema, evidence, lambda frame: True,
                                          record if record is not None else {})

    def save(self, result, stage='observing', remaining=None):
        h.atomic_json(self.directory/'draft.json', result)
        return h.role_checkpoint.save(self.directory, 'draft.json', stage,
                                      ['check another flow'] if remaining is None else remaining)

    def test_atomic_save_is_private_and_keeps_original_context(self):
        self.save({'reason': 'partial'})
        path = self.directory/'checkpoint.json'
        value = json.loads(path.read_text())
        self.assertEqual(value['context'], self.context)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.directory.glob('*.tmp-*')), [])

    def test_helper_waits_for_host_validation_and_returns_rejection(self):
        watch = self.watch()
        for value, expected in (({'reason': 'partial'}, 0), ({'unknown': 'field'}, 1)):
            with self.subTest(value=value):
                h.atomic_json(self.directory/'draft.json', value)
                request = self.directory/'checkpoint-request.json'
                previous = request.read_bytes() if request.exists() else None
                process = subprocess.Popen([sys.executable, str(Path(h.role_checkpoint.__file__)), 'save',
                    '--directory', str(self.directory), '--input', 'draft.json', '--remaining', 'continue'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    deadline = time.monotonic()+2
                    while time.monotonic() < deadline and (not request.exists() or request.read_bytes() == previous):
                        time.sleep(.02)
                    self.assertTrue(request.exists(), 'Helper must request host validation')
                    self.assertIsNone(process.poll(), 'Saving alone is not host acceptance')
                    watch.poll()
                    stdout, stderr = process.communicate(timeout=3)
                    self.assertEqual(process.returncode, expected, stdout+stderr)
                    if not expected:
                        self.assertEqual(json.loads(stdout)['validation'], 'verified')
                    else:
                        self.assertIn('Unknown partial result fields', stderr)
                finally:
                    if process.poll() is None:
                        process.kill();process.communicate()

    def test_draft_cannot_escape_or_follow_a_link(self):
        outside = self.directory.parent/(self.directory.name+'-outside.json')
        outside.write_text('{}')
        try:
            with self.assertRaises(ValueError):
                h.role_checkpoint.save(self.directory, outside, 'observing', [])
            (self.directory/'linked.json').symlink_to(outside)
            with self.assertRaises(ValueError):
                h.role_checkpoint.save(self.directory, 'linked.json', 'observing', [])
        finally:
            outside.unlink()

    def test_same_results_wording_and_remaining_edits_are_not_new_progress(self):
        watch = self.watch()
        watch.schema = h.obj({'reason': h.S})
        self.save({'reason': 'first wording'})
        self.assertTrue(watch.poll())
        self.save({'reason': 'different wording'}, remaining=['renamed remaining task'])
        self.assertFalse(watch.poll())
        self.assertEqual(watch.latest['result']['reason'], 'different wording')
        self.save({'reason': 'different wording'}, stage='reporting', remaining=[])
        self.assertTrue(watch.poll())
        self.assertFalse(watch.poll())

    def test_restored_seen_progress_is_not_counted_again(self):
        record = {}
        watch = self.watch(record)
        self.save({'reason': ''})
        self.assertTrue(watch.poll())
        restored = self.watch(record)
        self.assertFalse(restored.poll())

    def test_other_source_or_scope_is_never_adopted(self):
        for key in ('source', 'scope', 'role', 'iteration'):
            with self.subTest(key=key):
                self.save({'reason': ''})
                value = json.loads((self.directory/'checkpoint.json').read_text())
                value['context'][key] = 'other'
                h.atomic_json(self.directory/'checkpoint.json', value)
                watch = self.watch()
                self.assertFalse(watch.poll())
                self.assertIsNone(watch.latest)
                self.assertTrue(watch.invalid)

    def test_partial_coverage_cannot_claim_missing_evidence(self):
        self.save({'coverage': [{'flow_id': 'create', 'viewport': 'desktop', 'state': 'normal',
                                'perspective': 'first_time', 'result': 'passed', 'notes': '',
                                'steps': [{'action': 'click', 'before_evidence_id': 'missing',
                                           'after_evidence_id': 'also-missing', 'result': 'saved'}]}]})
        watch = self.watch()
        self.assertFalse(watch.poll())
        self.assertIsNone(watch.latest)

    def test_repeated_browser_operations_do_not_extend_idle(self):
        watch = self.watch()
        receipts = self.directory/'screenshots/browser-receipts.jsonl'
        for index, image in enumerate((png(), png()+b'extra-bytes')):
            path = self.directory/'screenshots'/f'{index}.png'
            path.write_bytes(image)
            frame = {'kind': 'frame', 'id': str(index), 'path': str(path), 'sha256': h.digest(path),
                     'viewport': {'width': 1440, 'height': 900}, 'url': 'http://localhost', 'source': 'live'}
            action = {'kind': 'action', 'tool': 'ux_click', 'args': {'selector': '#same'},
                      'frames': [str(index)], 'url': 'http://localhost'}
            with receipts.open('a') as stream:
                stream.write(json.dumps(frame)+'\n'+json.dumps(action)+'\n')
            self.assertEqual(watch.poll(), index == 0)

    def test_reporting_stage_ignores_new_browser_exploration(self):
        watch = self.watch()
        watch.schema = h.obj({'reason': h.S})
        self.save({'reason': ''}, stage='reporting', remaining=[])
        self.assertTrue(watch.poll())
        path = self.directory/'screenshots/other.png'
        path.write_bytes(png())
        (self.directory/'screenshots/browser-receipts.jsonl').write_text(json.dumps({
            'kind': 'frame', 'id': 'other', 'path': str(path), 'sha256': h.digest(path),
            'viewport': {'width': 1440, 'height': 900}, 'url': 'http://localhost'})+'\n'+json.dumps({
            'kind': 'action', 'tool': 'ux_click', 'args': {'selector': '#new'},
            'frames': ['other'], 'url': 'http://localhost'})+'\n')
        self.assertFalse(watch.poll())

    def test_reporting_cannot_return_to_observation(self):
        watch = self.watch()
        watch.schema = h.obj({'reason': h.S})
        self.save({'reason': ''}, stage='reporting', remaining=[])
        self.assertTrue(watch.poll())
        self.save({'reason': ''}, stage='observing')
        self.assertFalse(watch.poll())
        self.assertEqual(watch.latest['stage'], 'reporting')
        self.assertIn('cannot restart', watch.invalid)

    def test_checkpoint_cannot_drop_a_previously_observed_screen(self):
        watch = self.watch()
        # A planner snapshot uses the same stable-ID preservation rules.
        watch.schema = h.PLAN_SCHEMA
        self.save({'screens': [{'id': 'top', 'name': 'Top', 'url': 'http://localhost'}]})
        self.assertTrue(watch.poll())
        self.save({'screens': []})
        self.assertFalse(watch.poll())
        self.assertEqual(watch.latest['result']['screens'][0]['id'], 'top')
        self.assertIn('dropped earlier', watch.invalid)

    def test_checkpoint_cannot_change_already_verified_image_bytes(self):
        path = self.directory/'screenshots/proof.png'
        path.write_bytes(png())
        frame = {'kind': 'frame', 'id': 'proof', 'path': str(path), 'sha256': h.digest(path),
                 'viewport': {'width': 1440, 'height': 900}, 'url': 'http://localhost', 'source': 'live'}
        receipts = self.directory/'screenshots/browser-receipts.jsonl'
        receipts.write_text(json.dumps(frame)+'\n')
        result = {'evidence': [{'id': 'proof', 'path': str(path), 'screen_id': 'top', 'flow_id': 'create',
                               'description': 'proof', 'target': 'form', 'url': 'http://localhost',
                               'source': 'live', 'viewport': frame['viewport']}]}
        self.save(result)
        watch = self.watch()
        self.assertTrue(watch.poll())
        path.write_bytes(png()+b'changed bytes')
        frame['sha256'] = h.digest(path)
        receipts.write_text(json.dumps(frame)+'\n')
        value = json.loads((self.directory/'checkpoint.json').read_text())
        with self.assertRaisesRegex(ValueError, 'hash|bytes'):
            watch.accept(value)
        with self.assertRaisesRegex(ValueError, 'hash|bytes'):
            watch.verify_latest()
        with self.assertRaisesRegex(ValueError, 'hash|bytes'):
            self.watch(watch.record)


if __name__ == '__main__':
    unittest.main()
