"""Real local library tests, skipped when deps are not installed; no download."""
import io
import sys
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import office
import common
try:
    import pypdf
    import pypdfium2
    import pdfplumber
    DEPS=True
except ImportError:DEPS=False

@unittest.skipUnless(DEPS,'Local PDF dependencies not present; no network download in self-test')
class RealPDFTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.src=self.root/'source.pdf'
        w=pypdf.PdfWriter()
        for i in range(3):w.add_blank_page(width=300+i*10,height=200)
        with self.src.open('wb') as f:w.write(f)
        w.close()
    def test_pdf_inspection(self):self.assertEqual(office.facts(self.src)['pages'],3)
    def test_select_real_pdf(self):
        out=self.root/'select.pdf';office.pdf_edit('select',[self.src],out,'3,1')
        r=pypdf.PdfReader(out);self.assertEqual(len(r.pages),2);self.assertEqual(r.pages[0].mediabox.width,320)
    def test_rotate_preserves_unselected_pages(self):
        out=self.root/'rotate.pdf';office.pdf_edit('rotate',[self.src],out,'2',90)
        r=pypdf.PdfReader(out);self.assertEqual(len(r.pages),3);self.assertEqual(r.pages[1].rotation,90);self.assertEqual(r.pages[0].rotation,0)
    def test_merge_real_pdfs(self):
        out=self.root/'merge.pdf';office.pdf_edit('merge',[self.src,self.src],out)
        self.assertEqual(len(pypdf.PdfReader(out).pages),6)
    def test_no_overwrite_pdf(self):
        before=self.src.read_bytes()
        with self.assertRaises(common.OfficeError):office.pdf_edit('rotate',[self.src],self.src,'1',90)
        self.assertEqual(self.src.read_bytes(),before)
    def test_real_pdf_render_and_manifest(self):
        out=self.root/'pages';r=office.render(self.src,out,None,72,'auto')
        self.assertEqual(len(r['images']),3);self.assertTrue(r['complete']);self.assertEqual(r['visual_review'],'NOT_PERFORMED')
        self.assertTrue(office.visual_status(out)['source_hash_current'])
    def test_partial_render_is_not_full(self):
        r=office.render(self.src,self.root/'partial','1',72,'auto');self.assertFalse(r['complete'])
    def test_render_existing_output_refused(self):
        o=self.root/'existing';o.mkdir()
        with self.assertRaises(common.OfficeError):office.render(self.src,o,None,72,'auto')
    def test_pdf_extract_no_text_is_explicit(self):
        output=self.root/'text.md';office.extract(self.src,output,'2')
        self.assertIn('No extractable text',output.read_text(encoding="utf-8"));self.assertIn('Page 2',output.read_text(encoding="utf-8"))
    def test_encrypted_pdf_rejected(self):
        e=self.root/'encrypted.pdf';w=pypdf.PdfWriter();w.add_blank_page(100,100);w.encrypt('secret');w.write(e);w.close()
        with self.assertRaises(common.OfficeError):office.facts(e)


from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':unittest.main()
