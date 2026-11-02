#!/usr/bin/env python3
"""Bounded real-model comparisons in private temporary projects, never user settings."""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import http.server
import functools
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[3]
CONDITIONS=Path(__file__).with_name('visual-design-contract.json')

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class Benchmark:
    def __init__(self,destination):
        self.out=Path(destination).absolute();self.out.mkdir(parents=True,exist_ok=True);self.out.chmod(0o700)
        self.conditions=json.loads(CONDITIONS.read_text());self.lock=threading.Lock()
        self.budget=self.out/'budget.json'
        if not self.budget.exists():write(self.budget,{'used_seconds':0,'reserved_seconds':0,'calls':[]})

    def call(self,argv,workspace,home,output,limit):
        with self.lock:
            budget=json.loads(self.budget.read_text());remaining=self.conditions['model_budget_seconds']-budget['used_seconds']-budget['reserved_seconds']
            limit=min(limit,int(remaining))
            if limit<=0:return {'status':'budget_exhausted','elapsed_seconds':0}
            budget['reserved_seconds']+=limit;write(self.budget,budget)
        env={**os.environ,'CODEX_HOME':str(home),'PYTHONDONTWRITEBYTECODE':'1','UX_GAN_CHILD':'1'}
        start=time.monotonic();status='completed';proc=None
        try:
            # All inputs are argv elements. No shell interpolation or credential logging.
            with output.open('w') as log:
                output.chmod(0o600)
                proc=subprocess.Popen(argv,cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,text=True)
                try:code=proc.wait(timeout=limit)
                except subprocess.TimeoutExpired:
                    status='timeout';os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                    code=proc.returncode
            if code and status=='completed':status='failed'
        finally:
            elapsed=time.monotonic()-start
            with self.lock:
                budget=json.loads(self.budget.read_text());budget['reserved_seconds']-=limit;budget['used_seconds']+=elapsed
                budget['calls'].append({'output':str(output.relative_to(self.out)),'elapsed_seconds':elapsed,'status':status,'limit_seconds':limit});write(self.budget,budget)
        return {'status':status,'exit_code':code,'elapsed_seconds':elapsed,'limit_seconds':limit}

    def prepare(self):
        frozen=self.out/'conditions.json'
        value={**self.conditions,'conditions_sha256':hashlib.sha256(CONDITIONS.read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        if frozen.exists():
            if json.loads(frozen.read_text())!=value:raise ValueError('Frozen comparison inputs differ; start a separate comparison')
            return
        # Freeze exact source commits before any generation, including baseline docs/skills.
        source=self.out/'sources';source.mkdir()
        for label,commit in [('baseline',self.conditions['baseline_commit']),('candidate',self.conditions['candidate_commit'])]:
            dest=source/label;dest.mkdir()
            archive=subprocess.run(['git','archive',commit,'tools/codex-ux-stack'],cwd=ROOT,capture_output=True,check=True).stdout
            import io,tarfile
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(dest,filter='data')
        write(frozen,value)

    def home(self,directory):
        directory.mkdir(parents=True,exist_ok=True);directory.chmod(0o700)
        original=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))
        credential=original/'auth.json'
        if credential.is_file():shutil.copyfile(credential,directory/'auth.json');(directory/'auth.json').chmod(0o600)
        (directory/'config.toml').write_text('approval_policy="never"\nweb_search="disabled"\nmodel_reasoning_effort="max"\n[sandbox_workspace_write]\nnetwork_access=false\n')
        return directory

    def generation(self,label,case,trial):
        job=self.out/'generation'/f'{label}-{case}-{trial}';result_path=job/'result.json'
        if result_path.exists():return json.loads(result_path.read_text())
        job.mkdir(parents=True,exist_ok=True);workspace=job/'app';workspace.mkdir()
        source=self.out/'sources'/label/'tools/codex-ux-stack'
        skills=workspace/'.agents/skills';skills.mkdir(parents=True)
        for source_name,target_name in [('ooui-design','ooui-design'),('skill','ux-gan-harness'),('ux-visual-design','ux-visual-design')]:
            if (source/source_name).exists():shutil.copytree(source/source_name,skills/target_name)
        (workspace/'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>未実装</title><p>未実装</p></html>')
        (workspace/'AGENTS.md').write_text('Use only this test project. Never read credentials, install dependencies, send messages, charge, deploy or change repository history. UX_GAN_CHILD=1: do not start another harness. Use the supplied available UX Stack skills and local browser. Artifacts are editable prototypes, not human approval.\n')
        subprocess.run(['git','init','-q',str(workspace)],check=True)
        handler=functools.partial(Quiet,directory=str(workspace));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
        threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}'
        prompt=('実際に動く高品質なWebアプリを実装してください。利用可能な .agents/skills のUX Stack Skillを読み、用途に応じて設計・可視化・実装を行ってください。'
                '主成果物はindex.html。外部依存なしのHTML/CSS/JavaScript。Desktop/Tablet/Mobile、アクセシビリティ、失敗復旧、認知負荷を確認。'
                'MCPデザインツールは未接続なのでローカル代替を使う。実装まで依頼済みなので追加の承認待ちは不要。'
                'モデル呼び出し上限5分を見込み、まず動作するアプリを作り、可能な範囲でローカルブラウザーを使って確認。ハーネスの再帰起動は禁止。'
                '合成データのみ。テスト用にwindow.__UX_TEST={failNext:false}を用意。金銭・個人情報の実送信は禁止。'
                f'起動済みプレビュー: {url} 。\n要求:\n'+self.conditions['inputs'][case])
        (job/'prompt.txt').write_text(prompt)
        argv=['codex','exec','--ephemeral','--json','--sandbox','workspace-write','--model',self.conditions['model'],'-C',str(workspace),
              '--output-last-message',str(job/'last-message.txt'),'-c','model_reasoning_effort="max"']
        runtime=os.environ.get('UX_GAN_RUNTIME')
        if runtime:
            bridge={'command':'node','args':[str(source/'skill/scripts/visual-browser.cjs')],
                    'env':{'UX_GAN_RUNTIME':runtime,'UX_GAN_SCREENSHOTS':str(job/'model-screenshots'),'UX_GAN_TARGET':url},
                    'required':True,'default_tools_approval_mode':'approve','startup_timeout_sec':60,'tool_timeout_sec':60}
            def toml(value):
                if isinstance(value,dict):return '{'+', '.join(json.dumps(k)+' = '+toml(v) for k,v in value.items())+'}'
                if isinstance(value,list):return '['+', '.join(toml(v) for v in value)+']'
                return json.dumps(value)
            for key,value in bridge.items():argv+=['-c',f'mcp_servers.ux_gan_browser.{key}={toml(value)}']
        argv+=['--',prompt]
        try:result=self.call(argv,workspace,self.home(job/'codex-home'),job/'events.jsonl',self.conditions['generation_seconds'])
        finally:server.shutdown();server.server_close()
        result.update(case=case,label=label,trial=trial,workspace=str(workspace),html_exists=(workspace/'index.html').is_file(),external_design_mcp_calls=0,cost='not exposed; token usage retained in events')
        write(result_path,result);return result

    def generate(self,workers):
        self.prepare()
        # Counterbalance order across repeats. No retries or discarded failed trials.
        jobs=[(label,case,trial) for trial in range(1,self.conditions['trials']+1) for case in self.conditions['cases'] for label in (['baseline','candidate'] if trial==1 else ['candidate','baseline'])]
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(self.generation,*job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                r=future.result();print(json.dumps({k:r[k] for k in ['label','case','trial','status','elapsed_seconds'] if k in r}),flush=True)

    def ratings(self):
        mapping_path=self.out/'blind-map.json'
        if mapping_path.exists():mapping=json.loads(mapping_path.read_text())
        else:
            mapping={}
            for case in self.conditions['cases']:
                first=['baseline','candidate'];secrets.SystemRandom().shuffle(first)
                for trial in range(1,self.conditions['trials']+1):mapping[f'{case}-{trial}']=dict(zip(['A','B'],first if trial==1 else list(reversed(first))))
            write(mapping_path,mapping)
        for key,pair in mapping.items():
            job=self.out/'ratings'/key
            if (job/'result.json').exists():continue
            case,trial=key.rsplit('-',1);job.mkdir(parents=True,exist_ok=True);facts={};attachments=[]
            for anonymous,label in pair.items():
                generation=self.out/'generation'/f'{label}-{case}-{trial}';corrected=generation/'operations-corrected.json';op=json.loads((corrected if corrected.exists() else generation/'operations.json').read_text())
                facts[anonymous]={'checks':[{k:c[k] for k in ('id','viewport','passed')} for c in op['checks']],
                    'generation_status':json.loads((generation/'result.json').read_text())['status']}
                wanted=['desktop-initial','tablet-initial','mobile-initial','desktop-failure','mobile-completed','mobile-focus']
                if case=='application':wanted+=['mobile-confirm','mobile-payment']
                if case=='landing':wanted+=['mobile-signup']
                for name in wanted:
                    src=generation/('screens-corrected' if corrected.exists() else 'screens')/(name+'.png')
                    if not src.exists():continue
                    dst=job/(anonymous+'-'+name+'.png');shutil.copyfile(src,dst);attachments.append(dst)
            scores={'type':'object','properties':{name:{'type':'integer','minimum':1,'maximum':5} for name in self.conditions['rubric']},'required':self.conditions['rubric'],'additionalProperties':False}
            item={'type':'object','properties':{'scores':scores,'observations':{'type':'array','items':{'type':'string'}},'limitations':{'type':'array','items':{'type':'string'}}},'required':['scores','observations','limitations'],'additionalProperties':False}
            schema={'type':'object','properties':{'A':item,'B':item,'preference':{'type':'string','enum':['A','B','tie','unverified']},'reason':{'type':'string'}},'required':['A','B','preference','reason'],'additionalProperties':False}
            write(job/'schema.json',schema)
            prompt=('You are an independent UX evaluator. Compare anonymous A/B screenshots for the same synthetic brief. '
                    'Do not inspect source code, other folders or the blind mapping. Use the attached screenshots and fixed operation facts only. '
                    'Judge concrete hierarchy, legibility, priority, finding information, responsive wrapping/density, state feedback and cognitive effort. '
                    'Do not reward decoration or penalize a function solely because it is not visible in the initial image. '
                    'Distinguish screenshot observations from operation facts; no human usability testing or general superiority claims. '
                    'Rate each rubric dimension1-5 using anchors; name the image/state supporting key observations and mention uncertainty. '
                    'You have3minutes. Return the required JSON.\nBRIEF:\n'+self.conditions['inputs'][case]+'\nRUBRIC:\n'+json.dumps(self.conditions['rating_anchors'])+
                    '\nIMAGE ORDER:\n'+json.dumps([p.name for p in attachments])+'\nOPERATION FACTS:\n'+json.dumps(facts,ensure_ascii=False))
            (job/'prompt.txt').write_text(prompt)
            argv=['codex','exec','--ephemeral','--json','--sandbox','read-only','--skip-git-repo-check','--model',self.conditions['model'],
                  '-C',str(job),'--output-schema',str(job/'schema.json'),'--output-last-message',str(job/'rating.json'),'-c','model_reasoning_effort="max"']
            for image in attachments:argv+=['--image',str(image)]
            argv+=['--',prompt]
            result=self.call(argv,job,self.home(job/'codex-home'),job/'events.jsonl',self.conditions['rating_seconds']);write(job/'result.json',result)
            print(json.dumps({'rating':key,**result}),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','generate','ratings']);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=2);args=p.parse_args()
    bench=Benchmark(args.output)
    if args.command=='prepare':bench.prepare()
    elif args.command=='generate':bench.generate(max(1,min(args.workers,2)))
    else:bench.ratings()

if __name__=='__main__':main()
