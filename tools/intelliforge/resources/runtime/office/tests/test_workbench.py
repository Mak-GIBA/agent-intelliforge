import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import common
import install
import office


def make_docx(path, text='日本語の見出し', image=b'fake-png-bytes', extra=None):
    parts={
        '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        'word/document.xml':f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>',
        'word/media/image1.png':image,
    }
    parts.update(extra or {})
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for k,v in parts.items():z.writestr(k,v)
    return path


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/"日本語 home ' $()";self.home.mkdir()
        env={'HOME':str(self.home),'XDG_DATA_HOME':str(self.home/'share'),
             'XDG_CONFIG_HOME':str(self.home/'config'),'CODEX_HOME':str(self.home/'custom codex'),
             'PYTHONDONTWRITEBYTECODE':'1'}
        self.environ=mock.patch.dict(os.environ,env);self.environ.start();self.addCleanup(self.environ.stop)
        self.p=common.paths()
    def args(self, **kwargs):
        values={'force':False,'assets_only':True,'with_docling':False,'officecli':None}
        values.update(kwargs)
        return type('Args',(),values)()
    def do_install(self, **kw):
        with context_silent():return install.apply_install(self.args(**kw),self.p,None)
    def tree(self):
        return {str(p.relative_to(self.home)):p.read_bytes() for p in self.home.rglob('*') if p.is_file()}

class context_silent:
    def __enter__(self):
        self.p=mock.patch('sys.stdout',new_callable=io.StringIO);return self.p.start()
    def __exit__(self,*args):return self.p.__exit__(*args)


class CommonTests(Isolated):
    def test_absolute_path_with_japanese_and_spaces(self):
        self.assertEqual(common.absolute(str(self.home)),self.home)
    def test_relative_xdg_rejected(self):
        with mock.patch.dict(os.environ,{'XDG_DATA_HOME':'relative'}):
            with self.assertRaises(common.OfficeError):common.paths()
    def test_atomic_write_replaces_whole_file(self):
        f=self.home/'a';common.atomic_write(f,b'one');common.atomic_write(f,b'two');self.assertEqual(f.read_bytes(),b'two')
    def test_new_file_never_overwrites(self):
        f=self.home/'a';common.new_file(f,b'one')
        with self.assertRaises(common.OfficeError):common.new_file(f,b'two')
        self.assertEqual(f.read_bytes(),b'one')
    def test_no_symlink_managed_path(self):
        _portable_link(self.home/'s', self.home)
        with self.assertRaises(common.OfficeError):common.atomic_write(self.home/'s/x',b'x')
    def test_exclusive_lock_and_cleanup(self):
        path=self.home/'lock'
        with common.lock(path):
            with self.assertRaises(common.OfficeError):
                with common.lock(path):pass
        self.assertFalse(path.exists())
    def test_timeout_kills_child(self):
        with self.assertRaisesRegex(common.OfficeError,'timed out'):
            common.run([sys.executable,'-c','import time;time.sleep(10)'],timeout=1)
    def test_shell_metacharacters_are_literal(self):
        r=common.run([sys.executable,'-c','import sys;print(sys.argv[1])','$(touch bad); a'])
        self.assertEqual(r.stdout.strip(),'$(touch bad); a')
    def test_non_object_json_rejected(self):
        p=self.home/'x.json';p.write_text('[]', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):common.load_json(p)


