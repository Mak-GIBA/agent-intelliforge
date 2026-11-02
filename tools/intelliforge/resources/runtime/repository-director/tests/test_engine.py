"""Isolated contracts, also shipped in the standalone installer."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def module(name, path):
    spec=importlib.util.spec_from_file_location(name,path); obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


repository=module('rd_project',ROOT/'skill/scripts/repository.py')
installer=module('rd_install',ROOT/'install.py')
forge=module('rd_forge',ROOT/'skill/scripts/forge_inspect.py')


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'日本語 project';self.root.mkdir()
        (self.root/'app.py').write_text('def search(): return []\n', encoding="utf-8", newline="\n")
        (self.root/'pyproject.toml').write_text('[project]\nname="app"\n', encoding="utf-8", newline="\n")
        (self.root/'lock.txt').write_text('immutable\n', encoding="utf-8", newline="\n")
        (self.root/'.env').write_text('SECRET=do-not-copy\n', encoding="utf-8", newline="\n")

    def files(self):return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_inspect_and_preview_are_read_only_and_never_read_secrets(self):
        before=self.files()
        facts=repository.inspect(self.root)
        self.assertEqual(facts['mode'],'existing');self.assertEqual(facts['sources'],['app.py'])
        plan=repository.initialize(self.root,'auto','dialogue',False,'codex')
        self.assertFalse(plan['applied']);self.assertEqual(before,self.files())
        self.assertNotIn('do-not-copy',json.dumps(plan))

    def test_default_bootstrap_has_three_documents_and_readme_navigation(self):
        repository.initialize(self.root,'existing','delegate',True,'codex')
        self.assertEqual({p.name for p in (self.root/'docs').iterdir()},
                         {'purpose.md','architecture.md','development.md'})
        self.assertEqual(repository.inspect(self.root)['index'],'README.md')
        self.assertEqual(repository.check(self.root)['errors'],[])
        self.assertTrue(repository.check(self.root)['warnings'])
        before=self.files()
        self.assertEqual(repository.initialize(self.root,'auto','delegate',True,'codex')['changes'],[])
        self.assertEqual(self.files(),before)

    def test_compact_drafts_keep_status_out_of_visible_document_text(self):
        repository.initialize(self.root,'auto','dialogue',True,'codex')
        for path in (self.root/'docs').glob('*.md'):
            text=path.read_text(encoding="utf-8")
            self.assertIn('<!-- repository-director:draft -->',text)
            self.assertNotIn('文書状態：',text)
            self.assertNotIn('調査範囲',text)
            self.assertNotIn('未調査',text)
        architecture=(self.root/'docs/architecture.md').read_text(encoding="utf-8")
        self.assertIn('ファイル構成',architecture)
        self.assertIn('エントリーポイント',architecture)

    def test_existing_six_document_layout_is_preserved_without_extra_files(self):
        docs=self.root/'docs';docs.mkdir()
        for filename in ('purpose.md','repository-policy.md','requirements.md','architecture.md','core-logic.md','verification.md'):
            (docs/filename).write_text('# Human document\n\nKeep this content.\n', encoding="utf-8", newline="\n")
        (docs/'INDEX.md').write_text('# Existing index\n', encoding="utf-8", newline="\n")
        before={p:p.read_bytes() for p in docs.iterdir()}
        repository.initialize(self.root,'existing','dialogue',True,'codex')
        self.assertEqual(set(docs.iterdir()),set(before))
        for p,content in before.items():
            if p.name!='INDEX.md':self.assertEqual(p.read_bytes(),content)
        self.assertEqual(repository.check(self.root)['errors'],[])

    def test_grouped_custom_documents_are_reused_without_default_duplicates(self):
        (self.root/'specs').mkdir()
        for name in ('why.md','structure.md','contributing.md'):(self.root/'specs'/name).write_text('# Human document\n', encoding="utf-8", newline="\n")
        mapping=['purpose=specs/why.md','architecture=specs/structure.md','policy=specs/contributing.md']
        repository.initialize(self.root,'existing','dialogue',True,'codex',mapping)
        self.assertFalse((self.root/'docs').exists())
        before=self.files()
        self.assertEqual(repository.initialize(self.root,'auto','dialogue',True,'codex')['changes'],[])
        self.assertEqual(before,self.files())

    def test_explicit_mapping_takes_precedence_before_grouping_missing_roles(self):
        (self.root/'docs').mkdir();(self.root/'docs/purpose.md').write_text('# Previous purpose\n', encoding="utf-8", newline="\n")
        (self.root/'specs').mkdir();(self.root/'specs/business.md').write_text('# Business purpose\n', encoding="utf-8", newline="\n")
        result=repository.initialize(self.root,'existing','dialogue',True,'codex',['purpose=specs/business.md'])
        self.assertEqual(result['facts']['roles']['purpose'],['specs/business.md'])
        self.assertEqual(result['facts']['roles']['requirements'],['specs/business.md'])
        self.assertFalse((self.root/'docs/requirements.md').exists())

    def test_one_existing_document_can_hold_multiple_groups_across_reruns(self):
        (self.root/'specs').mkdir();(self.root/'specs/handbook.md').write_text('# Human handbook\n', encoding="utf-8", newline="\n")
        mappings=[r+'=specs/handbook.md' for r in ('purpose','architecture','policy')]
        repository.initialize(self.root,'existing','dialogue',True,'codex',mappings)
        self.assertFalse((self.root/'docs').exists())
        before=self.files()
        repository.initialize(self.root,'existing','dialogue',True,'codex')
        self.assertEqual(before,self.files())

    def test_documenting_the_draft_marker_does_not_mark_a_finished_doc_as_draft(self):
        (self.root/'README.md').write_text('# Guide\n\nRemove the marker `<!-- repository-director:draft -->` when finished.\n\n```html\n<!-- repository-director:draft -->\n```\n', encoding="utf-8", newline="\n")
        self.assertEqual(repository.check(self.root)['warnings'],[])

    def test_existing_bootstrap_preserves_sources_reuses_docs_and_is_idempotent(self):
        docs=self.root/'docs';docs.mkdir()
        (docs/'機能仕様.md').write_text('# 機能仕様\n\nHuman requirements.\n', encoding="utf-8", newline="\n")
        for name in ('README.md','AGENTS.md','CLAUDE.md'):(self.root/name).write_text('Human rule: preserve me\n', encoding="utf-8", newline="\n")
        before=self.files()
        repository.initialize(self.root,'existing','delegate',True,'claude')
        after=self.files()
        for name,content in before.items():
            if name.endswith('.md') and '/' not in name:self.assertTrue(after[name].startswith(content))
            else:self.assertEqual(after[name],content)
        self.assertNotIn('docs/requirements.md',after)
        self.assertIn('機能仕様.md',(self.root/'README.md').read_text(encoding="utf-8"))
        self.assertEqual(repository.check(self.root)['errors'],[])
        self.assertTrue(repository.check(self.root)['warnings'])
        result=repository.initialize(self.root,'auto','delegate',True,'claude')
        self.assertEqual(result['changes'],[]);self.assertEqual(self.files(),after)

    def test_custom_document_mapping_avoids_duplicate_specification(self):
        (self.root/'specs').mkdir();(self.root/'specs/contract.md').write_text('# Contract\n', encoding="utf-8", newline="\n")
        repository.initialize(self.root,'existing','dialogue',True,'codex',['requirements=specs/contract.md'])
        self.assertFalse((self.root/'docs/requirements.md').exists())
        self.assertIn('specs/contract.md',(self.root/'README.md').read_text(encoding="utf-8"))
        repository.initialize(self.root,'existing','dialogue',True,'codex')
        self.assertFalse((self.root/'docs/requirements.md').exists())

    def test_malformed_markers_stop_before_any_writes(self):
        (self.root/'AGENTS.md').write_text(repository.BEGIN, encoding="utf-8", newline="\n")
        before=self.files()
        with self.assertRaises(ValueError):repository.initialize(self.root,'existing','dialogue',True,'codex')
        self.assertEqual(self.files(),before)

    @unittest.skipIf(os.name=='nt','Symlink setup needs Windows developer mode')
    def test_linked_destination_is_not_followed(self):
        outside=Path(self.temp.name)/'outside';outside.mkdir()
        _portable_link(self.root/'docs', outside, target_is_directory=True)
        with self.assertRaises(ValueError):repository.initialize(self.root,'auto','dialogue',True,'codex')
        self.assertEqual(list(outside.iterdir()),[])

    @unittest.skipIf(os.name=='nt','Symlink setup needs Windows developer mode')
    def test_inspection_does_not_read_linked_readme(self):
        outside=Path(self.temp.name)/'private.md';outside.write_text('Private source', encoding="utf-8", newline="\n")
        _portable_link(self.root/'README.md', outside)
        with self.assertRaises(ValueError):repository.inspect(self.root)

    def test_check_detects_missing_links_and_unicode_headings(self):
        (self.root/'docs').mkdir()
        (self.root/'docs/INDEX.md').write_text('# 文書\n[good](detail.md#日本語の見出し)\n[bad](lost.md)\n[fragment](detail.md#missing)\n', encoding="utf-8", newline="\n")
        (self.root/'docs/detail.md').write_text('# 日本語の見出し\n', encoding="utf-8", newline="\n")
        result=repository.check(self.root)
        self.assertEqual(len(result['errors']),2)

    def test_custom_index_is_discovered_and_unindexed_documents_are_reported(self):
        repository.initialize(self.root,'auto','dialogue',True,'codex',index_path='docs/navigation.md')
        (self.root/'docs/orphan.md').write_text('# Orphan\n', encoding="utf-8", newline="\n")
        result=repository.check(self.root)
        self.assertEqual(result['errors'],[])
        self.assertTrue(any('orphan.md' in w for w in result['warnings']))

    def test_monorepo_initialization_and_git_changes_stay_in_selected_package(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        subprocess.run(['git','-C',str(self.root),'add','app.py'],check=True)
        (self.root/'packages/a').mkdir(parents=True);(self.root/'packages/a/code.py').write_text('x=1\n', encoding="utf-8", newline="\n")
        target=self.root/'packages/a'
        repository.initialize(target,'auto','dialogue',True,'codex')
        self.assertFalse((self.root/'AGENTS.md').exists())
        result=repository.check(target)
        self.assertIn('code.py',result['changed_files']);self.assertNotIn('app.py',result['changed_files'])

    def test_staged_unstaged_and_untracked_changes_are_all_reported(self):
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        subprocess.run(['git','-C',str(self.root),'add','app.py'],check=True)
        (self.root/'new.md').write_text('# New\n', encoding="utf-8", newline="\n")
        (self.root/'app.py').write_text('x=2\n', encoding="utf-8", newline="\n")
        result=repository.check(self.root)
        self.assertIn('app.py',result['changed_files']);self.assertIn('new.md',result['changed_files'])
        with self.assertRaises(ValueError):repository.check(self.root,'--output=/tmp/no')

    def test_local_transaction_restores_written_files_on_failure(self):
        one=self.root/'one.md';two=self.root/'two.md';one.write_text('before', encoding="utf-8", newline="\n")
        actual=repository.atomic
        def fail(path,data):
            if path==two:raise OSError('injected')
            actual(path,data)
        with patch.object(repository,'atomic',side_effect=fail):
            with self.assertRaises(OSError):repository.transaction({one:b'after',two:b'new'})
        self.assertEqual(one.read_text(encoding="utf-8"),'before');self.assertFalse(two.exists())

    @unittest.skipIf(os.name=='nt','POSIX file permissions')
    def test_document_replacement_preserves_existing_permissions(self):
        path=self.root/'README.md';path.write_text('# Existing\n', encoding="utf-8", newline="\n");path.chmod(0o640)
        repository.initialize(self.root,'auto','dialogue',True,'codex')
        self.assertEqual(path.stat().st_mode & 0o777,0o640)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        self.env={'HOME':str(self.home),'CODEX_HOME':str(self.home/'codex'),'RD_DATA_HOME':str(self.home/'data'),
                  'RD_SKILLS_DIR':str(self.home/'skills'),'RD_BIN_DIR':str(self.home/'bin'),
                  'XDG_CONFIG_HOME':str(self.home/'config'),'XDG_DATA_HOME':str(self.home/'share')}
        self.patch=patch.dict(os.environ,self.env);self.patch.start();self.addCleanup(self.patch.stop)

    def invoke(self,*args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=installer.main(list(args))
        return subprocess.CompletedProcess(args,code,out.getvalue(),err.getvalue())

    def test_preview_apply_rerun_doctor_remove_preserve_unrelated_guidance(self):
        before=list(self.home.rglob('*'));result=self.invoke()
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(before,list(self.home.rglob('*')))
        codex=self.home/'codex';codex.mkdir();(codex/'AGENTS.md').write_text('Human rule\n', encoding="utf-8", newline="\n")
        for args in [('--apply',),('--apply',),('--doctor',),('--uninstall','--apply')]:
            result=self.invoke(*args);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((codex/'AGENTS.md').read_text(encoding="utf-8"),'Human rule\n')
        self.assertFalse((self.home/'skills/repository-director/SKILL.md').exists())

    def test_edited_skill_and_guidance_are_protected(self):
        self.assertEqual(self.invoke('--apply').returncode,0)
        target=self.home/'skills/repository-director/SKILL.md';target.write_text('user version', encoding="utf-8", newline="\n")
        self.assertNotEqual(self.invoke('--update','--apply').returncode,0)
        self.assertEqual(target.read_text(encoding="utf-8"),'user version')

    def legacy_github(self,edited=False):
        folder=self.home/'skills/github-project-director';folder.mkdir(parents=True)
        data=b'legacy';(folder/'SKILL.md').write_bytes(data)
        record={'name':'github-project-director','files':{'SKILL.md':installer.digest(data)}}
        (folder/'.github-pm-install.json').write_text(json.dumps(record), encoding="utf-8", newline="\n")
        if edited:(folder/'SKILL.md').write_text('edited', encoding="utf-8", newline="\n")
        return folder

    def test_owned_legacy_skill_needs_explicit_migration_and_is_backed_up(self):
        old=self.legacy_github()
        self.assertNotEqual(self.invoke('--apply').returncode,0)
        self.assertEqual(self.invoke('--migrate-legacy').returncode,0)
        self.assertTrue((old/'SKILL.md').exists())
        result=self.invoke('--migrate-legacy','--apply');self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse((old/'SKILL.md').exists())
        self.assertTrue(list((self.home/'data/backups').glob('*.zip')))

    def test_edited_legacy_preflight_changes_nothing(self):
        old=self.legacy_github(True)
        before={str(p):p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        result=self.invoke('--migrate-legacy','--apply');self.assertNotEqual(result.returncode,0)
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.home.rglob('*') if p.is_file()})

    def test_standalone_does_not_coexist_with_a_legacy_plugin_runtime(self):
        path=self.home/'share/agent-intelliforge/codex/github-pm/settings.json'
        path.parent.mkdir(parents=True);path.write_text('{"installed": true, "method": "plugin"}', encoding="utf-8", newline="\n")
        result=self.invoke('--migrate-legacy','--apply')
        self.assertNotEqual(result.returncode,0);self.assertIn('intelliforge install',result.stderr)
        self.assertFalse((self.home/'skills').exists())

    def test_global_legacy_guidance_is_replaced_without_losing_other_rules(self):
        old=self.legacy_github();codex=self.home/'codex';codex.mkdir()
        body=('<!-- github-project-director:begin -->\n<!-- owner: '+installer.digest(str(old).encode())+' -->\nOld rules\n<!-- github-project-director:end -->\n').encode()
        path=codex/'AGENTS.md';path.write_bytes(b'Keep before\n'+body+b'Keep after\n')
        value=json.loads((old/'.github-pm-install.json').read_text(encoding="utf-8"))
        value['guidance']={'home':str(codex),'file':'AGENTS.md','sha256':installer.digest(body),'prefix':'','created':False}
        (old/'.github-pm-install.json').write_text(json.dumps(value), encoding="utf-8", newline="\n")
        result=self.invoke('--migrate-legacy','--apply');self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('github-project-director',path.read_text(encoding="utf-8"));self.assertIn('Keep before\nKeep after',path.read_text(encoding="utf-8"))

    def test_legacy_workbench_retires_managed_files_and_keeps_project_and_specify(self):
        skill=self.home/'skills/upstream-existing';skill.mkdir(parents=True)
        code=skill/'SKILL.md';code.write_text('legacy', encoding="utf-8", newline="\n")
        launcher=self.home/'bin/speckit-workbench';launcher.parent.mkdir();launcher.write_text('old', encoding="utf-8", newline="\n")
        specify=self.home/'bin/specify';specify.write_text('keep specify', encoding="utf-8", newline="\n")
        config=self.home/'config/speckit-workbench/install.json';config.parent.mkdir(parents=True)
        config.write_text(json.dumps({'managed':{str(p):installer.digest(p.read_bytes()) for p in (code,launcher)}}), encoding="utf-8", newline="\n")
        project=self.home/'app/docs/requirements.md';project.parent.mkdir(parents=True);project.write_text('Human spec', encoding="utf-8", newline="\n")
        result=self.invoke('--migrate-legacy','--apply');self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(code.exists());self.assertFalse(launcher.exists());self.assertFalse(config.exists())
        self.assertEqual(specify.read_text(encoding="utf-8"),'keep specify');self.assertEqual(project.read_text(encoding="utf-8"),'Human spec')

    def test_forged_legacy_manifest_cannot_remove_other_files(self):
        config=self.home/'config/speckit-workbench/install.json';config.parent.mkdir(parents=True)
        victim=self.home/'other.md';victim.write_text('keep', encoding="utf-8", newline="\n")
        config.write_text(json.dumps({'managed':{str(victim):installer.digest(victim.read_bytes())}}), encoding="utf-8", newline="\n")
        result=self.invoke('--migrate-legacy','--apply');self.assertNotEqual(result.returncode,0)
        self.assertEqual(victim.read_text(encoding="utf-8"),'keep');self.assertFalse((self.home/'skills/repository-director').exists())

    def test_update_requires_ownership_and_preserves_edited_guidance(self):
        self.assertEqual(self.invoke('--apply').returncode,0)
        guide=self.home/'codex/AGENTS.md';guide.write_text(guide.read_text(encoding="utf-8").replace('今回必要','CUSTOM 今回必要'), encoding="utf-8", newline="\n")
        self.assertNotEqual(self.invoke('--update','--apply').returncode,0)
        self.assertIn('CUSTOM',guide.read_text(encoding="utf-8"))

    def test_unchanged_managed_update_and_extract(self):
        self.assertEqual(self.invoke('--apply').returncode,0)
        self.assertEqual(self.invoke('--update','--apply').returncode,0)
        self.assertNotEqual(self.invoke('--doctor','--apply').returncode,0)
        target=self.home/'extract'
        self.assertNotEqual(self.invoke('--extract',str(target),'--dry-run').returncode,0)
        self.assertFalse(target.exists())
        result=self.invoke('--extract',str(target));self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((target/'skill/SKILL.md').is_file())
        self.assertNotEqual(self.invoke('--extract',str(target)).returncode,0)


class RemoteTests(unittest.TestCase):
    def test_gitlab_encodes_subgroups_and_paginates(self):
        calls=[]
        def run(args,**kwargs):
            calls.append(args);return subprocess.CompletedProcess(args,0,json.dumps([{'iid':n} for n in range(100)] if len(calls)==1 else []),'')
        result=forge.read('gitlab','gitlab.test','group/sub/project','issues',runner=run)
        self.assertTrue(result['complete']);self.assertEqual(result['pages'],2)
        self.assertIn('projects/group%2Fsub%2Fproject/issues',calls[0][-1])
        self.assertEqual(calls[0][calls[0].index('--method')+1],'GET')

    def test_failed_or_incomplete_reads_never_establish_absence(self):
        def fail(args,**kwargs):return subprocess.CompletedProcess(args,1,'','private token must not appear')
        with self.assertRaisesRegex(ValueError,'Remote read failed'):forge.read('gitlab','gitlab.test','g/r','requests',runner=fail)
        def full(args,**kwargs):return subprocess.CompletedProcess(args,0,json.dumps([{}]*100),'')
        result=forge.read('github','github.com','g/r','issues',max_pages=1,runner=full)
        self.assertFalse(result['complete'])

    def test_mr_notes_and_github_issue_filtering(self):
        responses=[{'iid':7},[{'body':'review'}]];calls=[]
        def run(args,**kwargs):calls.append(args);return subprocess.CompletedProcess(args,0,json.dumps(responses.pop(0)),'')
        result=forge.read('gitlab','gitlab.test','g/r','requests',7,runner=run)
        self.assertTrue(result['complete']);self.assertIn('/merge_requests/7/notes?',calls[-1][-1])
        def mixed(args,**kwargs):return subprocess.CompletedProcess(args,0,json.dumps([{'number':1},{'number':2,'pull_request':{}}]),'')
        self.assertEqual(len(forge.read('github','github.com','g/r','issues',runner=mixed)['items']),1)



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':unittest.main()
