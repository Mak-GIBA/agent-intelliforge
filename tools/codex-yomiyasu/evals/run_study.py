#!/usr/bin/env python3
"""Explicit model study. Never run by installation or offline self-tests.

Every job gets a fresh Codex session. Final text, usage, hashes and non-reasoning
tool receipts are retained; authentication and private reasoning are not exported.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('baseline', 'a', 'b', 'c')
LOCK = threading.Lock()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    tmp.replace(path)

def globals_to_disable():
    roots = [Path.home()/'.agents/skills', Path.home()/'.codex/skills']
    # --ignore-user-config omits the configured plugins. Disable the normal local
    # skills explicitly; cached versions of inactive plugins are not a skill scope.
    return sorted({str(p.resolve()) for root in roots if root.is_dir() for p in root.rglob('SKILL.md')})

def config_args(disabled):
    rows = ','.join('{path='+json.dumps(p)+',enabled=false}' for p in disabled)
    return ['--ignore-user-config', '--ignore-rules', '-c', 'project_doc_max_bytes=0',
            '-c', 'skills.config=['+rows+']']

def prepare(out, sources, upstream):
    try:
        import tomllib
    except ModuleNotFoundError as exc:
        raise ValueError('Study preparation requires Python 3.11+; installation and offline self-tests support Python 3.10+.') from exc
    if out.exists():
        raise ValueError('Use a new output directory')
    cfg = tomllib.loads((Path.home()/'.codex/config.toml').read_text())
    tasks = json.loads((ROOT/'evals/generation-tasks.json').read_text())['tasks']
    contract = {'schema':1, 'created':datetime.now(timezone.utc).isoformat(),
        'model':cfg['model'], 'effort':cfg.get('model_reasoning_effort','medium'),
        'cli_version':subprocess.check_output(['codex','--version'],text=True).strip(),
        'seed':20261011, 'arms':list(ARMS), 'tasks':tasks, 'repeats':2,
        'primary_metric':'Fraction of completed outputs with no meaning errors or requester residue and all three quality scores >=3/4',
        'selection':'Zero critical meaning errors and zero positive-control destruction; select highest primary pass fraction, then lower requester residue, then quality mean, then lower latency/tokens. Native route must pass. No superiority claim for a tie.',
        'grader':'Anonymous separate sessions of the same model; automatic review, not human evaluation',
        'isolation':'Ignore user config/rules, disable AGENTS through project_doc_max_bytes=0, disable existing skill paths per CLI invocation; project-scoped study skills only in native trials',
        'temperature':'Not controlled by the CLI',
        'source_hashes':json.loads((sources/'frozen-sources.json').read_text()),
        'upstream_hashes':{str(p.relative_to(upstream)):sha(p.read_bytes()) for p in sorted(upstream.rglob('*')) if p.is_file()},
        'timeouts':'480 seconds per generation/review job; no automatic retries or replay of completed receipts'}
    out.mkdir(parents=True)
    save(out/'contract.json',contract)
    save(out/'holdout-tasks.json',holdout_tasks())
    # Locations are execution state, excluded from the public evidence by the report writer.
    save(out/'locations.private.json',{'sources':str(sources.resolve()),'upstream':str(upstream.resolve()),'disabled':globals_to_disable()})
    jobs=[]
    for task in tasks:
        for repeat in (1,2):
            for arm in ARMS:
                jobs.append({'task':task['id'],'repeat':repeat,'arm':arm})
    random.Random(contract['seed']).shuffle(jobs)
    save(out/'writing-jobs.json',jobs)
    return contract

def guides(sources, upstream, arm):
    directory=sources/arm/'assets'
    paths=sorted(p for p in directory.rglob('*.md') if p.name not in {'sources.md','AGENTS_APPEND.md'})
    paths += [upstream/'SKILL.upstream.md', *sorted((upstream/'references').rglob('*.md'))]
    return '\n\n'.join('【'+(str(p.relative_to(directory)) if p.is_relative_to(directory) else 'upstream/'+str(p.relative_to(upstream)))+'】\n'+p.read_text() for p in paths)

def execute(prompt, cwd, contract, disabled, native=False, schema=None):
    output=cwd/'final-output.txt'
    argv=['codex','exec',*config_args(disabled),'--ephemeral','--skip-git-repo-check',
        '--sandbox','workspace-write' if native else 'read-only','--model',contract['model'],
        '-c','model_reasoning_effort='+json.dumps(contract['effort']),'--json','--output-last-message',str(output)]
    if schema:
        schema_file=cwd/'output-schema.json';schema_file.write_text(json.dumps(schema))
        argv += ['--output-schema',str(schema_file)]
    argv += ['-']
    start=time.monotonic()
    try:
        result=subprocess.run(argv,input=prompt,cwd=cwd,text=True,capture_output=True,timeout=480)
    except subprocess.TimeoutExpired as exc:
        stdout=exc.stdout.decode(errors='replace') if isinstance(exc.stdout,bytes) else exc.stdout or ''
        stderr=exc.stderr.decode(errors='replace') if isinstance(exc.stderr,bytes) else exc.stderr or ''
        events=[]
        for line in stdout.splitlines():
            try:events.append(json.loads(line))
            except ValueError:pass
        tools=[{k:e['item'][k] for k in ('type','command','exit_code','status','aggregated_output') if k in e['item']}
               for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type') not in {'reasoning','agent_message'}]
        errors=[line for line in stderr.splitlines() if any(word in line.lower() for word in ('reconnect','stream','timeout','usage limit','rate limit','error:'))]
        return {'status':'timeout','elapsed_seconds':round(time.monotonic()-start,2),'prompt_sha256':sha(prompt.encode()),
                'output':output.read_text() if output.exists() else None,'usage':None,'tools':tools,
                'transport_diagnostics':errors[-8:],'event_types':[e.get('type') for e in events[-8:]]}
    events=[]
    for line in result.stdout.splitlines():
        try:events.append(json.loads(line))
        except ValueError:pass
    tools=[]
    for event in events:
        item=event.get('item',{})
        if event.get('type')=='item.completed' and item.get('type') not in {'reasoning','agent_message'}:
            # Actual, bounded command receipts only, never chain-of-thought.
            tools.append({k:item[k] for k in ('type','command','exit_code','status','aggregated_output','server','tool') if k in item})
    usage=next((e.get('usage') for e in reversed(events) if e.get('type')=='turn.completed'),None)
    status='completed' if result.returncode==0 and output.exists() else 'execution_failed'
    if not native and tools:
        status='unexpected_tools'
    if status!='completed':
        # Preserve operational cause without copying potentially private stderr streams.
        known=[line for line in result.stderr.splitlines() if any(word in line.lower() for word in ('usage limit','rate limit','model is not','unsupported','error:'))]
        error='\n'.join(known)[-1200:] or 'No successful final-output receipt'
    else:error=None
    return {'status':status,'elapsed_seconds':round(time.monotonic()-start,2),'prompt_sha256':sha(prompt.encode()),
        'output':output.read_text() if output.exists() else None,'usage':usage,'tools':tools,'error':error}

def check_sources(contract, locations):
    sources=Path(locations['sources']);upstream=Path(locations['upstream'])
    for rel,digest in contract['source_hashes']['files'].items():
        if '__pycache__' in Path(rel).parts or rel.endswith('.pyc'):
            continue  # Historical manifest accidentally captured non-portable caches, not instruction inputs.
        if sha((sources/rel).read_bytes())!=digest:raise ValueError('Frozen study source changed: '+rel)
    for rel,digest in contract['upstream_hashes'].items():
        if sha((upstream/rel).read_bytes())!=digest:raise ValueError('Shared upstream changed: '+rel)
    return sources,upstream

def install_native(cwd, assets, upstream):
    spec=importlib.util.spec_from_file_location('study_installer',ROOT/'installer.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    skills=cwd/'.agents/skills'
    bundle={str(p.relative_to(assets)):p.read_bytes() for p in assets.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    module.assets=lambda:bundle
    module.VERSION='2.0.0-proposal.1' if assets.parent.name=='baseline' else '2.0.0-proposal.2'
    scan=module.conflict_scan
    disabled=set(globals_to_disable())
    def isolated_scan(target, project=None):
        result=scan(target,project)
        result['duplicate_skill']=[p for p in result['duplicate_skill']
            if str((Path(p)/'SKILL.md').resolve()) not in disabled]
        return result
    # Only paths disabled in this trial's CLI are excluded from the duplicate
    # check. The production installer's conflict protection remains unchanged.
    module.conflict_scan=isolated_scan
    # Use the actual installer, including the managed manifest required by lint
    # and diff. A manually copied skill is not the installed runtime under test.
    module.install_selected(skills,module.COMPONENTS,mode='auto',apply=True,
                            source=upstream.parent,project=cwd)
    return skills

def native_tasks():
    full='新入社員向けの技術報告を完成稿にしてください。素材：旧方式は毎回設定を読み込む。新方式は起動時に保持する。待機時間は200 msから150 msへ短縮した。同じ負荷条件。設定変更の反映には再起動が必要。運用担当者が再起動時期を決める。CPU環境は未評価。'
    paragraph='次の文章の段落構成だけを直してください。言い切りの強さや事実は変えないでください。原稿：検索精度は82%から86%になった。費用は月2万円増える。同じ評価データを使った。費用の承認は未決定。推論時間は2倍になった。'
    direct='次の文章は過剰な予防線だけを減らしてください。段落構成と数値は変えないでください。原稿：あくまで参考ですが、処置群は4.4%、対照群は4.1%でした。p値は0.18で、有意差は確認できていません。この結果だけで効果の有無は判断できない点には留意が必要です。'
    return [
        {'id':'N1','prompt':'$yomiyasu '+full,'expected':['yomiyasu','paragraph-writing','japanese-direct-writing']},
        {'id':'N2','prompt':full,'expected':['yomiyasu','paragraph-writing','japanese-direct-writing']},
        {'id':'N3','prompt':'$paragraph-writing '+paragraph,'expected':['paragraph-writing']},
        {'id':'N4','prompt':paragraph,'expected':['paragraph-writing']},
        {'id':'N5','prompt':'$japanese-direct-writing '+direct,'expected':['japanese-direct-writing']},
        {'id':'N6','prompt':direct,'expected':['japanese-direct-writing']},
        {'id':'N7','prompt':'「設定を保存しましした」の誤字だけ直してください。他は変更しないでください。','expected':[]},
        {'id':'N8','prompt':'次のコードだけを、aとbの和を返す形に直してください。説明文は不要です。\ndef add(a, b):\n    return a - b','expected':[]},
    ]

def read_receipts(tools, skills):
    reads={}
    for name in ('yomiyasu','paragraph-writing','japanese-direct-writing'):
        path=skills/name/'SKILL.md'
        marker='name: '+name
        matches=[]
        for item in tools:
            command=item.get('command','')
            text=item.get('aggregated_output','')
            if (str(path) in command or (name+'/SKILL.md' in command)) and path.read_text().strip() in text and item.get('exit_code')==0 and re.search(r'\b(cat|sed|head|python3?|read_file)\b',command):
                matches.append({'command':command,'exit_code':0,'content_sha256':sha(path.read_bytes())})
        if matches:reads[name]=matches
    return reads

def generate_job(out, phase, job, contract, locations):
    identifier=f"{job['task']}-{job['arm']}-{job.get('repeat',1)}"
    receipt=out/phase/(identifier+'.json')
    if receipt.exists():
        status=json.loads(receipt.read_text())['status']
        return identifier,'saved' if status=='completed' else 'retained_'+status
    sources,upstream=check_sources(contract,locations)
    with tempfile.TemporaryDirectory(prefix='yomiyasu-study-') as temp:
        cwd=Path(temp)
        if phase=='native':
            task=next(t for t in native_tasks() if t['id']==job['task'])
            skills=install_native(cwd,sources/job['arm']/'assets',upstream)
            prompt=task['prompt']+'\n送信・インストール・ユーザー設定変更は不要です。完成稿だけを返してください。'
        else:
            tasks=contract['tasks'] if phase=='writing' else json.loads((out/'holdout-tasks.json').read_text())
            task=next(t for t in tasks if t['id']==job['task'])
            prompt=('この比較は文章生成のみ。必要な規則と参照資料は展開済みなので、ツール・ファイル・検索・他のスキルを使わず、完成稿だけ返してください。\n\n'
                    +guides(sources,upstream,job['arm'])+'\n\n【執筆課題】\n'+task['instruction']+'\n'+task['input'])
        result=execute(prompt,cwd,contract,locations['disabled'],native=phase=='native')
        if phase=='native':
            result['reads']=read_receipts(result['tools'],skills)
            actual=set(result['reads']);expected=set(task['expected'])
            result['route_pass']=actual==expected and all(len(rows)==1 for rows in result['reads'].values()) and result['status']=='completed'
            result['expected_reads']=task['expected']
            # Replace only the temporary workspace prefix in actual command receipts.
            result=json.loads(json.dumps(result,ensure_ascii=False).replace(str(cwd),'<workspace>'))
        result.update(job_id=identifier,**job)
        save(receipt,result)
        return identifier,result['status']

def holdout_tasks():
    instruction='原稿を指定された読者向けの完成稿にしてください。意味・情報量・指定形式を保持し、事実や結論を足さないでください。'
    rows=[
        ('H1','report','運用担当者向け。ご指示どおりログ保存を説明します。REQ-21ではログを30日保存しなければならない。通知は任意。保存先は未決定。読みやすくしました。'),
        ('H2','research','研究者向け。要望に沿って説明しました。比較対象は方式CとD、条件は同じ。正解率はCが91%、Dが92%。95%信頼区間は重なる。この比較だけでは差の確実性を判断できない。追加評価もできます。'),
        ('H3','email','メールの宛先への連絡。伊藤様\n\nご依頼いただいた見積書をお送りします。総額は12万円です。11月5日までにご確認ください。\n\n高橋'),
        ('H4','article','AI技術の読者向け。教材の例文は引用として保持する。\n> 「ご依頼のとおりプロンプトを修正しました」\nこの引用は生成文に応答が残る例である。実際のプロンプトは入力と制約を含む。<!-- 編集者へ：後で分かりやすく直す -->'),
        ('H5','manual','管理者向け。初心者にも分かるように整理しました。\n1. `enabled = false`にする。\n2. 設定を保存する。\n再起動は不要。ただし既存の接続には反映しない。既存接続の切断は管理者が判断する。'),
        ('H6','research','研究報告の読者向け。図2：ご指定の粒度で作成した比較図。\n|方式|学習時間|\n|---|---|\n|E|3時間|\n|F|2時間|\n図2の比較では同じGPUを使った。CPUは未評価。[^a]\n[^a]: 本研究は学習時間を比較対象とし、推論時間は測定していない。\n[^b]: 以上のご指示を反映しました。'),
    ]
    return [{'id':i,'genre':g,'instruction':instruction,'input':x} for i,g,x in rows]

GRADE_SCHEMA={'type':'object','properties':{'ratings':{'type':'array','items':{'type':'object','properties':{
    'id':{'type':'string'},'meaning_errors':{'type':'array','items':{'type':'string'}},
    'requester_residue':{'type':'array','items':{'type':'string'}},
    'paragraph':{'type':'integer','minimum':0,'maximum':4},'naturalness':{'type':'integer','minimum':0,'maximum':4},
    'reader_fit':{'type':'integer','minimum':0,'maximum':4},'evidence':{'type':'string'}},
    'required':['id','meaning_errors','requester_residue','paragraph','naturalness','reader_fit','evidence'],'additionalProperties':False}}},
    'required':['ratings'],'additionalProperties':False}

def grade_batch(out, phase, files, batch_id, contract, locations):
    target=out/(phase+'-grades')/(batch_id+'.json')
    if target.exists():
        status=json.loads(target.read_text())['status']
        return batch_id,'saved' if status=='completed' else status
    tasks={t['id']:t for t in (contract['tasks'] if phase=='writing' else json.loads((out/'holdout-tasks.json').read_text()))}
    entries=[];mapping={}
    for i,path in enumerate(files):
        row=json.loads(path.read_text())
        code=f'X{i+1:02}';mapping[code]=path.name
        if row['status']!='completed':raise ValueError('Cannot grade incomplete trial: '+path.name)
        task=tasks[row['task']]
        entries.append({'id':code,'instruction':task['instruction'],'genre':task['genre'],'source':task['input'],
                        'protected_meanings':task.get('must_keep',[]),'final':row['output']})
    prompt=('条件名も生成規則も知らない評価者として、次の原稿/素材と完成稿を採点してください。編集はしないでください。\n'
      '重大な意味変更は、重要情報の脱落・創作・数値/単位/否定/限定/主体/因果/時系列/確信度/義務と推奨/決定と提案の変更です。'
      '制作指示と作業報告の削除、同義の言い換えは意味変更ではありません。新規執筆で許可された素材に基づく解釈は創作ではありません。'
      '保護対象は文字列一致ではなく意味です。メールの受信者への依頼、研究目的、操作指示、引用・コード・数式は正当な内容として保持します。'
      'sourceに与えられた用途・宛先の説明は執筆条件です。引用された悪い例はrequester_residueに数えないでください。'
      'requester_residueには完成稿へ混入したAIへの指示説明、制作報告、自己評価、追加対応の申し出を具体的に列挙します。'
      'paragraph（論点と根拠・順序）、naturalness（自然な日本語・不要な定型/抽象語/水増しがない）、reader_fit（用途と読者に必要な内容）を0〜4で採点します。'
      '0=目的を満たせない、1=大幅修正、2=局所修正が必要、3=そのまま実用可能、4=内容と表現が十分対応。文長や語尾のばらつき、短さ、主観や感情の追加そのものは加点しません。'
      '必ず実際の文と理由を短くevidenceへ示してください。\n'+json.dumps(entries,ensure_ascii=False))
    with tempfile.TemporaryDirectory(prefix='yomiyasu-judge-') as temp:
        result=execute(prompt,Path(temp),contract,locations['disabled'],schema=GRADE_SCHEMA)
    if result['status']=='completed':
        parsed=json.loads(result.pop('output'))
        if {r['id'] for r in parsed['ratings']}!=set(mapping):raise ValueError('Missing/extra judge rows')
        result['ratings']=[{**r,'output_file':mapping[r['id']]} for r in parsed['ratings']]
    save(target,result)
    return batch_id,result['status']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','writing','native','grade','holdout','grade-holdout'])
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--sources',type=Path)
    parser.add_argument('--upstream-dir',type=Path)
    parser.add_argument('--winner',choices=ARMS[1:])
    parser.add_argument('--workers',type=int,default=2,choices=[1,2])
    parser.add_argument('--ready-only',action='store_true',help='Grade only already complete frozen batches; no generation or retries')
    args=parser.parse_args()
    if args.phase=='prepare':
        print(json.dumps(prepare(args.out,args.sources,args.upstream_dir),ensure_ascii=False));return
    contract=json.loads((args.out/'contract.json').read_text());locations=json.loads((args.out/'locations.private.json').read_text())
    check_sources(contract,locations)
    if args.phase in {'grade','grade-holdout'}:
        phase='writing' if args.phase=='grade' else 'holdout'
        files=sorted((args.out/phase).glob('*.json'))
        expected=96 if phase=='writing' else 12
        if not args.ready_only and len(files)!=expected:raise ValueError(f'Expected {expected} complete receipts, got {len(files)}')
        manifest=args.out/(phase+'-grade-jobs.json')
        if not manifest.exists():
            if phase=='writing':
                names=[f"{j['task']}-{j['arm']}-{j['repeat']}.json" for j in json.loads((args.out/'writing-jobs.json').read_text())]
            else:names=[p.name for p in files]
            batches=[]
            batch_size=4 if phase=='holdout' else 12
            for i in range(0,len(names),batch_size):
                batch=names[i:i+batch_size];random.Random(contract['seed']+1+i).shuffle(batch);batches.append(batch)
            save(manifest,batches)
        batches=json.loads(manifest.read_text())
        calls=[([args.out/phase/name for name in batch],f'B{i+1:02}') for i,batch in enumerate(batches)
               if all((args.out/phase/name).exists() for name in batch)]
        function=lambda call:grade_batch(args.out,phase,call[0],call[1],contract,locations)
    else:
        phase=args.phase
        if phase=='writing':jobs=json.loads((args.out/'writing-jobs.json').read_text())
        elif phase=='native':
            jobs=[{'task':t['id'],'arm':a,'repeat':1} for t in native_tasks() for a in ARMS]
            random.Random(contract['seed']+2).shuffle(jobs)
            save(args.out/'native-jobs.json',jobs)
        else:
            if not args.winner:parser.error('--winner is required for holdout')
            jobs=[{'task':t['id'],'arm':a,'repeat':1} for t in holdout_tasks() for a in ('baseline',args.winner)]
            save(args.out/'holdout-jobs.json',jobs)
        calls=jobs
        function=lambda job:generate_job(args.out,phase,job,contract,locations)
    stopped=threading.Event()
    failures=[]
    def guarded(call):
        if stopped.is_set():return 'not-started','cancelled'
        return function(call)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(guarded,call) for call in calls]
        for completed,future in enumerate(as_completed(futures),1):
            try:identifier,status=future.result()
            except Exception:
                stopped.set()
                for pending in futures:pending.cancel()
                raise
            print(f'{args.phase} {completed}/{len(calls)} {identifier}: {status}',flush=True)
            if status not in {'completed','saved'}:
                failures.append((identifier,status))
    if failures:
        print(json.dumps({'status':'COMPLETE_WITH_EXECUTION_FAILURES','retained_failures':failures},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