class InstallerTests(Isolated):
    def test_assets_install_and_second_run_no_changes(self):
        self.do_install();before=self.tree();self.do_install();self.assertEqual(before,self.tree())
    def test_unmanaged_skill_conflict(self):
        self.p['skill'].mkdir(parents=True);(self.p['skill']/'SKILL.md').write_text('mine', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):self.do_install()
    def test_unmanaged_launcher_conflict(self):
        self.p['launcher'].parent.mkdir(parents=True);self.p['launcher'].write_text('mine', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):self.do_install()
    def test_edited_skill_preserved_even_force(self):
        self.do_install();target=self.p['skill']/'SKILL.md';target.write_text('my changes', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):self.do_install(force=True)
        self.assertEqual(target.read_text(encoding="utf-8"),'my changes')
    def test_new_extra_skill_file_preserved_on_force(self):
        self.do_install();p=self.p['skill']/'my-custom.txt';p.write_text('keep', encoding="utf-8", newline="\n")
        self.do_install(force=True);self.assertEqual(p.read_text(encoding="utf-8"),'keep')
    def test_force_retains_previous_release(self):
        a=self.do_install();b=self.do_install(force=True)
        self.assertNotEqual(a['release'],b['release']);self.assertTrue(Path(a['release']).exists())
    def test_unrelated_settings_not_modified(self):
        files=[self.p['codex']/'hooks.json',self.p['codex']/'config.toml',self.home/'AGENTS.md',self.home/'knowledge/note.md']
        for p in files:p.parent.mkdir(parents=True,exist_ok=True);p.write_text('keep-original', encoding="utf-8", newline="\n")
        self.do_install();self.do_install(force=True)
        self.assertTrue(all(p.read_text(encoding="utf-8")=='keep-original' for p in files))
    def test_invalid_manifest_rejected(self):
        self.p['config'].parent.mkdir(parents=True);self.p['config'].write_text('{', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):self.do_install()
    def test_manifest_wrong_owner_rejected(self):
        self.p['config'].parent.mkdir(parents=True);self.p['config'].write_text('{"owner":"other"}', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):self.do_install()
    def test_changed_runtime_rejected(self):
        a=self.do_install();(Path(a['release'])/'office.py').write_text('changed', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):self.do_install(force=True)
    def test_dependency_failure_keeps_old_install(self):
        a=self.do_install();before=self.p['config'].read_bytes();launch=self.p['launcher'].read_bytes()
        with mock.patch.object(install,'install_dependencies',side_effect=common.OfficeError('network unavailable')):
            with self.assertRaises(common.OfficeError):self.do_install(force=True,assets_only=False)
        self.assertEqual(before,self.p['config'].read_bytes());self.assertEqual(launch,self.p['launcher'].read_bytes())
    def test_publish_failure_rolls_back(self):
        self.do_install();before={p:p.read_bytes() for p in [self.p['launcher'],self.p['config'],self.p['skill']/'SKILL.md']}
        real=install.atomic_write;failed=[False]
        def boom(path,data,mode=0o600):
            if path==self.p['config'] and not failed[0]:failed[0]=True;raise OSError('simulated write failure')
            return real(path,data,mode)
        with mock.patch.object(install,'atomic_write',side_effect=boom):
            with self.assertRaises(OSError):self.do_install(force=True)
        for p,b in before.items():self.assertEqual(p.read_bytes(),b)
    def test_existing_external_binary_not_deleted(self):
        self.do_install();external=self.home/'officecli';external.write_text('external', encoding="utf-8", newline="\n")
        with context_silent():install.uninstall(self.p,True)
        self.assertEqual(external.read_text(encoding="utf-8"),'external')
    def test_uninstall_preserves_custom_skill_file(self):
        self.do_install();p=self.p['skill']/'custom.txt';p.write_text('retain', encoding="utf-8", newline="\n")
        with context_silent():install.uninstall(self.p,True)
        self.assertEqual(p.read_text(encoding="utf-8"),'retain');self.assertFalse(self.p['launcher'].exists())
    def test_uninstall_dry_run_has_no_writes(self):
        self.do_install();before=self.tree()
        with context_silent():install.uninstall(self.p,False)
        self.assertEqual(before,self.tree())
    def test_cli_dry_run_no_persistent_writes(self):
        before=self.tree()
        r=common.run([sys.executable,str(ROOT/'install.py'),'--dry-run'])
        self.assertEqual(r.returncode,0);self.assertEqual(before,self.tree())
    def test_installed_launcher_works_with_spaces(self):
        self.do_install();r=common.run([str(self.p['launcher']),'--help'])
        self.assertIn('pdf-select',r.stdout)
    def test_assets_doctor_reports_not_ready(self):
        self.do_install()
        with context_silent() as out:office.doctor()
        self.assertEqual(json.loads(out.getvalue())['capabilities']['document_tools'],'NOT_READY')
    def test_checksum_failure_discards_download(self):
        dest=self.home/'dl';response=mock.MagicMock();response.url='https://github.com/a'
        response.__enter__.return_value=response;response.read.side_effect=[b'wrong',b'']
        opener=mock.Mock();opener.open.return_value=response
        with mock.patch('urllib.request.build_opener',return_value=opener):
            with self.assertRaisesRegex(common.OfficeError,'Checksum'):install.fetch_checked('https://github.com/a',dest,'0'*64)
        self.assertFalse(dest.exists())
    def test_git_blob_reference_verification(self):
        data=b'reference';digest=hashlib.sha1(b'blob 9\0'+data).hexdigest();dest=self.home/'ref'
        response=mock.MagicMock();response.url='https://raw.githubusercontent.com/a';response.__enter__.return_value=response;response.read.side_effect=[data,b'']
        opener=mock.Mock();opener.open.return_value=response
        with mock.patch('urllib.request.build_opener',return_value=opener):install.fetch_checked(response.url,dest,digest,'git-blob')
        self.assertEqual(dest.read_bytes(),data)
    def test_redirect_downgrade_rejected(self):
        with self.assertRaises(common.OfficeError):install.HTTPSOnly().redirect_request(None,None,302,'',{},'http://github.com/unsafe')
    def test_redirect_unknown_host_rejected(self):
        with self.assertRaises(common.OfficeError):install.HTTPSOnly().redirect_request(None,None,302,'',{},'https://example.com/unsafe')
    def test_system_package_command_not_run_in_preview(self):
        with mock.patch.object(install,'platform') as platform, mock.patch.object(install.shutil,'which',return_value='/usr/bin/apt-get'), mock.patch('subprocess.run') as spawn,context_silent():
            platform.system.return_value='Linux';install.system_packages(False);spawn.assert_not_called()


