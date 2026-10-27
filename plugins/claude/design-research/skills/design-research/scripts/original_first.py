"""Original-first research: source review, isolated preparation, then measured changes.

Enabled only for new original_first_contract_version=1 runs. Old contracts are not
migrated. Parent receipts, fixed inputs and shared budgets govern every stage.
"""
from __future__ import annotations
import contextlib
import copy
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

from runtime import Blocked, atomic_json, regular_path, sha256, test_environment, capture, sandbox_command
from execution_units import digest, unit

KINDS={'builtin','official','official_adapter','faithful','adapted','approximation'}


def active(state):
    return state.get('original_first_contract_version')==1 and state['config']['mode']=='research'


def data(state):
    return state.setdefault('original_first',{'started_at':time.time(),'phase':'original',
                                            'artifacts':[],'experiments':{},'completed':False})


def instructions(role):
    common=('Read references/original-first.md. Original means the actual official implementation or a faithful '
            'implementation of the paper, not an inspired simplified proxy. Complete decisive source reading '
            'before evaluation. Existing model API/login access may replace transport, with differences recorded. '
            'Never claim paper-score reproduction under changed models or conditions. Do not execute, install, '
            'log in or edit project/settings; the parent owns these operations. ')
    return common+{
      'producer-originals': 'Return a minimal source-backed DESIGN dossier for the existing baseline and promising original candidates. '
          'No novel variants yet. Comparison findings are unmeasured, published results are reported, decision provisional/deferred. '
          'Supply exact original SOURCE descriptors. Include source_review.implementation={kind,source_ids,version,method,differences:[],parent_id:""}. '
          'kind is builtin, official, official_adapter or faithful; classify an approximation honestly but it cannot stand in for an original. '
          'paper/repository evidence and detailed reading are completed in the next per-candidate unit.',
      'producer-environment': 'Return the smallest pinned preparation manifest for the source-reviewed candidates. '
          'packages rows: candidate_id,kind=python/node,spec with exact version; repositories: candidate_id,source_id,url,commit (full hash). '
          'Set needs_model and required model features (text/json/tools/multimodal). Freeze a finite max_model_calls for the ENTIRE run, '
          'including probes, original and changed methods; never multiply the budget by stages. Supply no credentials or login actions. '
          'Use the existing configured model access; do not require a new API key when a compatible logged-in CLI works. '
          'Use no OS/global installers, production data or large model/dataset downloads.',
      'reviewer-original': 'Independently inspect the actual original-stage results, fixed thresholds, constraints and executed receipts. '
          'Return proceed=false when originals are sufficient or there are no measured grounds for changing them. '
          'proceed=true needs a concrete observed gap, experiment/artifact evidence_ids and parent_ids of actually measured original candidates. '
          'A failed setup or missing source is not measured inferiority. Literature/design does not need artificial measurements. '
          'Keep original results and explain precisely what a change should address.',
      'planner-adaptation': 'Return PLAN_V2 for a bounded comparison of measured original baseline and changed candidates. '
          'Keep purpose, metrics, tasks, inputs, expected outcomes, controls and model conditions identical. '
          'candidate_ids may add changed IDs; baseline_id must be one actually measured original. '
          'Do not repeat source discovery, original measurements or increase total experiment/time/call budgets.',
      'producer-adaptation': 'Return DESIGN for only the original baseline and changed candidates in the new frozen evaluation. '
          'Each changed candidate needs source_review.implementation kind=adapted/approximation, parent_id from measured originals, '
          'method, source_ids, version and substantive differences. Explain the observed gap it addresses. '
          'Preserve original source identities and source_review. No altered candidate may be labelled official or faithful. '
          'Experiments are planned; actual files/commands are built by the later assets unit.'
    }[role]


def schemas(h):
    return {
      'producer-originals':h.DESIGN,
      'producer-environment':h.obj({'status':h.choice(['ready','blocked']),'reason':h.S,
        'packages':h.arr(h.obj({'candidate_id':h.S,'kind':h.choice(['python','node']),'spec':h.S})),
        'repositories':h.arr(h.obj({'candidate_id':h.S,'source_id':h.S,'url':h.S,'commit':h.S})),
        'needs_model':h.B,'model_features':h.arr(h.S),'max_model_calls':h.I}),
      'reviewer-original':h.obj({'status':h.choice(['reviewed','blocked']),'reason':h.S,'proceed':h.B,
                                'evidence_ids':h.arr(h.S),'parent_ids':h.arr(h.S)}),
      'planner-adaptation':h.PLAN_V2,'producer-adaptation':h.DESIGN}


