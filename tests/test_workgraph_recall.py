import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/'tools/basic-memory-workgraph/workgraph_recall.py'
spec=importlib.util.spec_from_file_location('recall',SOURCE)
recall=importlib.util.module_from_spec(spec);spec.loader.exec_module(recall)


class Reader:
    def __init__(self):
        self.notes={'corrections/flow':{'title':'Keep writing flow','content':'scope: writing skill refactoring\ninstruction: preserve the order of editing stages','frontmatter':{'type':'correction'}}}
        self.fail=False
    def search(self,project,query,limit,deadline):
        if self.fail:raise ValueError('service unavailable')
        return [{'permalink':key,'title':value['title']} for key,value in self.notes.items()][:limit]
    def read(self,project,identifier,deadline):return self.notes[identifier]


class RecallTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.codex=Path(self.tmp.name)/'codex';self.root=self.codex/'basic-memory-workgraph';self.root.mkdir(parents=True)
        (self.root/'config.json').write_text('{"mode":"smart"}')
        (self.codex/'basic-memory.json').write_text('{"basicMemory":{"primaryProject":"fixture"}}')
        self.reader=Reader();self.service=recall.Recall(self.codex,self.reader)
        self.ticket='a'*64;self.work=Path(self.tmp.name)/'work';self.work.mkdir()
    def prepare(self,mode='implementation'):
        return self.service.prepare(self.ticket,'editing stages',self.work,mode)
    def select(self,decision='adopted'):
        return self.service.select(self.ticket,[{'id':'fixture:corrections/flow','decision':decision,'reason':'same writing task','condition':'preserve editing stage order','action':'compare the stage order','verification':'compare before and after'}],'implementation')
    def test_read_only_check_does_not_change_an_existing_record(self):
        self.prepare();self.select()
        before=self.service.path(self.ticket).read_bytes()
        self.assertEqual(self.service.check(self.ticket,[],mode='plan')['status'],'pending')
        self.assertEqual(before,self.service.path(self.ticket).read_bytes())
        with self.assertRaises(ValueError):self.service.check(self.ticket,[],close=True,mode='plan')

    def test_secrets_and_oversized_notes_are_not_adopted(self):
        with self.assertRaises(ValueError):self.service.prepare(self.ticket,'password=very-secret',self.work,'implementation')
        self.reader.notes['corrections/flow']['content']='x'*7000
        self.prepare()
        with self.assertRaises(ValueError):self.select()

    def test_changed_evidence_and_wrong_task_id_are_rejected(self):
        self.prepare();self.select()
        artifact=self.work/'review.md';artifact.write_text('before')
        fingerprint=hashlib.sha256(artifact.read_bytes()).hexdigest();artifact.write_text('after')
        report=self.service.check(self.ticket,[{'id':'fixture:corrections/flow','path':'review.md','sha256':fingerprint,'result':'verified'}])
        self.assertEqual(report['status'],'pending')
        with self.assertRaises(ValueError):self.service.prepare(self.ticket,'another purpose',self.work,'implementation')

    def test_search_failure_is_not_no_results(self):
        self.reader.fail=True
        self.assertEqual(self.prepare()['status'],'unavailable')
        self.assertEqual(self.service.check(self.ticket,[])['status'],'pending')
        self.assertTrue(self.service.stop(self.ticket)['block'])
        self.assertEqual(self.service.stop(self.ticket)['status'],'unverified')
        self.reader.fail=False;self.reader.notes={}
        self.assertEqual(self.prepare()['status'],'no_results')
    def test_changing_selection_invalidates_previous_check(self):
        self.prepare();self.select('excluded')
        self.assertEqual(self.service.check(self.ticket,[])['status'],'verified')
        self.select()
        self.assertTrue(self.service.stop(self.ticket)['block'])
    def test_seed_terms_never_extract_sensitive_fragments(self):
        for prompt in ('Contact writer@example.invalid about memory', '/home/example/private memory',
                       'api_key=fixture-secret memory', 'Bearer fixture-token memory'):
            self.assertEqual(recall.Recall.seed_query(prompt),'')
        self.assertEqual(recall.Recall.seed_query('Implement the plan.'),'')
        self.assertIn('memory',recall.Recall.seed_query('Verify memory application'))
    def test_read_only_never_writes_task_state(self):
        before=list(self.root.rglob('*'))
        self.assertEqual(self.prepare('plan')['status'],'found')
        self.assertEqual(before,list(self.root.rglob('*')))
        with self.assertRaises(ValueError):self.service.select(self.ticket,[],'plan')
    def test_selection_requires_evidence_and_detects_changed_note(self):
        self.prepare();self.select()
        self.assertEqual(self.service.check(self.ticket,[])['status'],'pending')
        artifact=self.work/'review.md';artifact.write_text('Compared stages: unchanged')
        evidence=[{'id':'fixture:corrections/flow','path':'review.md','sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'result':'verified'}]
        self.assertEqual(self.service.check(self.ticket,evidence)['status'],'verified')
        self.reader.notes['corrections/flow']['content']='new instruction'
        self.assertEqual(self.service.check(self.ticket,evidence)['status'],'pending')
    def test_off_disallows_automatic_state_and_selection(self):
        (self.root/'config.json').write_text('{"mode":"off"}')
        self.prepare()
        self.assertFalse(self.service.path(self.ticket).exists())
        with self.assertRaises(ValueError):self.select()
    def test_unreviewed_notes_cannot_be_adopted(self):
        self.reader.notes['corrections/flow']['frontmatter']['integrity_status']='needs_review'
        self.prepare()
        with self.assertRaises(ValueError):self.select()
    def test_evidence_cannot_escape_project_and_tickets_do_not_mix(self):
        self.prepare();self.select()
        with self.assertRaises(ValueError):self.service.check('b'*64,[])
        result=self.service.check(self.ticket,[{'id':'fixture:corrections/flow','path':'../secret','sha256':'0'*64,'result':'verified'}])
        self.assertEqual(result['status'],'pending')
    def test_excluded_notes_need_reason_and_cleanup_is_not_long_term_memory(self):
        self.prepare();self.select('excluded')
        self.assertEqual(self.service.check(self.ticket,[],close=True)['status'],'verified')
        self.assertFalse(self.service.path(self.ticket).exists())
        self.assertFalse((self.root/'corrections').exists())
    def test_one_stop_reminder_and_never_false_completion(self):
        self.prepare();self.select()
        self.assertTrue(self.service.stop(self.ticket)['block'])
        second=self.service.stop(self.ticket)
        self.assertFalse(second['block'])
        self.assertEqual(second['status'],'unverified')
        self.assertFalse(self.service.path(self.ticket).exists())

class HookApplicationTests(unittest.TestCase):
    def setUp(self):
        import test_workgraph as fixtures
        fixtures.WorkgraphTest.setUp(self)
        self.install=fixtures.WorkgraphTest.install.__get__(self)
        self.hook=fixtures.WorkgraphTest.hook.__get__(self)
        self.assertEqual(self.install().returncode,0)
    def prepare_selected(self):
        event={'session_id':'fixture','turn_id':'one','prompt':'writing flow','cwd':str(self.home)}
        ticket=hashlib.sha256(json.dumps([event['session_id'],event['turn_id']]).encode()).hexdigest()
        service=recall.Recall(self.codex,Reader())
        result=service.prepare(ticket,'writing flow',self.home,'implementation')
        identity=result['notes'][0]['id']
        service.select(ticket,[{'id':identity,'decision':'adopted','reason':'matching scope','condition':'retain flow','action':'compare stages','verification':'compare artifact'}],'implementation')
        return service,ticket,event
    def test_stop_reminds_once_and_reports_unverified_without_recursion(self):
        service,ticket,event=self.prepare_selected()
        first=self.hook('save',event)
        self.assertEqual(first['decision'],'block')
        second=self.hook('save',{**event,'stop_hook_active':True})
        self.assertIn('unverified',second['systemMessage'])
        self.assertFalse(service.path(ticket).exists())
    def test_plan_stop_never_writes_application_record(self):
        service,ticket,event=self.prepare_selected();before=service.path(ticket).read_bytes()
        self.assertEqual(self.hook('save',{**event,'permission_mode':'plan'}),{})
        self.assertEqual(before,service.path(ticket).read_bytes())

class LocalReaderTests(unittest.TestCase):
    def setUp(self):
        from unittest import mock
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.memory=self.root/'memory';self.memory.mkdir()
        (self.root/'config.json').write_text(json.dumps({'projects':{'fixture':{'mode':'local','path':str(self.memory)}}}))
        self.env=mock.patch.dict('os.environ',{'BASIC_MEMORY_CONFIG_DIR':str(self.root)})
        self.env.start();self.addCleanup(self.env.stop)
        self.reader=recall.RegisteredReader(['/missing/cli'])
    def test_registered_local_queries_do_not_start_cli_and_reread_changed_notes(self):
        import time
        folder=self.memory/'corrections';folder.mkdir();note=folder/'flow.md'
        note.write_text('---\ntitle: Editing stages\ntype: correction\nintegrity_status: checked\n---\nPreserve writing flow')
        result=self.reader.search('fixture','writing OR unrelated',5,time.monotonic()+5)
        self.assertEqual(len(result),1)
        first=self.reader.read('fixture',result[0]['permalink'],time.monotonic()+5)
        note.write_text(note.read_text()+'\nNew instruction')
        second=self.reader.read('fixture',result[0]['permalink'],time.monotonic()+5)
        self.assertNotEqual(recall.digest(first),recall.digest(second))
    def test_unregistered_projects_and_linked_notes_are_not_guessed(self):
        import time
        with self.assertRaises((OSError,ValueError)):self.reader.search('missing','flow',5,time.monotonic()+5)
        (self.memory/'bad.md').symlink_to(self.root/'config.json')
        with self.assertRaises(ValueError):self.reader.search('fixture','flow',5,time.monotonic()+5)
    def test_invalid_yaml_is_an_unavailable_source(self):
        import time
        (self.memory/'bad.md').write_text('---\ntitle: [unterminated\n---\nflow')
        with self.assertRaises(ValueError):self.reader.search('fixture','flow',5,time.monotonic()+5)
    def test_xdg_registry_is_used_when_explicit_config_dir_is_absent(self):
        import os
        from unittest.mock import patch
        xdg=self.root/'xdg';directory=xdg/'basic-memory';directory.mkdir(parents=True)
        (directory/'config.json').write_bytes((self.root/'config.json').read_bytes())
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(xdg)}):
            previous=os.environ.pop('BASIC_MEMORY_CONFIG_DIR')
            try:self.assertEqual(self.reader.local_root('fixture'),self.memory)
            finally:os.environ['BASIC_MEMORY_CONFIG_DIR']=previous
    def test_yaml_dates_and_inline_cli_work_inside_task_directory(self):
        import os,subprocess,sys,time
        folder=self.memory/'rules';folder.mkdir()
        (folder/'flow.md').write_text('---\ntitle: Flow\ntype: rule\ndate: 2026-01-01\n---\nPreserve writing flow')
        note=self.reader.search('fixture','flow',5,time.monotonic()+5)[0]
        recall.digest(note)
        codex=self.root/'codex';policy=codex/'basic-memory-workgraph';policy.mkdir(parents=True)
        (policy/'config.json').write_text('{"mode":"smart"}')
        (codex/'basic-memory.json').write_text('{"basicMemory":{"primaryProject":"fixture"}}')
        work=self.root/'work';work.mkdir();ticket='c'*64
        base=[sys.executable,'-B',str(SOURCE),'--codex-dir',str(codex)]
        def run(*args):
            result=subprocess.run([*base,*args],cwd=work,env=os.environ,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout)
            return json.loads(result.stdout)
        result=run('prepare','--ticket',ticket,'--query','flow','--mode','implementation')
        selection=[{'id':result['notes'][0]['id'],'decision':'excluded','reason':'different scope'}]
        run('select','--ticket',ticket,'--input',json.dumps(selection),'--mode','implementation')
        self.assertEqual(run('check','--ticket',ticket,'--input','[]','--mode','implementation','--close')['status'],'verified')
        self.assertFalse((work/'.workgraph-recall'/(ticket+'.json')).exists())
        self.assertEqual((work/'.workgraph-recall/.gitignore').read_text(),'*\n')


class ConfigureRuntimeTests(unittest.TestCase):
    def test_failed_configuration_write_restores_previous_files(self):
        from unittest.mock import patch
        import contextlib,io
        source=SOURCE.parent/'configure_workgraph.py'
        spec=importlib.util.spec_from_file_location('recall_configure',source)
        config=importlib.util.module_from_spec(spec);spec.loader.exec_module(config)
        with tempfile.TemporaryDirectory() as temporary:
            codex=Path(temporary)/'codex'
            with contextlib.redirect_stdout(io.StringIO()):config.configure(codex)
            originals={p:p.read_bytes() for p in codex.rglob('*') if p.is_file()}
            original=config.write_file;calls=[]
            def fail(path,content,stamp):
                calls.append(path)
                if len(calls)==4:raise OSError('fixture write failure')
                original(path,content,stamp)
            with patch.object(config,'write_file',side_effect=fail),self.assertRaises(OSError):
                config.configure(codex,mode='off',correction_mode='scoped')
            for path,content in originals.items():self.assertEqual(path.read_bytes(),content)
