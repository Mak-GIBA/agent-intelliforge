"""Verify preserved v3 normative blocks and maintained local reference links."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_flow(root, baseline):
    root = Path(root)
    contract = json.loads((root/'FLOW.json').read_text(encoding='utf-8'))
    if contract['schema'] != 1 or contract['baseline_commit'] != baseline['baseline_commit']:
        raise ValueError('Flow baseline differs')
    if len(contract['preserved']) != 9:
        raise ValueError('Incomplete preserved flow')
    wiring=[{k:row[k] for k in ('source','destination','replacements')} for row in contract['preserved']]
    revision = contract.get('editorial_revision')
    if revision is not None:
        revisions = baseline.get('editorial_wiring', {})
        if revision not in revisions:
            raise ValueError('Unknown editorial revision')
        allowed = revisions[revision]
    else:
        allowed = baseline['allowed_wiring']
    if wiring!=allowed:
        raise ValueError('Flow changes exceed the approved wiring-only moves')
    for row in contract['preserved']:
        original = baseline['files'][row['source']]
        if sha(original.encode()) != row['source_sha256']:
            raise ValueError('Legacy source identity differs')
        adapted = original
        for before, after in row['replacements']:
            if before not in adapted:
                raise ValueError('Unmatched allowed wiring change')
            adapted = adapted.replace(before, after)
        raw = adapted.encode()
        relative = PurePosixPath(row['destination'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid flow destination')
        path = root/relative
        actual = path.read_bytes()
        offset = row.get('offset', 0)
        if (len(raw) != row['preserved_bytes'] or sha(raw) != row['preserved_sha256']
                or actual[offset:offset+len(raw)] != raw):
            raise ValueError('Preserved legacy rule changed: '+str(relative))
    expected = {'references/audience.md', 'references/clarity.md', 'references/finish.md', 'references/review.md'}
    if set(contract['normal_required']) != expected:
        raise ValueError('Required v3 flow stages changed')
    for name in [*contract['normal_required'], *contract['conditional'].values()]:
        if not (root/name).is_file():
            raise ValueError('Missing flow reference: '+name)
    # Only maintained instructions; unmodified upstream manuals have their own layout.
    for path in [root/'SKILL.md', *sorted((root/'references').glob('*.md'))]:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            linked = path.parent/target.split('#', 1)[0]
            if not linked.is_file():
                raise ValueError('Broken maintained link: '+str(path.relative_to(root))+' -> '+target)
    return {'status': 'passed', 'preserved_resources': len(contract['preserved']), 'baseline_commit': contract['baseline_commit']}


def verify_native_records(candidate, quality, adapter, tasks):
    """Check actual paired records and reviews, rather than trusting a pass summary."""
    candidate, adapter = Path(candidate), Path(adapter)
    artifacts = quality['artifacts']
    contracts = [n for n in artifacts if re.fullmatch(r'native-r[123]/contract.json', n)]
    if len(contracts) != 1:
        raise ValueError('Missing native comparison contract')
    directory = PurePosixPath(contracts[0]).parent
    contract = json.loads((candidate/contracts[0]).read_text(encoding='utf-8'))
    if contract['tasks'] != tasks or contract['adapter_sha256'] != quality['adapter_sha256']:
        raise ValueError('Native contract belongs to another input or adapter')
    runner=(directory/'runner.py').as_posix()
    if runner not in artifacts or sha((candidate/runner).read_bytes())!=contract['runner_sha256']:
        raise ValueError('Native evaluator snapshot differs')
    expected_ids = {'W'+str(n).zfill(2) for n in range(1,25)}
    if len(tasks) != 24 or {t['id'] for t in tasks} != expected_ids:
        raise ValueError('Incomplete native task set')
    for task in tasks:
        for arm in ('baseline', 'candidate'):
            name = (directory/(task['id']+'-'+arm+'.json')).as_posix()
            if name not in artifacts:
                raise ValueError('Missing paired native output')
            record = json.loads((candidate/name).read_text(encoding='utf-8'))
            if record['status'] != 'completed' or not record.get('text'):
                raise ValueError('Incomplete paired native output')
            if arm == 'baseline':
                continue
            if not record['draft_unchanged'] or not record['skills_unchanged']:
                raise ValueError('Native input or Skill changed')
            if task['mode'] == 'file' and not record['final_file_present']:
                raise ValueError('Native requested file missing')
            if not record['diagnosis_has_no_result_file']:
                raise ValueError('Native diagnosis changed output scope')
            outputs = '\n'.join(t.get('aggregated_output','') for t in record['tools'])
            outputs = re.sub(r'(?m)^\s*\d+\t', '', outputs)
            required = [] if task['id'] in {'W21','W22','W23','W24'} else ['audience','clarity','finish','review']
            required += task['conditional']
            for name in required:
                raw = (adapter/'references'/(name+'.md')).read_text(encoding='utf-8').strip()
                if raw not in outputs:
                    raise ValueError('Native required reference not observed: '+task['id']+'/'+name)
            if task['mode'] == 'file':
                commands = '\n'.join(t.get('command','') for t in record['tools'])
                if any(name not in commands for name in ('writing_lint.py','check.py')):
                    raise ValueError('Native checker invocation not observed')
    critical, regressions = [], []
    for batch in range(6):
        name = (directory/('review-'+str(batch)+'.json')).as_posix()
        if name not in artifacts:
            raise ValueError('Missing native review')
        review = json.loads((candidate/name).read_text(encoding='utf-8'))
        rows = review['result']['cases']
        selected = tasks[batch*4:(batch+1)*4]
        receipt=review['receipt']
        if receipt['status']!='completed' or receipt['tools'] or json.loads(receipt['output'])!=review['result']:
            raise ValueError('Native review receipt differs from recorded ratings')
        pairs=[]
        for i,task in enumerate(selected):
            order=('baseline','candidate') if i%2==0 else ('candidate','baseline')
            versions={label:json.loads((candidate/directory/(task['id']+'-'+arm+'.json')).read_text(encoding='utf-8'))['text']
                      for label,arm in zip(('X','Y'),order)}
            pairs.append({**{k:task[k] for k in ('id','instruction','input','requirements')},'versions':versions})
        if review['pairs']!=pairs:
            raise ValueError('Native reviewed texts differ from actual Skill outputs')
        if len(rows) != 4 or {r['id'] for r in rows} != {t['id'] for t in selected}:
            raise ValueError('Incomplete native review')
        for i, task in enumerate(selected):
            row = next(r for r in rows if r['id'] == task['id'])
            label = 'Y' if i % 2 == 0 else 'X'
            critical.extend(task['id']+': '+x for x in row[label+'_errors'])
            regressions.extend(task['id']+': '+x for x in row['regressions_'+label])
    if critical or regressions or quality.get('critical_errors') != critical or quality.get('unresolved_regressions') != regressions:
        raise ValueError('Native reviews do not support a pass')

from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