def saved(h,state,workspace,run_dir,path,value,kind='research_protocol'):
    if value is not None:
        raw=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
        if path.exists() and path.read_text('utf-8')!=raw:
            raise Blocked('Original first: immutable stage artifact changed: '+path.name)
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(raw,'utf-8')
    row={'path':str(path.relative_to(workspace)),'sha256':sha256(path)}
    if row not in data(state)['artifacts']:data(state)['artifacts'].append(row)
    if path.stat().st_size:
        h.add_record(state,workspace,path,kind=kind,description='Original-first '+path.name)
    return row


def call(h,role,state,workspace,run_dir,validator=None,name=None):
    state['phase']=name or role;h.save(state,run_dir)
    result=unit(role,schemas(h)[role],state,workspace,run_dir,h.checked_role,validator,
                name=name or role)
    return result


def implementation(candidate):
    value=candidate.get('source_review',{}).get('implementation',{})
    if (value.get('kind') not in KINDS or not isinstance(value.get('source_ids'),list)
            or any(not isinstance(value.get(k),str) for k in ('version','method','parent_id'))
            or not value.get('method') or not isinstance(value.get('differences'),list)):
        raise Blocked('Original first: candidate needs typed implementation origin: '+candidate['id'])
    return value


def validate_origins(dossier,*,changed=False,parents=()):
    sources={s['id']:s for s in dossier.get('sources',[])}
    for candidate in dossier['candidates']:
        value=implementation(candidate)
        if any(s not in sources for s in value['source_ids']):
            raise Blocked('Original first: implementation references an unknown original source')
        if changed and candidate['id'] not in parents:
            if value['kind'] not in {'adapted','approximation'} or value['parent_id'] not in parents or not value['differences']:
                raise Blocked('Original first: changed method needs measured parent and explicit differences')
        elif value['kind'] in {'adapted','approximation'}:
            raise Blocked('Original first: approximation cannot replace the original stage')
        elif value['kind']=='builtin' and not candidate.get('baseline'):
            raise Blocked('Original first: only the existing baseline may be a source-free builtin')
        elif value['kind'] in {'official','official_adapter'} and (not any(sources[s]['source_type']=='repository' for s in value['source_ids']) or candidate['source_review']['reuse']['strategy'] not in {'direct','wrapper'}):
            raise Blocked('Original first: official use needs an actual repository and direct/wrapper route')
        elif value['kind']=='faithful' and not any(sources[s]['source_type'] in {'paper','preprint'} for s in value['source_ids']):
            raise Blocked('Original first: faithful paper implementation needs the original paper')
        elif value['kind']!='builtin' and (not value['source_ids'] or not value['version']):
            raise Blocked('Original first: original needs exact source/version')


def validate_core(h,value,state):
    h.source_descriptor_format(value.get('sources',[]),state)
    draft=h.nested_dossier(value)
    from dossier import validate_dossier
    result=validate_dossier(draft)
    if not result['valid']:raise Blocked('Original first: invalid source dossier: '+'; '.join(result['errors'][:6]))
    validate_origins(draft)
    if draft['decision']['status'] not in {'provisional','deferred'}:
        raise Blocked('Original first: no adoption decision before original trials')


