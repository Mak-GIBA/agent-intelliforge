"""Research records remain verifiable without models or external downloads."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('research_archive', ROOT/'scripts/research_archive.py')
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)


class ResearchArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.repo = self.root/'repo'; self.repo.mkdir()
        self.files = {
            'docs/design-research/topic/report.md': b'Report and limitations\n',
            'docs/design-research/topic/runs/R/state.json': b'{"status":"held"}\n',
            'docs/codex-yomiyasu/evidence/demo/README.md': b'Summary\n',
            'docs/codex-yomiyasu/evidence/demo/native/run.json': b'{"status":"completed"}\n',
            'tools/codex-yomiyasu/evaluation-v130/README.md': b'Old protocol\n',
            'tools/codex-yomiyasu/evaluation-v130/assets/guide.md': b'Original guide\n',
            'tools/codex-yomiyasu/evals/flow-v3-baseline.json': b'{"required":true}\n',
            'tools/ecc-on-demand/evaluation/fixture.json': b'{"required":true}\n'}
        for name, raw in self.files.items():
            p = self.repo/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
        self.git('init', '-q'); self.git('add', '.')
        self.git('-c', 'user.name=Archive fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Fixture')
        self.entry = A.build(self.repo, 'HEAD', self.root/'build', 'fixture-archive')
        self.archive = self.root/'build/fixture-archive.tar.gz'

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, stderr=subprocess.STDOUT)

    def altered(self, mutation):
        with tarfile.open(self.archive) as t:
            rows = [(m.name, t.extractfile(m).read()) for m in t.getmembers()]
        rows = mutation(rows)
        dest = self.root/'altered.tar.gz'
        with tarfile.open(dest, 'w:gz') as t:
            for name, raw in rows:
                info = tarfile.TarInfo(name); info.size = len(raw); t.addfile(info, io.BytesIO(raw))
        entry = copy.deepcopy(self.entry)
        entry.update(sha256=A.sha(dest.read_bytes()), archive_bytes=dest.stat().st_size)
        return entry, dest

    def test_restore_all_original_bytes_and_keep_runtime_fixtures_out_of_archive(self):
        self.assertEqual(A.verify(self.entry, self.archive)['files'], 6)
        dest = self.root/'restored'; A.restore(self.entry, self.archive, dest)
        for name, raw in self.files.items():
            if A.group(name):
                self.assertEqual((dest/name).read_bytes(), raw)
            else:
                self.assertFalse((dest/name).exists())
        self.assertEqual((self.repo/'tools/ecc-on-demand/evaluation/fixture.json').read_bytes(), self.files['tools/ecc-on-demand/evaluation/fixture.json'])

    def test_build_is_deterministic_and_reads_committed_data(self):
        (self.repo/'docs/design-research/topic/runs/R/state.json').write_bytes(b'UNCOMMITTED')
        A.build(self.repo, 'HEAD', self.root/'second', 'fixture-archive')
        self.assertEqual((self.root/'second/fixture-archive.tar.gz').read_bytes(), self.archive.read_bytes())
        self.assertEqual((self.repo/'docs/design-research/topic/runs/R/state.json').read_bytes(), b'UNCOMMITTED')

    def test_outer_checksum_rejects_corrupt_archive(self):
        p = self.root/'corrupt'; p.write_bytes(self.archive.read_bytes()+b'x')
        with self.assertRaisesRegex(ValueError, 'checksum or size'):
            A.verify(self.entry, p)

    def test_changed_inner_content_is_rejected_even_with_updated_archive_checksum(self):
        entry, archive = self.altered(lambda rows: [(n, b'wrong' if n.endswith('state.json') else raw) for n, raw in rows])
        with self.assertRaisesRegex(ValueError, 'Archived file differs'):
            A.restore(entry, archive, self.root/'restored')
        self.assertFalse((self.root/'restored').exists())

    def test_missing_duplicate_and_unsafe_members_are_rejected(self):
        mutations = [lambda rows: rows[:-1], lambda rows: rows+[rows[0]],
                     lambda rows: rows+[('records/../escape', b'bad')]]
        for mutation in mutations:
            entry, archive = self.altered(mutation)
            with self.assertRaises((ValueError, KeyError)):
                A.restore(entry, archive, self.root/'restored')
            self.assertFalse((self.root/'escape').exists())
            self.assertFalse((self.root/'restored').exists())

    def test_restore_refuses_existing_destination(self):
        dest = self.root/'existing'; dest.mkdir(); (dest/'user.txt').write_bytes(b'Keep me')
        with self.assertRaisesRegex(ValueError, 'must not exist'):
            A.restore(self.entry, self.archive, dest)
        self.assertEqual((dest/'user.txt').read_bytes(), b'Keep me')

    def test_download_failure_and_reintroduced_records_do_not_pass(self):
        with patch.object(A.urllib.request, 'urlopen', side_effect=urllib.error.URLError('offline')):
            with self.assertRaises(urllib.error.URLError):
                with A.archive_file(self.entry):
                    self.fail('Download failure was ignored')
        registry = self.root/'build/registry.json'
        with self.assertRaisesRegex(ValueError, 'tracked'):
            A.check_tree(self.repo, registry)
        inventory = json.loads((self.root/'build/inventory.json').read_text())
        removed = [n for n, row in inventory['files'].items() if row['removed']]
        self.git('rm', '--', *removed)
        self.assertEqual(A.check_tree(self.repo, registry)['status'], 'passed')

    def test_new_raw_runs_and_local_artifacts_are_not_a_bypass(self):
        inventory = json.loads((self.root/'build/inventory.json').read_text())
        self.git('rm', '--', *[n for n, row in inventory['files'].items() if row['removed']])
        for name in ('docs/design-research/new/runs/NEW/state.json', '.artifacts/new/state.json'):
            p = self.repo/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'{}')
            self.git('add', '-f', '--', name)
            with self.assertRaisesRegex(ValueError, 'Raw run records'):
                A.check_tree(self.repo, self.root/'build/registry.json')
            self.git('rm', '-f', '--', name)


if __name__ == '__main__':
    unittest.main()
