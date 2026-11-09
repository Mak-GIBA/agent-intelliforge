#!/usr/bin/env python3
"""Opt-in: one <=300s model batch, six fictional cases, isolated CLI writes/readbacks.

Never runs from installation/tests. Needs authenticated Codex and an existing compatible
Basic Memory CLI/PyYAML runtime. No user graph/configuration is modified. No retries.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

SOURCE=Path(__file__).resolve().parents[1]


def run(cli,output,replay_answer=None):
    started=time.monotonic();root=Path(tempfile.mkdtemp(prefix='workgraph-capture-smoke-'))
    codex=root/'codex';policy=codex/'basic-memory-workgraph';policy.mkdir(parents=True)
    work=root/'work';work.mkdir();notes=root/'notes';notes.mkdir();registry=root/'registry';registry.mkdir()
    env={**os.environ,'BASIC_MEMORY_CONFIG_DIR':str(registry),'BASIC_MEMORY_HOME':str(notes),
         'BASIC_MEMORY_DEFAULT_SEARCH_TYPE':'text','HF_HUB_OFFLINE':'1','DR_GAN_CHILD':'1'}
    (registry/'config.json').write_text(json.dumps({'projects':{'fixture':{'path':str(notes),'mode':'local'}},'default_project':'fixture','log_level':'ERROR'}))
    (codex/'basic-memory.json').write_text('{"basicMemory":{"primaryProject":"fixture"}}')
    (policy/'config.json').write_text(json.dumps({'mode':'smart','correctionMode':'scoped','decisionMode':'scoped','caseMode':'progressive','skillMode':'review','recallCli':[str(cli)]}))
    for name in ('workgraph_capture.py','workgraph_recall.py','workgraph_tools.py','workgraph_sequence.py','recall_runtime.py','memory-policy.md'):
        shutil.copyfile(SOURCE/name,policy/name)
    shutil.copytree(SOURCE/'templates',policy/'templates')
    # Seed one pre-existing note. This is fixture setup, never a user memory write.
    (notes/'validations').mkdir()
    (notes/'validations/duplicate.md').write_text('---\ntitle: Synthetic ledger retry limit\ntype: validation\nsharing_scope: private\ntraining_use: excluded\nprivacy_review: pending\n---\n\n## Observations\n- [trigger] Ledger queue rejects the third retry.\n- [procedure] Retry once after acknowledging the old job.\n- [evidence] The synthetic A/B check recovered 4 of 4 rejected jobs; blind retry recovered 0 of 4.\n- [limits] Only the ledger fixture, no throughput claim.\n')
    cases=[
      {'id':'correction','evidence':'A briefing began with per-option details. User requested a comparison and recommendation first for decision makers. The revised output and acceptance are not yet observed. Save only this contextual adjustment, not a global preference.'},
      {'id':'lesson','evidence':'A synthetic worker stayed unhealthy after a documented restart. Experiment: reset the stale readiness marker before restart recovered 3/3 stuck workers; restart alone recovered 0/3. Marker reuse, not restart command availability, was the checked interaction. Cause outside this fixture remains unknown. Useful for other marker-based worker restarts; not proof for unrelated services.'},
      {'id':'decision','evidence':'For this synthetic account project the user explicitly chose optimistic locking over a distributed mutex because contention was measured low and no global ordering was required. Consequence: clients must handle conflicts. Revisit if conflict rate exceeds 2% or global ordering becomes required. Choice is decided by user; implementation benefit and acceptance unknown. Preserve project rationale, not a universal rule.'},
      {'id':'case','evidence':'Synthetic checkout review: assistant output grouped all form fields without steps; user then requested a short address step followed by payment because novices lost their place. No revision or outcome yet. This unfinished sequence is useful to compare staged forms for novice checkout users with the same constraints; no acceptance/adoption claims. Keep two actual observations only.'},
      {'id':'duplicate','evidence':'Same ledger retry limit procedure and identical 4/4 versus 0/4 check as the existing note, with no new condition or evidence.'},
      {'id':'ordinary','evidence':'A routine typo was fixed and the existing tests passed. No correction, non-obvious lesson, project decision or reusable characteristic was observed.'}
    ]
    template=json.loads((SOURCE.parents[1]/'tests/fixtures/progressive-case.json').read_text())
    (root/'cases.json').write_text(json.dumps(cases))
    schema={'type':'object','properties':{'cases':{'type':'array','items':{'type':'object','properties':{
      'id':{'type':'string'},'outcome':{'type':'string','enum':['capture','duplicate','out_of_scope']},
      'candidate':{'type':'string'},'reason':{'type':'string'}},'required':['id','outcome','candidate','reason'],'additionalProperties':False}}},'required':['cases'],'additionalProperties':False}
    schema_path=root/'schema.json';schema_path.write_text(json.dumps(schema));answer=root/'answer.json'
    prompt=('This is one isolated memory capture evaluation. No tools, subagents or external access. '
            'Return JSON decisions and complete candidate JSON strings (empty string for ordinary). '
            'Use only the supplied synthetic evidence. Do not claim user acceptance or actual adoption. '
            'For duplicate supply a validation candidate so the driver exercises duplicate search without writing. '
            'The driver runs the real configured CLI prepare/apply/readback/finish for your output; it never touches the user graph.\n'
            +(SOURCE/'memory-policy.md').read_text()+'\n'+(SOURCE/'templates/CAPTURE_SAVE.md').read_text()
            +'\n'+(SOURCE/'templates/CORRECTIONS.md').read_text()+'\n'+(SOURCE/'templates/CAPTURE.md').read_text()
            +'\nCase v2 shape (replace with the two observed steps and unknown outcome, do not copy unrelated steps):\n'+json.dumps(template)
            +'\nUse distinct titles/query terms; all notes need Observations, Case needs Interaction JSON. Decision metadata: status decided, actor user. '
            'Candidates use exact kind names correction/workflow/decision/case/validation. '
            'Existing note:\n'+(notes/'validations/duplicate.md').read_text()+'\nSix situations:\n'+json.dumps(cases))
    args=['codex','exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--sandbox','read-only',
          '--json','--output-schema',str(schema_path),'--output-last-message',str(answer),'-']
    # Preserve only the selected model/effort, never account credentials or other configuration.
    try:
        import tomllib
        config=tomllib.loads((Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'config.toml').read_text())
        if config.get('model'):args[2:2]=['--model',config['model']]
        if config.get('model_reasoning_effort'):args[2:2]=['-c','model_reasoning_effort='+json.dumps(config['model_reasoning_effort'])]
    except (OSError,ValueError):pass
    if replay_answer:
        shutil.copyfile(replay_answer,answer)
    else:
        process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                                 cwd=root,env=env,start_new_session=True)
        try:
            stdout,stderr=process.communicate(prompt,timeout=max(1,300-(time.monotonic()-started)))
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try:stdout,stderr=process.communicate(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate()
            result={'status':'incomplete','timeout':True,'cases':[],'limit_seconds':300,'retries':0}
            output.write_text(json.dumps(result,indent=2));return result
        (root/'events.jsonl').write_text(stdout);(root/'stderr.txt').write_text(stderr)
        if process.returncode or not answer.exists():
            result={'status':'unavailable','exit_code':process.returncode,'cases':[],'retries':0}
            output.write_text(json.dumps(result,indent=2));return result
    sys.path.insert(0,str(policy));import workgraph_capture as module
    os.environ.update({k:env[k] for k in ('BASIC_MEMORY_CONFIG_DIR','BASIC_MEMORY_HOME','BASIC_MEMORY_DEFAULT_SEARCH_TYPE','HF_HUB_OFFLINE')})
    writer=module.CliWriter([str(cli)]);writer.deadline=started+300
    service=module.Capture(codex,work,writer=writer)
    reports=[];values=json.loads(answer.read_text())['cases'];seen=set()
    for index,row in enumerate(values):
        identity=row['id'];seen.add(identity);ticket=module.recall.digest(['synthetic',identity]);token='c'*64
        (policy/'state').mkdir(exist_ok=True)
        (policy/'state'/(ticket+'.json')).write_text(json.dumps({'version':1,'token':token,'workdir':module.recall.digest(str(work))}))
        report={'id':identity,'model_outcome':row['outcome']}
        try:
            if time.monotonic()-started>=300:raise TimeoutError()
            before={p.relative_to(notes).as_posix():p.read_bytes() for p in notes.rglob('*.md')}
            if row['outcome']=='out_of_scope':
                report['finish']=service.finish(ticket,token,'out_of_scope','implementation')['status']
            else:
                candidate=json.loads(row['candidate']);prepared=service.prepare(candidate)
                decisions=[{'id':m['id'],'decision':'duplicate' if identity=='duplicate' else 'distinct',
                            'reason':'Identical checked procedure' if identity=='duplicate' else 'Different scenario and source evidence'} for m in prepared['matches']]
                result=service.apply(ticket,token,candidate,prepared['review'],decisions,'implementation')
                report['capture']=result['status'];report['finish']=service.finish(ticket,token,'complete','implementation')['status']
            after={p.relative_to(notes).as_posix():p.read_bytes() for p in notes.rglob('*.md')}
            report['new_notes']=len(set(after)-set(before));report['changed_notes']=sum(after.get(k)!=v for k,v in before.items())
        except (ValueError,KeyError,TypeError,OSError,TimeoutError):report['status']='failed'
        reports.append(report)
    expected={'correction':'saved','lesson':'saved','decision':'saved','case':'saved','duplicate':'duplicate','ordinary':None}
    passed=len(values)==6 and seen==set(expected) and all(
        r.get('capture')==expected[r['id']] and r.get('finish')==('out_of_scope' if r['id']=='ordinary' else expected[r['id']])
        and r.get('new_notes')==(1 if expected[r['id']]=='saved' else 0) and r.get('changed_notes')==0 for r in reports)
    result={'status':'passed' if passed else 'incomplete','cases':reports,'notes':len(list(notes.rglob('*.md'))),
            'elapsed_seconds':round(time.monotonic()-started,1),'limit_seconds':300,'retries':0,
            'model_invocations':0 if replay_answer else 1,'replayed_model_output':bool(replay_answer),
            'limits':'One synthetic model batch; driver performs actual CLI writes and readbacks. Does not prove future capture rates, semantic truth, acceptance or the agent independently following the CLI workflow.'}
    output.write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cli',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replay-answer',type=Path,help='Machine-only replay of an existing synthetic answer; never calls a model')
    args=parser.parse_args();result=run(args.cli.resolve(),args.output,args.replay_answer)
    print(json.dumps(result));raise SystemExit(0 if result['status']=='passed' else 2)
