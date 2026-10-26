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
        self.u.save(self.candidate/'quality.json',{'status':'passed',
            'case_ids':['E'+str(i).zfill(2) for i in range(1,13)]+['K'+str(i).zfill(2) for i in range(1,7)],
            'critical_errors':[],'unresolved_regressions':[],
            'adapter_sha256':{k:v for k,v in self.u.digest(adapter).items() if k not in {'UPSTREAMS.json','resources.json'}},
            'artifacts':{'synthetic-result.json':I.sha(result.read_bytes())}})
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


if __name__=='__main__':unittest.main()
