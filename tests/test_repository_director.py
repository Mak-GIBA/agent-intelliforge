"""Repository Director contracts; isolated projects, no hosts or network."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


class DistributionContracts(unittest.TestCase):
    def test_one_kit_replaces_both_old_selections(self):
        from agent_intelliforge.catalog import definitions, selection, ForgeError
        catalog = definitions(ROOT)
        self.assertIn('repository-director', catalog)
        self.assertNotIn('speckit', catalog)
        self.assertNotIn('github-pm', catalog)
        for name in ('speckit', 'github-pm'):
            with self.assertRaisesRegex(ForgeError, 'repository-director'):
                selection([name], catalog)

    def test_bulk_preview_dispatches_new_kit(self):
        result = subprocess.run(['bash', str(ROOT / 'install_all.sh'), '--only', 'repository-director'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('install_repository_director.sh', result.stdout)
        self.assertIn('--apply', result.stdout)


class PortableMigrationTests(unittest.TestCase):
    def fixture(self, directory):
        from agent_intelliforge import ownership
        root=Path(directory);state=root/'state';skills=root/'skills'
        old=state/'codex/github-pm'
        ownership.replace_tree(old/'bundle','agent-intelliforge/codex/github-pm',{'old.py':b'# old'})
        ownership.replace_tree(skills/'github-project-director','agent-intelliforge/codex/github-project-director',{'SKILL.md':b'old skill'})
        (old/'settings.json').write_text(json.dumps({'owner':'agent-intelliforge/codex/github-pm','installed':True,'method':'native','skills':[str(skills/'github-project-director')]}))
        env={'HOME':str(root),'CODEX_HOME':str(root/'codex'),'RD_SKILLS_DIR':str(skills),'XDG_DATA_HOME':str(root/'share'),'XDG_CONFIG_HOME':str(root/'config')}
        return state,skills,old,env

    def test_native_migration_is_explicit_and_retires_owned_skills(self):
        from agent_intelliforge import runtime
        from agent_intelliforge.catalog import definitions,ForgeError
        with tempfile.TemporaryDirectory() as td:
            state,skills,old,env=self.fixture(td)
            args=SimpleNamespace(action='install',skills_dir=skills,mode=None,migrate_legacy=False)
            plan={'operations':[{'kit':'repository-director','agent':'codex','method':'native'}]}
            kit=definitions(ROOT)['repository-director']
            with patch.dict(os.environ,env):
                with self.assertRaisesRegex(ForgeError,'migrate-legacy'):runtime.portable_action(ROOT,[kit],plan,args,state)
                self.assertTrue((skills/'github-project-director/SKILL.md').exists())
                args.migrate_legacy=True
                self.assertEqual(runtime.portable_action(ROOT,[kit],plan,args,state),0)
                from agent_intelliforge import cli
                self.assertEqual(cli.inspect_plan([kit],'codex',False,state)['operations'][0]['method'],'native')
                args.action='update'
                self.assertEqual(runtime.portable_action(ROOT,[kit],plan,args,state),0)
                self.assertEqual(sorted(p.parent.name for p in skills.rglob('SKILL.md')),['repository-director'])
            self.assertFalse((skills/'github-project-director/SKILL.md').exists())
            self.assertTrue((skills/'repository-director/SKILL.md').is_file())
            self.assertFalse(json.loads((old/'settings.json').read_text())['installed'])

    def test_preview_reuses_legacy_portable_route_without_host_commands(self):
        from agent_intelliforge import cli,plugins
        from agent_intelliforge.catalog import definitions
        with tempfile.TemporaryDirectory() as td:
            state,skills,old,env=self.fixture(td)
            with patch.dict(os.environ,env),patch.object(plugins,'checked',side_effect=AssertionError('host command in preview')):
                plan=cli.inspect_plan([definitions(ROOT)['repository-director']],'codex',False,state)
            self.assertEqual(plan['operations'][0]['method'],'native')
            self.assertEqual(plan['operations'][0]['migration']['from'],['github-pm'])

    def test_migration_context_restores_old_resources_when_new_install_fails(self):
        from agent_intelliforge.director_migration import migrate
        with tempfile.TemporaryDirectory() as td:
            state,skills,old,env=self.fixture(td)
            before=(old/'settings.json').read_bytes()
            with patch.dict(os.environ,env),self.assertRaisesRegex(RuntimeError,'injected'):
                with migrate(ROOT,state,'codex',True,skills):
                    self.assertFalse((skills/'github-project-director/SKILL.md').exists())
                    raise RuntimeError('injected')
            self.assertEqual((skills/'github-project-director/SKILL.md').read_bytes(),b'old skill')
            self.assertEqual((old/'settings.json').read_bytes(),before)

    def test_plugin_retirement_is_verified_and_rollback_restores_registration(self):
        from agent_intelliforge import plugins,ownership
        from agent_intelliforge.director_migration import migrate
        with tempfile.TemporaryDirectory() as td:
            state=Path(td)/'state';old=state/'claude/speckit';market=state/'claude/marketplace'
            ownership.replace_tree(old/'bundle','agent-intelliforge/claude/speckit',{'old.py':b'old'})
            config={'owner':'agent-intelliforge/claude/speckit','method':'plugin','installed':True}
            (old/'settings.json').write_text(json.dumps(config))
            identity='speckit@agent-intelliforge'
            ownership.replace_tree(market,'agent-intelliforge/claude/marketplace',{
                'plugins/speckit/old.json':b'{}',
                '.claude-plugin/marketplace.json':json.dumps({'plugins':[{'name':'speckit'}]}).encode()})
            registry=state/'claude/plugin-registrations.json';registry.write_text(json.dumps({identity:{'source':str(market)}}))
            present={identity};commands=[]
            def checked(argv,**kwargs):
                commands.append(argv)
                if argv[1:3]==['plugin','list']:
                    return json.dumps({'installed':[{'pluginId':i,'installed':True,'enabled':True} for i in present]})
                if argv[1:3]==['plugin','uninstall']:present.remove(identity)
                elif argv[1:3]==['plugin','install']:present.add(identity)
                else:raise AssertionError(argv)
                return ''
            with patch.object(plugins,'checked',side_effect=checked),self.assertRaisesRegex(RuntimeError,'injected'):
                with migrate(ROOT,state,'claude',True):
                    self.assertNotIn(identity,present)
                    raise RuntimeError('injected')
            self.assertIn(identity,present)
            self.assertTrue(json.loads((old/'settings.json').read_text())['installed'])
            self.assertIn(identity,json.loads(registry.read_text()))
            self.assertTrue((market/'plugins/speckit/old.json').is_file())
            self.assertTrue(any('--keep-data' in command for command in commands))

    def test_first_portable_update_migration_installs_the_new_registration(self):
        from agent_intelliforge import runtime,plugins
        from agent_intelliforge.catalog import definitions
        with tempfile.TemporaryDirectory() as td:
            state,skills,old,env=self.fixture(td)
            args=SimpleNamespace(action='update',skills_dir=skills,mode=None,migrate_legacy=True)
            plan={'operations':[{'kit':'repository-director','agent':'codex','method':'plugin'}]}
            with patch.dict(os.environ,env),patch.object(plugins,'preflight') as preflight,patch.object(plugins,'conflict_skills'),patch.object(plugins,'manage') as manage:
                self.assertEqual(runtime.portable_action(ROOT,[definitions(ROOT)['repository-director']],plan,args,state),0)
            self.assertEqual(preflight.call_args.args[2],'install')
            self.assertEqual(manage.call_args.args[3],'install')


def load_tests(loader, tests, pattern):
    # Python 3.11 retains each loader's discovery root. Keep the outer suite's
    # root intact while preserving any requested test-name filter.
    kit_loader = unittest.TestLoader()
    kit_loader.testNamePatterns = loader.testNamePatterns
    tests.addTests(kit_loader.discover(str(ROOT/'tools/repository-director/tests'),pattern='test_*.py',top_level_dir=str(ROOT/'tools/repository-director/tests')))
    return tests


if __name__ == '__main__':
    unittest.main()