def prepare(h,state,workspace,run_dir):
    d=data(state)
    if d.get('sources_ready'):return
    if not d.get('source_dossier'):
        value=call(h,'producer-originals',state,workspace,run_dir,lambda v,s:validate_core(h,v,s))
        h.collect_sources(value['sources'],state,workspace,run_dir)
        d['source_dossier']=value;h.save(state,run_dir)
    state['proposal_design']=copy.deepcopy(d['source_dossier'])
    draft=h.nested_dossier(state['proposal_design'])
    for candidate in list(draft['candidates']):
        cid=candidate['id']
        if cid in d.setdefault('reviewed_candidates',[]):continue
        state['unit_task']={'candidate_id':cid,'candidate':candidate,'question':candidate['summary'],
                            'patch_keys':['sources','claims','candidate','comparison']}
        def check(value,current):
            h.patch_format(value,current);preview=copy.deepcopy(draft);h.patch_candidate(preview,value,cid)
            validate_origins(preview)
            from report_contract import assess
            assess(preview,current,require_all=False,verify_access=False)
        value=unit('producer-evidence',h.PATCH,state,workspace,run_dir,h.checked_role,check,
                   name='original-evidence-'+cid)
        h.patch_candidate(draft,value,cid);h.collect_sources(value['sources'],state,workspace,run_dir)
        d['reviewed_candidates'].append(cid)
        d['source_dossier']={**d['source_dossier'],'dossier_json':json.dumps(draft,ensure_ascii=False)}
        state['proposal_design']=copy.deepcopy(d['source_dossier']);h.save(state,run_dir)
    state.pop('unit_task',None)
    from report_contract import assess
    d['adoption_holds']=assess(draft,state)
    holds=assess(draft,state,for_trial=True)
    d['source_holds']=holds
    state['original_first_task']={'candidates':draft['candidates'],'sources':draft['sources'],
                                  'source_holds':holds,'purpose':state['config'].get('evaluation_purpose','auto')}
    manifest=call(h,'producer-environment',state,workspace,run_dir,validate_manifest)
    if manifest['status']!='ready':raise Blocked('Original first: preparation plan blocked: '+manifest['reason'])
    saved(h,state,workspace,run_dir,run_dir/'original-first/preparation.json',manifest)
    d['preparation']=manifest
    prepare_environments(h,state,workspace,run_dir)
    d['sources_ready']=True;state['original_sources']=copy.deepcopy(draft)
    state['original_runtime']={'environments':d['environments'],'unavailable':d['preparation_failures'],'model':d.get('model')}
    state.pop('original_first_task',None);h.save(state,run_dir)


def validate_manifest(value,state):
    candidates={c['id'] for c in h_dossier(state)['candidates']}
    if value['needs_model'] and not 1<=value['max_model_calls']<=10000:
        raise Blocked('Original first: declare a finite model-call budget')
    if value['needs_model'] and (not state['config'].get('allow_model_access') or not 1<=value['max_model_calls']<=state['config'].get('model_call_limit',0)):
        raise Blocked('Original first: model experiments require explicit access and a shared call limit')
    if set(value['model_features'])-{'text','json','tools','multimodal'}:
        raise Blocked('Original first: unsupported model capability')
    for package in value['packages']:
        # Exact registry versions only. Git code is separately pinned and checked out.
        pattern=r'[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9_.+!-]+' if package['kind']=='python' else r'(?:@[\w.-]+/)?[\w.-]+@[0-9][\w.+-]*'
        if package['candidate_id'] not in candidates or not re.fullmatch(pattern,package['spec']):
            raise Blocked('Original first: packages need candidate identity and exact version')
    for repo in value['repositories']:
        from urllib.parse import urlsplit
        url=urlsplit(repo['url'])
        if (repo['candidate_id'] not in candidates or repo['source_id'] not in state.get('sources',{})
                or url.scheme!='https' or url.username or url.password or url.query or url.fragment
                or not re.fullmatch('[0-9a-fA-F]{40,64}',repo['commit'])):
            raise Blocked('Original first: repositories need actual source identity and pinned HTTPS commit')


def h_dossier(state):
    return json.loads(data(state)['source_dossier']['dossier_json'])


def remaining(state):
    value=data(state)['started_at']+state['config']['phase_timeout']-time.time()
    if value<=0:raise Blocked('Original first: shared preparation/experiment deadline exhausted')
    return value


