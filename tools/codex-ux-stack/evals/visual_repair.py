#!/usr/bin/env python3
"""One bounded real UX-GAN repair/review round per version and repair case."""
import argparse
import concurrent.futures
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
from visual_benchmark import Benchmark,ROOT,write,Quiet
import functools
import http.server
import threading

RULES=Path(__file__).with_name('visual-repair-contract.json')

def contract(case):
    if case=='documents':
        screens=[('S-list','文書一覧','/','#list'),('S-detail','文書とメモ','/#detail','#detail')]
        actions=[('A-open','S-list','#open-contract','文書を開く'),('A-back','S-detail','#back','文書一覧へ戻る')]
        retain=['query','kind','select-contract']
    else:
        screens=[('S-confirm','申込内容の確認','/#confirm','#confirm'),('S-payment','模擬決済','/#payment','#payment')]
        actions=[('A-next','S-confirm','#continue-confirm','模擬決済へ進む'),('A-back','S-payment','#back-payment','申込内容を確認する')]
        retain=[]
    jid='J-doc' if case=='documents' else 'J-payment'
    return {'schema_version':1,'revision':1,'project':{'name':case},'journeys':[{'id':jid,'purpose':'必須の往復を完了する','actions':[a[0] for a in actions],'required':True}],
        'screens':[{'id':sid,'title':title,'purpose':title,'route':route,'states':['normal'],'component':{'path':'index.html'}} for sid,title,route,_ in screens],
        'actions':[{'id':aid,'screen_id':sid,'label':label,'kind':'click','locator':{'selector':selector}} for aid,sid,selector,label in actions],
        'transitions':[{'id':'T-forward','action_id':actions[0][0],'from':{'screen_id':screens[0][0],'state':'normal'},'condition':'次の画面へ進む','to':{'screen_id':screens[1][0],'state':'normal'},'on_error':None,'retained_fields':retain},
                       {'id':'T-return','action_id':actions[1][0],'from':{'screen_id':screens[1][0],'state':'normal'},'condition':'元の画面へ戻る','to':{'screen_id':screens[0][0],'state':'normal'},'on_error':None,'retained_fields':retain+(['note'] if case=='documents' else [])}],
        'requirements':[{'id':'R-flow','journey_id':jid,'required':True,'acceptance':[{'id':'AC-'+sid,'screen_id':sid,'state':'normal','type':'visible','locator':{'selector':selector},'expected':True} for sid,_,_,selector in screens]}],
        'artifacts':[],'approval':{'status':'not_requested','source':'synthetic repair requested; no human approval'}}

class Repair:
    def __init__(self,out):self.bench=Benchmark(out);self.rules=json.loads(RULES.read_text())
    def job(self,label,case,retry_setup=False):
        original=self.bench.out/'repair'/f'{label}-{case}'
        if retry_setup:
            failed=json.loads((original/'result.json').read_text())
            if failed['elapsed_seconds']>=1 or list((original/'app/artifacts/ux-gan').glob('*/state.json')) or 'Recursive harness execution refused' not in (original/'harness.log').read_text():raise ValueError('Only the evidenced pre-model setup failure may be retried')
        job=self.bench.out/'repair'/(f'{label}-{case}-setup-corrected' if retry_setup else f'{label}-{case}');result=job/'result.json'
        if result.exists():return json.loads(result.read_text())
        job.mkdir(parents=True,exist_ok=True);app=job/'app'
        shutil.copytree(self.bench.out/'generation'/f'{label}-{case}-1'/'app',app,ignore=shutil.ignore_patterns('.git','artifacts','ui-ux-review*'))
        source=job/'source';source.mkdir();archive=subprocess.run(['git','archive',self.rules[label+'_commit'],'tools/codex-ux-stack'],cwd=ROOT,capture_output=True,check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(source,filter='data')
        kit=source/'tools/codex-ux-stack';page=app/'index.html';regression=self.rules['regressions'][case]
        text=page.read_text();injection='<style data-seeded-regression>'+regression['selector']+'{'+regression['effect']+'}</style>'
        page.write_text(text.replace('</head>',injection+'</head>') if '</head>' in text else injection+text)
        ux=app/'docs/ux/design-contract.json';write(ux,contract(case))
        subprocess.run(['git','init','-q',str(app)],check=True)
        handler=functools.partial(Quiet,directory=str(app));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
        threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
        home=self.bench.home(job/'codex-home');(job/'test-home').mkdir()
        # The static checker is outside the writable app. It returns failure for
        # functional defects; the independent reviewer still assesses the UI.
        checker=ROOT/'tools/codex-ux-stack/evals/visual_operations.cjs'
        test=shlex.join(['node',str(checker),str(job),case,'--corrected-async','--require-pass'])
        command=[sys.executable,'-B',str(kit/'skill/scripts/harness.py'),'run','--project',str(app),'--url',url,
            '--profile','focused','--focus',regression['focus'],'--max-iterations','1','--phase-timeout',str(self.rules['phase_seconds']),
            '--model',self.rules['model'],'--browser','local-playwright','--test-command',test,
            '--brief',regression['focus']+' 画面と操作を見てから修正し、独立して再確認する。docs/ux/design-contract.jsonのIDsと条件を保つ。新しい要求や説明を増やさない。']
        for viewport in self.rules['viewports']:command+=['--viewport',viewport]
        if label=='candidate':command+=['--ux-contract','docs/ux/design-contract.json']
        old_home=os.environ.get('HOME');old_browser=os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
        # HOME is invocation-local in the wrapper. The pinned browser cache is
        # only read; no installation or personal configuration mutation occurs.
        wrapper=job/'launch.py';wrapper.write_text('import os,subprocess,sys\nos.environ["HOME"]='+repr(str(job/'test-home'))+'\nos.environ["PLAYWRIGHT_BROWSERS_PATH"]='+repr(old_browser or str(Path(old_home or str(Path.home()))/'.cache/ms-playwright'))+'\nsys.exit(subprocess.call(sys.argv[1:]))\n')
        try:r=self.bench.call([sys.executable,str(wrapper),*command],app,home,job/'harness.log',self.rules['phase_seconds']*4+120,child=False)
        finally:server.shutdown();server.server_close()
        states=list((app/'artifacts/ux-gan').glob('*/state.json'))
        if states:
            state=json.loads(states[0].read_text());r.update(harness_status=state['status'],reason=state['reason'],iteration=state['iteration'],run_id=state['run_id'],contract_report=state.get('ux_contract_report'))
        r.update(label=label,case=case,scope=regression['focus'],source_commit=self.rules[label+'_commit']);write(result,r)
        print(json.dumps(r,ensure_ascii=False),flush=True);return r
    def run(self,retry_setup=False):
        # Budget writes must not race another evaluator process. The supervisor
        # starts this phase only after all generation and rating calls finish.
        write(self.bench.out/'repair-conditions.json',self.rules)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(self.job,label,case,retry_setup) for case in self.rules['cases'] for label in ['baseline','candidate']]
            for future in concurrent.futures.as_completed(futures):future.result()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--retry-setup',action='store_true',help='Retry only the preserved, evidenced failure before any model call');args=parser.parse_args();Repair(args.output).run(args.retry_setup)
