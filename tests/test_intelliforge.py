"""Additive distribution contracts; no personal installation/model calls."""
from __future__ import annotations

import contextlib
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from agent_intelliforge import cli, ownership, portable, provider, runtime, plugins
from agent_intelliforge.catalog import ForgeError, definitions, safe_relative, selection


class DistributionTests(unittest.TestCase):
    def test_catalog_selection_is_fixed_and_complete(self):
        catalog = definitions(ROOT)
        self.assertEqual([k['id'] for k in selection(['yomiyasu,workgraph','yomiyasu'],catalog)], ['workgraph','yomiyasu'])
        self.assertEqual(len(catalog['speckit']['skills']),8)
        with self.assertRaises(ForgeError): selection(['yomiyasu,typo'],catalog)
        output=io.StringIO()
        with contextlib.redirect_stdout(output):self.assertEqual(cli.main(['list','--only','yomiyasu','--json']),0)
        self.assertEqual([kit['id'] for kit in json.loads(output.getvalue())],['yomiyasu'])

    def test_inspect_and_preview_have_no_writes_or_processes(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / 'missing'
            with patch.object(subprocess,'run',side_effect=AssertionError('process in preview')), patch.object(subprocess,'call',side_effect=AssertionError('process in preview')):
                for command in ('inspect','install','update','uninstall'):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(cli.main([command,'--agent','claude','--only','yomiyasu','--state-dir',str(state),'--json']),0)
            self.assertFalse(state.exists())

    def test_invalid_options_fail_before_preview(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['install','--upstream-only','--only','yomiyasu']),2)
            if os.name != 'nt':
                self.assertEqual(cli.main(['install','--only','yomiyasu','--skills-dir','/tmp/protected','--apply']),2)

    def test_legacy_default_delegates_without_new_installer(self):
        with patch.object(cli.shutil,'which',return_value='bash'),patch.object(cli.subprocess,'call',return_value=0) as call:
            self.assertEqual(cli.legacy_action(ROOT,[definitions(ROOT)['yomiyasu']],'install'),0)
        self.assertEqual(call.call_args.args[0],['bash',str(ROOT/'install_all.sh'),'--only','yomiyasu','--apply'])

    def test_helper_parser_preserves_host_and_literal_arguments(self):
        with patch.object(runtime,'kit_run',return_value=0) as run:
            self.assertEqual(cli.main(['kit-run','ux-stack','--agent','claude','--tool','harness.py','--','--help']),0)
        self.assertEqual(run.call_args.args[:3],('ux-stack','claude',['--tool','harness.py','--','--help']))

    def test_portable_paths_reject_windows_aliases(self):
        for name in ('../escape','C:/escape','file:stream','CON.txt','dir/name.','dir/Nul','a\\b'):
            with self.subTest(name=name), self.assertRaises(ForgeError): safe_relative(name)

    def test_plugin_sources_are_contained_and_names_match(self):
        for host,catalog in [('codex','.agents/plugins/marketplace.json'),('claude','.claude-plugin/marketplace.json')]:
            for item in json.loads((ROOT/catalog).read_text(encoding='utf-8'))['plugins']:
                source = item['source']['path'] if host=='codex' else item['source']
                directory = ROOT/safe_relative(source)
                manifest = directory/('plugin.json' if host=='codex' else '.claude-plugin/plugin.json')
                self.assertEqual(json.loads(manifest.read_text(encoding='utf-8'))['name'],item['name'])
                self.assertTrue(directory.resolve().is_relative_to(ROOT))

    def test_upstream_commands_remain_explicit(self):
        for path in (ROOT/'plugins/claude/speckit/skills').glob('*/SKILL.md'):
            self.assertIn('disable-model-invocation: true',path.read_text(encoding='utf-8').split('---',2)[1])

    def test_ports_preserve_inline_code_and_unicode(self):
        specification=importlib.util.spec_from_file_location('forge_builder',ROOT/'tools/intelliforge/build.py')
        module=importlib.util.module_from_spec(specification); specification.loader.exec_module(module)
        data='from __future__ import annotations\nx="日本語"; import subprocess; y=42\n'.encode()
        ported=module.portable_python(data,'inline.py').decode()
        self.assertIn('y=42',ported); self.assertIn('x="日本語"',ported)
        compile(ported,'inline.py','exec')

    def test_generated_nested_text_io_is_utf8_and_preserves_explicit_encoding(self):
        specification=importlib.util.spec_from_file_location('forge_builder',ROOT/'tools/intelliforge/build.py')
        module=importlib.util.module_from_spec(specification);specification.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'source.txt';target=Path(temporary)/'result.txt'
            source.write_bytes('日本語\n2行\n'.encode('utf-8'))
            code=f'from pathlib import Path\nPath({str(target)!r}).write_text(Path({str(source)!r}).read_text(),)\nexplicit=Path({str(source)!r}).read_text(encoding="utf-8")\n'
            ported=module.portable_python(code.encode('utf-8'),'text_io.py').decode('utf-8')
            self.assertIn('newline="\\n"',ported)
            self.assertEqual(ported.count('encoding="utf-8"'),3)
            environment=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONUTF8='0',PYTHONCOERCECLOCALE='0',LC_ALL='C')
            result=subprocess.run([sys.executable,'-B','-c',ported],env=environment,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode('utf-8','replace'))
            self.assertEqual(target.read_bytes(),source.read_bytes())


