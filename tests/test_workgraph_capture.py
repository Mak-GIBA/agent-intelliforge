"""Synthetic graph only: validate capture writes, conflicts and turn accounting."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'tools/basic-memory-workgraph'
sys.path.insert(0,str(SOURCE))
import workgraph_capture as capture


class Backend:
    def __init__(self):self.notes={};self.fail=False;self.writes=0;self.corrupt=False;self.after_write_error=False
    def search(self,project,query,limit,deadline):
        if self.fail:raise ValueError('unavailable')
        return [{'permalink':key,'title':value['title']} for key,value in self.notes.items()][:limit]
    def read(self,project,identifier,deadline):return copy.deepcopy(self.notes[identifier])
    def write(self,project,note,folder,checksum=None):
        self.writes+=1;key=folder+'/'+note.metadata['title'].lower().replace(' ','-')
        if checksum and self.notes[key]['checksum']!=checksum:return None
        content=note.render()+('changed' if self.corrupt else '')
        self.notes[key]={'title':note.metadata['title'],'content':content,'frontmatter':note.metadata.copy(),'checksum':str(self.writes)}
        return None if self.after_write_error else {'permalink':key}


def candidate(kind='validation'):
    return {'kind':kind,'query':'synthetic fixture',
            'admission':{key:'Grounded synthetic evidence for '+key for key in capture.GATES[kind]},
            'note':'---\ntitle: Synthetic fixture\ntype: '+kind+'\n---\n\n# Synthetic fixture\n\n## Observations\n- [check] A bounded synthetic check supports this procedure.\n'}


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.codex=Path(self.tmp.name)/'codex';self.root=self.codex/'basic-memory-workgraph';(self.root/'state').mkdir(parents=True)
        self.work=Path(self.tmp.name)/'work';self.work.mkdir();self.ticket='a'*64;self.token='b'*64
        self.config={'mode':'smart','correctionMode':'scoped','caseMode':'progressive','decisionMode':'scoped'}
        (self.root/'memory-policy.md').write_text('Synthetic test policy')
        self.write_config();(self.codex/'basic-memory.json').write_text('{"basicMemory":{"primaryProject":"fixture"}}')
        (self.root/'state'/(self.ticket+'.json')).write_text(json.dumps({'version':1,'token':self.token,'armed':False,'workdir':capture.recall.digest(str(self.work))}))
        self.backend=Backend();self.service=capture.Capture(self.codex,self.work,self.backend,self.backend)
    def write_config(self):(self.root/'config.json').write_text(json.dumps(self.config))
    def apply(self,data,decisions=None,mode='implementation'):
        prepared=self.service.prepare(data)
        if decisions is None:decisions=[{'id':row['id'],'decision':'distinct','reason':'Different tested property'} for row in prepared['matches']]
        return self.service.apply(self.ticket,self.token,data,prepared['review'],decisions,mode)
    def test_write_readback_and_finish_without_extra_stop(self):
        self.assertEqual(self.apply(candidate())['status'],'saved')
        result=self.service.finish(self.ticket,self.token,'complete','implementation')
        self.assertEqual(result['status'],'saved');self.assertFalse(result['extra_evaluation'])
        self.assertFalse(self.service.task_path(self.ticket).exists())
        note=list(self.backend.notes.values())[0]['frontmatter']
        self.assertEqual(note['sharing_scope'],'private');self.assertEqual(note['training_use'],'excluded')
        with self.assertRaises(ValueError):self.service.finish(self.ticket,self.token,'no_candidate','implementation')
    def test_error_after_committed_write_is_recovered_by_readback_without_retry(self):
        self.backend.after_write_error=True
        self.assertEqual(self.apply(candidate())['status'],'saved');self.assertEqual(self.backend.writes,1)
    def test_duplicate_is_no_write(self):
        data=candidate();self.apply(data);prepared=self.service.prepare(data)
        result=self.apply(data,[{'id':prepared['matches'][0]['id'],'decision':'duplicate','reason':'No new information'}])
        self.assertEqual(result['status'],'duplicate');self.assertEqual(self.backend.writes,1)
    def test_update_requires_new_evidence_and_conditional_write(self):
        data=candidate();self.apply(data)
        data.update(action='update',target='validations/synthetic-fixture',change_evidence='A second bounded check adds a limit.')
        data['note']+='- [limit] The recovery applies only to this failure.\n'
        prepared=self.service.prepare(data)
        decisions=[{'id':prepared['matches'][0]['id'],'decision':'update','reason':'Same procedure, new limit'}]
        self.assertEqual(self.apply(data,decisions)['status'],'updated');self.assertEqual(self.backend.writes,2)
        self.assertEqual(self.service.finish(self.ticket,self.token,'complete','implementation')['status'],'updated')
    def update_fixture(self,observation):
        data=candidate();data.update(action='update',target='validations/synthetic-fixture',change_evidence='New bounded observation.')
        data['note']+='- [limit] '+observation+'\n'
        prepared=self.service.prepare(data)
        decisions=[{'id':row['id'],'decision':'update' if row['identifier']==data['target'] else 'distinct','reason':'Same note with new evidence' if row['identifier']==data['target'] else 'Different procedure'} for row in prepared['matches']]
        return self.apply(data,decisions)
    def test_multiple_updates_and_revisiting_an_earlier_candidate_can_finish(self):
        self.apply(candidate())
        for observation in ('First checked limit.','A revised checked limit.','First checked limit.'):
            self.assertEqual(self.update_fixture(observation)['status'],'updated')
        self.assertEqual(self.service.finish(self.ticket,self.token,'complete','implementation')['status'],'updated')
    def test_external_edit_after_verified_update_still_prevents_completion(self):
        self.apply(candidate());self.update_fixture('Checked limit.')
        self.backend.notes['validations/synthetic-fixture']['content']+='external change'
        self.assertEqual(self.service.finish(self.ticket,self.token,'complete','implementation')['status'],'failed')
    def test_updating_one_note_does_not_hide_another_notes_external_edit(self):
        self.apply(candidate());other=candidate();other['note']=other['note'].replace('Synthetic fixture','Other procedure')
        self.apply(other);self.update_fixture('Checked limit.')
        self.backend.notes['validations/other-procedure']['content']+='external change'
        self.assertEqual(self.service.finish(self.ticket,self.token,'complete','implementation')['status'],'failed')
    def test_failed_update_remains_failed_at_finish(self):
        self.apply(candidate());self.backend.corrupt=True
        self.assertEqual(self.update_fixture('Checked limit.')['status'],'failed')
        self.assertEqual(self.service.finish(self.ticket,self.token,'complete','implementation')['status'],'failed')
    def test_concurrent_source_or_configuration_change_rejects_stale_review(self):
        data=candidate();prepared=self.service.prepare(data)
        self.config['skillMode']='off';self.write_config()
        with self.assertRaises(ValueError):self.service.apply(self.ticket,self.token,data,prepared['review'],[],'implementation')
        self.assertEqual(self.backend.writes,0)
    def test_two_prepared_creates_do_not_race_into_a_duplicate_write(self):
        data=candidate();review=self.service.prepare(data)['review']
        self.apply(data)
        other=capture.Capture(self.codex,self.work,self.backend,self.backend)
        with self.assertRaises(ValueError):other.apply(self.ticket,self.token,data,review,[],'implementation')
        self.assertEqual(self.backend.writes,1)
    def test_failed_readback_cannot_be_called_complete(self):
        self.backend.corrupt=True
        self.assertEqual(self.apply(candidate())['status'],'failed')
        self.assertEqual(self.service.finish(self.ticket,self.token,'complete','implementation')['status'],'failed')
    def test_readback_receipt_is_rechecked_before_finish(self):
        self.apply(candidate());self.backend.notes['validations/synthetic-fixture']['content']+='changed'
        self.assertEqual(self.service.finish(self.ticket,self.token,'complete','implementation')['status'],'failed')
    def test_search_failure_is_never_a_no_results_write(self):
        self.backend.fail=True
        with self.assertRaises(ValueError):self.apply(candidate())
        self.assertEqual(self.backend.writes,0)
    def test_missing_policy_and_invalid_mode_never_write(self):
        (self.root/'memory-policy.md').unlink()
        with self.assertRaises((ValueError,OSError)):self.apply(candidate())
        (self.root/'memory-policy.md').write_text('Synthetic test policy')
        self.config['decisionMode']='invalid';self.write_config()
        with self.assertRaises(ValueError):self.apply(candidate())
        self.assertEqual(self.backend.writes,0)
    def test_plan_off_stale_token_and_wrong_directory_never_write(self):
        data=candidate();before={p:p.read_bytes() for p in self.tmp_path().rglob('*') if p.is_file()}
        with self.assertRaises(ValueError):self.apply(data,mode='plan')
        with self.assertRaises(ValueError):self.service.finish(self.ticket,self.token,'no_candidate','plan')
        self.assertEqual(before,{p:p.read_bytes() for p in self.tmp_path().rglob('*') if p.is_file()})
        self.token='c'*64
        with self.assertRaises(ValueError):self.apply(data)
        self.config['mode']='off';self.write_config()
        with self.assertRaises(ValueError):self.apply(data)
        self.assertEqual(self.backend.writes,0)
    def tmp_path(self):return Path(self.tmp.name)
    def test_decision_scoped_to_repository_and_mode(self):
        data=candidate('decision');data['note']=data['note'].replace('type: decision','type: decision\nstatus: decided\nactor: user')
        self.assertEqual(self.apply(data)['status'],'saved')
        meta=self.backend.notes['codex/decisions/synthetic-fixture']['frontmatter']
        self.assertEqual(meta['repository'],self.service.scope());self.assertEqual(meta['acceptance'],'unknown')
        data['note']=data['note'].replace('actor: user','actor: user\nrepository: repo:example.invalid/wrong/repo')
        with self.assertRaises(ValueError):self.service.prepare(data)
        self.config['decisionMode']='off';self.write_config()
        with self.assertRaises(ValueError):self.service.prepare(candidate('decision'))
    def test_decision_paraphrases_are_valid_without_byte_identical_admission(self):
        data=candidate('decision');data['note']=data['note'].replace('type: decision','type: decision\nstatus: decided\nactor: user')
        data['note']+='\n## Decision\n'+''.join('- ['+key+'] Concise paraphrase of '+key+'.\n' for key in capture.GATES['decision'])
        self.assertEqual(self.apply(data)['status'],'saved')
        data['note']=data['note'].replace('- [revisit] Concise paraphrase of revisit.\n','')
        with self.assertRaises(ValueError):self.service.prepare(data)
    def test_no_self_approved_sharing_or_missing_evidence(self):
        for suffix in ('sharing_scope: public','training_use: approved','privacy_review: passed','integrity_status: checked'):
            data=candidate();data['note']=data['note'].replace('type: validation','type: validation\n'+suffix)
            with self.assertRaises(ValueError):self.service.prepare(data)
        data=candidate();del data['admission']['evidence']
        with self.assertRaises((ValueError,TypeError)):self.service.prepare(data)
    def test_finish_reports_no_candidate_and_diagnostics_are_bounded_and_private(self):
        self.assertEqual(self.service.finish(self.ticket,self.token,'no_candidate','implementation')['status'],'no_candidate')
        for index in range(80):self.service.diagnose(capture.recall.digest(index),'out_of_scope',{'decision'})
        records=json.loads((self.root/'diagnostics.json').read_text())['records']
        self.assertEqual(len(records),64)
        self.assertEqual(set(records[0]),{'turn','time','outcome','kinds'})
        self.assertEqual((self.root/'diagnostics.json').stat().st_mode&0o777,0o600)
        with patch('workgraph_capture.time.time',return_value=10**12):self.assertEqual(self.service.status()['records'],0)
    def test_pending_enables_only_one_evaluation_request(self):
        result=self.service.finish(self.ticket,self.token,'pending','implementation')
        self.assertTrue(result['extra_evaluation'])
        state=json.loads((self.root/'state'/(self.ticket+'.json')).read_text())
        self.assertTrue(state['armed']);self.assertFalse(state['finished'])
    def test_stop_continuation_cannot_arm_another_evaluation(self):
        path=self.root/'state'/(self.ticket+'.json');state=json.loads(path.read_text());state['stop_evaluation']=True;path.write_text(json.dumps(state))
        result=self.service.finish(self.ticket,self.token,'pending','implementation')
        self.assertFalse(result['extra_evaluation']);self.assertTrue(json.loads(path.read_text())['finished'])
    def test_case_uses_existing_sequence_validator(self):
        data=candidate('case');payload=json.loads((SOURCE.parents[1]/'tests/fixtures/progressive-case.json').read_text())
        data['note']=data['note'].replace('type: case','type: case\ncapture_kind: interaction_case\ncase_format_version: 2')
        data['note']+='\n## Interaction\n```json\n'+json.dumps(payload)+'\n```\n'
        self.assertEqual(self.apply(data)['status'],'saved')
        payload['steps'][0]['actor']='invented';data['note']=data['note'].split('## Interaction')[0]+'## Interaction\n```json\n'+json.dumps(payload)+'\n```\n'
        with self.assertRaises(ValueError):self.service.prepare(data)
    def test_progressive_can_save_an_unfinished_correction_sequence(self):
        data=candidate('case');payload=json.loads((SOURCE.parents[1]/'tests/fixtures/progressive-case.json').read_text())
        payload.update(steps=payload['steps'][:2],latest_output_id='o1',state='open',outcome='unverified',assessments=[])
        data['note']=data['note'].replace('type: case','type: case\ncapture_kind: interaction_case\ncase_format_version: 2')
        data['note']+='\n## Interaction\n```json\n'+json.dumps(payload)+'\n```\n'
        self.assertEqual(self.apply(data)['status'],'saved')
        self.config['caseMode']='reusable';self.write_config()
        with self.assertRaises(ValueError):self.service.prepare(data)


if __name__=='__main__':unittest.main()
