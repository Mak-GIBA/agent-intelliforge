"""Candidate states are tested with synthetic review records, not model-quality claims."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

if 'I' not in globals():
    spec=importlib.util.spec_from_file_location('upstream_v4_engine',Path(__file__).resolve().parents[1]/'installer.py')
    I=importlib.util.module_from_spec(spec);sys.modules[spec.name]=I;spec.loader.exec_module(I)
    A=I.assets()


class UpstreamCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source';self.source.mkdir()
        for name,raw in I.own_bundle('kotonoha','auto').items():
            p=self.source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        self.u=types.ModuleType('candidate_tests');self.u.I=I
        self.u.__file__=str(Path(__file__).resolve().parents[1]/'update_upstreams.py')
        exec(compile(A['engine/update_upstreams.py'],self.u.__file__,'exec'),self.u.__dict__)
        self.candidate=self.root/'candidate'
    def prepare(self):
        active=json.loads((self.source/'UPSTREAMS.json').read_text())['sources']['yomiyasu']
        files={name:raw for name,raw in I.inventory(self.source).items() if name.startswith('upstream/')}
        with patch.object(I,'resolve_release',return_value=active),patch.object(I,'fetch_release',return_value=files):
            return self.u.prepare(self.candidate,'yomiyasu',destination=self.source)
    def quality_fixture(self):
        adapter=self.candidate/'adapter'
        caps=json.loads((adapter/'capabilities.json').read_text())['capabilities']
        self.u.save(self.candidate/'review.json',{'reviewed':True,'capabilities':[c['id'] for c in caps],
            'unintegrated':[],'source_changes':['Synthetic test record; no real review claimed']})
        result=self.candidate/'synthetic-result.json';self.u.save(result,{'synthetic':True})
        quality={'status':'passed',
            'case_ids':['E'+str(i).zfill(2) for i in range(1,13)]+['K'+str(i).zfill(2) for i in range(1,7)],
            'critical_errors':[],'unresolved_regressions':[],
            'adapter_sha256':{k:v for k,v in self.u.digest(adapter).items() if k not in {'UPSTREAMS.json','resources.json'}},
            'artifacts':{'synthetic-result.json':I.sha(result.read_bytes())}}
        if (adapter/'FLOW.json').is_file():
            tasks=json.loads(A['evals/flow-tasks.json'])['tasks']
            directory=self.candidate/'native-r1';directory.mkdir()
            (directory/'runner.py').write_text('# Synthetic evaluator fixture\n')
            self.u.save(directory/'contract.json',{'tasks':tasks,'adapter_sha256':quality['adapter_sha256'],
                'runner_sha256':I.sha((directory/'runner.py').read_bytes())})
            # Synthetic transaction fixtures. These are never exported as real model evidence.
            for task in tasks:
                required=[] if task['id'] in {'W21','W22','W23','W24'} else ['audience','clarity','finish','review']
                required+=task['conditional']
                outputs='\n'.join((adapter/'references'/(n+'.md')).read_text() for n in required)
                record={'status':'completed','text':'synthetic fixture','draft_unchanged':True,'skills_unchanged':True,
                        'final_file_present':True,'diagnosis_has_no_result_file':True,
                        'tools':[{'exit_code':0,'aggregated_output':outputs,'command':'synthetic writing_lint.py check.py'}]}
                for arm in ('baseline','candidate'):self.u.save(directory/(task['id']+'-'+arm+'.json'),record)
            for batch in range(6):
                selected=tasks[batch*4:(batch+1)*4]
                rated={'cases':[
                    {'id':t['id'],'X_errors':[],'Y_errors':[],'regressions_X':[],'regressions_Y':[]}
                    for t in selected]}
                self.u.save(directory/('review-'+str(batch)+'.json'),{'result':rated,
                    'receipt':{'status':'completed','tools':[],'output':json.dumps(rated)},
                    'pairs':[{**{k:t[k] for k in ('id','instruction','input','requirements')},
                              'versions':{'X':'synthetic fixture','Y':'synthetic fixture'}} for t in selected]})
            quality.update(protocol='native-flow-v1',completed_pairs=24,route_failures=[],case_ids=[t['id'] for t in tasks])
            quality['artifacts'].update({p.relative_to(self.candidate).as_posix():I.sha(p.read_bytes()) for p in directory.iterdir() if p.is_file()})
        self.u.save(self.candidate/'quality.json',quality)
    def test_prepare_does_not_change_active_source(self):
        before=self.u.digest(self.source);r=self.prepare()
        self.assertFalse(r['applied']);self.assertEqual(before,self.u.digest(self.source))
        self.assertEqual(json.loads((self.candidate/'adapter/UPSTREAMS.json').read_text())['integration']['status'],'pending')
    def test_existing_candidate_and_source_containment_are_refused(self):
        self.prepare()
        with self.assertRaises(ValueError):self.prepare()
        with self.assertRaises(ValueError):self.u.prepare(self.source/'nested',destination=self.source)
    def test_source_fetch_failure_leaves_nothing(self):
        with patch.object(I,'resolve_release',side_effect=OSError('offline')):
            with self.assertRaises(OSError):self.u.prepare(self.candidate,'yomiyasu',destination=self.source)
        self.assertFalse(self.candidate.exists())
    def test_frozen_original_tamper_blocks_before_execution(self):
        self.prepare();p=self.candidate/'adapter/upstream/SKILL.upstream.md';p.write_text('changed')
        with self.assertRaisesRegex(ValueError,'Frozen originals'):self.u.verify(self.candidate)
    def test_missing_review_and_quality_hold_candidate(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError,'review is incomplete'):self.u.verify(self.candidate)
        self.quality_fixture();p=self.candidate/'quality.json';value=json.loads(p.read_text());value['critical_errors']=['synthetic error'];self.u.save(p,value)
        with self.assertRaisesRegex(ValueError,'quality comparison'):self.u.verify(self.candidate)
    def test_changed_adapter_cannot_reuse_quality(self):
        self.prepare();self.quality_fixture();p=self.candidate/'adapter/SKILL.md';p.write_text(p.read_text()+'\nChanged norm.\n')
        with self.assertRaisesRegex(ValueError,'another adapter'):self.u.verify(self.candidate)
    def test_verify_then_promote_records_verified_sources_and_preserves_previous(self):
        self.prepare();self.quality_fixture();before=self.u.digest(self.source)
        self.assertEqual(self.u.verify(self.candidate)['status'],'verified')
        self.assertEqual(self.u.promote(self.candidate,self.source)['status'],'promoted')
        self.assertEqual(json.loads((self.source/'UPSTREAMS.json').read_text())['integration']['status'],'verified')
        self.assertEqual(self.u.digest(self.candidate/'previous'),before)
    def test_stale_verification_or_current_source_change_blocks_promotion(self):
        self.prepare();self.quality_fixture();self.u.verify(self.candidate)
        path=self.source/'SKILL.md';path.write_text('user change')
        with self.assertRaisesRegex(ValueError,'Maintained source changed'):self.u.promote(self.candidate,self.source)
    def test_modified_output_after_verification_blocks_promotion(self):
        self.prepare();self.quality_fixture();self.u.verify(self.candidate)
        (self.candidate/'synthetic-result.json').write_text('changed')
        with self.assertRaisesRegex(ValueError,'artifact changed'):self.u.promote(self.candidate,self.source)

    def test_concurrent_promotion_lock_preserves_source(self):
        self.prepare();self.quality_fixture();self.u.verify(self.candidate)
        before=self.u.digest(self.source)
        with I.lock(self.source),self.assertRaises(I.InstallError):
            self.u.promote(self.candidate,self.source)
        self.assertEqual(self.u.digest(self.source),before)
        self.assertFalse((self.candidate/'previous').exists())

    def test_native_pass_summary_cannot_replace_missing_receipts(self):
        self.prepare();self.quality_fixture()
        path=self.candidate/'quality.json';value=json.loads(path.read_text())
        if not (self.candidate/'adapter/FLOW.json').is_file():return
        name='native-r1/W01-candidate.json';value['artifacts'].pop(name);(self.candidate/name).unlink()
        self.u.save(path,value)
        with self.assertRaisesRegex(ValueError,'Missing paired native output'):self.u.verify(self.candidate)

    def test_native_reference_receipt_and_review_must_support_summary(self):
        self.prepare();self.quality_fixture()
        if not (self.candidate/'adapter/FLOW.json').is_file():return
        path=self.candidate/'native-r1/W01-candidate.json';record=json.loads(path.read_text());record['tools']=[]
        self.u.save(path,record)
        quality=self.candidate/'quality.json';value=json.loads(quality.read_text());value['artifacts']['native-r1/W01-candidate.json']=I.sha(path.read_bytes());self.u.save(quality,value)
        with self.assertRaisesRegex(ValueError,'required reference not observed'):self.u.verify(self.candidate)

    def test_removing_flow_cannot_reuse_supplied_guide_quality(self):
        self.prepare();self.quality_fixture()
        (self.candidate/'adapter/FLOW.json').unlink()
        with self.assertRaisesRegex(ValueError,'Missing preserved flow contract'):self.u.verify(self.candidate)

    def test_answer_changed_outside_skill_run_cannot_keep_earlier_rating(self):
        self.prepare();self.quality_fixture()
        p=self.candidate/'native-r1/W01-candidate.json';record=json.loads(p.read_text());record['text']='manually repaired answer';self.u.save(p,record)
        p=self.candidate/'quality.json';quality=json.loads(p.read_text());quality['artifacts']['native-r1/W01-candidate.json']=I.sha((self.candidate/'native-r1/W01-candidate.json').read_bytes());self.u.save(p,quality)
        with self.assertRaisesRegex(ValueError,'reviewed texts differ'):self.u.verify(self.candidate)

    def test_returned_reference_remains_visible_when_later_search_fails(self):
        self.prepare();self.quality_fixture()
        p=self.candidate/'native-r1/W01-candidate.json';record=json.loads(p.read_text());record['tools'][0]['exit_code']=2;self.u.save(p,record)
        p=self.candidate/'quality.json';quality=json.loads(p.read_text());quality['artifacts']['native-r1/W01-candidate.json']=I.sha((self.candidate/'native-r1/W01-candidate.json').read_bytes());self.u.save(p,quality)
        self.assertEqual(self.u.verify(self.candidate)['status'],'verified')


if __name__=='__main__':unittest.main()