def prepare_environments(h,state,workspace,run_dir):
    d=data(state);manifest=d['preparation'];root=run_dir/'original-first/environments'
    d.setdefault('environments',{});d.setdefault('preparation_failures',{})
    attempts=d.setdefault('preparation_attempts',{})
    for candidate in h_dossier(state)['candidates']:
        cid=candidate['id']
        if cid in d['environments'] or cid in d['preparation_failures']:continue
        if cid in attempts:
            d['preparation_failures'][cid]='Interrupted preparation; preserve files and inspect receipts before a new run'
            h.save(state,run_dir);continue
        if d['source_holds'].get(cid):
            d['preparation_failures'][cid]='; '.join(d['source_holds'][cid]);continue
        packages=[p for p in manifest['packages'] if p['candidate_id']==cid]
        repos=[r for r in manifest['repositories'] if r['candidate_id']==cid]
        if (packages or repos) and not state['config']['allow_network']:
            d['preparation_failures'][cid]='External preparation unavailable offline; not a performance failure';continue
        path=root/cid;path.mkdir(parents=True,exist_ok=True)
        attempts[cid]={'status':'started','directory':str(path)};h.save(state,run_dir)
        env=test_environment(path)
        commands=[]
        if any(p['kind']=='python' for p in packages):
            commands += [[sys.executable,'-m','venv',str(path/'python')],
                         [str(path/'python/bin/python'),'-m','pip','wheel','--disable-pip-version-check',
                          '--wheel-dir',str(path/'wheels'),*[p['spec'] for p in packages if p['kind']=='python']],
                         [str(path/'python/bin/python'),'-m','pip','install','--disable-pip-version-check',
                          '--no-index','--find-links',str(path/'wheels'),
                          *[p['spec'] for p in packages if p['kind']=='python']],
                         [str(path/'python/bin/python'),'-m','pip','freeze','--all']]
        if any(p['kind']=='node' for p in packages):
            commands += [['npm','install','--prefix',str(path/'node'),'--no-audit','--no-fund',
                          *[p['spec'] for p in packages if p['kind']=='node']]]
        for repo in repos:
            dest=path/'repositories'/repo['source_id'];dest.parent.mkdir(parents=True,exist_ok=True)
            commands += [['git','init',str(dest)],['git','-C',str(dest),'fetch','--depth','1',repo['url'],repo['commit']],
                         ['git','-C',str(dest),'checkout','--detach','FETCH_HEAD']]
        receipts=[]
        try:
            for i,argv in enumerate(commands):
                result=capture(sandbox_command('workspace-write',state['config']['allow_network'],argv),
                    cwd=path,env=env,directory=path/f'setup-{i}',timeout=min(remaining(state),state['config']['phase_timeout']),label='prepare '+cid)
                receipts.append({'argv':argv,**result})
                for output in result['paths'].values():
                    output=Path(output)
                    saved(h,state,workspace,run_dir,output,None,'preparation_output')
                if result['exit_code'] or result['timed_out']:
                    raise Blocked('Isolated preparation failed; not measured inferiority')
            for repo in repos:
                dest=path/'repositories'/repo['source_id']
                result=capture(['git','-C',str(dest),'rev-parse','HEAD'],cwd=path,env=env,
                               directory=path/('verify-'+repo['source_id']),timeout=min(remaining(state),10),label='verify checkout')
                if Path(result['paths']['stdout']).read_text(encoding="utf-8").strip().lower()!=repo['commit'].lower():
                    raise Blocked('Checkout differs from the pinned original')
            record={'candidate_id':cid,'packages':packages,'repositories':repos,
                    'python':str(path/'python/bin/python') if any(p['kind']=='python' for p in packages) else sys.executable,
                    'node_modules':str(path/'node/node_modules'),'directory':str(path),'receipts':receipts,
                    'dependency_files':[{'path':str(p.relative_to(workspace)),'sha256':sha256(p)}
                        for p in sorted([*path.glob('wheels/*.whl'),*path.glob('node/package-lock.json')])]}
            saved(h,state,workspace,run_dir,path/'manifest.json',record,'preparation')
            d['environments'][cid]=record
            attempts[cid]['status']='complete'
        except (Blocked,OSError) as exc:
            d['preparation_failures'][cid]=str(exc)
            attempts[cid]['status']='failed'
        h.save(state,run_dir)
    if manifest['needs_model']:
        prepare_model(h,state,workspace,run_dir)


