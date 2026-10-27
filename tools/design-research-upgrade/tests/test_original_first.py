"""Synthetic source/protocol fixtures; actual parent execution is not a research result."""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

import test_bounded_pipeline as pipeline
import harness as h
import runtime as rt
import original_first as original
import model_access as access
from test_effectiveness import contract


def origin(kind='faithful',parent=''):
    return {'kind':kind,'source_ids':[] if kind=='builtin' else ['S1'],'version':'fixture-1',
            'method':'Synthetic unchanged parity predicate','differences':['input adapter'] if parent else [],'parent_id':parent}


class OriginalFlowTests(unittest.TestCase):
    def setUp(self):
        pipeline.BoundedPipelineTests.setUp(self)
        self.state['original_first_contract_version']=1
        self.state['report_contract_version']=2
        self.project_files({'official.py':'def original(x):\n return x % 2 == 0\n'})
        source={'id':'S1','title':'Synthetic original implementation','source_type':'repository',
                'local_path':'official.py','read_level':'full_text','peer_review_status':'not_applicable',
                'retrieved_at':'2026-10-27','study_id':'fixture','correction_status':'not_applicable'}
        self.draft['sources']=[source]
        for c in self.draft['candidates']:
            c['source_review']={'promising':True,'reason':'Synthetic source fixture','paper_reads':[],
                               'reuse':{'strategy':'not_applicable','reason':'Protocol fixture only'},
                               'implementation':origin('builtin' if c['baseline'] else 'official')}
        self.draft['candidates'][1]['source_review']['reuse']={'strategy':'direct','reason':'Synthetic original fixture',
            'source_ids':['S1'],'version':'fixture-1','code_paths':['official.py'],'api':'original(int)->bool',
            'tests':'Protocol fixture tests','dependencies':'Python stdlib','integration':'Fixture runner only',
            'license':{'status':'verified','identifier':'MIT','locator':'synthetic fixture'},'compatibility':'unknown'}
        self.design.update(dossier_json=json.dumps(self.draft),sources=[])
        self.scout={**copy.deepcopy(self.design),'sources':[{'id':'S1','title':source['title'],'url':'','path':'official.py',
                                                        'locator':'Complete synthetic module','read_level':'full_text'}]}
        self.allow_change=False

    project_files=pipeline.BoundedPipelineTests.project_files
    default_reply=pipeline.BoundedPipelineTests.default_reply

    def reply(self,role,state):
        if role=='producer-originals':return copy.deepcopy(self.scout)
        if role=='producer-environment':
            return {'status':'ready','reason':'No installation needed','packages':[],'repositories':[],
                    'needs_model':False,'model_features':[],'max_model_calls':0}
        if role=='reviewer-original':
            evidence=[r['id'] for r in state['evidence'].values() if r['kind']=='experiment']
            return {'status':'reviewed','reason':'Actual fixture gap' if self.allow_change else 'No measured need to change',
                    'proceed':self.allow_change,'evidence_ids':evidence,'parent_ids':['B'] if self.allow_change else []}
        return self.default_reply(role,state)

    def drive(self,reply=None):
        def invoke(role,schema,state,workspace,run_dir,validator=None):
            self.calls.append(role)
            value=(reply or self.reply)(role,state)
            h.validate_shape(value,schema);h.normalize_unit_paths(value,state,workspace,run_dir)
            if validator:validator(value,state)
            return value
        with patch.object(h,'checked_role',side_effect=invoke),patch.object(h,'sandbox_command',side_effect=lambda _s,_n,a:a),patch('report_polish.finish',return_value=None):
            h.loop(self.state,self.workspace,self.run)

    def test_sources_are_reviewed_before_plan_and_assets(self):
        self.drive()
        self.assertLess(self.calls.index('producer-evidence'),self.calls.index('planner'))
        self.assertLess(self.calls.index('producer-environment'),self.calls.index('producer-assets'))
        self.assertEqual(self.calls.count('producer-evidence'),2)
        self.assertEqual(self.state['status'],'research_complete')
        self.assertFalse(self.state['original_first']['change_decision']['proceed'])
        self.assertEqual([r for r in self.state['evidence'].values() if r['kind']=='experiment'],[])

    def test_approximation_cannot_be_initial_original(self):
        value=copy.deepcopy(self.scout);d=json.loads(value['dossier_json'])
        d['candidates'][1]['source_review']['implementation']['kind']='approximation';value['dossier_json']=json.dumps(d)
        with self.assertRaisesRegex(rt.Blocked,'approximation'):
            self.drive(lambda role,state:value if role=='producer-originals' else self.reply(role,state))
        self.assertNotIn('planner',self.calls);self.assertNotIn('producer-assets',self.calls)

    def test_unmeasured_effect_cannot_authorize_adaptation(self):
        self.allow_change=True
        with self.assertRaisesRegex(rt.Blocked,'measured gap'):self.drive()
        self.assertNotIn('producer-adaptation',self.calls)

    def test_source_checkpoint_is_reused_after_later_timeout(self):
        def first(role,state):
            if role=='producer-assets':raise rt.Blocked('synthetic timeout')
            return self.reply(role,state)
        with self.assertRaises(rt.Blocked):self.drive(first)
        self.drive()
        self.assertEqual(self.calls.count('producer-originals'),1)
        self.assertEqual(self.calls.count('producer-evidence'),2)
        self.assertEqual(self.calls.count('producer-environment'),1)

    def test_measured_originals_precede_changes_and_baseline_is_reused(self):
        self.allow_change=True
        self.project_files({'official.py':'def original(x):\n return x > 0\n'})
        c=contract();self.plan['evaluation_json']=json.dumps(c)
        self.plan['criteria']=[{'id':'R1','title':'parity','kind':'runtime','required':True,'acceptance':'Compare actual outputs'}]
        self.state['config']['evaluation_purpose']='effectiveness'
        def reply(role,state):
            phase=state.get('original_first',{}).get('phase','original')
            if role=='planner-adaptation':
                value=copy.deepcopy(self.plan);new=copy.deepcopy(c)
                new.update(candidate_ids=['B','C'],baseline_id='B')
                value['evaluation_json']=json.dumps(new);return value
            if role=='producer-adaptation':
                value=copy.deepcopy(state['proposal_design']);draft=json.loads(value['dossier_json'])
                parent=copy.deepcopy(next(x for x in draft['candidates'] if x['id']=='B'));parent['baseline']=True
                child=copy.deepcopy(parent);child.update(id='C',name='Changed predicate',baseline=False)
                child['source_review']['implementation']=origin('adapted','B')
                child['source_review']['reuse'].update(strategy='custom',reason='Measured predicate gap in the fixture')
                draft['candidates']=[parent,child]
                draft['comparison']=[{'candidate_id':cid,'criterion':'parity','finding':'unmeasured','basis':'unknown','claim_ids':[]} for cid in ['B','C']]
                draft['decision'].update(candidate_id='B',status='provisional')
                draft.pop('evaluation_result',None);value['dossier_json']=json.dumps(draft);return value
            if role=='producer-assets':
                if phase=='original':
                    code=('import json\nfrom official import original\n'
                          'tasks='+repr(c['tasks'])+'\ntrials=[]\n'
                          "for task in tasks:\n for cid in ('A','B'):\n  trials.append({'task_id':task['id'],'trial_id':'1','candidate_id':cid,'output':original(task['input'])})\n")
                else:
                    code=("import json,os\ndata=json.load(open(os.environ['DR_ORIGINAL_RESULTS']))\n"
                          "tasks=data['tasks'];trials=data['trials']\n"
                          "for task in tasks:\n trials.append({'task_id':task['id'],'trial_id':'1','candidate_id':'C','output':task['input']%2==0})\n")
                code+="json.dump({'contract_sha256':"+repr(state['evaluation_contract_sha256'])+",'tasks':tasks,'trials':trials},open('results.json','w'))\n"
                return {'status':'proposed','reason':'Actual local fixture functions','files':[{'path':'run.py','content':code}],
                        'experiments':[{'id':'E1','command':'python3 run.py','check_ids':['R1'],'input_files':['official.py'],
                                        'artifact_paths':['results.json'],'timeout_seconds':5}]}
            if role=='producer-results':
                value=copy.deepcopy(state['proposal_design']);draft=json.loads(value['dossier_json'])
                paths=sorted({r['artifact_path'] for r in state['evaluation_summary']['trials']})
                draft['evaluation_result']={'contract_sha256':state['evaluation_contract_sha256'],'artifact_paths':paths}
                draft['decision'].update(candidate_id='C' if phase=='adaptation' else 'B',status='provisional')
                value['dossier_json']=json.dumps(draft);return value
            if role=='reviewer-check':
                value=self.default_reply(role,state)
                value['checks'][0].update(result='pass',reason='Parent executes and grades actual fixture functions',
                    evidence_ids=[r['id'] for r in state['evidence'].values() if r['kind']=='experiment'])
                return value
            return self.reply(role,state)
        self.drive(reply)
        self.assertEqual(self.state['status'],'research_complete')
        self.assertLess(self.calls.index('reviewer-original'),self.calls.index('producer-adaptation'))
        self.assertEqual(self.calls.count('producer-assets'),2)
        receipts=[r for r in self.state['evidence'].values() if r['kind']=='experiment']
        self.assertEqual(len(receipts),2)
        self.assertEqual(self.state['original_first']['experiments']['1'],['original:E1','adaptation:E1'])
        before=copy.deepcopy(self.state['evaluation_summary'])
        self.drive(reply)
        self.assertEqual(len([r for r in self.state['evidence'].values() if r['kind']=='experiment']),2)
        self.assertEqual(self.state['evaluation_summary'],before)

    def test_shared_experiment_budget_and_stage_execution_keys(self):
        from execution_units import execution_key
        self.state['proposal']={'files':[]}
        d=original.data(self.state)
        original.reserve_experiment(self.state,'E1')
        first=execution_key(self.state,'python run.py',[], 'E1',[])
        d['phase']='adaptation'
        self.assertNotEqual(first,execution_key(self.state,'python run.py',[],'E1',[]))
        original.reserve_experiment(self.state,'E1');original.reserve_experiment(self.state,'E2')
        with self.assertRaisesRegex(rt.Blocked,'allowance'):original.reserve_experiment(self.state,'E3')

    def test_manifest_requires_pins_and_explicit_model_budget(self):
        original.data(self.state)['source_dossier']=copy.deepcopy(self.scout)
        value=self.reply('producer-environment',self.state)
        value['packages']=[{'candidate_id':'B','kind':'python','spec':'some-library>=1'}]
        with self.assertRaisesRegex(rt.Blocked,'exact version'):original.validate_manifest(value,self.state)
        value['packages']=[];value.update(needs_model=True,max_model_calls=2)
        with self.assertRaisesRegex(rt.Blocked,'explicit access'):original.validate_manifest(value,self.state)

    def test_baseline_reuse_cannot_change_outputs(self):
        self.state['evaluation_contract']={'baseline_id':'B'}
        self.state['evaluation_contract_sha256']='new-contract'
        path=self.run/'old-result.json'
        value={'contract_sha256':'old','tasks':[{'id':'T','input':3,'expected':False}],
               'trials':[{'task_id':'T','trial_id':'1','candidate_id':'B','output':False}]}
        path.write_text(json.dumps(value))
        d=original.data(self.state);d.update(phase='adaptation',original_snapshot={'result_artifacts':[{'path':str(path.relative_to(self.workspace)),'sha256':rt.sha256(path)}]})
        derived=original.baseline_results(self.state,self.workspace)
        original.verify_reused(derived,self.state,self.workspace)
        derived['trials'][0]['output']=True
        with self.assertRaisesRegex(rt.Blocked,'differs'):original.verify_reused(derived,self.state,self.workspace)

    def test_offline_preparation_is_unverified_and_not_executed(self):
        d=original.data(self.state);d.update(source_dossier=self.scout,source_holds={},
            preparation={**self.reply('producer-environment',self.state),
                         'packages':[{'candidate_id':'B','kind':'python','spec':'fixture==1.0'}]})
        with patch.object(original,'capture') as execute:
            original.prepare_environments(h,self.state,self.workspace,self.run)
        execute.assert_not_called()
        self.assertIn('offline',d['preparation_failures']['B'])
        self.assertNotIn('B',d['environments'])

    def test_uncertain_preparation_is_not_replayed(self):
        d=original.data(self.state);d.update(source_dossier=self.scout,source_holds={},
            preparation=self.reply('producer-environment',self.state),preparation_attempts={'B':{'status':'started'}})
        with patch.object(original,'capture') as execute:
            original.prepare_environments(h,self.state,self.workspace,self.run)
        execute.assert_not_called()
        self.assertIn('Interrupted',d['preparation_failures']['B'])

    def test_missing_preparation_tool_is_unverified_not_a_method_score(self):
        d=original.data(self.state);d.update(source_dossier=self.scout,source_holds={},
            preparation={**self.reply('producer-environment',self.state),
                         'packages':[{'candidate_id':'B','kind':'node','spec':'fixture@1.0.0'}]})
        self.state['config']['allow_network']=True
        with patch.object(original,'capture',side_effect=FileNotFoundError('synthetic missing npm')),patch.object(original,'sandbox_command',side_effect=lambda s,n,a:a):
            original.prepare_environments(h,self.state,self.workspace,self.run)
        self.assertIn('missing npm',d['preparation_failures']['B'])
        self.assertNotIn('B',d['environments'])
        self.assertNotIn('evaluation_summary',self.state)

    def test_isolated_python_install_records_actual_inventory(self):
        # Synthetic local wheel: no package registry/network, real venv and pip installation.
        import zipfile
        d=original.data(self.state);d.update(source_dossier=self.scout,source_holds={},
            preparation={**self.reply('producer-environment',self.state),
                         'packages':[{'candidate_id':'B','kind':'python','spec':'dr_fixture==1.0'}]})
        self.state['config']['allow_network']=True
        real_capture=original.capture
        def execute(argv,**kwargs):
            if 'wheel' in argv:
                path=Path(argv[argv.index('--wheel-dir')+1]);path.mkdir()
                wheel=path/'dr_fixture-1.0-py3-none-any.whl'
                with zipfile.ZipFile(wheel,'w') as z:
                    z.writestr('dr_fixture.py','VALUE=37\n')
                    z.writestr('dr_fixture-1.0.dist-info/METADATA','Metadata-Version: 2.1\nName: dr_fixture\nVersion: 1.0\n')
                    z.writestr('dr_fixture-1.0.dist-info/WHEEL','Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
                    z.writestr('dr_fixture-1.0.dist-info/RECORD','')
                argv=[__import__('sys').executable,'-c','print("synthetic local wheel")']
            return real_capture(argv,**kwargs)
        with patch.object(original,'sandbox_command',side_effect=lambda s,n,a:a),patch.object(original,'capture',side_effect=execute):
            original.prepare_environments(h,self.state,self.workspace,self.run)
        self.assertNotIn('B',d['preparation_failures'])
        record=d['environments']['B']
        import subprocess
        result=subprocess.run([record['python'],'-I','-c','import dr_fixture; print(dr_fixture.VALUE)'],capture_output=True,text=True,check=True)
        self.assertEqual(result.stdout.strip(),'37')
        self.assertEqual(len(record['dependency_files']),1)
        self.assertTrue(all((self.workspace/r['path']).is_file() for r in d['artifacts']))

    def test_model_fallback_counts_failed_probe_and_freezes_working_transport(self):
        d=original.data(self.state);d['preparation']={**self.reply('producer-environment',self.state),
                                                   'needs_model':True,'model_features':['text'],'max_model_calls':3}
        def resolve(config,requested=None,*,backend=None):
            return {'backend':backend or 'api','model':'fixture','capabilities':['text'],'scope':'fixture'}
        def response(model,*args):
            if model.connection['backend']=='api':raise OSError('fixture provider unavailable')
            return {'usage':None,'choices':[{'message':{'content':'OK'}}]}
        with patch.object(access,'resolve',side_effect=resolve),patch.object(access.ModelAccess,'_api',response),patch.object(access.ModelAccess,'_codex',response),patch.object(original.shutil,'which',return_value='codex'):
            original.prepare_model(h,self.state,self.workspace,self.run)
        self.assertEqual([p['success'] for p in d['model_probes']],[False,True])
        self.assertEqual(d['model_selector'],'codex')
        ledger=json.loads((self.run/'original-first/model-access/ledger.json').read_text())
        self.assertEqual([c['status'] for c in ledger['calls']],['failed','complete'])
        self.assertEqual(ledger['max_calls'],3)


class ModelAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.connection={'backend':'api','model':'fixture-model','base_url':'http://127.0.0.1','key_env':'FIXTURE_KEY',
                         'capabilities':['text','json'],'scope':'synthetic API transport'}

    def test_failed_dispatch_consumes_budget_and_resume_does_not_reset(self):
        model=access.ModelAccess(self.connection,self.root,max_calls=1,deadline=time.time()+5)
        with patch.object(model,'_api',side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):model.request({'messages':[]})
        resumed=access.ModelAccess(self.connection,self.root,max_calls=1,deadline=time.time()+5)
        with self.assertRaisesRegex(rt.Blocked,'budget'):resumed.request({'messages':[]})
        self.assertNotIn('base_url',resumed.ledger['connection'])

    def test_different_model_cannot_reuse_ledger(self):
        access.ModelAccess(self.connection,self.root,max_calls=2,deadline=time.time()+5)
        with self.assertRaisesRegex(rt.Blocked,'changed'):
            access.ModelAccess({**self.connection,'model':'other'},self.root,max_calls=2,deadline=time.time()+5)

    def test_cli_does_not_fake_native_tool_or_sampling_support(self):
        model=access.ModelAccess({**self.connection,'backend':'codex'},self.root,max_calls=2,deadline=time.time()+5)
        for body in ({'tools':[{}]},{'temperature':0},{'messages':[{'content':[{'type':'image_url'}]}]}):
            with self.assertRaises(rt.Blocked):model.request(body)
        self.assertEqual(model.ledger['calls'],[])

    def test_cli_media_cannot_be_enabled_by_declaring_capabilities(self):
        model=access.ModelAccess({**self.connection,'backend':'codex','capabilities':['text','json','multimodal']},
                                self.root,max_calls=1,deadline=time.time()+5)
        with patch.object(model,'_codex') as dispatch:
            for kind in ('image_url','input_audio','input_file'):
                with self.assertRaisesRegex(rt.Blocked,'modalities'):
                    model.request({'messages':[{'content':[{'type':kind,'url':'https://example.invalid/fixture'}]}]})
            dispatch.assert_not_called()
        self.assertEqual(model.ledger['calls'],[])

    def test_cli_connection_rejects_unsupported_capability_declarations(self):
        path=self.root/'connection.json'
        path.write_text(json.dumps({'backend':'codex','model':'fixture','capabilities':['text','multimodal']}))
        with patch.object(access.shutil,'which',return_value='codex'):
            with self.assertRaisesRegex(rt.Blocked,'text/json only'):
                access.resolve({'model_connection_file':str(path)})

    def test_plain_text_about_media_fields_is_still_plain_text(self):
        model=access.ModelAccess({**self.connection,'backend':'codex'},self.root,max_calls=1,deadline=time.time()+5)
        with patch.object(model,'_codex',return_value={'choices':[{'message':{'content':'fixture'}}]}) as dispatch:
            value=model.request({'messages':[{'role':'user','content':'Explain image_url and input_audio as JSON field names.'}]})
        dispatch.assert_called_once()
        self.assertEqual(value['choices'][0]['message']['content'],'fixture')
        self.assertEqual(model.ledger['calls'][0]['status'],'complete')

    def test_api_bridge_keeps_real_key_in_parent_and_returns_actual_reply(self):
        seen={}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                seen['auth']=self.headers.get('Authorization');seen['body']=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                raw=json.dumps({'model':'fixture-model','choices':[{'message':{'role':'assistant','content':'fixture response'}}],
                                'usage':{'prompt_tokens':3,'completion_tokens':2}}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        model=access.ModelAccess({**self.connection,'base_url':f'http://127.0.0.1:{server.server_port}/v1'},self.root,max_calls=2,deadline=time.time()+10)
        with patch.dict(os.environ,{'FIXTURE_KEY':'synthetic-not-a-real-key'}),model.bridge() as bridge:
            import urllib.request
            self.assertNotEqual(bridge['OPENAI_API_KEY'],'synthetic-not-a-real-key')
            req=urllib.request.Request(bridge['OPENAI_BASE_URL']+'/chat/completions',
                data=json.dumps({'model':'original-paper-model','messages':[{'role':'user','content':'fixture'}]}).encode(),
                headers={'Authorization':'Bearer '+bridge['OPENAI_API_KEY'],'Content-Type':'application/json'})
            with urllib.request.urlopen(req) as response:value=json.load(response)
        self.assertEqual(seen['body']['model'],'fixture-model')
        self.assertEqual(value['choices'][0]['message']['content'],'fixture response')
        self.assertNotIn('synthetic-not-a-real-key',model.path.read_text())
        self.assertEqual(model.ledger['calls'][0]['usage']['completion_tokens'],2)


if __name__=='__main__':unittest.main()
