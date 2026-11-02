#!/usr/bin/env python3
"""Local-only gh/glab fixture for the opt-in workflow evaluation, never a real client."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    folder = Path(__file__).resolve().parent
    state_path = folder / 'state.json'
    state = json.loads(state_path.read_text())
    argv = sys.argv[1:]
    with (folder / 'calls.jsonl').open('a') as out:
        out.write(json.dumps(argv, ensure_ascii=False) + '\n')

    def option(*flags, default=None):
        for flag in flags:
            if flag in argv:
                return argv[argv.index(flag) + 1]
            for arg in argv:
                if arg.startswith(flag + '='):
                    return arg[len(flag) + 1:]
        return default

    def output(value):
        if '--jq' in argv:
            query = option('--jq').lstrip('.')
            if query in value:
                print(value[query]); return
        print(json.dumps(value, ensure_ascii=False))

    def save():
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')

    def fail(message):
        print(message, file=sys.stderr); return 1

    if '--version' in argv:
        print('local workflow fixture; not a real service'); return 0
    if '--help' in argv or not argv:
        print('Fixture: auth status; repo view; pr/mr list/view/create/edit/update. '
              '--repo/-R, --base/--target-branch, --head/--source-branch, --title, '
              '--body-file (gh), --description (glab), --output json (glab). '
              'api GET projects/:id[/merge_requests]; POST/PUT with --input JSON_FILE.'); return 0
    if not state['authenticated']:
        return fail('fixture authentication unavailable; no real login is supported')
    if argv[:2] == ['auth', 'status']:
        print('Authenticated local fixture'); return 0
    base = state['base']
    gitroot = folder.parent
    def git(*args):
        return subprocess.check_output(['git', '-C', str(gitroot), *args], text=True).strip()
    def request():
        value = state['request']
        if value:
            value = dict(value)
            sha = subprocess.run(['git', '-C', str(gitroot), 'ls-remote', '--exit-code',
                                  'origin', 'refs/heads/' + value['headRefName']],
                                 text=True, capture_output=True)
            value['headRefOid'] = sha.stdout.split()[0] if sha.returncode == 0 else None
            value.update(iid=value['number'], description=value['body'], web_url=value['url'],
                         source_branch=value['headRefName'], target_branch=value['baseRefName'],
                         sha=value['headRefOid'], draft=value['isDraft'])
        return value

    repo = {'nameWithOwner': 'example/catalog', 'url': 'https://forge.example.invalid/example/catalog',
            'defaultBranchRef': {'name': base}, 'default_branch': base, 'path_with_namespace': 'example/catalog'}
    if argv[:2] == ['repo', 'view']:
        output(repo); return 0
    if argv[0] == 'api':
        endpoint = next((a for a in argv[1:] if a.startswith(('projects/', 'repos/'))), '')
        method = option('--method', '-X', default='GET')
        if method != 'GET':
            if '/merge_requests' not in endpoint or method not in ('POST', 'PUT'):
                return fail('unsupported mutation')
            payload = json.loads(Path(option('--input')).read_text())
            argv = ['mr', 'create' if method == 'POST' else 'update', '--source-branch', payload.get('source_branch', git('branch', '--show-current')),
                    '--target-branch', payload.get('target_branch', base), '--title', payload.get('title', request()['title'] if request() else ''),
                    '--description', payload.get('description', '')]
        elif '/merge_requests/' in endpoint or '/pulls/' in endpoint:
            output(request()); return 0
        elif '/merge_requests' in endpoint or endpoint.endswith('/pulls'):
            output([request()] if request() else []); return 0
        elif endpoint:
            output(repo); return 0
        else:
            return fail('unsupported fixture endpoint')
    if len(argv) < 2 or argv[0] not in ('pr', 'mr'):
        return fail('unsupported fixture command')
    action = argv[1]
    if action == 'list':
        value = request()
        head = option('--head', '--source-branch')
        output([value] if value and (not head or value['headRefName'] == head) else []); return 0
    if action == 'view':
        if not request(): return fail('No pull request exists')
        output(request()); return 0
    if action == 'diff':
        print(git('diff', base + '...HEAD')); return 0
    if action == 'checks':
        output([]); return 0
    if action not in ('create', 'edit', 'update'):
        state['forbidden'].append(argv); save()
        return fail('merge/review/comment/release is outside this fixture task')
    body = option('--body', '--description', '-d')
    body_path = option('--body-file', '--description-file')
    if body_path: body = Path(body_path).read_text()
    if action == 'create':
        state['create_attempts'] += 1
        if state['request']:
            save(); return fail('duplicate request')
        head = option('--head', '--source-branch', '-s', default=git('branch', '--show-current'))
        remote = subprocess.run(['git', '-C', str(gitroot), 'ls-remote', '--exit-code', 'origin', 'refs/heads/' + head], capture_output=True)
        if remote.returncode:
            save(); return fail('source branch has not been pushed')
        state['request'] = {'number': 1, 'title': option('--title', '-t', default=''), 'body': body or '',
                            'url': 'https://forge.example.invalid/example/catalog/requests/1',
                            'baseRefName': option('--base', '--target-branch', '-b', default=base),
                            'headRefName': head, 'state': 'OPEN', 'isDraft': '--draft' in argv}
        save()
        if state.get('timeout_once'):
            state['timeout_once'] = False; save()
            return fail('fixture timeout after server accepted request; inspect before retry')
    else:
        if not state['request']: return fail('No request to update')
        state['edit_attempts'] += 1
        if body is not None: state['request']['body'] = body
        if option('--title', '-t'): state['request']['title'] = option('--title', '-t')
        save()
    output(request()); return 0


if __name__ == '__main__':
    raise SystemExit(main())
