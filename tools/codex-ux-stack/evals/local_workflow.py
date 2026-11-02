#!/usr/bin/env python3
"""Supplemental scoped workflow proof; original comparison failures stay intact."""
import argparse
import concurrent.futures
import functools
import hashlib
import http.server
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import threading
from visual_benchmark import Benchmark,ROOT,Quiet,write
from visual_repair import contract

RULES=Path(__file__).with_name('local-workflow-contract.json')

class LocalWorkflow:
    def __init__(self,out):self.bench=Benchmark(out);self.rules=json.loads(RULES.read_text())
    def job(self,name):
        job=self.bench.out/'local-workflow'/name;result=job/'result.json'
        if result.exists():return json.loads(result.read_text())
        job.mkdir(parents=True,exist_ok=True);app=job/'app';app.mkdir();source=job/'source';source.mkdir()
        archive=subprocess.run(['git','archive',self.rules['source_commit'],'tools/codex-ux-stack'],cwd=ROOT,capture_output=True,check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(source,filter='data')
        kit=source/'tools/codex-ux-stack';spec=importlib.util.spec_from_file_location('_workflow_contract_'+name,kit/'ux-visual-design/scripts/ux_contract.py');engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
        document=name=='document_return';c=contract('documents' if document else 'application')
        for screen in c['screens']:screen['route']='/'
        for action in c['actions']:action['locator']={'selector':'[data-action-id="'+action['id']+'"]'}
        for requirement in c['requirements']:
            for check in requirement['acceptance']:check['locator']={'selector':'#screen[data-screen-id="'+check['screen_id']+'"]'}
        if document:
            c['screens'][0]['fields']=[{'id':'query','label':'検索語','type':'search'}];c['screens'][1]['fields']=[{'id':'note','label':'メモの下書き','type':'textarea'}]
            c['transitions'][0]['retained_fields']=['query'];c['transitions'][1]['retained_fields']=['query','note']
        write(app/'docs/ux/design-contract.json',c)
        selector='[data-action-id="A-back"]' if document else '[data-action-id="A-next"]'
        html=engine._preview(c).replace('</style>',selector+'{display:none!important}</style>');(app/'index.html').write_text(html)
        (app/'AGENTS.md').write_text('This is an isolated interactive wireframe fixture. Fix only the requested journey. Preserve the canonical contract and its IDs. No backend, real sending or charging is intended. Do not change tests, Git history or harness outputs. Never start a nested harness.\n')
        subprocess.run(['git','init','-q',str(app)],check=True)
        handler=functools.partial(Quiet,directory=str(app));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
        check=job/'check.cjs';runtime=os.environ['UX_GAN_RUNTIME']
        check.write_text("const {chromium}=require("+json.dumps(runtime+'/node_modules/playwright')+");(async()=>{const b=await chromium.launch({headless:true});try{const p=await b.newPage();p.setDefaultTimeout(2000);await p.goto("+json.dumps(url)+");"+
            ("await p.locator('[data-field=query]').fill('契約');await p.locator('[data-action-id=\"A-open\"]').click();await p.locator('[data-field=note]').fill('確認メモ');await p.locator('[data-action-id=\"A-back\"]').click();if(await p.locator('[data-field=query]').inputValue()!=='契約')throw Error('query lost');await p.locator('[data-action-id=\"A-open\"]').click();if(await p.locator('[data-field=note]').inputValue()!=='確認メモ')throw Error('note lost');" if document else
             "await p.locator('[data-action-id=\"A-next\"]').click();if(await p.locator('#screen').getAttribute('data-screen-id')!=='S-payment')throw Error('wrong destination');await p.locator('[data-action-id=\"A-back\"]').click();if(await p.locator('#screen').getAttribute('data-screen-id')!=='S-confirm')throw Error('wrong return');")+
            "}finally{await b.close();}})().catch(e=>{console.error(e.message);process.exit(1)});\n")
        test=shlex.join(['node',str(check)]);home=self.bench.home(job/'codex-home');(job/'test-home').mkdir()
        settings=home/'config.toml';settings.write_text(settings.read_text().replace('model_reasoning_effort="max"','model_reasoning_effort='+json.dumps(self.rules['reasoning_effort'])))
        brief=('検索語を入力して文書へ移動し、メモの下書きを入力して一覧へ戻り、再び文書を開いて下書きを保持する。' if document else '申込内容の確認から模擬決済へ進み、確認へ戻る。')
        brief+=' この2画面の試作の必須操作に表示上の回帰がある。実画面で再現し、最小の修正後に独立して再確認する。フロントエンド試作のため、実API・保存サーバー・本決済の欠如を不具合にしない。契約とテストは変更しない。デスクトップの宣言範囲だけを確認し、全体の合格とは扱わない。'
        argv=[sys.executable,'-B',str(kit/'skill/scripts/harness.py'),'run','--project',str(app),'--url',url,'--profile','focused','--focus',brief,'--viewport','desktop','--max-iterations','1','--phase-timeout',str(self.rules['phase_seconds']),'--model',self.rules['model'],'--browser','local-playwright','--ux-contract','docs/ux/design-contract.json','--test-command',test,'--brief',brief]
        wrapper=job/'launch.py';wrapper.write_text('import os,subprocess,sys\nos.environ["HOME"]='+repr(str(job/'test-home'))+'\nos.environ["PLAYWRIGHT_BROWSERS_PATH"]='+repr(os.environ.get('PLAYWRIGHT_BROWSERS_PATH') or str(Path.home()/'.cache/ms-playwright'))+'\nsys.exit(subprocess.call(sys.argv[1:]))\n')
        write(job/'fixture.json',{'protocol':self.rules,'html_sha256':hashlib.sha256(html.encode()).hexdigest(),'contract_sha256':engine.digest(c)})
        try:r=self.bench.call([sys.executable,str(wrapper),*argv],app,home,job/'harness.log',self.rules['phase_seconds']*4+80,child=False)
        finally:server.shutdown();server.server_close()
        states=list((app/'artifacts/ux-gan').glob('*/state.json'))
        if states:
            state=json.loads(states[0].read_text());r.update(harness_status=state['status'],reason=state['reason'],iteration=state['iteration'],run_id=state['run_id'],contract_report=state.get('ux_contract_report'))
        r['case']=name;write(result,r);print(json.dumps(r,ensure_ascii=False),flush=True);return r
    def run(self):
        write(self.bench.out/'local-workflow-conditions.json',self.rules)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(self.job,self.rules['cases']))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();LocalWorkflow(args.output).run()
