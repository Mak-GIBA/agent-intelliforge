"""Behavioral contracts for UX design exchange; temporary projects only."""
from pathlib import Path
import copy
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'tools/codex-ux-stack/ux-visual-design/scripts/ux_contract.py'
spec = importlib.util.spec_from_file_location('ux_contract_under_test', SCRIPT)
ux = importlib.util.module_from_spec(spec); spec.loader.exec_module(ux)


def example():
    return {
        'schema_version': 1, 'revision': 1,
        'project': {'name': '文書管理', 'users': [{'id':'staff','context':'文書を探してメモを残す'}],
                    'goals': ['目的の文書を見つける'], 'objects': [{'id':'document','attributes':['title'],'operations':['open']} ]},
        'journeys': [{'id':'J-doc','purpose':'文書を開いて一覧へ戻る','actions':['A-open','A-back'],'required':True}],
        'screens': [
            {'id':'S-list','title':'文書','purpose':'文書を選ぶ','route':'/','states':['normal','empty'],
             'component':{'path':'index.html','symbol':'list'},'layout':{'x':24,'y':32,'width':340,'height':420}},
            {'id':'S-detail','title':'文書の詳細','purpose':'文書とメモを読む','route':'/#detail','states':['normal','failure'],
             'component':{'path':'index.html','symbol':'detail'},'layout':{'x':410,'y':32,'width':340,'height':420}}],
        'actions': [
            {'id':'A-open','screen_id':'S-list','label':'文書を開く','kind':'click','locator':{'selector':'#open'}},
            {'id':'A-back','screen_id':'S-detail','label':'文書一覧へ戻る','kind':'click','locator':{'selector':'#back'}}],
        'transitions': [
            {'id':'T-open','action_id':'A-open','from':{'screen_id':'S-list','state':'normal'},
             'condition':'文書が取得できた','to':{'screen_id':'S-detail','state':'normal'},'on_error':None,'retained_fields':['query','note']},
            {'id':'T-back','action_id':'A-back','from':{'screen_id':'S-detail','state':'normal'},
             'condition':'一覧へ戻る','to':{'screen_id':'S-list','state':'normal'},'on_error':None,'retained_fields':['query','note']}],
        'requirements': [{'id':'R-doc','journey_id':'J-doc','purpose':'一覧と詳細を往復できる','required':True,'acceptance':[
            {'id':'AC-list','screen_id':'S-list','state':'normal','type':'visible','locator':{'selector':'#list'},'expected':True},
            {'id':'AC-detail','screen_id':'S-detail','state':'normal','type':'visible','locator':{'selector':'#detail'},'expected':True}]}],
        'artifacts': [], 'approval': {'status':'not_requested','source':'implementation requested'},
    }


class UXContractTests(unittest.TestCase):
    def test_valid_contract_and_missing_reference(self):
        contract=example();self.assertEqual(ux.validate(contract),[])
        contract['transitions'][0]['to']['screen_id']='missing'
        self.assertTrue(any('missing' in e for e in ux.validate(contract)))

    def test_duplicate_ids_and_unsafe_component_paths_are_rejected(self):
        contract=example();contract['actions'][1]['id']='A-open'
        self.assertTrue(any('duplicate' in e.lower() for e in ux.validate(contract)))
        contract=example();contract['screens'][0]['component']['path']='../outside.py'
        self.assertTrue(ux.validate(contract))

    def test_three_way_merges_independent_edits_and_keeps_conflicts(self):
        base=example();local=copy.deepcopy(base);remote=copy.deepcopy(base)
        local['screens'][0]['title']='検索';remote['screens'][1]['title']='詳細とメモ'
        result=ux.reconcile(base,local,remote)
        self.assertEqual(result['status'],'ready')
        self.assertEqual([s['title'] for s in result['contract']['screens']],['検索','詳細とメモ'])
        remote['screens'][0]['title']='一覧'
        result=ux.reconcile(base,local,remote)
        self.assertEqual(result['status'],'conflict');self.assertTrue(result['conflicts'])
        self.assertEqual(local['screens'][0]['title'],'検索')

    def test_svg_human_edit_round_trip_preserves_component_and_business_goal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);contract=example();(root/'index.html').write_text('<h1>fixture</h1>')
            ux.render_bundle(contract,root/'design')
            svg=root/'design/wireframes.svg';text=svg.read_text()
            self.assertIn('data-screen-id="S-list"',text)
            svg.write_text(text.replace('>文書</text>','>文書を探す</text>'))
            result=ux.import_design(contract,svg)
            self.assertEqual(result['screens'][0]['title'],'文書を探す')
            self.assertEqual(result['project'],contract['project'])
            self.assertEqual(result['screens'][0]['component'],contract['screens'][0]['component'])
            self.assertEqual((root/'index.html').read_text(),'<h1>fixture</h1>')

    def test_exports_escape_content_and_do_not_overwrite_edited_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);contract=example();contract['screens'][0]['title']='</script><script>alert(1)</script>'
            ux.render_bundle(contract,root)
            self.assertNotIn('</script><script>alert(1)</script>',(root/'wireframes.html').read_text())
            (root/'flow.mmd').write_text('human edit')
            with self.assertRaises(ux.ContractError):ux.render_bundle(contract,root)
            self.assertEqual((root/'flow.mmd').read_text(),'human edit')

    def test_unknown_svg_ids_and_xml_entities_are_not_silently_imported(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);ux.render_bundle(example(),root)
            svg=root/'wireframes.svg';svg.write_text(svg.read_text().replace('data-screen-id="S-list"','data-screen-id="unknown"'))
            with self.assertRaises(ux.ContractError):ux.import_design(example(),svg)
            svg.write_text('<!DOCTYPE svg [<!ENTITY x "expanded">]><svg>&x;</svg>')
            with self.assertRaises(ux.ContractError):ux.import_design(example(),svg)


if __name__=='__main__':unittest.main()
