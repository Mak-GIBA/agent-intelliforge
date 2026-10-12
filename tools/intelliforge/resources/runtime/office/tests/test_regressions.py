import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from common import OfficeError,run
import office
from test_workbench import Isolated,make_docx

class Regressions(Isolated):
    def test_utf16_doctype_rejected(self):
        evil='<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY y "payload">]><x>&y;</x>'.encode('utf-16')
        doc=make_docx(self.home/'x.docx',extra={'bad.xml':evil})
        with self.assertRaises(OfficeError):office.facts(doc)
    def test_verify_copy_detects_changed_original(self):
        src=make_docx(self.home/'a.docx');out=self.home/'b.docx';office.prepare(src,out)
        make_docx(src,text='Changed source')
        result=run([sys.executable,str(ROOT/'office.py'),'verify-copy',str(out)],check=False)
        self.assertNotEqual(result.returncode,0);self.assertIn('ORIGINAL_CHANGED',result.stderr)
    def test_verify_copy_valid(self):
        src=make_docx(self.home/'a.docx');out=self.home/'b.docx';office.prepare(src,out)
        make_docx(out,text='Edited copy')
        result=run([sys.executable,str(ROOT/'office.py'),'verify-copy',str(out)])
        self.assertTrue(json.loads(result.stdout)['original_unchanged'])
    def test_render_cannot_overwrite_original_directory(self):
        doc=make_docx(self.home/'a.docx')
        with self.assertRaises(OfficeError):office.render(doc,self.home,None,144,'auto')
    def test_office_screenshot_requires_explicit_pages(self):
        doc=make_docx(self.home/'a.docx');dest=self.home/'stage';dest.mkdir()
        with mock.patch.object(office,'config',return_value={}):
            with self.assertRaisesRegex(OfficeError,'explicit pages'):office._render_job(doc,dest,None,144,'officecli')
    def test_office_engine_env_disables_updates(self):
        with mock.patch.object(office,'office_binary',return_value=Path('/test/officecli')),mock.patch.object(office,'run') as execute:
            office.office_command({},['help','docx'])
            env=execute.call_args.kwargs['env']
            self.assertEqual(env['OFFICECLI_SKIP_UPDATE'],'1');self.assertEqual(env['OFFICECLI_NO_AUTO_RESIDENT'],'1')
    def test_render_headless_backend_not_x11(self):
        # This regression follows a real headless conversion failure with the gen backend.
        source=(ROOT/'office.py').read_text(encoding="utf-8")
        self.assertIn("'SAL_USE_VCLPLUGIN':'svp'",source)
        self.assertNotIn("'SAL_USE_VCLPLUGIN':'gen'",source)
    def test_preview_does_not_claim_visual_verified(self):
        doc=(ROOT/'skills/office-workbench/references/workflows.md').read_text(encoding="utf-8")
        self.assertIn('PNG',doc);self.assertIn('別',doc)
    def test_skip_deps_and_mcp_combination_rejected(self):
        result=run([sys.executable,str(ROOT/'install.py'),'--assets-only','--with-mcp'],check=False)
        self.assertNotEqual(result.returncode,0);self.assertFalse(self.p['config'].exists())
    def test_version_command_no_install_required(self):
        r=run([sys.executable,str(ROOT/'office.py'),'--version'])
        self.assertIn('1.0.0',r.stdout)

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