class OwnershipTests(unittest.TestCase):
    def lifecycle(self, temporary, agent='claude'):
        kit = definitions(ROOT)['yomiyasu']; state = Path(temporary)/'state'
        args = argparse.Namespace(action='install', skills_dir=Path(temporary)/'skills', upstream_only=False, mode='explicit')
        plan = cli.inspect_plan([kit],agent,True,state)
        return kit,state,args,plan

    def test_install_rerun_update_upstream_only_doctor_uninstall(self):
        with tempfile.TemporaryDirectory() as temporary:
            kit,state,args,plan=self.lifecycle(temporary)
            def upstream(bundle,home,agent):
                return ownership.replace_tree(home/'upstream',runtime.owner('yomiyasu-upstream',agent),{'SKILL.upstream.md':b'unchanged upstream original'})
            with patch.object(plugins,'preflight'),patch.object(plugins,'manage'),patch.object(plugins.shutil,'which',return_value='claude'),patch.object(plugins,'installed',return_value={'yomiyasu@agent-intelliforge'}),patch.object(runtime,'prepare_dependencies'),patch.object(runtime,'upstream_update',upstream),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runtime.portable_action(ROOT,[kit],plan,args,state),0)
                self.assertEqual(runtime.portable_action(ROOT,[kit],plan,args,state),0)
                args.action='update';self.assertEqual(runtime.portable_action(ROOT,[kit],plan,args,state),0)
                bundle=state/'claude/yomiyasu/bundle';before=ownership.inventory(bundle)
                args.upstream_only=True;self.assertEqual(runtime.portable_action(ROOT,[kit],plan,args,state),0)
                self.assertEqual(ownership.inventory(bundle),before)
                self.assertEqual(runtime.diagnose(kit,'claude',state)['exit_code'],0)
                self.assertIn('disable-model-invocation: true',(state/'claude/marketplace/plugins/yomiyasu/skills/yomiyasu/SKILL.md').read_text(encoding='utf-8').split('---',2)[1])
                args.action='uninstall';self.assertEqual(runtime.portable_action(ROOT,[kit],plan,args,state),0)
                self.assertFalse(bundle.exists());self.assertTrue((state/'claude/yomiyasu/upstream/SKILL.upstream.md').exists())

    def test_plugin_failure_rolls_back_runtime_and_upstream(self):
        with tempfile.TemporaryDirectory() as temporary:
            kit,state,args,plan=self.lifecycle(temporary)
            def upstream(bundle,home,agent):
                return ownership.replace_tree(home/'upstream',runtime.owner('yomiyasu-upstream',agent),{'SKILL.upstream.md':b'original'})
            with patch.object(plugins,'preflight'),patch.object(plugins,'manage',side_effect=ForgeError('injected native manager failure')),patch.object(runtime,'prepare_dependencies'),patch.object(runtime,'upstream_update',upstream),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(ForgeError): runtime.portable_action(ROOT,[kit],plan,args,state)
            self.assertFalse((state/'claude/yomiyasu/bundle').exists())
            self.assertFalse((state/'claude/yomiyasu/upstream').exists())
            self.assertFalse((state/'claude/marketplace').exists())

    def test_reinstall_backup_and_manual_edit_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination=Path(temporary)/'bundle'
            ownership.replace_tree(destination,'test',{'SKILL.md':b'first'})
            backup=ownership.replace_tree(destination,'test',{'SKILL.md':b'second'})
            self.assertEqual((backup/'SKILL.md').read_bytes(),b'first')
            (destination/'SKILL.md').write_bytes(b'user edit')
            with self.assertRaises(ForgeError): ownership.replace_tree(destination,'test',{'SKILL.md':b'third'})
            with self.assertRaises(ForgeError): ownership.remove_tree(destination,'test')
            self.assertEqual((destination/'SKILL.md').read_bytes(),b'user edit')

    def test_unowned_link_and_case_collisions_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination=Path(temporary)/'bundle'; destination.mkdir()
            with self.assertRaises(ForgeError): ownership.replace_tree(destination,'test',{'a':b'a'})
            destination.rmdir()
            with self.assertRaises(ForgeError): ownership.replace_tree(destination,'test',{'A.md':b'a','a.md':b'b'})
            self.assertFalse(destination.exists())
            if os.name!='nt':
                destination.symlink_to(temporary,target_is_directory=True)
                with self.assertRaises(ForgeError): ownership.replace_tree(destination,'test',{'a':b'a'})

    def test_stage_rename_failure_restores_previous_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination=Path(temporary)/'bundle'; ownership.replace_tree(destination,'test',{'a':b'original'})
            original=Path.rename
            def fail(path,target):
                if path.name.startswith('.bundle-'): raise OSError('injected commit failure')
                return original(path,target)
            with patch.object(Path,'rename',fail),self.assertRaises(OSError):
                ownership.replace_tree(destination,'test',{'a':b'changed'})
            self.assertEqual((destination/'a').read_bytes(),b'original')

    def test_unowned_plugin_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(plugins.shutil,'which',return_value='codex'),patch.object(plugins,'checked',return_value='{"marketplaces":[]}'),patch.object(plugins,'installed',return_value={'yomiyasu@agent-intelliforge'}):
            with self.assertRaises(ForgeError): plugins.preflight(definitions(ROOT)['yomiyasu'],'codex','install',Path(temporary))


