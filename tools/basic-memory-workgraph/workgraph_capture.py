#!/usr/bin/env python3
"""Guarded automatic capture, readback receipts and bounded turn diagnostics."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
import workgraph_recall as recall
import workgraph_tools as tools

FOLDERS={'rule':'rules','workflow':'workflows','validation':'validations',
         'correction':'corrections','case':'cases','decision':'codex/decisions'}
GATES={'rule':('transfer','utility','evidence','durability','added_value'),
       'workflow':('transfer','utility','evidence','durability','added_value'),
       'validation':('transfer','utility','evidence','durability','added_value'),
       'correction':('context','mismatch','requested','evidence'),
       'decision':('context','actor','choice','alternatives','rationale','consequences','revisit','evidence'),
       'case':('context','reusable_feature','evidence','limits')}
OUTCOMES={'saved','updated','duplicate','out_of_scope','no_candidate','pending','failed','not_evaluated'}


def note_value(value):
    """Core adds a permalink and normalizes whitespace; other fields must survive."""
    note=tools.parse_note(value,'candidate.md')
    return {'metadata':{k:v for k,v in note.metadata.items() if k!='permalink'},'body':note.body.strip()}


class CliWriter(recall.CliReader):
    deadline=None
    def run(self,args,deadline):
        return super().run(args,min(deadline,self.deadline) if self.deadline else deadline)
    def write(self,project,note,folder,checksum=None):
        args=['write-note','--project',project,'--title',note.metadata['title'],'--folder',folder]
        if checksum:args+=['--overwrite','--expected-checksum',checksum]
        # Even a nonzero exit may follow a committed write. Caller must read back.
        try:
            remaining=min(25,self.deadline-time.monotonic()) if self.deadline else 25
            if remaining<=0:return None
            result=subprocess.run([*self.command,'tool',*args],input=note.render(),capture_output=True,
                                  text=True,timeout=remaining,env={**os.environ,'BASIC_MEMORY_DEFAULT_SEARCH_TYPE':'text'})
            if result.returncode:return None
            value=json.loads(result.stdout)
            return value if isinstance(value,dict) and not value.get('error') else None
        except (OSError,ValueError,subprocess.TimeoutExpired):return None


class Capture:
    def __init__(self,codex_dir,workdir=None,reader=None,writer=None):
        self.recall=recall.Recall(codex_dir,reader,workdir)
        self.root=self.recall.root;self.workdir=self.recall.workdir;self.writer=writer
    def config(self):
        self.recall.root=self.root
        value=self.recall.config()
        for key,allowed,default in (('mode',('smart','always','off'),'smart'),('correctionMode',('off','scoped'),'off'),
                                    ('decisionMode',('off','scoped'),'off'),('caseMode',('off','reusable','progressive'),'off'),
                                    ('skillMode',('off','review','auto'),'review')):
            if value.get(key,default) not in allowed:raise ValueError('Invalid capture configuration')
        self.policy()
        return value
    def policy(self):
        path=self.root/'memory-policy.md'
        if not path.is_file():path=self.root/'assets/memory-policy.md'
        text=recall.safe_path(path).read_text(encoding='utf-8')
        if not text.strip():raise ValueError('Capture policy unavailable')
        return text
    def backend(self):
        self.recall.root=self.root
        return self.recall.backend()
    def scope(self):return recall.repository_scope(self.workdir)
    def writable(self,mode):
        if mode!='implementation' or self.config().get('mode','smart')=='off':
            raise ValueError('Implementation mode and enabled automatic capture required')
    def authorize(self,ticket,token,mode):
        self.writable(mode)
        if not re.fullmatch('[a-f0-9]{64}',ticket):raise ValueError('Invalid turn')
        state=recall.object_file(recall.safe_path(self.root/'state'/(ticket+'.json')))
        if (not isinstance(token,str) or not secrets.compare_digest(state.get('token',''),token)
                or state.get('version')!=1 or state.get('finished')):raise ValueError('Invalid, stale or finished turn')
        if state.get('workdir') and state['workdir']!=recall.digest(str(self.workdir)):raise ValueError('Wrong task directory')
        return state
    @contextmanager
    def lock(self):
        directory=recall.safe_path(self.root/'state');directory.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd=os.open(directory/'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'r+') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX);yield
    def task_path(self,ticket):
        if not re.fullmatch('[a-f0-9]{64}',ticket):raise ValueError('Invalid turn')
        return recall.safe_path(self.workdir/'.workgraph-capture'/(ticket+'.json'))
    def record(self,ticket,receipt):
        path=self.task_path(ticket)
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        ignored=path.parent/'.gitignore'
        if not ignored.exists():
            fd=os.open(ignored,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as stream:stream.write('*\n')
        state=recall.object_file(path) if path.exists() else {'receipts':{}}
        state['receipts'][receipt['candidate']]=receipt
        recall.atomic(path,state)
    def candidate(self,data):
        if not isinstance(data,dict):raise ValueError('Candidate must be an object')
        kind=data.get('kind');gates=GATES.get(kind)
        if not gates:raise ValueError('Unsupported automatic note type')
        config=self.config()
        mode_key={'correction':'correctionMode','decision':'decisionMode','case':'caseMode'}.get(kind)
        if config.get('mode','smart')=='off' or mode_key and config.get(mode_key,'off')=='off':
            raise ValueError('Automatic capture of this note type is off')
        admission=data.get('admission',{})
        if kind=='rule' and admission.get('category')=='future_preference':gates=('context','instruction','evidence','exceptions')
        if any(not recall.safe_text(admission.get(key),2000) for key in gates):raise ValueError('Incomplete admission evidence')
        content=recall.safe_text(data.get('note'),30000);tools.screen(content)
        note=tools.parse_note(content,'candidate.md');meta=note.metadata
        if meta['type']!=kind or not meta['title'].strip() or len(meta['title'])>180 or re.search(r'[/\\\r\n]',meta['title']):raise ValueError('Candidate type/title mismatch')
        if any(meta.get(k,v)!=v for k,v in {'sharing_scope':'private','training_use':'excluded','privacy_review':'pending'}.items()):
            raise ValueError('Automatic capture requires private/excluded/pending; no sharing approval inferred')
        meta.update(sharing_scope='private',training_use='excluded',privacy_review='pending')
        meta.pop('review_sha256',None);meta.pop('permalink',None)
        if meta.get('integrity_status')=='checked':raise ValueError('New content cannot self-certify integrity')
        if kind in ('case','decision') or meta.get('scope')=='project':
            if meta.get('repository',self.scope())!=self.scope():raise ValueError('Wrong repository scope')
            meta.update(scope='project',repository=self.scope())
        if kind=='decision':
            if meta.get('status') not in ('proposed','decided','superseded'):raise ValueError('Decision status required')
            if meta.get('actor') not in ('user','agent','team'):raise ValueError('Decision actor required')
            if meta.get('verification','unknown') not in ('unknown','partial','verified'):raise ValueError('Invalid verification')
            meta.setdefault('verification','unknown');meta.setdefault('acceptance','unknown')
            if meta['acceptance'] not in ('unknown','accepted','rejected'):raise ValueError('Invalid acceptance')
            if meta['acceptance']!='unknown' and not recall.safe_text(admission.get('acceptance_evidence'),2000):raise ValueError('Explicit acceptance evidence required')
            if meta['verification']!='unknown' and not recall.safe_text(admission.get('verification_evidence'),2000):raise ValueError('Checked property evidence required')
            section='## Decision\n'+''.join('- ['+key+'] '+admission[key].strip()+'\n' for key in GATES['decision'])
            if re.search(r'^## Decision\s*$',note.body,re.M):
                existing=re.findall(r'^## Decision\s*\n(.*?)(?=^## |\Z)',note.body,re.M|re.S)
                if len(existing)!=1:raise ValueError('Expected one Decision section')
                for key in GATES['decision']:
                    fields=re.findall(r'^- \['+key+r'\] (.+)$',existing[0],re.M)
                    if len(fields)!=1 or not fields[0].strip():raise ValueError('Decision body must retain every reviewed evidence field')
            else:note.body=note.body.rstrip()+'\n\n'+section
        if kind=='case':
            tools.interaction(note)
            if meta.get('case_format_version')!=2:raise ValueError('New automatic Cases require v2')
            if config.get('caseMode')=='reusable' and tools.interaction(note)['outcome'] not in ('partial','verified'):
                raise ValueError('Reusable mode requires an observed result; use progressive for unfinished Cases')
            meta.setdefault('integrity_status','unreviewed')
        if '## Observations' not in note.body:raise ValueError('Missing searchable observations')
        relations=re.findall(r'^## Relations\s*\n(.*?)(?=^## |\Z)',note.body,re.M|re.S)
        links=[]
        for section in relations:
            for line in section.splitlines():
                if not line.strip():continue
                match=re.fullmatch(r'- (learned_from|generalized_to|implements|validated_by|packaged_as) \[\[([^\]\n]+)\]\]',line)
                if not match:raise ValueError('Invalid typed relation')
                if match[1]=='packaged_as':raise ValueError('Skill registration uses its dedicated reviewed workflow')
                links.append(recall.safe_text(match[2],300))
        query=recall.safe_text(data.get('query'),180)
        if not query:raise ValueError('Same-concept search terms required')
        action=data.get('action','create')
        if action not in ('create','update'):raise ValueError('Invalid action')
        if action=='update' and not recall.safe_text(data.get('target'),300):raise ValueError('Update target required')
        return note,query,links
    def prepare(self,data):
        note,query,links=self.candidate(data);settings=self.recall.memory_settings()
        project=settings.get('primaryProject')
        if not isinstance(project,str) or not project:raise ValueError('Missing primary memory project')
        reader=self.backend();deadline=time.monotonic()+20;matches=[]
        projects=list(dict.fromkeys([project,*settings.get('secondaryProjects',[])]))
        for source in projects:
            rows=reader.search(source,query,11,deadline)
            if query!=note.metadata['title']:rows+=reader.search(source,note.metadata['title'],11,deadline)
            for row in rows:
                identifier=row.get('permalink')
                if not isinstance(identifier,str):raise ValueError('Invalid search result')
                if any(m['id']==source+':'+identifier for m in matches):continue
                if len(matches)>=10:raise ValueError('Too many duplicate candidates; refine query')
                value=reader.read(source,identifier,deadline)
                body=recall.safe_text(value.get('content'),40000);tools.screen(body)
                matches.append({'id':source+':'+identifier,'project':source,'identifier':identifier,
                                'fingerprint':recall.digest(value),'content':body})
            if len(matches)>10:raise ValueError('Too many duplicate candidates; refine query')
        target=data.get('target')
        if data.get('action')=='update' and not any(m['identifier']==target and m['project']==project for m in matches):
            value=reader.read(project,target,deadline);body=recall.safe_text(value.get('content'),40000);tools.screen(body)
            matches.append({'id':project+':'+target,'project':project,'identifier':target,'fingerprint':recall.digest(value),'content':body})
        for identifier in links:reader.read(project,identifier,deadline)
        identity=recall.digest([data,self.scope(),project])
        review=recall.digest([identity,self.config(),self.policy(),matches])
        return {'status':'ready','candidate':identity,'review':review,'project':project,'matches':matches,
                'limits':'Agent must assess evidence, scope, duplicates and preserved content; checks do not prove semantic truth.'}
    def apply(self,ticket,token,data,review,decisions,mode):
        self.authorize(ticket,token,mode)
        with self.lock():
            self.authorize(ticket,token,mode)
            prepared=self.prepare(data)
            if prepared['review']!=review:raise ValueError('Search/configuration changed; prepare and review again')
            offered={item['id']:item for item in decisions}
            if len(offered)!=len(decisions) or set(offered)!={m['id'] for m in prepared['matches']}:
                raise ValueError('Review every same-concept search match')
            for item in offered.values():
                if item.get('decision') not in ('distinct','duplicate','update') or not recall.safe_text(item.get('reason'),1000):
                    raise ValueError('Each match needs a semantic decision and reason')
            note,_,_=self.candidate(data);project=prepared['project'];identity=prepared['candidate']
            receipt={'candidate':identity,'kind':data['kind'],'status':'pending'}
            duplicates=[m for m in prepared['matches'] if offered[m['id']]['decision']=='duplicate']
            if duplicates:
                if data.get('action','create')!='create':raise ValueError('Duplicate requires no update')
                receipt.update(status='duplicate',references=[{'project':m['project'],'identifier':m['identifier'],'fingerprint':m['fingerprint']} for m in duplicates])
                self.record(ticket,receipt);return receipt
            action=data.get('action','create');target=data.get('target');checksum=None
            updates=[m for m in prepared['matches'] if offered[m['id']]['decision']=='update']
            if action=='update':
                if len(updates)!=1 or updates[0]['identifier']!=target or updates[0]['project']!=project:raise ValueError('Choose the exact update target')
                previous=tools.parse_note(updates[0]['content'],'existing.md')
                if previous.metadata.get('sharing_scope','private')!='private' or previous.metadata.get('training_use','excluded')!='excluded':
                    raise ValueError('Automatic update of shared/training-approved notes refused')
                if previous.metadata['title']!=note.metadata['title'] or previous.metadata['type']!=note.metadata['type']:
                    raise ValueError('Update must preserve note identity and type')
                if previous.metadata.get('integrity_status')=='needs_review':raise ValueError('Use the grounded audit/repair workflow for a flagged note')
                if data['kind'] in ('case','decision') and previous.metadata.get('repository')!=self.scope():
                    raise ValueError('Update target belongs to another or unknown repository')
                if note_value(updates[0]['content'])==note_value(note.render()):
                    receipt.update(status='duplicate',references=[{k:updates[0][k] for k in ('project','identifier','fingerprint')}])
                    self.record(ticket,receipt);return receipt
                if not recall.safe_text(data.get('change_evidence'),2000):raise ValueError('Material change evidence required')
            elif updates:raise ValueError('Create cannot overwrite a reviewed match')
            writer=self.writer or CliWriter(self.config().get('recallCli'))
            if action=='update':
                current=writer.read(project,target,time.monotonic()+20)
                if note_value(current['content'])!=note_value(updates[0]['content']):raise ValueError('Concurrent update; review again')
                checksum=current.get('checksum')
                if not checksum:raise ValueError('Backend provides no conditional-write checksum')
            self.record(ticket,receipt)  # No note content or admission prose in task state.
            writer.write(project,note,FOLDERS[data['kind']],checksum)
            # Never retry a write here: CLI failures can occur after a committed write.
            try:
                if action=='create':
                    rows=self.backend().search(project,note.metadata['title'],11,time.monotonic()+20)
                    candidates=[r['permalink'] for r in rows if r.get('title')==note.metadata['title']]
                    if len(candidates)!=1:raise ValueError('Cannot identify the written note uniquely')
                    target=candidates[0]
                actual=self.backend().read(project,target,time.monotonic()+20)
                if note_value(actual['content'])!=note_value(note.render()):raise ValueError('Readback content mismatch')
                self.candidate({**data,'note':actual['content']})
                receipt.update(status='updated' if action=='update' else 'saved',references=[{'project':project,'identifier':target,'fingerprint':recall.digest(actual)}])
            except (OSError,ValueError,TypeError,KeyError,ImportError,subprocess.TimeoutExpired):
                receipt['status']='failed'
            self.record(ticket,receipt)
            return receipt
    def diagnose(self,ticket,outcome,kinds):
        if not re.fullmatch('[a-f0-9]{64}',ticket) or outcome not in OUTCOMES or not set(kinds)<=set(GATES):raise ValueError('Invalid diagnostic enum/reference')
        path=recall.safe_path(self.root/'diagnostics.json');now=int(time.time())
        records=recall.object_file(path).get('records',[]) if path.exists() else []
        records=[{k:r[k] for k in ('time','turn','outcome','kinds')} for r in records
                 if isinstance(r,dict) and isinstance(r.get('time'),int) and r['time']>=now-14*86400
                 and isinstance(r.get('turn'),str) and re.fullmatch('[a-f0-9]{64}',r['turn'])
                 and r.get('outcome') in OUTCOMES and isinstance(r.get('kinds'),list) and all(k in GATES for k in r['kinds'])]
        records=[r for r in records if r.get('turn')!=ticket]
        records.append({'time':now,'turn':ticket,'outcome':outcome,'kinds':sorted(kinds)})
        recall.atomic(path,{'version':1,'records':records[-64:]})
    def finish(self,ticket,token,outcome,mode):
        state=self.authorize(ticket,token,mode)
        if outcome not in ('complete','no_candidate','out_of_scope','pending','failed'):raise ValueError('Invalid finish outcome')
        with self.lock():
            state=self.authorize(ticket,token,mode)
            path=self.task_path(ticket);receipts=recall.object_file(path).get('receipts',{}) if path.exists() else {}
            if outcome=='complete' and not receipts:raise ValueError('Complete needs capture receipts; otherwise use no_candidate/out_of_scope')
            if outcome in ('no_candidate','out_of_scope') and receipts:raise ValueError('Capture attempts must be accounted for')
            for receipt in receipts.values():
                if receipt['status'] not in ('saved','updated','duplicate'):outcome='failed';continue
                try:
                    for ref in receipt.get('references',[]):
                        actual=self.backend().read(ref['project'],ref['identifier'],time.monotonic()+20)
                        if recall.digest(actual)!=ref['fingerprint']:raise ValueError('Receipt source changed')
                except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired):outcome='failed'
            if outcome=='complete':
                statuses={r['status'] for r in receipts.values()}
                result='updated' if 'updated' in statuses else 'saved' if 'saved' in statuses else 'duplicate'
            else:result=outcome
            self.diagnose(ticket,result,{r['kind'] for r in receipts.values()})
            pending=outcome in ('pending','failed') and not state.get('stop_evaluation')
            state.update(finished=not pending,armed=pending,candidate=pending,capture_pending=pending)
            recall.atomic(self.root/'state'/(ticket+'.json'),state)
            if outcome not in ('pending','failed'):path.unlink(missing_ok=True)
            return {'status':result,'receipts':len(receipts),'extra_evaluation':pending}
    def status(self):
        path=self.root/'diagnostics.json';now=int(time.time())
        records=recall.object_file(path).get('records',[]) if path.exists() else []
        records=[r for r in records if r.get('time',0)>=now-14*86400][-64:]
        counts={key:sum(r.get('outcome')==key for r in records) for key in sorted(OUTCOMES)}
        states=list((self.root/'state').glob('*.json')) if (self.root/'state').is_dir() else []
        unattested=sum(not recall.object_file(p).get('finished') and not recall.object_file(p).get('armed') for p in states if not p.is_symlink())
        return {'records':len(records),'outcomes':counts,'unattested_turns':unattested,'retention_days':14,'limit':64,
                'limits':'Unattested turns may be Plan, interrupted or unevaluated; absence is not proof of a missed memory.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-dir',type=Path,default=Path(os.environ.get('CODEX_HOME',Path.home()/'.codex')))
    parser.add_argument('--policy-root',type=Path)
    parser.add_argument('--cwd',type=Path,default=Path.cwd())
    commands=parser.add_subparsers(dest='action',required=True)
    prepare=commands.add_parser('prepare');prepare.add_argument('--input',required=True)
    apply=commands.add_parser('apply');apply.add_argument('--input',required=True);apply.add_argument('--review',required=True);apply.add_argument('--decisions',required=True)
    finish=commands.add_parser('finish');finish.add_argument('--outcome',required=True)
    for cmd in (apply,finish):
        cmd.add_argument('--ticket',required=True);cmd.add_argument('--token',required=True)
        cmd.add_argument('--mode',choices=('implementation','plan'),required=True)
    commands.add_parser('status')
    args=parser.parse_args()
    def read(value):
        if value.lstrip().startswith(('{','[')):return json.loads(value)
        path=recall.safe_path(Path(value).absolute())
        if path.stat().st_size>60000:raise ValueError('Oversized candidate input')
        return json.loads(path.read_text(encoding='utf-8'))
    try:
        service=Capture(args.codex_dir,args.cwd)
        if args.policy_root:service.root=recall.safe_path(args.policy_root.absolute());service.recall.root=service.root
        if args.action=='prepare':result=service.prepare(read(args.input))
        elif args.action=='apply':result=service.apply(args.ticket,args.token,read(args.input),args.review,read(args.decisions),args.mode)
        elif args.action=='finish':result=service.finish(args.ticket,args.token,args.outcome,args.mode)
        else:result=service.status()
        print(json.dumps(result,ensure_ascii=False))
        if result.get('status')=='failed':return 2
        return 0
    except (OSError,ValueError,KeyError,TypeError,ImportError,subprocess.TimeoutExpired):
        print(json.dumps({'status':'unavailable','error':'Capture validation, retrieval or authorization failed. Check configuration and sanitized input; no blind retry.'}))
        return 1


if __name__=='__main__':raise SystemExit(main())
