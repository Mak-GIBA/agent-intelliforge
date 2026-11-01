#!/usr/bin/env python3
"""Bounded read-only Issue/PR/MR and note inventory for gh/glab."""
from __future__ import annotations
import argparse
import json
import os
import re
from agent_intelliforge import subprocess_bridge as subprocess
import sys
from urllib.parse import quote


def read(provider, host, repo, kind, number=None, max_pages=20, runner=subprocess.run):
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?',host): raise ValueError('Invalid hostname')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+',repo) or any(p in ('.','..') for p in repo.split('/')):
        raise ValueError('Use an explicit namespace/project')
    if provider not in ('github','gitlab') or kind not in ('issues','requests'):raise ValueError('Unsupported resource')
    if provider=='github' and repo.count('/')!=1:raise ValueError('GitHub requires owner/repo')
    if number is not None and number<1 or not 1<=max_pages<=100:raise ValueError('Invalid number/page bound')
    resource=('pulls' if provider=='github' else 'merge_requests') if kind=='requests' else 'issues'
    endpoint=f'repos/{repo}/{resource}' if provider=='github' else f'projects/{quote(repo,safe="")}/{resource}'
    prefix=['gh' if provider=='github' else 'glab','api','--hostname',host,'--method','GET']
    def request(url):
        try:
            result=runner([*prefix,url],capture_output=True,text=True,encoding='utf-8',timeout=60,
                          env={**os.environ,'GH_PROMPT_DISABLED':'1','GLAB_PROMPT_DISABLED':'1'})
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise ValueError('Remote read unavailable: '+type(exc).__name__) from exc
        if result.returncode:raise ValueError('Remote read failed; check the selected host, connection and permissions')
        return json.loads(result.stdout)
    detail=request(endpoint+'/'+str(number)) if number else None
    if detail is not None:
        if not isinstance(detail,dict) or not ('iid' in detail or 'number' in detail):raise ValueError('Unexpected remote detail response')
        if provider=='github' and resource=='pulls':endpoint=f'repos/{repo}/issues'
        endpoint+='/'+str(number)+('/comments' if provider=='github' else '/notes')
    items=[]
    for page in range(1,max_pages+1):
        query=f'?per_page=100&page={page}' + ('&state=all' if number is None else '')
        batch=request(endpoint+query)
        if not isinstance(batch,list):raise ValueError('Unexpected remote collection response')
        items.extend(item for item in batch if not (provider=='github' and kind=='issues' and number is None and 'pull_request' in item))
        if len(batch)<100:return {'items':items,'detail':detail,'pages':page,'complete':True}
    return {'items':items,'detail':detail,'pages':max_pages,'complete':False,'note':'Page bound reached. Absence and uniqueness are not established.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--provider',choices=('github','gitlab'),required=True);p.add_argument('--host',required=True)
    p.add_argument('--repo',required=True);p.add_argument('--kind',choices=('issues','requests'),required=True)
    p.add_argument('--number',type=int);p.add_argument('--max-pages',type=int,default=20)
    a=p.parse_args(argv)
    try:
        value=read(a.provider,a.host,a.repo,a.kind,a.number,a.max_pages)
        print(json.dumps(value,ensure_ascii=False,indent=2));return int(not value['complete'])
    except (ValueError,OSError) as e:
        print(str(e),file=sys.stderr);return 2



from agent_intelliforge.runtime_ports import apply_ports as _apply_ports, portable_link as _portable_link
_apply_ports(globals())
if __name__=='__main__':raise SystemExit(main())
