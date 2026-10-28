"""Single-Skill lifecycle and portable integrity. Synthetic source fixtures only."""
import copy
import importlib.util
import json
import os
from pathlib import Path
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

if 'I' not in globals():
    spec=importlib.util.spec_from_file_location('layout_engine',Path(__file__).resolve().parents[1]/'installer.py')
    I=importlib.util.module_from_spec(spec);sys.modules[spec.name]=I;spec.loader.exec_module(I)
    A=I.assets()


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.root=self.home/'skills'
        env=patch.dict(os.environ,HOME=str(self.home),CODEX_HOME=str(self.home/'.codex'));env.start();self.addCleanup(env.stop)
        self.bundle=copy.deepcopy(A)
        lock=json.loads(self.bundle['kotonoha/UPSTREAMS.json']);lock['integration']['status']='verified'
        self.bundle['kotonoha/UPSTREAMS.json']=(json.dumps(lock)+'\n').encode()
        fake=patch.object(I,'assets',return_value=self.bundle);fake.start();self.addCleanup(fake.stop)
        runtime=patch.object(I,'prepare_writing_runtime',return_value={'versions':{'fixture':True}})
        runtime.start();self.addCleanup(runtime.stop)
    def install(self,**kw):return I.install_selected(self.root,apply=True,**kw)
    def snapshot(self):return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file() and '.kotonoha-installer-backups' not in p.parts}
    def legacy(self,name):
        path=self.root/name;path.mkdir(parents=True,exist_ok=True)
        raw=('---\nname: '+name+'\n---\nSynthetic v3 fixture.\n').encode()
        (path/'SKILL.md').write_bytes(raw)
        (path/I.MANIFEST).write_text(json.dumps({'schema':1,'owner':I.OWNERS[name],
            'component':name,'mode':'explicit','version':'3.0.0','files':{'SKILL.md':I.sha(raw)}}), encoding="utf-8", newline="\n")
    def test_fresh_install_is_self_contained_and_only_one_skill(self):
        result=self.install()
        self.assertTrue(result['applied']);self.assertEqual(result['component'],'kotonoha')
        self.assertEqual([p.parent.name for p in self.root.rglob('SKILL.md')],['kotonoha'])
        self.assertTrue((self.root/'kotonoha/scripts/check.py').is_file())
        self.assertEqual(I.doctor(self.root/'kotonoha')[1],0)
    def test_preview_has_no_runtime_network_or_writes(self):
        with patch.object(I,'prepare_writing_runtime',side_effect=AssertionError('runtime in preview')):
            r=I.install_selected(self.root,update=True)
        self.assertFalse(r['applied']);self.assertFalse(self.root.exists())
    def test_idempotent_and_mode_preserved(self):
        self.install(mode='explicit');before=self.snapshot()
        self.assertFalse(self.install()['applied']);self.assertEqual(before,self.snapshot())
        self.install(update=True)
        self.assertEqual(json.loads((self.root/'kotonoha'/I.MANIFEST).read_text(encoding="utf-8"))['mode'],'explicit')
    def test_mode_change_requires_update(self):
        self.install()
        with self.assertRaises(I.InstallError):self.install(mode='explicit')
    def test_four_owned_v3_entries_migrate_and_exact_backups_remain(self):
        import zipfile
        for name in I.LEGACY_COMPONENTS:self.legacy(name)
        before={name:I.inventory(self.root/name) for name in I.LEGACY_COMPONENTS}
        r=self.install(update=True)
        self.assertEqual(set(r['retire']),set(I.LEGACY_COMPONENTS)-{'kotonoha'})
        for name,archive in r['backups'].items():
            with zipfile.ZipFile(archive) as z:self.assertEqual(before[name],{k:z.read(k) for k in z.namelist()})
        self.assertEqual({p.parent.name for p in self.root.rglob('SKILL.md')},{'kotonoha'})
    def test_legacy_only_requires_update_and_keeps_its_explicit_mode(self):
        self.legacy('yomiyasu')
        with self.assertRaises(I.InstallError):self.install()
        result=self.install(update=True)
        self.assertEqual(result['mode'],'explicit')
    def test_edited_extra_and_foreign_legacy_block_before_any_change(self):
        for kind in ('edited','extra','foreign'):
            with self.subTest(kind=kind):
                root=self.home/kind;self.root=root;self.legacy('yomiyasu')
                if kind=='edited':(root/'yomiyasu/SKILL.md').write_text('user edit', encoding="utf-8", newline="\n")
                elif kind=='extra':(root/'yomiyasu/notes.md').write_text('user notes', encoding="utf-8", newline="\n")
                else:(root/'yomiyasu'/I.MANIFEST).unlink()
                before=self.snapshot()
                with patch.object(I,'prepare_writing_runtime',side_effect=AssertionError('before preflight')):
                    with self.assertRaises(I.InstallError):self.install(update=True)
                self.assertEqual(before,self.snapshot())
    def test_current_edits_and_missing_files_block(self):
        self.install();path=self.root/'kotonoha/SKILL.md';path.write_text('edited', encoding="utf-8", newline="\n")
        with self.assertRaises(I.InstallError):self.install(update=True,force=True)
        self.assertEqual(path.read_text(encoding="utf-8"),'edited')
        path.unlink()
        with self.assertRaises(I.InstallError):self.install(update=True)
    def test_failure_during_legacy_retirement_rolls_back_every_directory(self):
        for name in I.LEGACY_COMPONENTS:self.legacy(name)
        before=self.snapshot();original=I.os.replace
        def fail(a,b):
            if Path(a)==self.root/'paragraph-writing':raise OSError('simulated retirement failure')
            return original(a,b)
        with patch.object(I.os,'replace',side_effect=fail):
            with self.assertRaises(OSError):self.install(update=True)
        self.assertEqual(before,self.snapshot())
    def test_pending_integration_is_not_installed(self):
        lock=json.loads(self.bundle['kotonoha/UPSTREAMS.json']);lock['integration']['status']='pending'
        self.bundle['kotonoha/UPSTREAMS.json']=json.dumps(lock).encode()
        with self.assertRaises(I.InstallError):self.install()
        self.assertFalse(self.root.exists())
    def test_new_upstream_requires_review_without_mutating_installation(self):
        self.install();before=self.snapshot()
        latest={'tag':'v999.0.0','commit':'f'*40}
        with patch.object(I,'resolve_release',return_value=latest),patch.object(I,'resolve_meiseki',return_value=latest):
            r=self.install(update=True,upstream_only=True)
        self.assertEqual(r['status'],'UPSTREAM_REVIEW_REQUIRED');self.assertFalse(r['applied'])
        self.assertEqual(before,self.snapshot())
    def test_api_failure_is_explicit_and_keeps_active_versions(self):
        self.install();before=self.snapshot()
        with patch.object(I,'resolve_release',side_effect=OSError('offline')),patch.object(I,'resolve_meiseki',side_effect=OSError('offline')):
            r=I.check_updates(self.root)
        self.assertTrue(all(v['status']=='check_failed' for v in r['upstreams'].values()));self.assertEqual(before,self.snapshot())
    def test_upstream_only_needs_existing_and_disallows_mode(self):
        with self.assertRaises(I.InstallError):self.install(update=True,upstream_only=True)
        self.install()
        with self.assertRaises(I.InstallError):self.install(update=True,upstream_only=True,mode='auto')
    def test_standalone_copy_runs_checker_without_install_metadata(self):
        import shutil
        self.install();copy=self.home/'copy';shutil.copytree(self.root/'kotonoha',copy)
        (copy/I.MANIFEST).unlink()
        left=self.home/'left.md';right=self.home/'right.md';left.write_text('入力値は3件です。', encoding="utf-8", newline="\n");right.write_bytes(left.read_bytes())
        command=[sys.executable,'-B',str(copy/'scripts/check.py'),'compare',str(left),str(right)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['upstream']['status'],'EXECUTED')
        target=copy/'upstream/scripts/markdown_visibility.py';target.write_bytes(target.read_bytes()+b'\n# changed\n')
        self.assertEqual(subprocess.run(command,capture_output=True,timeout=45).returncode,2)
    def test_untracked_module_is_rejected(self):
        self.install();path=self.root/'kotonoha/upstream/scripts/untracked.py';path.write_text('pass', encoding="utf-8", newline="\n")
        self.assertEqual(I.doctor(self.root/'kotonoha')[1],2)
    def test_uninstall_and_source_export(self):
        self.install();I.uninstall_selected(self.root,apply=False);self.assertTrue((self.root/'kotonoha').exists())
        I.uninstall_selected(self.root,apply=True);self.assertFalse((self.root/'kotonoha').exists())
        target=self.home/'export';I.extract(target)
        self.assertEqual({p.parent.name for p in target.rglob('SKILL.md')},{'kotonoha'})
        spec=importlib.util.spec_from_file_location('exported_v4',target/'installer.py')
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        self.assertIn('kotonoha/SKILL.md',module.assets())
    def test_symlink_and_duplicate_are_preserved(self):
        self.root.mkdir();_portable_link(self.root/'kotonoha', self.home/'missing')
        with self.assertRaises(I.InstallError):self.install()
        (self.root/'kotonoha').unlink()
        other=self.home/'.agents/skills/kotonoha';other.mkdir(parents=True);(other/'SKILL.md').write_text('foreign', encoding="utf-8", newline="\n")
        with self.assertRaises(I.InstallError):self.install()
    def test_no_configuration_or_user_rules_changed(self):
        cfg=self.home/'.codex/config.toml';cfg.parent.mkdir();cfg.write_text('keep=true', encoding="utf-8", newline="\n")
        rules=self.home/'AGENTS.md';rules.write_text('keep', encoding="utf-8", newline="\n")
        self.install();self.assertEqual(cfg.read_text(encoding="utf-8"),'keep=true');self.assertEqual(rules.read_text(encoding="utf-8"),'keep')



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':unittest.main()