class ProcessTests(unittest.TestCase):
    def test_windows_npm_host_shim_keeps_literal_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);shim=root/'codex.cmd'
            script=root/'node_modules/@openai/codex/bin/codex.js'
            script.parent.mkdir(parents=True);script.write_text('fixture',encoding='utf-8')
            def which(name):return str(shim) if name=='codex' else 'node.exe' if name=='node' else None
            literal='日本語 & echo unwanted | > file'
            with patch.object(portable.shutil,'which',side_effect=which):
                self.assertEqual(portable.native_command(['codex','exec',literal],windows=True),['node.exe',str(script),'exec',literal])
                self.assertEqual(portable.native_command(['codex','exec',literal],windows=False),['codex','exec',literal])
                with self.assertRaises(ForgeError):portable.native_command([str(root/'unknown.cmd'),literal],windows=True)

    def test_windows_claude_role_uses_child_only_powershell_setting(self):
        request={'mode':'workspace-write','prompt':'test','schema':{'type':'object'},'images':[],'model':None,'configurations':[]}
        command=provider.claude_command(request,windows=True)
        tools=command[command.index('--tools')+1].split(',')
        self.assertIn('PowerShell',tools);self.assertNotIn('Bash',tools)
        before=dict(os.environ)
        self.assertEqual(provider.role_environment(windows=True)['CLAUDE_CODE_USE_POWERSHELL_TOOL'],'1')
        self.assertEqual(dict(os.environ),before)

    def test_claude_request_uses_stdin_and_only_structured_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);schema=root/'schema.json';output=root/'result.json'
            schema.write_text('{"type":"object"}',encoding='utf-8')
            argv=['exec','-C',str(root),'--sandbox','read-only','--output-schema',str(schema),'--output-last-message',str(output),'--','-']
            captured={'exit_code':0,'timed_out':False,'truncated':False,'stdout':'{"subtype":"success","structured_output":{"verified":true}}','stderr':''}
            with patch.object(sys,'stdin',io.StringIO('large prompt from stdin')),patch.object(provider,'capabilities',return_value={'ready':True}),patch.object(provider,'isolated_command',return_value=['isolated']),patch.object(provider,'capture',return_value=captured) as capture,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(provider.main(argv),0)
            self.assertEqual(capture.call_args.kwargs['input_text'],'large prompt from stdin')
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')),{'verified':True})

    def test_yomiyasu_port_checks_owned_original_before_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary);source=home/'upstream'
            script=b'import json; print(json.dumps({"fixture":True}))\n'
            ownership.replace_tree(source,runtime.owner('yomiyasu-upstream','claude'),{'scripts/yomiyasu_lint.py':script})
            from agent_intelliforge.runtime_ports import apply_ports
            namespace={'__file__':'check.py','upstream':lambda *args:None}
            with patch.dict(os.environ,{'INTELLIFORGE_KIT_HOME':str(home),'INTELLIFORGE_AGENT':'claude'}):
                apply_ports(namespace)
                self.assertEqual(namespace['upstream']('yomiyasu_lint.py',[])['report'],{'fixture':True})
                (source/'scripts/yomiyasu_lint.py').write_bytes(b'user edit')
                with self.assertRaises(ForgeError):namespace['upstream']('yomiyasu_lint.py',[])
    def test_large_stdin_never_uses_command_line(self):
        prompt='あ'*50000
        child_environment=dict(os.environ,LC_ALL='C',PYTHONUTF8='0',PYTHONCOERCECLOCALE='0')
        before=dict(child_environment)
        value=portable.capture([sys.executable,'-c','import sys;print(len(sys.stdin.read()))'],cwd=None,env=child_environment,timeout=10,input_text=prompt)
        self.assertEqual(value['stdout'].strip(),'50000')
        self.assertEqual(child_environment,before)

    def test_output_is_bounded(self):
        value=portable.capture([sys.executable,'-c','print("x"*100000)'],cwd=None,env=None,timeout=10,limit=4096)
        self.assertTrue(value['truncated']); self.assertLessEqual(len(value['stdout']),4096)

    def test_timeout_kills_child_process_tree(self):
        value=portable.capture([sys.executable,'-c','import subprocess,sys,time;subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);time.sleep(60)'],cwd=None,env=None,timeout=.2)
        self.assertTrue(value['timed_out'])

    def test_structured_claude_failure_is_not_success(self):
        for text in ('{"is_error":true,"structured_output":{}}','{"result":"not structured"}','[]'):
            with self.assertRaises(ForgeError): provider.structured_output(text)
        self.assertEqual(provider.structured_output('{"subtype":"success","structured_output":{"ok":true}}'),{'ok':True})

    def test_readonly_claude_role_and_disabled_web(self):
        request={'mode':'read-only','prompt':'test','schema':{'type':'object'},'images':[],'model':None,'configurations':['web_search="disabled"']}
        command=provider.claude_command(request); tools=command[command.index('--tools')+1]
        self.assertNotIn('Bash',tools);self.assertNotIn('Edit',tools);self.assertNotIn('WebSearch',tools)
        self.assertNotIn('--dangerously-skip-permissions',command)
        self.assertNotIn('--bare',command)

    def test_claude_isolation_never_falls_back(self):
        with tempfile.TemporaryDirectory() as temporary,patch.dict(os.environ,{'INTELLIFORGE_STATE_DIR':temporary}):
            with self.assertRaises(ForgeError): provider.isolated_command(['claude'],Path(temporary),[],True)


