"""Offline conformance and regression tests. Upstream execution uses marked stubs."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock
import zipfile

if 'I' not in globals():
    spec = importlib.util.spec_from_file_location('proposal_installer', Path(__file__).resolve().parents[1]/'installer.py')
    I = importlib.util.module_from_spec(spec); sys.modules[spec.name] = I; spec.loader.exec_module(I)
    A = I.assets()
L = types.ModuleType('proposal_check')
L.__file__ = str(Path(tempfile.gettempdir())/'proposal-local/scripts/check.py')
sys.modules[L.__name__] = L
exec(compile(A['scripts/check.py'].decode('utf-8'), 'check.py', 'exec'), L.__dict__)


def fixture(version=1):
    """Synthetic upstream, deliberately not the actual yomiyasu implementation."""
    values = {
        'SKILL.md': f'---\nname: yomiyasu\ndescription: synthetic fixture\n---\n# Stub {version}\n'.encode(),
        'LICENSE': b'TEST LICENSE - synthetic only\n',
        'UNICODE-LICENSE.txt': b'TEST Unicode license placeholder - synthetic only\n',
        'references/domains/tech.md': b'Synthetic reference\n',
        'scripts/markdown_visibility.py': b'READY = True\n',
        'scripts/yomiyasu_lint.py': b'# Unicode License; --json\nimport json\nimport markdown_visibility\nprint(json.dumps({"fixture": True, "findings": []}))\n',
        'scripts/yomiyasu_diff.py': b'# --json\nimport json\nprint(json.dumps({"fixture": True, "changes": []}))\n',
    }
    rows = [{'path': 'skills/yomiyasu/'+k, 'type': 'blob', 'mode': '100644',
             'sha': I.blob_sha(v), 'size': len(v)} for k, v in values.items()]
    rows += [{'path': 'LICENSE', 'type': 'blob', 'mode': '100644',
              'sha': I.blob_sha(values['LICENSE']), 'size': len(values['LICENSE'])}]
    meta = {'repository': I.REPO, 'tag': f'v0.0.{version}', 'commit': str(version)*40,
            'files': I.release_file_manifest({'tree': rows, 'truncated': False})}
    mapped = {I.map_upstream(k): v for k, v in values.items()}
    return meta, mapped, rows


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='yomiyasu-unit-')
        self.home = Path(self.tmp.name)
        self.root = self.home/'skills'
        self.project = self.home/'project'; self.project.mkdir()
        self.env = mock.patch.dict(os.environ, {'HOME': str(self.home), 'CODEX_HOME': str(self.home/'.codex')})
        self.env.start()
        self.runtime_patch = mock.patch.object(I, 'prepare_writing_runtime', return_value={'versions':{'fixture':True}})
        self.runtime_mock = self.runtime_patch.start(); self.addCleanup(self.runtime_patch.stop)
        meiseki={k:v for k,v in I.assets().items() if k.startswith('meiseki-upstream/')}
        self.meiseki_patch = mock.patch.object(I, 'fetch_meiseki', return_value=({},meiseki))
        self.meiseki_mock = self.meiseki_patch.start(); self.addCleanup(self.meiseki_patch.stop)
        self.old_cwd = Path.cwd(); os.chdir(self.project)
        self.meta, self.up, self.rows = fixture()
        self.resolve = mock.patch.object(I, 'resolve_release', return_value=self.meta)
        self.fetch = mock.patch.object(I, 'fetch_release', return_value=self.up)
        self.resolve_mock = self.resolve.start(); self.fetch_mock = self.fetch.start()
    def tearDown(self):
        self.fetch.stop(); self.resolve.stop(); self.env.stop(); os.chdir(self.old_cwd); self.tmp.cleanup()
    def install(self, names=I.COMPONENTS, **kwargs):
        return I.install_selected(self.root, names, apply=True, project=self.project, **kwargs)
    def snapshot(self, name='yomiyasu'):
        return I.inventory(self.root/name)
    def legacy(self, names=I.COMPONENTS):
        self.install(names)
        for name in names:
            target = self.root/name
            marker = json.loads((target/I.MANIFEST).read_text())
            marker['version'] = '1.3.0'
            (target/I.MANIFEST).write_text(json.dumps(marker))


# Lifecycle contracts moved to test_layout_v4.py. Source parsing, text diagnostics
# and frozen evaluation preparation below remain independent regression coverage.

class UpstreamAndSecurityTests(unittest.TestCase):
    def test_paths_are_rejected(self):
        for value in ('../x','/x','x/../y','x\\y','C:x','x//y','x\0y','.'):
            with self.subTest(value=value):
                with self.assertRaises(I.InstallError):I.safe_rel(value)
    def test_observed_v1_1_1_tree_selection(self):
        tree=json.loads(A['tests/upstream-v1.1.1-tree.json'])
        files=I.release_file_manifest(tree)
        self.assertEqual(len(files),13)
        self.assertIn('UNICODE-LICENSE.txt',files)
        self.assertIn('scripts/markdown_visibility.py',files)
        self.assertNotIn('.claude-plugin/plugin.json',files)
        self.assertEqual(files['SKILL.md']['git_blob_sha1'],'ad38af2140d4e102cad69737f2ca035cc1e87677')
    def test_unicode_license_is_included(self):
        _,_,rows=fixture(); files=I.release_file_manifest({'tree':rows,'truncated':False})
        self.assertIn('UNICODE-LICENSE.txt',files);self.assertIn('scripts/markdown_visibility.py',files)
    def test_legacy_layout_supported(self):
        _,_,rows=fixture();rows=[{**r,'path':r['path'].removeprefix('skills/yomiyasu/')} for r in rows if r['path'].startswith('skills/')]
        self.assertIn('SKILL.md',I.release_file_manifest({'tree':rows}))
    def test_truncated_tree_blocks(self):
        with self.assertRaises(I.InstallError):I.release_file_manifest({'tree':[],'truncated':True})
    def test_symlink_tree_blocks(self):
        _,_,rows=fixture();rows[0]['mode']='120000'
        with self.assertRaises(I.InstallError):I.release_file_manifest({'tree':rows})
    def test_path_traversal_in_tree_blocks(self):
        _,_,rows=fixture();rows.append({'path':'skills/yomiyasu/scripts/../../evil.py','type':'blob','mode':'100644','sha':'a'*40,'size':1})
        with self.assertRaises(I.InstallError):I.release_file_manifest({'tree':rows})
    def test_nested_skill_blocks(self):
        _,_,rows=fixture();rows.append({'path':'skills/yomiyasu/references/nested/SKILL.md','type':'blob','mode':'100644','sha':'a'*40,'size':1})
        with self.assertRaises(I.InstallError):I.release_file_manifest({'tree':rows})
    def test_conflicting_duplicate_license_blocks(self):
        _,_,rows=fixture();rows[-1]['sha']='a'*40
        with self.assertRaises(I.InstallError):I.release_file_manifest({'tree':rows})
    def test_missing_required_files_blocks(self):
        with self.assertRaises(I.InstallError):I.release_file_manifest({'tree':[]})
    def test_size_limit_blocks(self):
        _,_,rows=fixture();rows[0]['size']=I.MAX_FILE+1
        with self.assertRaises(I.InstallError):I.release_file_manifest({'tree':rows})
    def test_hash_mismatch_blocks(self):
        with self.assertRaises(I.InstallError):I.verify_file('SKILL.md',b'bad',{'size':3,'git_blob_sha1':'a'*40})
    def test_python_syntax_blocks(self):
        raw=b'def x(:'
        with self.assertRaises(SyntaxError):I.verify_file('scripts/a.py',raw,{'size':len(raw),'git_blob_sha1':I.blob_sha(raw)})
    def test_contract_missing_helper(self):
        _,files,_=fixture();del files['upstream/scripts/markdown_visibility.py']
        with self.assertRaises(I.InstallError):I.upstream_contract(files)
    def test_contract_missing_license(self):
        _,files,_=fixture();del files['upstream/UNICODE-LICENSE.txt']
        with self.assertRaises(I.InstallError):I.upstream_contract(files)
    def test_changed_skill_name_blocks(self):
        _,files,_=fixture();files['upstream/SKILL.upstream.md']=b'---\nname: different\n---\n'
        with self.assertRaises(I.InstallError):I.upstream_contract(files)
    def test_allowed_urls(self):
        I.validate_url('https://api.github.com/repos/nanaism/yomiyasu/releases/latest')
        I.validate_url('https://raw.githubusercontent.com/nanaism/yomiyasu/main/README.md')
    def test_other_endpoints_are_rejected(self):
        for url in ('http://api.github.com/repos/nanaism/yomiyasu/x','https://api.github.com/repos/evil/repo/x','https://evil.example/x','https://user:pass@api.github.com/repos/nanaism/yomiyasu/x'):
            with self.subTest(url=url):
                with self.assertRaises(I.InstallError):I.validate_url(url)
    def test_lightweight_tag_resolution(self):
        with mock.patch.object(I,'json_download',return_value={'object':{'type':'commit','sha':'a'*40}}):
            self.assertEqual(I.tag_commit('v1.1.1'),'a'*40)
    def test_annotated_tag_ignores_remote_url(self):
        replies=[{'object':{'type':'tag','sha':'b'*40,'url':'https://evil.example'}},{'object':{'type':'commit','sha':'a'*40}}]
        with mock.patch.object(I,'json_download',side_effect=replies) as getter:
            self.assertEqual(I.tag_commit('v1.1.1'),'a'*40)
            self.assertIn('/git/tags/'+('b'*40),getter.call_args[0][0])
    def test_prerelease_is_rejected(self):
        with mock.patch.object(I,'json_download',return_value={'prerelease':True,'tag_name':'v1.1.1'}):
            with self.assertRaises(I.InstallError):I.resolve_release()
    def test_downloaded_files_verified_and_mapped(self):
        meta,files,_=fixture()
        source={spec['repo_path']:files[I.map_upstream(name)] for name,spec in meta['files'].items()}
        with mock.patch.object(I,'download',side_effect=lambda url:source[url.split(meta['commit']+'/',1)[1]]):
            self.assertEqual(I.fetch_release(meta),files)


class TextRegressionTests(unittest.TestCase):
    def test_soft_wrapped_meta_is_detected(self):
        self.assertTrue(L.local_lint('ご依頼に\n沿って整理しました。'))
    def test_footnote_continuation_detected(self):
        self.assertTrue(L.local_lint('[^a]: 注記\n    ご依頼に沿って整理しました。'))
    def test_nested_inline_quotes_are_protected(self):
        self.assertFalse(L.local_lint('「中に『ご依頼に沿って』を含む」という用例。'))
    def test_comment_continuation_detected(self):
        self.assertTrue(L.local_lint('<!--\nここに図を入れる\n-->'))
    def test_four_backtick_fence_protected(self):
        self.assertFalse(L.local_lint('````\n```\nご依頼に沿って\n````'))
    def test_outline_respects_blank_paragraphs(self):
        rows=L.outline('# 見出し\n\n方式Aは速い。理由を示す。\n\n方式Bは遅い。')
        self.assertEqual([x['first_sentence'] for x in rows if x['kind']=='paragraph'],['方式Aは速い。','方式Bは遅い。'])
    def test_outline_ignores_code(self):
        self.assertFalse([x for x in L.outline('```\ncode\n```') if x['kind']=='paragraph'])
    def test_outline_decimal(self):
        rows=L.outline('正解率は0.82だった。比較を続ける。')
        self.assertEqual(rows[0]['first_sentence'],'正解率は0.82だった。')
    def test_negative_to_positive_is_flagged(self):
        self.assertTrue(L.compare_anchors('効果は確認できない。','効果を確認した。'))
    def test_no_significance_to_no_effect_flagged(self):
        self.assertTrue(L.compare_anchors('有意差はなかった。','効果はない。'))
    def test_protected_number_changed(self):
        self.assertTrue(L.compare_anchors('正解率は82%。','正解率は86%。'))
    def test_url_changed(self):
        self.assertTrue(L.compare_anchors('[出典](https://example.org/a)','[出典](https://example.org/b)'))
    def test_term_removed(self):
        self.assertTrue(L.compare_anchors('Poincareモデルを比較した。','モデルを比較した。',['Poincare']))
    def test_citation_removed(self):
        self.assertTrue(L.compare_anchors('結果を報告した[1]。','結果を報告した。'))
    def test_code_changed(self):
        self.assertTrue(L.compare_anchors('```python\nx=1\n```','```python\nx=2\n```'))
    def test_math_changed(self):
        self.assertTrue(L.compare_anchors('$x=y$','$x=z$'))
    def test_same_anchors_do_not_prove_semantics(self):
        # A counter cannot know that ownership has swapped. This limitation is explicit.
        self.assertEqual(L.compare_anchors('Aは82%、Bは86%。','Aは86%、Bは82%。'),[])
    def test_identical_text_unchanged(self):
        s='本研究では方式Aを評価した。正解率は82%だった。'
        self.assertEqual(L.compare_anchors(s,s),[])
    def test_empty_after_is_flagged(self):
        self.assertTrue(L.compare_anchors('結果を報告した。',''))
    def test_template_todo_is_kept(self):
        self.assertFalse(L.local_lint('TODO: 担当者名を記入。','template'))
    def test_safe_reader_request_in_email(self):
        self.assertFalse(L.local_lint('ご依頼の資料をご確認ください。','email'))
    def test_technical_prompt_is_kept(self):
        self.assertFalse(L.local_lint('プロンプトの長さを測定した。','research'))
    def test_input_rejects_nul(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'a.md';p.write_bytes(b'abc\0')
            with self.assertRaises(ValueError):L.read_text(str(p))
    def test_input_bom_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'a.md';p.write_bytes(b'\xef\xbb\xbfabc')
            self.assertEqual(L.read_text(str(p))[1],'abc')


class DevelopmentCorpusTests(unittest.TestCase):
    pass

for _case in [json.loads(x) for x in A['evals/boundary-cases.jsonl'].decode().splitlines() if x]:
    if _case['split'] != 'development':continue
    def _test(self, case=_case):
        self.assertEqual(bool(L.local_lint(case['text'],case['genre'])),case['expected'],case['id'])
    setattr(DevelopmentCorpusTests,'test_'+_case['id'],_test)

if __name__=='__main__':unittest.main()

class GenerationPreparationTests(Isolated):
    def module(self):
        mod=types.ModuleType('generation_preparation')
        mod.__file__=str(self.home/'evals/prepare_generation_eval.py')
        exec(compile(A['evals/prepare_generation_eval.py'].decode(),mod.__file__,'exec'),mod.__dict__)
        return mod
    def setup_sources(self):
        up=self.home/'upstream';up.mkdir();(up/'SKILL.upstream.md').write_text('Upstream rules')
        old=self.home/'old';new=self.home/'new'
        for folder,names in [(old,['SKILL.md','paragraph-writing/SKILL.md','japanese-direct-writing/SKILL.md']),
                             (new,['SKILL.md','references/paragraphs.md','references/audience.md','references/directness.md','references/review.md'])]:
            for rel in names:
                p=folder/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('Rules '+rel)
        tasks=[{'id':'W01','instruction':'Rewrite','input':'Input','must_keep':['DO_NOT_LEAK_ANSWER']}]
        return up,old,new,tasks
    def test_balanced_preparation(self):
        up,old,new,tasks=self.setup_sources()
        r=self.module().prepare(tasks,up,old,new,self.home/'out',repeats=3)
        self.assertEqual(len(r['jobs']),9)
        self.assertEqual(set(j['arm'] for j in r['jobs']),{'upstream_only','existing_three_skills','proposal'})
        self.assertTrue(all(j['status']=='NOT_RUN' for j in r['jobs']))
    def test_answers_not_in_generation_prompt(self):
        up,old,new,tasks=self.setup_sources();out=self.home/'out'
        self.module().prepare(tasks,up,old,new,out)
        for p in (out/'prompts').glob('*'):
            self.assertNotIn('DO_NOT_LEAK_ANSWER',p.read_text())
    def test_prepare_existing_destination_refused(self):
        up,old,new,tasks=self.setup_sources();out=self.home/'out';out.mkdir()
        with self.assertRaises(ValueError):self.module().prepare(tasks,up,old,new,out)
    def test_preparation_deterministic(self):
        up,old,new,tasks=self.setup_sources();m=self.module()
        a=m.prepare(tasks,up,old,new,self.home/'out1');b=m.prepare(tasks,up,old,new,self.home/'out2')
        self.assertEqual(a,b)
    def test_task_id_path_rejected(self):
        up,old,new,tasks=self.setup_sources();tasks[0]['id']='../bad'
        with self.assertRaises(ValueError):self.module().prepare(tasks,up,old,new,self.home/'out')
