#!/usr/bin/env python3
"""Non-mutating textlint/Markdown diagnostics; unavailable is distinct from findings."""
from __future__ import annotations
import argparse
import difflib
import json
import os
from pathlib import Path
import re
from agent_intelliforge import subprocess_bridge as subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent


def settings():
    if os.environ.get('KOTONOHA_RUNTIME_DIR'):
        candidates=[Path(os.environ['KOTONOHA_RUNTIME_DIR'])/'settings.json']
    else:
        candidates=[HERE.parents[2]/'.kotonoha-runtime/settings.json',HERE.parents[3]/'dependencies/kotonoha/settings.json']
    for path in candidates:
        if path.is_file():
            data=json.loads(path.read_text(encoding='utf-8'))
            if data.get('owner')!='agent-intelliforge/kotonoha': raise ValueError('Runtime owner mismatch')
            return data
    return None


def execute(command,cwd):
    try:
        p=subprocess.run(command,cwd=cwd,capture_output=True,text=True,encoding='utf-8',timeout=90)
        if p.returncode not in (0,1):return {'status':'unavailable','error':p.stderr[-1500:]}
        try:messages=json.loads(p.stdout.strip() or p.stderr.strip() or ('[]' if p.returncode == 0 else ''))
        except ValueError:return {'status':'unavailable','error':(p.stderr or p.stdout)[-1500:]}
        if not isinstance(messages,list):return {'status':'unavailable','error':'Unexpected lint JSON'}
        return {'status':'checked','messages':messages}
    except (OSError,subprocess.TimeoutExpired) as e:return {'status':'unavailable','error':str(e)}


def lint(path,config):
    path=path.resolve(strict=True)
    if path.suffix.lower() not in ('.md','.markdown','.txt') or path.stat().st_size>2_000_000:
        raise ValueError('Expected UTF-8 Markdown/text no larger than 2 MB')
    text=path.read_text(encoding='utf-8-sig')
    if '\x00' in text:raise ValueError('NUL input refused')
    if not config:return {'status':'unavailable','error':'Run installer --apply to prepare the writing runtime'}
    directory=Path(config['lint']);node=config['node']
    upstream=HERE.parent/'meiseki-upstream/references'
    with tempfile.TemporaryDirectory(prefix='kotonoha-lint-') as td:
        tmp=Path(td);sample=tmp/'input.md';sample.write_text(text,encoding='utf-8')
        rules=json.loads((upstream/'textlint.config.json').read_text(encoding='utf-8'))
        rules['rules']['prh']['rulePaths']=[str(upstream/'prh-llm-phrases.yml')]
        cfg=tmp/'textlint.json';cfg.write_text(json.dumps(rules),encoding='utf-8')
        result={'status':'checked','textlint':execute([node,str(directory/'node_modules/textlint/bin/textlint.js'),
            '--rules-base-directory',str(directory/'node_modules'),'--config',str(cfg),'--format','json',str(sample)],tmp)}
        if path.suffix.lower() in ('.md','.markdown'):
            result['markdownlint']=execute([node,str(directory/'node_modules/markdownlint-cli/markdownlint.js'),
                '--config',str(upstream/'markdownlint.config.jsonc'),'--json',str(sample)],tmp)
        if any(v.get('status')=='unavailable' for v in result.values() if isinstance(v,dict)):result['status']='partial'
        result['replacement_character_lines']=[i for i,line in enumerate(text.splitlines(),1) if '\ufffd' in line]
        return result


def markdown_new(before,after,old_text,new_text):
    """Match unchanged lines so shifted pre-existing diagnostics are not new."""
    mapping={}
    for block in difflib.SequenceMatcher(a=old_text.splitlines(),b=new_text.splitlines(),autojunk=False).get_matching_blocks():
        mapping.update({block.b+i+1:block.a+i+1 for i in range(block.size)})
    old={(r.get('lineNumber'),tuple(r.get('ruleNames',[])),r.get('errorDetail')) for r in before}
    return [r for r in after if (mapping.get(r.get('lineNumber')),tuple(r.get('ruleNames',[])),r.get('errorDetail')) not in old]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path);p.add_argument('--before',type=Path)
    args=p.parse_args()
    try:
        config=settings();result=lint(args.file,config)
        if args.before:
            before=lint(args.before,config);result['before']=before
            if all(x.get('markdownlint',{}).get('status')=='checked' for x in (before,result)):
                result['new_markdown_findings']=markdown_new(before['markdownlint']['messages'],result['markdownlint']['messages'],
                    args.before.read_text(encoding='utf-8-sig'),args.file.read_text(encoding='utf-8-sig'))
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 2 if result['status'] in ('unavailable','partial') else 0
    except (OSError,ValueError,KeyError) as error:
        print(json.dumps({'status':'unavailable','error':str(error)},ensure_ascii=False));return 2


from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':raise SystemExit(main())