def check_plan(plan,state):
    if not active(state) or data(state)['phase']=='adaptation':return
    d=data(state);contract=json.loads(plan['evaluation_json'])
    available=set(d['environments'])
    if not set(contract['candidate_ids'])<=available:
        raise Blocked('Original first: evaluation must use reviewed, ready originals; unavailable candidates stay unverified')


def attach_origin(value,state):
    if not active(state):return
    d=data(state)
    if not d.get('source_dossier'):return
    draft=json.loads(value['dossier_json']);known={c['id']:c for c in h_dossier(state)['candidates']}
    fixed_sources={s['id']:s for s in h_dossier(state).get('sources',[])}
    for source in draft.get('sources',[]):
        fixed=fixed_sources.get(source['id'])
        if fixed:
            if any(source.get(k)!=fixed.get(k) for k in ('title','url','source_type','version')):
                raise Blocked('Original first: original source identity changed')
            source.update(copy.deepcopy(fixed))
    for candidate in draft['candidates']:
        if candidate['id'] in known:
            candidate['source_review']=copy.deepcopy(known[candidate['id']]['source_review'])
    validate_origins(draft,changed=d['phase']=='adaptation',parents=set(d.get('original_ids',known)))
    value['dossier_json']=json.dumps(draft,ensure_ascii=False)


@contextlib.contextmanager
def experiment_context(h,state,workspace,run_dir,scratch,env):
    if not active(state):yield env,False;return
    d=data(state);remaining(state)
    path=scratch/'.dr';path.mkdir()
    mapping={**d['environments']}
    for cid,parent in d.get('adaptation_parents',{}).items():mapping[cid]=mapping[parent]
    atomic_json(path/'runtimes.json',mapping)
    env.update(DR_RUNTIMES=str(path/'runtimes.json'),PYTHONPATH=str(Path(__file__).parent))
    if d['phase']=='adaptation':
        baseline=baseline_results(state,workspace)
        atomic_json(path/'original-results.json',baseline)
        env['DR_ORIGINAL_RESULTS']=str(path/'original-results.json')
    if not d['preparation']['needs_model']:yield env,False;return
    from model_access import resolve,public_connection,ModelAccess
    connection=resolve(state['config'],backend=d.get('model_selector'))
    if public_connection(connection)!=d['model']:raise Blocked('Original first: model connection changed; start a new comparison')
    access=ModelAccess(connection,run_dir/'original-first/model-access',
                       max_calls=d['preparation']['max_model_calls'],
                       deadline=d['started_at']+state['config']['phase_timeout'],timeout=state['config']['phase_timeout'])
    with access.bridge() as config:
        env.update(config);yield env,True
    d['model_usage']={'path':str(access.path.relative_to(workspace)),'sha256':sha256(access.path)}
    # Usage is mutable during the run; freeze/export it only once experiments finish.


def reserve_experiment(state,experiment_id):
    if not active(state):return
    d=data(state);keys=d['experiments'].setdefault(str(state['iteration']),[])
    key=d['phase']+':'+experiment_id
    if key not in keys:
        if len(keys)>=3:raise Blocked('Original first: shared three-experiment allowance exhausted')
        keys.append(key)


def baseline_results(state,workspace):
    d=data(state);record=d['original_snapshot'];baseline=state['evaluation_contract']['baseline_id']
    tasks={};trials=[]
    for row in record['result_artifacts']:
        path=Path(workspace)/row['path']
        if sha256(path)!=row['sha256']:raise Blocked('Original first: original output changed')
        value=json.loads(path.read_text('utf-8'))
        for task in value['tasks']:tasks[task['id']]=task
        trials += [t for t in value['trials'] if t['candidate_id']==baseline]
    if not trials:raise Blocked('Original first: baseline has no measured original outputs')
    return {'contract_sha256':state['evaluation_contract_sha256'],'tasks':list(tasks.values()),'trials':trials,
            'reused_from':record['result_artifacts']}


def verify_reused(data_value,state,workspace):
    if not active(state) or data(state)['phase']!='adaptation':return
    baseline=state['evaluation_contract']['baseline_id']
    wanted=baseline_results(state,workspace)['trials']
    actual=[t for t in data_value['trials'] if t['candidate_id']==baseline]
    key=lambda t:(t['task_id'],t['trial_id'],t['candidate_id'])
    if sorted(actual,key=key)!=sorted(wanted,key=key):
        raise Blocked('Original first: reused baseline differs from actual original outputs')