class DocumentTests(Isolated):
    def test_inspect_docx_and_media(self):
        p=make_docx(self.home/'source.docx');r=office.facts(p)
        self.assertEqual(r['paragraphs'],1);self.assertEqual(len(r['media']),1);self.assertIsNone(r['pages'])
    def test_prepare_preserves_original(self):
        p=make_docx(self.home/'source.docx');before=p.read_bytes();out=self.home/'edited.docx'
        r=office.prepare(p,out);self.assertEqual(before,out.read_bytes());self.assertEqual(before,p.read_bytes());self.assertTrue(r['original_unchanged'])
    def test_prepare_same_path_rejected(self):
        p=make_docx(self.home/'source.docx')
        with self.assertRaises(common.OfficeError):office.prepare(p,p)
    def test_prepare_existing_output_rejected(self):
        p=make_docx(self.home/'source.docx');o=self.home/'o.docx';o.write_bytes(b'keep')
        with self.assertRaises(common.OfficeError):office.prepare(p,o)
        self.assertEqual(o.read_bytes(),b'keep')
    def test_legacy_format_rejected(self):
        p=self.home/'a.doc';p.write_text('x', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):office.source_file(p)
    def test_spreadsheet_not_routed_here(self):
        p=self.home/'a.xlsx';p.write_text('x', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):office.source_file(p)
    def test_duplicate_zip_members_rejected(self):
        import warnings
        p=make_docx(self.home/'s.docx')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(p,'a') as z:z.writestr('word/document.xml','<x/>')
        with self.assertRaises(common.OfficeError):office.facts(p)
    def test_zip_path_traversal_rejected(self):
        p=make_docx(self.home/'s.docx',extra={'../bad.xml':'<x/>'})
        with self.assertRaises(common.OfficeError):office.facts(p)
    def test_xml_entity_rejected(self):
        p=make_docx(self.home/'s.docx',extra={'bad.xml':'<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><x>&y;</x>'})
        with self.assertRaises(common.OfficeError):office.facts(p)
    def test_macros_rejected(self):
        p=make_docx(self.home/'s.docx',extra={'word/vbaProject.bin':b'foo'})
        with self.assertRaises(common.OfficeError):office.facts(p)
    def test_external_image_link_rejected_for_render(self):
        p=make_docx(self.home/'s.docx',extra={'word/_rels/document.xml.rels':'<Relationships><Relationship TargetMode="External" Target="https://example.invalid/x" Type="a/image"/></Relationships>'})
        with self.assertRaises(common.OfficeError):office.assert_render_safe(office.facts(p))
    def test_hyperlink_is_not_followed(self):
        p=make_docx(self.home/'s.docx',extra={'word/_rels/document.xml.rels':'<Relationships><Relationship TargetMode="External" Target="https://example.invalid/x" Type="a/hyperlink"/></Relationships>'})
        office.assert_render_safe(office.facts(p))
    def test_media_change_detected(self):
        a=make_docx(self.home/'a.docx');b=make_docx(self.home/'b.docx',image=b'changed')
        self.assertIn('MEDIA_CHANGED',office.compare(a,b,True)['issues'])
    def test_text_change_with_media_preserved(self):
        a=make_docx(self.home/'a.docx');b=make_docx(self.home/'b.docx',text='edited')
        self.assertEqual(office.compare(a,b,True,['word/document.xml'])['issues'],[])
    def test_scope_check_flags_unexpected_part(self):
        a=make_docx(self.home/'a.docx');b=make_docx(self.home/'b.docx',text='edited')
        self.assertIn('UNEXPECTED_PART_CHANGE',office.compare(a,b,False,['word/styles.xml'])['issues'])
    def test_pages_are_one_based(self):self.assertEqual(office.page_indices('1,3-4',4),[0,2,3])
    def test_out_of_range_rejected(self):
        for value in ['0','1-9','4-2','1,1','1,','1;rm']:
            with self.subTest(value=value),self.assertRaises(common.OfficeError):office.page_indices(value,4)
    def test_large_all_render_requires_range(self):
        with self.assertRaises(common.OfficeError):office.page_indices(None,500,100)
    def test_office_adapter_blocks_setup(self):
        for cmd in ([],['install'],['update'],['skills','install'],['config'],['watch','x.docx']):
            with self.subTest(cmd=cmd),self.assertRaises(common.OfficeError):office.office_command({},cmd)
    def test_binary_replacement_detected(self):
        b=self.home/'b';b.write_bytes(b'changed')
        d={'officecli':{'path':str(b),'sha256':common.sha(b'original')}}
        with self.assertRaises(common.OfficeError):office.office_binary(d)
    def test_stale_renders_detected(self):
        p=make_docx(self.home/'s.docx');directory=self.home/'out';directory.mkdir()
        (directory/'render.json').write_bytes(common.json_bytes({'source':str(p),'source_sha256':'wrong','images':[]}))
        with self.assertRaisesRegex(common.OfficeError,'stale'):office.visual_status(directory)
    def test_render_checks_do_not_claim_visual_quality(self):
        p=make_docx(self.home/'s.docx');directory=self.home/'out';directory.mkdir();img=directory/'page.png';img.write_bytes(b'png')
        (directory/'render.json').write_bytes(common.json_bytes({'source':str(p),'source_sha256':common.file_sha(p),'images':[{'file':'page.png','sha256':common.file_sha(img)}],'complete':True}))
        self.assertEqual(office.visual_status(directory)['visual_review'],'NOT_VERIFIED_BY_CODE')


