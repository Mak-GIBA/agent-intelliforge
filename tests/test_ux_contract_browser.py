"""Actual Chromium assertions, including failed checks and screenshot integrity."""
import hashlib
import json
import os
import unittest
from pathlib import Path
import test_ux_gan_browser as browser
from test_ux_visual_contract import example
from test_ux_contract_runtime import runtime

@unittest.skipUnless(os.getenv('UX_GAN_RUNTIME'),'Requires installed real Chromium runtime')
class ContractBrowserTests(unittest.TestCase):
    setUp=browser.BrowserTests.setUp
    tearDown=browser.BrowserTests.tearDown
    rpc=browser.BrowserTests.rpc
    tool=browser.BrowserTests.tool

    def configure_contract(self):
        self.contract=example()
        for t in self.contract['transitions']:t['retained_fields']=['query','note']
        self.contract['screens'][0]['fields']=[{'id':'query','label':'検索','type':'search'}]
        self.contract['screens'][1]['fields']=[{'id':'note','label':'メモ','type':'textarea'}]
        self.contract['requirements'][0]['acceptance'] += [
            {'id':'AC-query','screen_id':'S-list','state':'normal','type':'value','locator':{'selector':'#query'},'expected':'契約'},
            {'id':'AC-name','screen_id':'S-detail','state':'normal','type':'accessible_name','locator':{'selector':'#back'},'expected':'文書一覧へ戻る'}]
        (self.base/'index.html').write_text('''<!doctype html><html lang="ja"><meta charset="utf-8"><title>契約検証</title>
<label>検索<input id="query" value="契約"></label><label>メモ<textarea id="note">共有メモ</textarea></label>
<section id="list"><h1>文書</h1><button id="open">文書を開く</button><button id="wrong">別の経路</button></section>
<section id="detail" hidden><h1>契約書</h1><button id="back">文書一覧へ戻る</button></section>
<script>function render(){list.hidden=location.hash==='#detail';detail.hidden=!list.hidden}
open=document.getElementById('open');open.onclick=()=>location.hash='detail';
document.getElementById('wrong').onclick=open.onclick;back.onclick=()=>location.hash='';addEventListener('hashchange',render);render()</script></html>''')
        p=self.base/'design.json';p.write_text(json.dumps(self.contract));run=self.base/'run';run.mkdir()
        self.frozen=runtime.freeze(p,self.base,run);return run/'ux-contract.json'

    def check(self,screen,state='normal',transition=None):
        args={'screen_id':screen,'state':state}
        if transition:args['transition_id']=transition
        return json.loads(self.tool('ux_check_contract',**args)['content'][0]['text'])

    def test_actual_transitions_retention_and_accessible_names_all_viewports(self):
        for width,height in [(1440,900),(768,1024),(390,844)]:
            self.tool('ux_navigate',url=self.url+'/');self.tool('ux_resize',width=width,height=height)
            self.assertTrue(all(c['passed'] for c in self.check('S-list')['checks']))
            self.tool('ux_click',selector='#open')
            detail=self.check('S-detail',transition='T-open')
            self.assertTrue(all(c['passed'] for c in detail['checks']),detail)
            self.tool('ux_click',selector='#back')
            result=self.check('S-list',transition='T-back');self.assertTrue(all(c['passed'] for c in result['checks']),result)
        # Runtime expects role_dir/screenshots, not a model-generated audit JSON.
        report=runtime.observations(self.frozen,self.base,['desktop','tablet','mobile'])
        self.assertTrue(report['ready'],report);self.assertEqual(report['verified'],len(self.frozen['required_checks'])*3)
        entries=[json.loads(line) for line in (self.out/'browser-receipts.jsonl').read_text().splitlines()]
        used=next(e['frame_id'] for e in entries if e['kind']=='contract_check')
        frame=Path(next(e['path'] for e in entries if e['kind']=='frame' and e['id']==used));frame.write_bytes(frame.read_bytes()+b'changed')
        self.assertFalse(runtime.observations(self.frozen,self.base,['desktop','tablet','mobile'])['ready'])

    def test_wrong_route_and_wrong_action_do_not_satisfy_the_design(self):
        self.tool('ux_navigate',url=self.url+'/')
        wrong=self.check('S-detail');self.assertFalse(wrong['route_matches']);self.assertFalse(any(c['passed'] for c in wrong['checks']))
        self.check('S-list');self.tool('ux_click',selector='#wrong')
        wrong=self.check('S-detail',transition='T-open');self.assertFalse(next(c for c in wrong['checks'] if c['id']=='T-open')['passed'])
        report=runtime.observations(self.frozen,self.base,['desktop']);self.assertFalse(report['ready']);self.assertTrue(report['failed'])

if __name__=='__main__':unittest.main()
