"""Kit identity migration fixtures; host commands are simulated, no personal installs."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from agent_intelliforge import ownership,plugins,cli
from agent_intelliforge.catalog import ForgeError,definitions,selection
from agent_intelliforge.kotonoha_migration import describe,migrate

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.state=Path(self.temp.name);self.agent='codex';self.old=self.state/self.agent/'yomiyasu';self.new=self.state/self.agent/'kotonoha'
        ownership.replace_tree(self.old/'bundle','agent-intelliforge/codex/yomiyasu',{'old.txt':b'original bundle'})
        self.skill=self.state/'skills/kotonoha';ownership.replace_tree(self.skill,'agent-intelliforge/codex/kotonoha',{'SKILL.md':b'original skill'})
        self.config={'owner':'agent-intelliforge/codex/yomiyasu','method':'native','mode':'explicit','skills':[str(self.skill)],'installed':True}
        self.save()
    def save(self):
        (self.old/'settings.json').write_text(json.dumps(self.config))
    def test_preview_selects_existing_method_without_processes_or_writes(self):
        before=ownership.inventory(self.state)
        with patch.object(plugins,'checked',side_effect=AssertionError('host in preview')):
            p=cli.inspect_plan([definitions()['kotonoha']],'codex',False,self.state)
        self.assertEqual(p['operations'][0]['method'],'native')
        self.assertEqual(p['operations'][0]['migration']['from'],'yomiyasu')
        self.assertEqual(before,ownership.inventory(self.state))
    def test_native_migration_preserves_mode_and_recovery_copy(self):
        with migrate(self.state,self.agent,'native'):
            value=json.loads((self.new/'settings.json').read_text());self.assertEqual(value['mode'],'explicit')
            ownership.verify(self.new/'bundle','agent-intelliforge/codex/kotonoha')
        self.assertFalse(self.old.exists())
        backups=list((self.new.parent/'migration-backups').iterdir())
        self.assertEqual((backups[0]/'bundle/old.txt').read_bytes(),b'original bundle')
        self.assertIsNone(describe(self.state,self.agent))
    def test_failure_restores_native_skill_and_old_settings(self):
        old_config=(self.old/'settings.json').read_bytes()
        with self.assertRaisesRegex(RuntimeError,'injected'):
            with migrate(self.state,self.agent,'native'):
                (self.skill/'SKILL.md').write_text('new output')
                raise RuntimeError('injected')
        self.assertEqual((self.skill/'SKILL.md').read_bytes(),b'original skill')
        self.assertEqual((self.old/'settings.json').read_bytes(),old_config)
        self.assertFalse(self.new.exists())
    def test_both_names_and_edited_bundle_are_preserved(self):
        self.new.mkdir()
        with self.assertRaises(ForgeError):describe(self.state,self.agent)
        self.new.rmdir();(self.old/'bundle/old.txt').write_text('user edit')
        with self.assertRaises(ForgeError):
            with migrate(self.state,self.agent,'native'):self.fail('should not migrate')
        self.assertEqual((self.old/'bundle/old.txt').read_text(),'user edit')
    def test_symlink_is_rejected_before_writes(self):
        target=self.old.parent/'other';target.mkdir();
        try:self.new.symlink_to(target,target_is_directory=True)
        except OSError:self.skipTest('Symlink privileges unavailable')
        with self.assertRaises(ForgeError):describe(self.state,self.agent)
        self.assertFalse(list(target.iterdir()))
    def plugin_fixture(self,enabled,host='codex'):
        if host!='codex':
            self.old.rename(self.state/'old-temp');self.agent=host;self.old=self.state/host/'yomiyasu';self.old.parent.mkdir();(self.state/'old-temp').rename(self.old);self.new=self.state/host/'kotonoha'
            # No native skills in a plugin installation.
            marker=self.old/'bundle/.intelliforge.json';v=json.loads(marker.read_text());v['owner']='agent-intelliforge/'+host+'/yomiyasu';marker.write_text(json.dumps(v))
        self.config.update(owner='agent-intelliforge/'+host+'/yomiyasu',method='plugin',skills=[]);self.save()
        market=self.old.parent/'marketplace';ownership.replace_tree(market,'agent-intelliforge/'+host+'/marketplace',{'plugins/yomiyasu/old.json':b'old'})
        registry=self.old.parent/'plugin-registrations.json';registry.write_text(json.dumps({'yomiyasu@agent-intelliforge':{'source':str(market),'agent':host}}))
        rows={'yomiyasu@agent-intelliforge':{'enabled':enabled}}
        commands=[]
        def command(argv,**kw):
            commands.append(argv)
            if argv[1:]==['plugin','list','--json']:
                return json.dumps({'installed':[dict(v,pluginId=k) for k,v in rows.items()]})
            if argv[1:]==['plugin','--help']:return 'add remove' if host=='codex' else 'install uninstall disable'
            action=argv[2];name=argv[3]
            if action in ('add','install'):rows[name]={'enabled':True}
            elif action=='disable':rows[name]['enabled']=False
            elif action in ('remove','uninstall'):rows.pop(name,None)
            return ''
        return rows,commands,command,registry
    def test_disabled_codex_stops_before_mutation_when_cli_cannot_preserve_it(self):
        rows,commands,command,registry=self.plugin_fixture(False)
        before=registry.read_bytes()
        with patch.object(plugins,'checked',side_effect=command),self.assertRaisesRegex(ForgeError,'disabled plugin'):
            with migrate(self.state,'codex','plugin'):self.fail('unsafe migration')
        self.assertFalse(self.new.exists());self.assertEqual(registry.read_bytes(),before)
        self.assertFalse(rows['yomiyasu@agent-intelliforge']['enabled'])
    def test_plugin_verified_before_old_retirement_and_disabled_state_preserved(self):
        rows,commands,command,registry=self.plugin_fixture(False,'claude')
        with patch.object(plugins,'checked',side_effect=command):
            with migrate(self.state,'claude','plugin'):
                command(['claude','plugin','install','kotonoha@agent-intelliforge'])
        self.assertEqual(rows,{'kotonoha@agent-intelliforge':{'enabled':False}})
        self.assertEqual(set(json.loads(registry.read_text())),{'kotonoha@agent-intelliforge'})
        self.assertFalse(self.old.exists())
    def test_plugin_failure_keeps_old_registration(self):
        rows,commands,command,registry=self.plugin_fixture(True)
        before=registry.read_bytes()
        with patch.object(plugins,'checked',side_effect=command),self.assertRaises(RuntimeError):
            with migrate(self.state,'codex','plugin'):
                command(['codex','plugin','add','kotonoha@agent-intelliforge']);raise RuntimeError('injected')
        self.assertEqual(rows,{'yomiyasu@agent-intelliforge':{'enabled':True}})
        self.assertEqual(registry.read_bytes(),before);self.assertFalse(self.new.exists())
    def test_failed_staging_does_not_leave_new_runtime(self):
        import shutil
        copy=shutil.copytree
        def stage(source,destination,*a,**kw):
            if Path(destination)==self.new/'bundle':raise OSError('injected staging failure')
            return copy(source,destination,*a,**kw)
        with patch('agent_intelliforge.kotonoha_migration.shutil.copytree',side_effect=stage),self.assertRaises(OSError):
            with migrate(self.state,'codex','native'):self.fail('staging failed')
        self.assertFalse(self.new.exists());self.assertTrue((self.old/'bundle/old.txt').exists())

    def test_failed_old_registration_retirement_restores_old_plugin(self):
        rows,commands,command,registry=self.plugin_fixture(True)
        def fail(argv,**kw):
            result=command(argv,**kw)
            if argv[2:] == ['remove','yomiyasu@agent-intelliforge']:raise ForgeError('injected retirement failure')
            return result
        with patch.object(plugins,'checked',side_effect=fail),self.assertRaises(ForgeError):
            with migrate(self.state,'codex','plugin'):
                command(['codex','plugin','add','kotonoha@agent-intelliforge'])
        self.assertEqual(rows,{'yomiyasu@agent-intelliforge':{'enabled':True}})
        self.assertFalse(self.new.exists());self.assertTrue(self.old.exists())

    def test_source_only_check_cannot_silently_migrate_the_runtime(self):
        from agent_intelliforge import runtime
        from types import SimpleNamespace
        args=SimpleNamespace(action='update',skills_dir=self.skill.parent,upstream_only=True,mode=None)
        kit=definitions()['kotonoha'];plan={'operations':[{'kit':'kotonoha','agent':'codex','method':'native'}]}
        with self.assertRaisesRegex(ForgeError,'Complete the kit rename'):
            runtime.portable_action(Path(__file__).resolve().parents[1],[kit],plan,args,self.state)
        self.assertFalse(self.new.exists())

    def test_native_update_uses_the_full_runtime_transaction(self):
        from agent_intelliforge import runtime
        from types import SimpleNamespace
        args=SimpleNamespace(action='update',skills_dir=self.skill.parent,upstream_only=False,mode=None)
        kit=definitions()['kotonoha'];plan={'operations':[{'kit':'kotonoha','agent':'codex','method':'native'}]}
        def upstream(bundle,home,agent):
            return ownership.replace_tree(home/'upstream','agent-intelliforge/codex/yomiyasu-upstream',{'SKILL.upstream.md':b'fixture'})
        with patch.object(runtime,'prepare_dependencies'),patch.object(runtime,'upstream_update',side_effect=upstream):
            self.assertEqual(runtime.portable_action(Path(__file__).resolve().parents[1],[kit],plan,args,self.state),0)
        self.assertFalse(self.old.exists())
        config=json.loads((self.new/'settings.json').read_text())
        self.assertEqual(config['version'],'5.0.0');self.assertEqual(config['mode'],'explicit')
        ownership.verify(self.skill,'agent-intelliforge/codex/kotonoha')
        self.assertIn('allow_implicit_invocation: false',(self.skill/'agents/openai.yaml').read_text())

    def test_plugin_update_runs_through_host_manager_and_removes_old_catalog_entry(self):
        from agent_intelliforge import runtime
        from types import SimpleNamespace
        rows,commands,command,registry=self.plugin_fixture(True,'claude')
        def host(argv,**kw):
            if argv[1:]==['plugin','marketplace','list','--json']:return '{"marketplaces":[]}'
            if argv[1:3]==['plugin','marketplace']:return ''
            return command(argv,**kw)
        args=SimpleNamespace(action='update',skills_dir=self.state/'unused-skills',upstream_only=False,mode=None)
        kit=definitions()['kotonoha'];plan={'operations':[{'kit':'kotonoha','agent':'claude','method':'plugin'}]}
        def upstream(bundle,home,agent):
            return ownership.replace_tree(home/'upstream','agent-intelliforge/claude/yomiyasu-upstream',{'SKILL.upstream.md':b'fixture'})
        with patch.object(runtime,'prepare_dependencies'),patch.object(runtime,'upstream_update',side_effect=upstream),patch.object(plugins,'checked',side_effect=host),patch.object(plugins.shutil,'which',return_value='fixture'):
            self.assertEqual(runtime.portable_action(Path(__file__).resolve().parents[1],[kit],plan,args,self.state),0)
        self.assertEqual(set(rows),{'kotonoha@agent-intelliforge'})
        market=self.new.parent/'marketplace'
        self.assertFalse((market/'plugins/yomiyasu').exists())
        self.assertTrue((market/'plugins/kotonoha/.claude-plugin/plugin.json').is_file())
        self.assertEqual([p['name'] for p in json.loads((market/'.claude-plugin/marketplace.json').read_text())['plugins']],['kotonoha'])

    def test_unowned_former_plugin_cannot_be_duplicated_by_new_install(self):
        with patch.object(plugins.shutil,'which',return_value='fixture'),patch.object(plugins,'checked',return_value='{"marketplaces":[]}'),patch.object(plugins,'installed',return_value={'yomiyasu@agent-intelliforge'}):
            with self.assertRaisesRegex(ForgeError,'verified migration context'):
                plugins.preflight(definitions()['kotonoha'],'codex','install',self.state)

    def test_commit_failure_does_not_print_a_success_summary(self):
        import contextlib,io
        from agent_intelliforge import runtime
        from types import SimpleNamespace
        @contextlib.contextmanager
        def fail(*a):
            yield
            raise ForgeError('injected final commit failure')
        def action(*a):
            print('{"installed":true}')
            return 0
        output=io.StringIO();args=SimpleNamespace(action='update',upstream_only=False)
        plan={'operations':[{'kit':'kotonoha','agent':'codex','method':'native'}]}
        with patch('agent_intelliforge.kotonoha_migration.migrate',fail),patch.object(runtime,'_portable_action',side_effect=action),contextlib.redirect_stdout(output),self.assertRaises(ForgeError):
            runtime.portable_action(Path.cwd(),[],plan,args,self.state)
        self.assertEqual(output.getvalue(),'')

    def test_retired_distribution_entrypoints_are_absent(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('install_codex_yomiyasu.sh','plugins/codex/yomiyasu','plugins/claude/yomiyasu','tools/codex-yomiyasu','tools/intelliforge/resources/runtime/yomiyasu'):
            self.assertFalse((root/name).exists(),name)
        self.assertTrue((root/'install_kotonoha.sh').is_file())

    def test_former_kit_id_is_not_an_alias(self):
        with self.assertRaisesRegex(ForgeError,'--only kotonoha'):selection(['yomiyasu'],definitions())
        self.assertEqual(selection(['kotonoha'],definitions())[0]['id'],'kotonoha')