def after_results(h,state,workspace,run_dir,call_unit):
    """Return True only when a new adaptation stage was frozen and must execute next."""
    if not active(state):return False
    d=data(state)
    if d.get('completed'):return False
    summary=copy.deepcopy(state.get('evaluation_summary',{}))
    draft=h.nested_dossier(state['proposal_design'])
    paths={r['path']:r for r in state['evidence'].values() if r.get('kind')=='artifact'}
    result_paths=draft.get('evaluation_result',{}).get('artifact_paths',[])
    if summary.get('status')=='measured' and not result_paths:
        result_paths=sorted({r['artifact_path'] for r in summary.get('trials',[])})
    snapshot={'contract':copy.deepcopy(state['evaluation_contract']),'plan':copy.deepcopy(state['plan']),
              'summary':summary,'dossier':draft,'result_artifacts':[{'path':p,'sha256':paths[p]['sha256']} for p in result_paths if p in paths]}
    if d['phase']=='original':
        d['original_snapshot']=snapshot;d['original_ids']=[c['id'] for c in draft['candidates']]
        saved(h,state,workspace,run_dir,run_dir/'original-first/original-results.json',snapshot)
        state['original_first_task']={'original':snapshot,'remaining_experiments':3-len(d['experiments'].get(str(state['iteration']),[]))}
        decision=call(h,'reviewer-original',state,workspace,run_dir)
        if decision['status']!='reviewed':raise Blocked('Original first: original-stage review incomplete')
        if decision['proceed']:
            if (summary.get('status')!='measured' or not decision['reason'].strip() or not decision['evidence_ids']
                    or not decision['parent_ids'] or not set(decision['parent_ids'])<=set(d['original_ids'])
                    or any(state['evidence'].get(i,{}).get('kind') not in {'experiment','artifact'} for i in decision['evidence_ids'])):
                raise Blocked('Original first: adaptation needs a measured gap and original parent evidence')
        saved(h,state,workspace,run_dir,run_dir/'original-first/change-decision.json',decision)
        d['change_decision']=decision;h.save(state,run_dir)
        if not decision['proceed']:
            d['completed']=True;state.pop('original_first_task',None);finalize(h,state,workspace,run_dir);return False
        plan=call(h,'planner-adaptation',state,workspace,run_dir)
        new=json.loads(plan['evaluation_json']);old=snapshot['contract']
        for key in ('purpose','tasks','task_manifest','metrics','controls','dataset'):
            if new.get(key)!=old.get(key):raise Blocked('Original first: adaptation changed frozen common conditions: '+key)
        if new['baseline_id'] not in decision['parent_ids'] or not set(old['candidate_ids']).isdisjoint(set(new['candidate_ids'])-{new['baseline_id']}):
            raise Blocked('Original first: changed candidates need new identities and an original baseline')
        if plan['criteria']!=snapshot['plan']['criteria'] or plan['test_commands']!=snapshot['plan']['test_commands']:
            raise Blocked('Original first: adaptation changed the frozen criteria or backend checks')
        d['pending_adaptation_plan']=plan;h.save(state,run_dir)
        resume_transition(h,state,workspace,run_dir)
        return True
    saved(h,state,workspace,run_dir,run_dir/'original-first/adaptation-results.json',snapshot)
    d['completed']=True;finalize(h,state,workspace,run_dir);return False


