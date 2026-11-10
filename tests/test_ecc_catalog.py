"""Native catalog recovery, provenance and scoped reads, without user state."""
import json
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import test_ecc_on_demand as fixtures

ecc = fixtures.ecc


class CatalogRecoveryTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.ManagerTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        for name in ('root', 'home', 'plugin', 'manager', 'codex', 'config', 'originals'):
            setattr(self, name, getattr(fixture, name))
        self.manager.apply()
        self.codex.calls.clear()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.plugin), *args], text=True,
                                       env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}).strip()

    def commit(self):
        self.git('add', 'skills', '.codex-plugin/plugin.json')
        if (self.plugin / 'commands').exists():
            self.git('add', 'commands')
        self.git('commit', '-qm', 'Fixture source revision')
        (self.plugin / '.codex-marketplace-install.json').write_text(json.dumps({
            'source_type': 'git', 'source': 'https://github.com/affaan-m/ECC.git',
            'revision': self.git('rev-parse', 'HEAD'), 'ref_name': None, 'sparse_paths': []}))

    def change(self, name='tdd-workflow', *, commit=True):
        path = self.plugin / 'skills' / name / 'SKILL.md'
        path.write_text(path.read_text() + '\nUpdated source guidance.\n')
        if commit:
            self.commit()
        return path

    def owned_bytes(self):
        return {str(p): p.read_bytes() for p in [self.manager.state_path,
                self.manager.directory / 'catalog.json', self.config]}

    def test_healthy_lookup_is_offline(self):
        value = self.manager.resolve('tdd-workflow')
        self.assertEqual(value['name'], 'tdd-workflow')
        self.assertEqual(self.codex.calls, [])
        self.assertEqual(self.manager.search('testing')['matches'][0]['name'], 'python-testing')
        self.assertEqual(self.codex.calls, [])

    def test_same_version_official_update_refreshes_once(self):
        self.change()
        value = self.manager.resolve('tdd-workflow')
        self.assertEqual(value['name'], 'tdd-workflow')
        self.assertEqual(self.codex.calls, [True])
        self.assertEqual(self.manager.resolve('tdd-workflow')['path'], value['path'])
        self.assertEqual(self.codex.calls, [True])
        self.assertEqual(self.manager.read_snapshot()[0]['version'], '9.0.0')

    def test_unrelated_tamper_does_not_block_healthy_original(self):
        self.change('api-design', commit=False)
        value = self.manager.resolve('error-handling')
        self.assertEqual(value['name'], 'error-handling')
        self.assertTrue(value['warnings'])
        self.assertEqual(self.codex.calls, [True])
        with self.assertRaises(ecc.ManagementError):
            self.manager.resolve('api-design')

    def test_target_tamper_is_not_blessed_by_refresh(self):
        before = self.owned_bytes()
        self.change(commit=False)
        with self.assertRaises(ecc.ManagementError):
            self.manager.resolve('tdd-workflow')
        self.assertEqual(before, self.owned_bytes())
        self.assertEqual(self.codex.calls, [True])

    def test_read_only_lookup_never_refreshes_or_writes(self):
        self.change()
        before = self.owned_bytes()
        self.assertEqual(self.manager.resolve('error-handling', refresh=False)['name'], 'error-handling')
        with self.assertRaises(ecc.ManagementError):
            self.manager.resolve('tdd-workflow', refresh=False)
        self.assertEqual(self.codex.calls, [])
        self.assertEqual(before, self.owned_bytes())

    def test_refresh_failure_keeps_healthy_results_and_old_owned_state(self):
        self.change()
        before = self.owned_bytes()
        with mock.patch.object(self.codex, 'skills', side_effect=ecc.ManagementError('native unavailable')) as call:
            value = self.manager.resolve('error-handling')
        self.assertEqual(call.call_count, 1)
        self.assertEqual(value['name'], 'error-handling')
        self.assertTrue(value['warnings'])
        self.assertEqual(before, self.owned_bytes())

    def test_new_registered_version_wins_while_old_cache_remains(self):
        old = self.plugin
        new = old.parent / '10.0.0'
        shutil.copytree(old, new)
        self.plugin = new
        for row in self.originals:
            row['path'] = str(new / Path(row['path']).relative_to(old))
        self.assertTrue(old.exists())
        value = self.manager.resolve('tdd-workflow')
        self.assertTrue(value['path'].startswith(str(new) + os.sep))
        self.assertTrue(old.exists())
        self.assertEqual(self.codex.calls, [True])

    def test_unregistered_new_cache_is_never_selected(self):
        rogue = self.plugin.parent / '99.0.0'
        shutil.copytree(self.plugin, rogue)
        value = self.manager.resolve('tdd-workflow')
        self.assertTrue(value['path'].startswith(str(self.plugin) + os.sep))
        self.assertEqual(self.codex.calls, [True])
        self.manager.resolve('tdd-workflow')
        self.assertEqual(self.codex.calls, [True])

    def test_unknown_name_checks_native_inventory_once(self):
        path = self.plugin / 'skills' / 'new-testing' / 'SKILL.md'
        path.parent.mkdir()
        path.write_text('---\nname: new-testing\ndescription: testing\n---\nNew guidance.\n')
        self.originals.append({'name': 'ecc:new-testing', 'path': str(path), 'description': 'testing',
                               'enabled': True, 'pluginId': ecc.PLUGIN})
        self.commit()
        self.assertEqual(self.manager.resolve('new-testing')['name'], 'new-testing')
        self.assertEqual(self.codex.calls, [True])

    def test_generated_command_refresh_requires_tracked_source_and_exact_wrapper(self):
        source = self.plugin / 'commands' / 'fixture.md'
        source.parent.mkdir()
        source.write_text('---\ndescription: Fixture command\n---\n\n# Fixture\n\nOriginal command.\n')
        name = 'source-command-fixture'
        generated = self.plugin / '.codex-plugin/migrated-command-skills' / name / 'SKILL.md'
        generated.parent.mkdir(parents=True)
        def render(body):
            return ('---\nname: "source-command-fixture"\ndescription: "Fixture command"\n---\n\n'
                    '# source-command-fixture\n\nUse this skill when the user asks to run the migrated '
                    'source command `fixture`.\n\n## Command Template\n\n' + body)
        generated.write_text(render('# Fixture\n\nOriginal command.\n'))
        self.originals.append({'name': 'ecc:' + name, 'path': str(generated),
                               'description': 'Fixture command', 'enabled': True, 'pluginId': ecc.PLUGIN})
        self.commit()
        self.manager.refresh()
        source.write_text(source.read_text().replace('Original command.', 'Updated command.'))
        generated.write_text(render('# Fixture\n\nUpdated command.\n'))
        self.commit()
        self.assertEqual(self.manager.resolve(name)['name'], name)
        generated.write_text(generated.read_text() + '\nUntracked injected guidance.\n')
        with self.assertRaises(ecc.ManagementError):
            self.manager.resolve(name)

    def test_refresh_rejects_edited_native_metadata_or_foreign_origin(self):
        self.change()
        self.git('remote', 'set-url', 'origin', 'https://example.invalid/other.git')
        before = self.owned_bytes()
        with self.assertRaises(ecc.ManagementError):
            self.manager.refresh()
        self.assertEqual(before, self.owned_bytes())

    def test_managed_edit_is_hard_failure_without_native_calls(self):
        self.manager.installed_script.write_text('modified managed helper')
        with self.assertRaises(ecc.ManagementError):
            self.manager.resolve('error-handling')
        self.assertEqual(self.codex.calls, [])

    def test_dry_run_refresh_preserves_all_owned_bytes(self):
        self.change()
        before = self.owned_bytes()
        self.assertEqual(self.manager.refresh(dry_run=True)['status'], 'planned')
        self.assertEqual(before, self.owned_bytes())

    def test_failed_state_write_restores_catalog_and_state(self):
        self.change()
        before = self.owned_bytes()
        original_write = ecc.atomic_write
        failed = False
        def fail_once(path, data, mode=0o600):
            nonlocal failed
            if path == self.manager.state_path and not failed:
                failed = True
                raise OSError('fixture write failure')
            return original_write(path, data, mode)
        with mock.patch.object(ecc, 'atomic_write', side_effect=fail_once):
            with self.assertRaises(OSError):
                self.manager.refresh()
        self.assertEqual(before, self.owned_bytes())

    def test_doctor_child_commands_are_read_only(self):
        with mock.patch.object(self.codex, 'verify_entrypoints', return_value=[]) as call:
            report = self.manager.doctor()
        self.assertEqual(report['status'], 'ready', report)
        commands = call.call_args.args[0]
        self.assertTrue(all('--no-refresh' in argv for argv in commands.values()))

    def test_doctor_reports_all_bad_originals_without_writing(self):
        self.change('api-design', commit=False)
        (self.plugin / 'skills/python-patterns/SKILL.md').unlink()
        before = self.owned_bytes()
        report = self.manager.doctor()
        self.assertEqual(report['status'], 'needs_attention')
        bad = {r['target']: r['code'] for r in report['catalog_issues'] if r.get('target')}
        self.assertEqual(bad, {'api-design': 'source_modified', 'python-patterns': 'source_missing'})
        self.assertEqual(before, self.owned_bytes())

    def test_search_refills_after_bad_candidates_and_reports_all_unavailable(self):
        for index in range(6):
            name = 'api-fixture-' + str(index)
            path = self.plugin / 'skills' / name / 'SKILL.md'
            path.parent.mkdir()
            path.write_text('---\nname: '+name+'\ndescription: specialtest\n---\nGuidance.\n')
            self.originals.append({'name':'ecc:'+name, 'path':str(path), 'description':'specialtest',
                                   'enabled':True, 'pluginId':ecc.PLUGIN})
        self.commit(); self.manager.refresh()
        self.change('api-fixture-0', commit=False)
        result = self.manager.search('specialtest')
        self.assertEqual([r['name'] for r in result['matches']], ['api-fixture-'+str(i) for i in range(1,6)])
        self.assertTrue(result['warnings'])

    def test_all_matching_candidates_unavailable_is_not_no_results(self):
        row = next(r for r in self.originals if r['name'] == 'ecc:api-design')
        row['description'] = 'uniquefailure'
        self.manager.apply()
        self.change('api-design', commit=False)
        with self.assertRaises(ecc.CatalogError) as failure:
            self.manager.search('uniquefailure', refresh=False)
        self.assertEqual(failure.exception.code, 'sources_unavailable')
        self.assertEqual(self.manager.search('nonmatchingquery', refresh=False)['matches'], [])

    def test_parent_symlink_is_rejected_even_with_unchanged_bytes(self):
        directory = self.plugin / 'skills/tdd-workflow'
        moved = self.root / 'linked-original'
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(ecc.CatalogError) as failure:
            self.manager.resolve('tdd-workflow', refresh=False)
        self.assertEqual(failure.exception.code, 'source_unsafe')
        self.assertEqual(self.manager.resolve('error-handling', refresh=False)['name'], 'error-handling')

    def test_registered_root_cannot_be_escaped(self):
        outside = self.root / 'outside.md'; outside.write_text('outside')
        with self.assertRaises(ecc.CatalogError):
            ecc.source_bytes(outside, self.plugin)

    def test_local_commit_without_native_revision_change_is_rejected(self):
        self.change(commit=False)
        self.git('add', 'skills'); self.git('commit', '-qm', 'Unregistered local edit')
        before = self.owned_bytes()
        with self.assertRaises(ecc.ManagementError):
            self.manager.refresh()
        self.assertEqual(before, self.owned_bytes())

    def test_legacy_snapshot_migrates_only_after_successful_refresh(self):
        path = self.manager.directory / 'catalog.json'
        value=json.loads(path.read_text());value['version']=1
        value.pop('roots');value.pop('cache_signature')
        path.write_text(json.dumps(value))
        state=self.manager.state();state['files'][str(path)]=ecc.digest(path.read_bytes())
        self.manager.state_path.write_text(json.dumps(state))
        self.manager.resolve('tdd-workflow', refresh=False)
        self.assertEqual(json.loads(path.read_text())['version'], 1)
        self.change()
        self.manager.resolve('tdd-workflow')
        self.assertEqual(json.loads(path.read_text())['version'], 2)

    def test_catalog_tamper_is_hard_failure(self):
        path=self.manager.directory/'catalog.json'
        path.write_text(path.read_text()+'\n')
        with self.assertRaises(ecc.CatalogError) as failure:
            self.manager.resolve('tdd-workflow')
        self.assertEqual(failure.exception.code,'managed_file_modified')
        self.assertEqual(self.codex.calls,[])

    def test_reader_cannot_see_half_committed_catalog_pair(self):
        self.change()
        written=threading.Event();release=threading.Event();reader_started=threading.Event()
        original=ecc.atomic_write
        def slow(path,data,mode=0o600):
            result=original(path,data,mode)
            if path == self.manager.directory/'catalog.json':
                written.set()
                if not release.wait(5):raise AssertionError('fixture writer did not resume')
            return result
        def read():
            reader_started.set()
            return self.manager.resolve('tdd-workflow',refresh=False)
        with ThreadPoolExecutor(max_workers=2) as pool, mock.patch.object(ecc,'atomic_write',side_effect=slow):
            writer=pool.submit(self.manager.refresh)
            try:
                self.assertTrue(written.wait(5))
                reader=pool.submit(read);self.assertTrue(reader_started.wait(2))
                self.assertFalse(reader.done())
            finally:release.set()
            self.assertEqual(writer.result(timeout=5)['status'],'ready')
            self.assertEqual(reader.result(timeout=5)['name'],'tdd-workflow')

    def test_two_simultaneous_refreshes_keep_valid_owned_state(self):
        self.change()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.manager.refresh(),range(2)))
        self.assertTrue(all(r['status']=='ready' for r in results))
        self.manager.resolve('tdd-workflow',refresh=False)
        self.manager.check_files(self.manager.state())

    def test_edit_after_git_proof_cannot_be_saved_as_trusted_hash(self):
        before=self.owned_bytes()
        original=ecc.prove_original
        changed=False
        def inject(row,tree):
            nonlocal changed
            proof=original(row,tree)
            if row['name']=='tdd-workflow' and not changed:
                self.change(commit=False);changed=True
            return proof
        with mock.patch.object(ecc,'prove_original',side_effect=inject):
            with self.assertRaises(ecc.CatalogError):
                self.manager.refresh()
        self.assertEqual(before,self.owned_bytes())

    def test_official_update_survives_unrelated_source_corruption(self):
        updated=self.change('tdd-workflow')
        self.change('api-design',commit=False)
        result=self.manager.resolve('tdd-workflow')
        self.assertEqual(result['name'],'tdd-workflow')
        self.assertTrue(result['warnings'])
        saved=json.loads((self.manager.directory/'catalog.json').read_text())
        row=next(r for r in saved['skills'] if r['name']=='tdd-workflow')
        self.assertEqual(row['sha256'],ecc.digest(updated.read_bytes()))
        self.codex.calls.clear()
        self.assertEqual(self.manager.resolve('tdd-workflow')['name'],'tdd-workflow')
        self.assertEqual(self.codex.calls,[])
        with self.assertRaises(ecc.CatalogError):self.manager.resolve('api-design',refresh=False)
        # Repairing the other source allows the next refresh to clear its block.
        self.git('checkout','--','skills/api-design/SKILL.md')
        self.assertEqual(self.manager.resolve('api-design')['name'],'api-design')

    def test_removing_native_marker_cannot_downgrade_apply_verification(self):
        self.change(commit=False)
        (self.plugin/'.codex-marketplace-install.json').unlink()
        before=self.owned_bytes()
        with self.assertRaises(ecc.ManagementError):self.manager.apply()
        self.assertEqual(before,self.owned_bytes())

    def test_refresh_lock_wait_is_bounded(self):
        with self.manager.lock():
            start=time.monotonic()
            with self.assertRaises(ecc.CatalogError) as failure:
                self.manager.refresh(deadline=start+.1)
            self.assertEqual(failure.exception.code,'catalog_busy')
            self.assertLess(time.monotonic()-start,.5)

    def test_official_update_survives_missing_or_symlinked_unrelated_source(self):
        for damage in ('missing','symlink'):
            with self.subTest(damage=damage):
                self.change('tdd-workflow')
                path=self.plugin/'skills/api-design/SKILL.md'
                original=path.read_bytes();path.unlink()
                if damage=='symlink':
                    foreign=self.root/'foreign.md';foreign.write_bytes(original);path.symlink_to(foreign)
                try:
                    self.assertEqual(self.manager.resolve('tdd-workflow')['name'],'tdd-workflow')
                    with self.assertRaises(ecc.CatalogError):self.manager.resolve('api-design',refresh=False)
                    report=self.manager.refresh()
                    self.assertEqual(report['status'],'needs_attention')
                    self.assertTrue(report['warnings'])
                finally:
                    if path.is_symlink():path.unlink()
                    path.write_bytes(original)
                self.manager.refresh()

    def test_slow_old_refresh_cannot_overwrite_new_registered_catalog(self):
        self.change('tdd-workflow')
        old=self.plugin;prepared=threading.Event();release=threading.Event()
        original_lock=self.manager.lock
        from contextlib import contextmanager
        @contextmanager
        def pause(*args,**kwargs):
            if threading.current_thread().name.startswith('old-catalog'):
                prepared.set()
                if not release.wait(5):raise AssertionError('fixture did not release old refresh')
            with original_lock(*args,**kwargs):yield
        with ThreadPoolExecutor(max_workers=1,thread_name_prefix='old-catalog') as pool, mock.patch.object(self.manager,'lock',side_effect=pause):
            pending=pool.submit(self.manager.refresh)
            try:
                self.assertTrue(prepared.wait(5))
                new=old.parent/'10.0.0';shutil.copytree(old,new)
                for row in self.originals:row['path']=str(new/Path(row['path']).relative_to(old))
                self.manager.refresh()
            finally:release.set()
            with self.assertRaises(ecc.CatalogError):pending.result(timeout=5)
        self.assertTrue(self.manager.resolve('tdd-workflow',refresh=False)['path'].startswith(str(new)+os.sep))

    def test_omitted_required_original_does_not_block_verified_update(self):
        self.change('tdd-workflow')
        self.originals[:]=[r for r in self.originals if r['name']!='ecc:python-patterns']
        (self.plugin/'skills/python-patterns/SKILL.md').unlink()
        value=self.manager.resolve('tdd-workflow')
        self.assertEqual(value['name'],'tdd-workflow')
        self.assertTrue(value['warnings'])
        with self.assertRaises(ecc.CatalogError) as failure:
            self.manager.resolve('python-patterns',refresh=False)
        self.assertIn(failure.exception.code,('source_missing','source_unregistered'))
        self.manager.check_files(self.manager.state())

    def test_cli_dry_run_reports_partial_plan_without_key_error(self):
        self.change('tdd-workflow');self.change('api-design',commit=False)
        before=self.owned_bytes();output=io.StringIO();errors=io.StringIO()
        with mock.patch.object(ecc,'Codex',return_value=self.codex),contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
            code=ecc.main(['--codex-home',str(self.home),'--skills-root',str(self.manager.skills_root),'refresh','--dry-run'])
        self.assertEqual(code,0,errors.getvalue())
        value=json.loads(output.getvalue())
        self.assertEqual(value['status'],'planned')
        self.assertEqual(value['warning_count'],len(value['warnings']))
        self.assertEqual(before,self.owned_bytes())

    def test_markerless_non_git_source_cannot_be_blessed_by_apply(self):
        self.change(commit=False)
        shutil.rmtree(self.plugin/'.git')
        (self.plugin/'.codex-marketplace-install.json').unlink()
        before=self.owned_bytes()
        with self.assertRaises(ecc.CatalogError):self.manager.apply()
        self.assertEqual(before,self.owned_bytes())

    def test_legacy_valid_hashes_still_read_without_git_provenance(self):
        shutil.rmtree(self.plugin/'.git')
        (self.plugin/'.codex-marketplace-install.json').unlink()
        self.assertEqual(self.manager.resolve('error-handling',refresh=False)['name'],'error-handling')
        self.change('api-design',commit=False)
        with self.assertRaises(ecc.ManagementError):self.manager.resolve('api-design')
        self.assertEqual(self.manager.resolve('error-handling',refresh=False)['name'],'error-handling')


class SharedDeadlineTests(unittest.TestCase):
    def test_initialize_and_skills_list_share_one_deadline(self):
        fixture=fixtures.ManagerTest();fixture.setUp();self.addCleanup(fixture.doCleanups)
        binary=fixture.root/'slow-codex'
        binary.write_text('#!'+sys.executable+'\nimport sys,json,time\n'
                          'for line in sys.stdin:\n'
                          ' request=json.loads(line)\n'
                          ' if "id" not in request:continue\n'
                          ' time.sleep(.2)\n'
                          ' print(json.dumps({"id":request["id"],"result":{} if request["id"]==1 else {"data":[{"skills":[]}]}}),flush=True)\n')
        binary.chmod(0o755)
        native=ecc.Codex(str(binary),fixture.home,timeout=.3)
        start=time.monotonic()
        with self.assertRaisesRegex(ecc.ManagementError,'timed out'):
            native.skills(fixture.root,enable_ecc=True)
        self.assertLess(time.monotonic()-start,1)


if __name__ == '__main__':
    unittest.main()