class MCPTests(Isolated):
    def setUp(self):
        super().setUp();self.do_install();self.toml=self.p['codex']/'config.toml';self.toml.parent.mkdir(parents=True)
    def test_mcp_preview_no_write(self):
        before=self.tree()
        with mock.patch.object(office,'office_binary',return_value=self.home/'x'):
            r=office.codex_mcp(True,False)
        self.assertFalse(r['apply']);self.assertEqual(before,self.tree())
    def test_mcp_name_conflict_refused(self):
        self.toml.write_text('[mcp_servers.codex-office-workbench]\ncommand="other"\n', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):office.codex_mcp(True,True)
    def test_mcp_invalid_toml_preserved(self):
        self.toml.write_text('[', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):office.codex_mcp(True,True)
        self.assertEqual(self.toml.read_text(encoding="utf-8"),'[')
    def test_mcp_registration_via_official_cli_and_readback(self):
        self.toml.write_text('model="keep"\n[mcp_servers.other]\ncommand="existing"\n', encoding="utf-8", newline="\n")
        def simulated(argv,**kwargs):
            self.assertEqual(argv[:4],['codex','mcp','add',office.MCP_NAME])
            self.toml.write_text(self.toml.read_text(encoding="utf-8")+'\n[mcp_servers.codex-office-workbench]\ncommand='+json.dumps(str(self.p['launcher']))+'\nargs=["mcp"]\n', encoding="utf-8", newline="\n")
            return subprocess.CompletedProcess(argv,0,'','')
        with mock.patch.object(office,'office_binary',return_value=self.home/'x'),mock.patch.object(office.shutil,'which',return_value='/bin/codex'),mock.patch.object(office,'run',side_effect=simulated):
            r=office.codex_mcp(True,True)
        self.assertEqual(r['status'],'ENABLED');self.assertIn('model="keep"',self.toml.read_text(encoding="utf-8"))
    def test_mcp_disable_only_matching_configuration(self):
        self.toml.write_text('[mcp_servers.codex-office-workbench]\ncommand="/another/cli"\nargs=["mcp"]\n', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):office.codex_mcp(False,True)
    def test_uninstall_refuses_active_mcp(self):
        self.toml.write_text('[mcp_servers.codex-office-workbench]\ncommand="x"\n', encoding="utf-8", newline="\n")
        with self.assertRaises(common.OfficeError):install.uninstall(self.p,True)


class SkillContractTests(unittest.TestCase):
    def test_single_skill_name_and_explicit_invocation(self):
        text=(ROOT/'skills/office-workbench/SKILL.md').read_text(encoding="utf-8")
        self.assertIn('name: office-workbench',text);self.assertIn('$office-workbench',text)
    def test_preservation_and_visual_review_are_separate(self):
        text=(ROOT/'skills/office-workbench/SKILL.md').read_text(encoding="utf-8")
        for term in ('NOT_VERIFIED','EVERY page','original','PDF','Markdown','Macros'.lower()):
            self.assertIn(term.lower(),text.lower())
    def test_no_font_or_binary_files_bundled(self):
        bad={'.ttf','.otf','.ttc','.woff','.exe','.dll'}
        self.assertFalse(any(p.suffix.lower() in bad for p in ROOT.rglob('*')))


from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':unittest.main()