def resume_transition(h,state,workspace,run_dir):
    d=data(state)
    if not d.get('pending_adaptation_plan'):return
    plan=d['pending_adaptation_plan']
    state['plan']=copy.deepcopy(plan);state.pop('evaluation_contract_sha256',None)
    from evaluation_contract import freeze
    freeze(state);d['phase']='adaptation'
    state['original_first_task']={'original':d['original_snapshot'],'decision':d['change_decision'],
        'baseline_reuse':'Read DR_ORIGINAL_RESULTS at execution; preserve its trial rows exactly. Do not rerun the baseline.'}
    h.save(state,run_dir)
    changed=call(h,'producer-adaptation',state,workspace,run_dir,lambda v,s:h.design_format(v,s),
                 name='adaptation-producer-design')
    baseline=state['evaluation_contract']['baseline_id']
    draft=h.nested_dossier(changed)
    d['adaptation_parents']={c['id']:implementation(c)['parent_id'] for c in draft['candidates'] if c['id']!=baseline}
    checkpoints=state['producer_checkpoints'][str(state['iteration'])]
    checkpoints.update(design=changed,design_sha256=__import__('hashlib').sha256(json.dumps(changed,sort_keys=True).encode()).hexdigest())
    checkpoints.pop('assets',None);checkpoints.pop('assets_sha256',None)
    # Source/measurement units remain complete. Final review/presentation will use the changed cohort.
    for row in state.get('units',{}).values():
        if row.get('status')=='pending':
            row.update(required=False,status='superseded',superseded_by='adaptation-stage final review')
    state['proposal_design']=copy.deepcopy(changed)
    state.pop('evaluation_summary',None);state.pop('evaluation_review_bound',None)
    state.pop('original_first_task',None);d.pop('pending_adaptation_plan')
    h.save(state,run_dir)


def finalize(h,state,workspace,run_dir):
    if not active(state):return
    d=data(state)
    if d.get('model_usage'):
        row=d['model_usage']
        path=Path(workspace)/row['path']
        if sha256(path)!=row['sha256']:raise Blocked('Original first: model ledger changed')
        if row not in d['artifacts']:d['artifacts'].append(row)
    audit={'phase':d['phase'],'completed':d['completed'],'model':d.get('model'),
           'preparation_failures':d['preparation_failures'],
           'original_summary':d.get('original_snapshot',{}).get('summary'),
           'change_decision':d.get('change_decision'),'adaptation_parents':d.get('adaptation_parents',{}),
           'experiments':d['experiments']}
    saved(h,state,workspace,run_dir,run_dir/'original-first/research-audit.json',audit)
    d['audit']=audit


def prepare_model(h,state,workspace,run_dir):
    from model_access import resolve,public_connection,ModelAccess
    d=data(state)
    if d.get('model'):return
    manifest=d['preparation'];probes=d.setdefault('model_probes',[])
    def selected(connection,selector):
        identity=public_connection(connection)
        d['model']=identity;d['model_selector']=selector
        target=run_dir/'original-first/model-access/ledger.json'
        seed={'schema_version':1,'connection':identity,'max_calls':manifest['max_model_calls'],
              'calls':[{**row,'phase':'probe'} for p in probes for row in p['calls']]}
        atomic_json(target,seed);h.save(state,run_dir)
    for probe in probes:
        if probe.get('success'):
            connection=resolve(state['config'],backend=probe.get('selector'))
            if public_connection(connection)!=probe['connection']:
                raise Blocked('Original first: model changed after successful probe')
            selected(connection,probe.get('selector'));return
    selectors=[None]
    if not state['config'].get('model_connection_file') and shutil.which('codex'):
        selectors.append('codex')
    for selector in selectors:
        if len(probes)>=min(2,manifest['max_model_calls']):break
        try:connection=resolve(state['config'],backend=selector)
        except (Blocked,OSError,ValueError):continue
        identity=public_connection(connection)
        if any(p['connection']==identity for p in probes):continue
        if set(manifest['model_features'])-set(connection['capabilities']):continue
        directory=run_dir/'original-first/model-probes'/str(len(probes)+1)
        access=ModelAccess(connection,directory,max_calls=1,deadline=d['started_at']+state['config']['phase_timeout'],timeout=min(60,remaining(state)))
        probe={'connection':identity,'selector':selector,'success':False,
               'calls':[{'status':'started','effective_model':connection['model']}]}
        probes.append(probe);h.save(state,run_dir)
        try:
            access.request({'model':connection['model'],'messages':[{'role':'user','content':'Reply with OK only.'}]})
            success=True
        except Exception:success=False
        probe.update(success=success,calls=copy.deepcopy(access.ledger['calls']))
        saved(h,state,workspace,run_dir,directory/'probe.json',probes[-1],'model_probe')
        h.save(state,run_dir)
        if success:
            selected(connection,selector);return
    raise Blocked('Original first: no compatible working API/login transport; candidates remain unverified')

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
