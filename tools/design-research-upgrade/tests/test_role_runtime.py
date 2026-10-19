"""Role permission changes must not invalidate saved research inputs."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_stages as stages
import execution_units as units
import harness as h
import role_runtime as roles
import runtime as rt


class RoleRuntimeTests(unittest.TestCase):
    def test_new_configuration_and_explicit_readonly(self):
        args = h.parser().parse_args(['research', '--brief', 'fixture'])
        state = {'config': h.config_from(args, Path('/fixture'))}
        self.assertEqual(roles.role_sandbox(state, 'planner'), 'workspace-write')
        state['config']['role_sandbox'] = 'read-only'
        self.assertEqual(roles.role_sandbox(state, 'producer-assets'), 'read-only')
        self.assertEqual(roles.role_sandbox(state, 'fixer'), 'workspace-write')

    def test_override_keeps_completed_checkpoint_reusable(self):
        stages.StageTests.setUp(self)
        self.state.update(execution_contract_version=2)
        before = copy.deepcopy(self.state['config'])
        invoke = Mock(return_value=self.design)
        first = units.unit('producer-design', h.DESIGN, self.state, self.workspace, self.run, invoke)
        roles.override_sandbox(self.state, 'workspace-write', 'fixture-time')
        self.assertEqual(self.state['config'], before)
        self.assertEqual(first, units.unit('producer-design', h.DESIGN, self.state, self.workspace, self.run, invoke))
        self.assertEqual(invoke.call_count, 1)
        self.assertEqual(roles.role_sandbox(self.state, 'producer-assets'), 'workspace-write')
        self.assertEqual(self.state['role_runtime_history'][0]['previous'], 'read-only')

    def test_temp_is_private_without_redirecting_authentication(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {'HOME':'/fixture/home','CODEX_HOME':'/fixture/codex',
                                         'UV_CACHE_DIR':'/explicit/cache'}):
                env=roles.child_environment(temporary, 'DR_GAN_CHILD')
            self.assertEqual(env['HOME'], '/fixture/home')
            self.assertEqual(env['CODEX_HOME'], '/fixture/codex')
            self.assertEqual(env['UV_CACHE_DIR'], '/explicit/cache')
            self.assertTrue(Path(env['TMPDIR']).is_dir())
            self.assertTrue(Path(env['TMPDIR']).is_relative_to(temporary))

    def test_unrelated_auth_failure_is_not_a_browser_retry(self):
        self.assertEqual(roles.failure_kind('MCP playwright unauthorized 401'), 'authentication')
        self.assertFalse(roles.browser_failure('authentication'))
        self.assertEqual(roles.failure_kind('MCP tool call requires approval, but approval policy is never'), 'tool_approval')
        self.assertFalse(roles.browser_failure('tool_approval'))
        self.assertEqual(roles.failure_kind('MCP provider returned 429 rate limit'), 'rate_limit')
        self.assertTrue(roles.browser_failure(roles.failure_kind('MCP playwright failed to initialize')))

    def test_role_invocation_receives_network_policy_and_output_root(self):
        stages.StageTests.setUp(self)
        self.state['config'].update(allow_network=False, role_sandbox='workspace-write')
        seen=[]
        def capture(argv, **kw):
            seen.append((argv, kw['env']))
            output=Path(argv[argv.index('--output-last-message')+1])
            output.write_text(json.dumps({'status':'ready'}))
            paths={}
            for name in ('stdout','stderr'):
                path=output.parent/(name+'.log');path.write_text('');paths[name]=str(path)
            return {'exit_code':0,'timed_out':False,'truncated':False,'duration_seconds':0,'paths':paths}
        with patch.object(h,'role_prompt',return_value='fixture'), patch.object(h,'capture',side_effect=capture):
            result=h.run_role('planner',h.obj({'status':h.S}),self.state,self.workspace,self.run)
        self.assertEqual(result, {'status':'ready'})
        argv,env=seen[0]
        self.assertEqual(argv[argv.index('--sandbox')+1], 'workspace-write')
        self.assertIn('sandbox_workspace_write.network_access=false',argv)
        self.assertIn('--add-dir',argv)
        self.assertEqual(env['DR_GAN_CHILD'],'1')
