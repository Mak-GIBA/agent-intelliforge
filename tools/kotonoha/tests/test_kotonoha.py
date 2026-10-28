"""Portable runtime and diagnostic contracts; no network or personal installation."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
import zipfile

if 'I' not in globals():
    spec=importlib.util.spec_from_file_location('kotonoha_test_installer',Path(__file__).resolve().parents[1]/'installer.py')
    I=importlib.util.module_from_spec(spec);sys.modules[spec.name]=I;spec.loader.exec_module(I)
    A=I.assets()

class KotonohaContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='kotonoha-contract-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for name,data in A.items():
            if name.startswith(('scripts/','meiseki-upstream/')):
                p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        self.runtime=self.module('writing_runtime');self.lint=self.module('writing_lint')
    def module(self,name):
        m=types.ModuleType('kotonoha_'+name);m.__file__=str(self.root/'scripts'/f'{name}.py')
        exec(compile(A[f'scripts/{name}.py'],m.__file__,'exec'),m.__dict__);return m
    def test_new_entry_and_legacy_alias_have_distinct_discovery(self):
        self.assertIn(b'name: kotonoha',I.own_bundle('kotonoha','auto')['SKILL.md'])
        self.assertIn(b'allow_implicit_invocation: true',I.agent_yaml('kotonoha','auto'))
        self.assertIn(b'allow_implicit_invocation: false',I.agent_yaml('yomiyasu','auto'))
        self.assertIn(b'allow_implicit_invocation: false',I.agent_yaml('kotonoha','explicit'))
    def test_original_meiseki_is_byte_verified_and_licensed(self):
        meta=json.loads(A['meiseki-upstream/UPSTREAM.json'])
        for name,digest in meta['files'].items():
            local='SKILL.upstream.md' if name=='SKILL.md' else name
            raw=A['meiseki-upstream/'+local]
            if isinstance(digest,str):self.assertEqual(I.sha(raw),digest)
            else:
                self.assertEqual(I.blob_sha(raw),digest['git_blob_sha1'])
                self.assertEqual(len(raw),digest['size'])
        self.assertIn(b'MIT License',A['meiseki-upstream/LICENSE'])
    def test_unreviewed_upstream_is_rejected_before_preparation(self):
        with mock.patch.object(I,'json_download',side_effect=[{'tag_name':'v9.0.0'},{'sha':'a'*40}]),mock.patch.object(I,'download',return_value=b'changed'):
            with self.assertRaises(I.InstallError):I.fetch_meiseki()
    def test_lint_unavailable_is_not_a_clean_document(self):
        path=self.root/'input.md';path.write_text('本文。',encoding='utf-8')
        self.assertEqual(self.lint.lint(path,None)['status'],'unavailable')
    def test_missing_tool_and_findings_are_distinct(self):
        with mock.patch.object(self.lint.subprocess,'run',side_effect=FileNotFoundError('node')):
            self.assertEqual(self.lint.execute(['node'],self.root)['status'],'unavailable')
        process=types.SimpleNamespace(returncode=1,stdout='[{"messages":[{"ruleId":"example"}]}]',stderr='')
        with mock.patch.object(self.lint.subprocess,'run',return_value=process):
            self.assertEqual(self.lint.execute(['node'],self.root)['status'],'checked')
    def test_markdown_stderr_and_no_findings(self):
        for process in (types.SimpleNamespace(returncode=1,stdout='',stderr='[{"lineNumber":1}]'),
                        types.SimpleNamespace(returncode=0,stdout='',stderr='')):
            with mock.patch.object(self.lint.subprocess,'run',return_value=process):
                self.assertEqual(self.lint.execute(['node'],self.root)['status'],'checked')
    def test_shifted_existing_markdown_warning_is_not_new(self):
        before=[{'lineNumber':2,'ruleNames':['MD018'],'errorDetail':None}]
        after=[{'lineNumber':3,'ruleNames':['MD018'],'errorDetail':None}]
        self.assertEqual(self.lint.markdown_new(before,after,'a\n#bad','inserted\na\n#bad'),[])
        self.assertEqual(len(self.lint.markdown_new([],after,'a','a\nb\n#bad')),1)
    def test_unmanaged_runtime_not_overwritten(self):
        root=self.root/'runtime';root.mkdir();(root/'user.txt').write_text('keep')
        with self.assertRaises(RuntimeError):self.runtime.prepare(root)
        self.assertEqual((root/'user.txt').read_text(),'keep')
        self.assertFalse(root.with_name('.runtime.lock').exists())
    def test_windows_reparse_paths_are_refused(self):
        attributes=types.SimpleNamespace(st_mode=0o040755,st_file_attributes=0x400)
        with mock.patch.object(Path,'lstat',return_value=attributes):
            with self.assertRaises(RuntimeError):self.runtime.safe(self.root/'junction')
            with self.assertRaises(I.InstallError):I.safe_path(self.root/'junction')
    def archive(self,name='bin/node'):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as archive:archive.writestr(name,b'fixture executable')
        raw=buffer.getvalue()
        return raw,{'url':'https://nodejs.org/dist/v24.0.0/fixture.zip','sha256':hashlib.sha256(raw).hexdigest()}
    def test_runtime_archive_digest_is_checked_before_extraction(self):
        raw,spec=self.archive();spec['sha256']='0'*64
        with mock.patch.object(self.runtime.urllib.request,'urlopen',return_value=io.BytesIO(raw)):
            with self.assertRaises(RuntimeError):self.runtime.fetch(spec,self.root/'runtime')
        self.assertFalse((self.root/'runtime').exists())
    def test_archive_traversal_refused(self):
        raw,spec=self.archive('../escape')
        with mock.patch.object(self.runtime.urllib.request,'urlopen',return_value=io.BytesIO(raw)):
            with self.assertRaises(RuntimeError):self.runtime.fetch(spec,self.root/'runtime')
        self.assertFalse((self.root/'escape').exists())
    def test_runtime_manual_edit_is_detected(self):
        raw,spec=self.archive();target=self.root/'runtime'
        with mock.patch.object(self.runtime.urllib.request,'urlopen',return_value=io.BytesIO(raw)):self.runtime.fetch(spec,target)
        self.runtime.verify(target);(target/'bin/node').write_bytes(b'modified')
        with self.assertRaises(RuntimeError):self.runtime.verify(target)
    def test_unsafe_source_and_existing_directory_refused(self):
        _,spec=self.archive();spec['url']='https://example.com/fixture.zip'
        with self.assertRaises(RuntimeError):self.runtime.fetch(spec,self.root/'runtime')
        target=self.root/'existing';target.mkdir()
        with self.assertRaises(RuntimeError):self.runtime.fetch(spec,target)

if __name__=='__main__':unittest.main()
