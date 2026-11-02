"""Test local Git/forge recipes and the trial observer, not model decisions or real APIs."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from workflow import prepare, git, inspect


class WorkflowFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)

    def cli(self, root, name, *args):
        return subprocess.run([str(root / '.fixture' / name), *args], capture_output=True, text=True)

    def change(self, root, branch=None):
        if branch: git(root, 'switch', '-qc', branch)
        source = root / 'shipping.py'
        source.write_text(source.read_text().replace('total > 5000', 'total >= 5000'))
        git(root, 'add', 'shipping.py'); git(root, 'commit', '-qm', '5,000円以上の注文を送料無料にする')
        git(root, 'push', '-qu', 'origin', 'HEAD')

    def test_timeout_is_reconciled_without_recreating_or_moving_base(self):
        root = prepare(Path(self.temp.name), 'novice')
        before = git(root, 'rev-parse', 'main')
        self.change(root, 'work/free-shipping')
        body = root / '.fixture/body.md'; body.write_text('5,000円ちょうどの注文も送料無料にします。')
        result = self.cli(root, 'gh', 'pr', 'create', '--base', 'main', '--head', 'work/free-shipping',
                          '--title', '送料の境界を修正する', '--body-file', str(body))
        self.assertNotEqual(result.returncode, 0)  # accepted remotely before the simulated timeout
        result = self.cli(root, 'gh', 'pr', 'list', '--head', 'work/free-shipping', '--state', 'all')
        self.assertEqual(len(json.loads(result.stdout)), 1)
        result = self.cli(root, 'gh', 'pr', 'view', '1')
        self.assertEqual(json.loads(result.stdout)['headRefOid'], git(root, 'rev-parse', 'HEAD'))
        state = json.loads((root / '.fixture/state.json').read_text())
        self.assertEqual(state['create_attempts'], 1)
        self.assertEqual(git(root, 'rev-parse', 'main'), before)

    def test_continuation_edits_existing_pr_and_leaves_unrelated_change_unstaged(self):
        root = prepare(Path(self.temp.name), 'continuation')
        self.change(root)
        before = json.loads((root / '.fixture/state.json').read_text())['request']['body']
        body = root / '.fixture/body.md'; body.write_text(before + '\n境界の修正を追加しました。')
        self.assertEqual(self.cli(root, 'gh', 'pr', 'edit', '1', '--body-file', str(body)).returncode, 0)
        state = json.loads((root / '.fixture/state.json').read_text())
        self.assertEqual((state['create_attempts'], state['edit_attempts']), (0, 1))
        self.assertIn('担当者の注記', state['request']['body'])
        self.assertEqual(git(root, 'status', '--short'), 'M notes.txt')
        self.assertEqual(git(root, 'show', 'HEAD:notes.txt'), 'human notes')

    def test_gitlab_recipe_uses_team_target_and_exposes_head_and_draft(self):
        root = prepare(Path(self.temp.name), 'team-policy')
        self.change(root, 'work/free-shipping')
        payload = root / '.fixture/mr.json'
        payload.write_text(json.dumps({'source_branch': 'work/free-shipping', 'target_branch': 'integration',
                                       'title': '送料の境界を修正する', 'description': '5,000円以上を送料無料にします。'}))
        result = self.cli(root, 'glab', 'api', '--method', 'POST', 'projects/example%2Fcatalog/merge_requests', '--input', str(payload))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli(root, 'glab', 'mr', 'view', '1', '--output', 'json')
        value = json.loads(result.stdout)
        self.assertEqual(value['target_branch'], 'integration')
        self.assertEqual(value['sha'], git(root, 'rev-parse', 'HEAD'))
        self.assertFalse(value['draft'])

    def test_auth_failure_is_not_an_empty_collection_or_a_write(self):
        root = prepare(Path(self.temp.name), 'incomplete')
        for args in [('auth', 'status'), ('mr', 'list'), ('mr', 'create', '--title', 'must not publish')]:
            result = self.cli(root, 'glab', *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('authentication unavailable', result.stderr)
        self.assertIsNone(json.loads((root / '.fixture/state.json').read_text())['request'])
        result = subprocess.run(['python3', 'integration_check.py'], cwd=root, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_observer_and_remote_head_follow_a_permitted_work_copy(self):
        root = prepare(Path(self.temp.name), 'continuation')
        copy = root / '.fixture/work'
        git(root, 'clone', '-q', str(root / '.fixture/remote.git'), str(copy))
        git(copy, 'switch', '-q', 'work/free-shipping')
        git(copy, 'config', 'user.name', 'Fixture Developer')
        git(copy, 'config', 'user.email', 'fixture@example.invalid')
        git(copy, 'branch', '-D', 'main')  # a clone need not have a local base branch
        self.change(copy)
        value = json.loads(self.cli(root, 'gh', 'pr', 'view', '1').stdout)
        self.assertEqual(value['headRefOid'], git(copy, 'rev-parse', 'HEAD'))
        observed = inspect(root)
        self.assertTrue(observed['new_commit'])
        self.assertTrue(observed['unrelated_edit_preserved'])
        self.assertEqual(json.loads((root / '.fixture/observed.json').read_text())['execution_root'], '.fixture/work')


if __name__ == '__main__': unittest.main()
