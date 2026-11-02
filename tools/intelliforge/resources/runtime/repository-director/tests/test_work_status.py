"""Read-only branch evidence from real, isolated Git repositories."""
import importlib.util
import json
import os
from pathlib import Path
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'skill/scripts/repository.py'
SPEC = importlib.util.spec_from_file_location('work_status_subject', SCRIPT)
repository = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(repository)


class WorkStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        config = Path(self.temp.name) / 'gitconfig'; config.write_text('', encoding="utf-8", newline="\n")
        environment = patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(config), 'GIT_CONFIG_NOSYSTEM': '1'})
        environment.start(); self.addCleanup(environment.stop)
        self.root = Path(self.temp.name) / '日本語 project'; self.root.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.root / 'shared.txt').write_text('original\n', encoding="utf-8", newline="\n")
        (self.root / 'other.txt').write_text('original\n', encoding="utf-8", newline="\n")
        self.git('add', '.'); self.git('commit', '-qm', 'base')

    def git(self, *args, root=None):
        return subprocess.check_output(['git', '-C', str(root or self.root), *args],
                                       stderr=subprocess.PIPE).decode().strip()

    def change(self, branch, path, text):
        self.git('switch', '-qc', branch)
        (self.root / path).write_text(text, encoding="utf-8", newline="\n")
        self.git('add', path); self.git('commit', '-qm', branch)

    def status(self, *args, code=0, project=None):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), 'work-status',
                                 '--project', str(project or self.root), '--base', 'main', *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stderr)
        return json.loads(result.stdout) if code == 0 else result

    def snapshot(self):
        return {str(p.relative_to(Path(self.temp.name))): p.read_bytes()
                for p in Path(self.temp.name).rglob('*') if p.is_file()}

    def test_branch_evidence_and_overlap_include_pending_changes_without_mutation(self):
        self.change('peer', 'shared.txt', 'peer\n')
        self.git('switch', '-q', 'main')
        self.change('task', 'other.txt', 'task\n')
        (self.root / 'shared.txt').write_text('pending\n', encoding="utf-8", newline="\n")
        (self.root / 'new\n日本語.txt').write_text('private contents never returned\n', encoding="utf-8", newline="\n")
        before = self.snapshot()
        value = self.status('--compare', 'peer')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(value['current']['branch'], 'task')
        self.assertEqual(value['current']['sha'], self.git('rev-parse', 'HEAD'))
        self.assertEqual(value['base']['sha'], self.git('rev-parse', 'main'))
        self.assertEqual(value['changes']['unstaged'][0]['path'], 'shared.txt')
        self.assertEqual(value['changes']['untracked'][0]['path'], 'new\n日本語.txt')
        self.assertEqual(value['comparisons'][0]['overlap_paths'], ['shared.txt'])
        self.assertEqual(value['comparisons'][0]['changed_paths'], ['shared.txt'])
        self.assertEqual(value['remote_freshness'], 'not_checked')
        self.assertEqual(value['conflicts'], 'not_checked')
        self.assertNotIn('private contents', json.dumps(value))

    def test_base_only_changes_are_not_reported_as_task_overlap(self):
        self.change('peer', 'other.txt', 'peer\n')
        self.git('switch', '-q', 'main')
        self.change('task', 'shared.txt', 'task\n')
        self.git('switch', '-q', 'main')
        (self.root / 'other.txt').write_text('new base\n', encoding="utf-8", newline="\n")
        self.git('add', '.'); self.git('commit', '-qm', 'base advances')
        self.git('switch', '-q', 'task')
        value = self.status('--compare', 'peer')
        branch = next(b for b in value['branches'] if b['name'] == 'task')
        self.assertEqual((branch['ahead'], branch['behind']), (1, 1))
        self.assertFalse(branch['contained_in_base'])
        self.assertEqual(value['comparisons'][0]['overlap_paths'], [])
        self.assertEqual(value['current']['changed_paths'], ['shared.txt'])

    def test_staged_rename_keeps_both_paths_and_unstaged_state(self):
        self.change('peer', 'shared.txt', 'peer\n')
        self.git('switch', '-q', 'main')
        self.git('mv', 'shared.txt', 'renamed 日本語.txt')
        (self.root / 'renamed 日本語.txt').write_text('pending\n', encoding="utf-8", newline="\n")
        value = self.status('--compare', 'peer')
        self.assertEqual(value['changes']['staged'][0]['original_path'], 'shared.txt')
        self.assertEqual(value['changes']['staged'][0]['path'], 'renamed 日本語.txt')
        self.assertEqual(value['changes']['unstaged'][0]['path'], 'renamed 日本語.txt')
        self.assertEqual(value['comparisons'][0]['overlap_paths'], ['shared.txt'])

    def test_linked_worktrees_are_listed_and_preserved_from_subdirectory(self):
        linked = Path(self.temp.name) / '別作業 folder'
        self.git('worktree', 'add', '-q', '-b', 'parallel', str(linked))
        (linked / 'shared.txt').write_text('other work\n', encoding="utf-8", newline="\n")
        package = self.root / 'package'; package.mkdir()
        before = self.snapshot()
        value = self.status(project=package)
        self.assertEqual(self.snapshot(), before)
        other = next(w for w in value['worktrees'] if w['path'] == str(linked))
        self.assertEqual(other['branch'], 'parallel')
        self.assertTrue(other['dirty'])
        self.assertEqual(value['repository'], str(self.root))

    def test_containment_is_ancestry_only_and_missing_upstream_is_unknown(self):
        self.change('task', 'shared.txt', 'task\n')
        self.git('branch', 'squashed-candidate')
        self.git('switch', '-q', 'main')
        self.git('merge', '--squash', 'task'); self.git('commit', '-qm', 'squash')
        self.git('config', 'branch.task.remote', '.')
        self.git('config', 'branch.task.merge', 'refs/heads/missing')
        value = self.status()
        task = next(b for b in value['branches'] if b['name'] == 'task')
        self.assertFalse(task['contained_in_base'])
        self.assertEqual(task['upstream']['status'], 'unavailable')
        main = next(b for b in value['branches'] if b['name'] == 'main')
        self.assertTrue(main['contained_in_base'])

    def test_detached_and_unborn_head_are_distinguished(self):
        self.git('checkout', '-q', '--detach')
        value = self.status()
        self.assertIsNone(value['current']['branch'])
        self.assertIsNotNone(value['current']['sha'])
        self.git('checkout', '-q', '--orphan', 'new-history')
        value = self.status()
        self.assertEqual(value['current']['branch'], 'new-history')
        self.assertIsNone(value['current']['sha'])
        self.assertIsNone(value['current']['changed_paths'])

    def test_unrelated_history_has_unknown_overlap_instead_of_empty_success(self):
        self.git('checkout', '-q', '--orphan', 'unrelated')
        self.git('commit', '-qm', 'independent root')
        self.git('switch', '-q', 'main')
        value = self.status('--compare', 'unrelated')
        self.assertIsNone(value['comparisons'][0]['changed_paths'])
        self.assertIsNone(value['comparisons'][0]['overlap_paths'])
        self.assertTrue(value['warnings'])

    def test_missing_refs_and_non_repository_fail_without_changing_files(self):
        before = self.snapshot()
        result = self.status('--compare', 'missing', code=2)
        self.assertIn('Cannot resolve revision', result.stderr)
        self.assertEqual(self.snapshot(), before)
        outside = Path(self.temp.name) / 'not git'; outside.mkdir()
        self.assertIn('Cannot inspect Git repository', self.status(project=outside, code=2).stderr)
        fresh = Path(self.temp.name) / 'empty git'; fresh.mkdir()
        self.git('init', '-q', '-b', 'main', root=fresh)
        self.assertIn('Cannot resolve revision', self.status(project=fresh, code=2).stderr)

    def test_gitlink_changes_are_not_hidden(self):
        initial = self.git('rev-parse', 'HEAD')
        self.git('update-index', '--add', '--cacheinfo', '160000,' + initial + ',module')
        self.git('commit', '-qm', 'add gitlink')
        self.change('task', 'other.txt', 'new commit\n')
        target = self.git('rev-parse', 'HEAD')
        self.git('update-index', '--cacheinfo', '160000,' + target + ',module')
        self.assertIn('module', [c['path'] for c in self.status()['changes']['staged']])
        self.git('commit', '-qm', 'move gitlink')
        self.assertIn('module', self.status()['current']['changed_paths'])

    def test_failed_reads_raise_instead_of_returning_empty_inventory(self):
        actual = subprocess.run
        def failing(argv, **kwargs):
            if 'for-each-ref' in argv:
                return subprocess.CompletedProcess(argv, 128, b'', b'unavailable')
            return actual(argv, **kwargs)
        with patch.object(repository.subprocess, 'run', side_effect=failing):
            with self.assertRaisesRegex(ValueError, 'Cannot inspect Git repository'):
                repository.work_status(self.root, 'main')

    def test_refs_moving_during_inspection_are_reported(self):
        self.change('peer', 'shared.txt', 'peer\n')
        self.git('switch', '-q', 'main')
        old_base = self.git('rev-parse', 'main')
        actual = subprocess.run; changed = False
        def moving(argv, **kwargs):
            nonlocal changed
            if 'worktree' in argv and not changed:
                changed = True
                actual(['git', '-C', str(self.root), 'update-ref', 'refs/heads/main', 'peer'], check=True)
            return actual(argv, **kwargs)
        with patch.object(repository.subprocess, 'run', side_effect=moving):
            value = repository.work_status(self.root, 'main')
        self.assertEqual(value['base']['sha'], old_base)
        self.assertFalse(value['refs_consistent'])
        self.assertTrue(any('Refs changed' in w for w in value['warnings']))

    @unittest.skipIf(os.name == 'nt', 'POSIX executable fixture')
    def test_fsmonitor_and_external_diff_are_not_executed(self):
        self.change('task', 'shared.txt', 'task\n')
        script = Path(self.temp.name) / 'forbidden.sh'
        marker = Path(self.temp.name) / 'executed'
        script.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n', encoding="utf-8", newline="\n")
        script.chmod(0o755)
        self.git('config', 'core.fsmonitor', str(script))
        self.git('config', 'diff.external', str(script))
        self.status('--compare', 'main')
        self.assertFalse(marker.exists())

    def test_clean_filters_are_disabled_and_uncertainty_is_reported(self):
        import shlex
        helper = Path(self.temp.name) / 'clean.py'
        marker = Path(self.temp.name) / 'clean-called'
        helper.write_text('from pathlib import Path\nimport sys\nPath(' + repr(str(marker)) +
                          ').write_text("called")\nsys.stdout.buffer.write(sys.stdin.buffer.read())\n', encoding="utf-8", newline="\n")
        (self.root / '.gitattributes').write_text('shared.txt filter=fixture\n', encoding="utf-8", newline="\n")
        self.git('add', '.gitattributes'); self.git('commit', '-qm', 'attributes')
        command = shlex.quote(sys.executable) + ' ' + shlex.quote(str(helper))
        self.git('config', 'filter.fixture.clean', command)
        self.git('config', 'filter.fixture.required', 'true')
        (self.root / 'shared.txt').write_text('modified\n', encoding="utf-8", newline="\n")
        before = self.snapshot()
        value = self.status()
        self.assertFalse(marker.exists())
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(value['changes_status'], 'filter_callbacks_disabled')
        self.assertTrue(value['warnings'])
        self.assertIsNone(value['worktrees'][0]['dirty'])



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__ == '__main__': unittest.main()
