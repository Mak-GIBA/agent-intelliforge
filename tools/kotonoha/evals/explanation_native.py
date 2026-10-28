#!/usr/bin/env python3
"""Separate bounded trials of actual conditional reference reads in temp projects."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import run_study as base
import explanation_study as study

TASKS=[
 {'id':'N-depth','prompt':'新任担当者向けの技術解説を完成稿にしてください。原稿：起動時の設定保持は処理の効率化につながる。適切な更新管理が重要となる。素材：従来は要求ごとに設定ファイルを読み込む。提案方式は起動時に読み込んでメモリに保持し、要求時はその値を使う。ファイルを編集しても保持した値は変わらず、再起動で読み直す。時間は未測定。','read_explanation':True},
 {'id':'N-mail','prompt':'$yomiyasu 同僚へ送るこの短いメールを整えて、完成稿だけ返してください。佐藤さん、明日の打ち合わせを14時から15時に変更できますか。難しければ元の14時でお願いします。田中','read_explanation':False},
 {'id':'N-code','prompt':'次のコードだけを、aとbの和を返す形に直してください。説明文は不要です。\ndef add(a,b):\n    return a-b','read_explanation':False}]

def full_reads(items, path):
    return [{'command':r.get('command'),'exit_code':0,'content_sha256':base.sha(path.read_bytes())}
            for r in items if r.get('exit_code')==0 and path.read_text().strip() in r.get('aggregated_output','')
            and (str(path) in r.get('command','') or 'yomiyasu/references/explanation.md' in r.get('command',''))
            and re.search(r'\b(cat|sed|head|python3?|read_file)\b',r.get('command',''))]

def execute_one(root,task,contract,source,disabled):
    receipt=root/'native'/f"{task['id']}.json"
    if receipt.exists():return task['id'],'retained_'+json.loads(receipt.read_text())['status']
    with tempfile.TemporaryDirectory(prefix='yomiyasu-depth-native-') as tmp:
        cwd=Path(tmp);skills=cwd/'.agents/skills'
        spec=importlib.util.spec_from_file_location('depth_installer',study.ROOT/'installer.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        assets=root/'holdout/snapshots/revised/assets' if (root/'holdout').is_dir() else root/'snapshots/improved/assets'
        module.assets=lambda:{p.relative_to(assets).as_posix():p.read_bytes() for p in assets.rglob('*') if p.is_file()}
        scan=module.conflict_scan
        def isolated_scan(target,project=None):
            result=scan(target,project)
            result['duplicate_skill']=[p for p in result['duplicate_skill'] if str((Path(p)/'SKILL.md').resolve()) not in disabled]
            return result
        module.conflict_scan=isolated_scan
        meta,upstream=module.source_upstream(source)
        for rel,digest in contract['files'].items():
            if rel.startswith('upstream/') and base.sha(upstream[rel])!=digest:
                raise ValueError('Actual upstream changed: '+rel)
        module.install_selected(skills,module.COMPONENTS,mode='auto',apply=True,source=source,project=cwd)
        result=base.execute(task['prompt'],cwd,contract,disabled,native=True)
        reads=full_reads(result['tools'],skills/'yomiyasu/references/explanation.md')
        skill_reads=base.read_receipts(result['tools'],skills)
        result.update(task=task['id'],expected_explanation_read=task['read_explanation'],
                      explanation_reads=reads,skill_reads=skill_reads,
                      reference_route_pass=result['status']=='completed' and bool(reads)==task['read_explanation'])
        base.save(receipt,result)
    return task['id'],result['status'],result['reference_route_pass']

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--upstream-source',type=Path,required=True);args=p.parse_args();root=args.out.resolve()
    c=json.loads((root/'contract.json').read_text());study.verify_inputs(root,c)
    disabled=json.loads((root/'locations.private.json').read_text())['disabled']
    native_contract=root/'native-contract.json'
    identity={'tasks':TASKS,'model':c['model'],'effort':c['effort'],'timeout_seconds':480,
              'native_script_sha256':base.sha(Path(__file__).read_bytes()),
              'installer_sha256':base.sha((study.ROOT/'installer.py').read_bytes()),
              'source_asset_sha256':study.hashes(root/'holdout/snapshots/revised/assets' if (root/'holdout').is_dir() else root/'snapshots/improved/assets'),
              'interpretation':'Full successful reference reads demonstrate loading, not internal application or prose superiority'}
    if native_contract.exists():
        if identity!=json.loads(native_contract.read_text()):raise ValueError('Native contract changed')
    else:base.save(native_contract,identity)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(execute_one,root,t,c,args.upstream_source,disabled) for t in TASKS]
        for job in as_completed(jobs):print(*job.result(),flush=True)

if __name__=='__main__':main()