class HookTests(unittest.TestCase):
    def test_claude_turn_token_plan_and_single_stop_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            state=Path(temporary);home=state/'claude/workgraph';bundle=home/'bundle';policy=home/'policy'
            source=ROOT/'tools/intelliforge/resources/runtime/workgraph'
            ownership.replace_tree(bundle,runtime.owner('workgraph','claude'),runtime.files(source))
            ownership.replace_tree(policy/'assets',runtime.owner('workgraph-policy','claude'),{
                name:data for name,data in runtime.files(source).items() if name=='memory-policy.md' or name.startswith('templates/')})
            ownership.atomic_write(policy/'config.json',b'{"mode":"always"}')
            ownership.atomic_write(home/'settings.json',json.dumps({'owner':runtime.owner('workgraph','claude'),'policy':str(policy)}).encode())
            def hook(action,event):
                out=io.StringIO()
                with patch.object(sys,'stdin',io.StringIO(json.dumps(event))),contextlib.redirect_stdout(out):
                    self.assertEqual(runtime.hook_run('claude',[action],state),0)
                return json.loads(out.getvalue()) if out.getvalue() else {}
            event={'session_id':'test-session','prompt':'Private test material','permission_mode':'default'}
            value=hook('recall',event);context=value['hookSpecificOutput']['additionalContext']
            self.assertIn('intelliforge hook --agent claude arm',context)
            import re
            ticket,token=re.search(r'--ticket ([a-f0-9]{64}) --token ([a-f0-9]{64})',context).groups()
            self.assertFalse(any('Private test material' in path.read_text(encoding='utf-8') for path in (policy/'state').glob('*.json')))
            runtime.hook_run('claude',['arm','--ticket',ticket,'--token',token,'--mode','implementation'],state)
            self.assertEqual(hook('save',event)['decision'],'block')
            self.assertEqual(hook('save',event),{})
            value=hook('recall',dict(event,permission_mode='plan'))
            self.assertNotIn('--token',value['hookSpecificOutput']['additionalContext'])
            self.assertEqual(hook('save',dict(event,permission_mode='plan')),{})


if __name__=='__main__': unittest.main()
