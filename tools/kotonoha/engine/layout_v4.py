"""Canonical layout and migration, evaluated in the standalone engine namespace."""

def own_bundle(component, mode):
    data = assets()
    prefix = 'kotonoha/'
    out = {name[len(prefix):]: raw for name, raw in data.items() if name.startswith(prefix)}
    out['agents/openai.yaml'] = agent_yaml('kotonoha', mode)
    out['resources.json'] = (json.dumps({'schema': 1, 'kind': 'kotonoha-source-integrity',
        'files': {name: sha(raw) for name, raw in sorted(out.items())
                  if name.startswith(('upstream/', 'meiseki-upstream/'))}},
        ensure_ascii=False, indent=2)+'\n').encode()
    return out


def resolve_meiseki(tag=None):
    repo = 'bamboo-nova/meiseki'
    release = json_download('https://api.github.com/repos/'+repo+'/releases/'+
                            ('latest' if tag is None else 'tags/'+urllib.parse.quote(tag, safe='')))
    if release.get('draft') or release.get('prerelease'):
        raise InstallError('meiseki must be a stable release')
    resolved = str(release['tag_name'])
    if tag and resolved != tag: raise InstallError('Requested release differs')
    commit = json_download('https://api.github.com/repos/'+repo+'/commits/'+urllib.parse.quote(resolved, safe=''))['sha']
    if not re.fullmatch('[a-f0-9]{40}', commit): raise InstallError('Invalid upstream commit')
    tree = json_download('https://api.github.com/repos/'+repo+'/git/trees/'+commit+'?recursive=1')
    if tree.get('truncated'): raise InstallError('Incomplete upstream tree')
    specs = {}; prefix = '.agents/skills/meiseki/'
    for row in tree.get('tree', []):
        path = row['path']
        name = 'LICENSE' if path == 'LICENSE' else path.removeprefix(prefix) if path.startswith(prefix) else None
        if name is None or row['type'] == 'tree': continue
        safe_rel(name)
        if row.get('mode') not in ('100644', '100755') or row['type'] != 'blob':
            raise InstallError('Nonregular upstream file')
        if name != 'SKILL.md' and Path(name).name == 'SKILL.md': raise InstallError('Nested Skill')
        if type(row.get('size')) != int or not 0 <= row['size'] <= MAX_FILE:
            raise InstallError('Upstream file size exceeds limit')
        specs[name] = {'repo_path': path, 'size': row['size'], 'git_blob_sha1': row['sha']}
    if not {'SKILL.md', 'LICENSE'} <= specs.keys() or len(specs) > MAX_COUNT or sum(x['size'] for x in specs.values()) > MAX_TOTAL:
        raise InstallError('Incomplete/oversized meiseki source')
    return {'repository': repo, 'tag': resolved, 'commit': commit, 'files': specs,
            'release_url': 'https://github.com/'+repo+'/releases/tag/'+resolved}


def fetch_meiseki_release(meta):
    out = {}
    for name, spec in sorted(meta['files'].items()):
        raw = download('https://raw.githubusercontent.com/'+meta['repository']+'/'+meta['commit']+'/'+spec['repo_path'])
        out['meiseki-upstream/'+('SKILL.upstream.md' if name == 'SKILL.md' else name)] = verify_file(name, raw, spec)
    out['meiseki-upstream/UPSTREAM.json'] = (json.dumps(meta, ensure_ascii=False, indent=2)+'\n').encode()
    return out


def integrated_sources():
    return json.loads(assets()['kotonoha/UPSTREAMS.json'])


def check_updates(root, names=COMPONENTS, ref=None, source="all"):
    active = integrated_sources(); result = {}
    target = root/'kotonoha'
    if target.is_dir():
        installed = inventory(target)
        manifest_for(installed, 'kotonoha')
        if 'UPSTREAMS.json' in installed: active = json.loads(installed['UPSTREAMS.json'])
    for name, resolve in [('yomiyasu', resolve_release), ('meiseki', resolve_meiseki)]:
        if source != 'all' and name != source: continue
        selected = active['sources'][name]
        try:
            latest = resolve(ref if name == 'yomiyasu' or source == 'meiseki' else None)
            changed = latest['commit'] != selected['commit']
            result[name] = {'integrated': {k:selected.get(k) for k in ('tag','commit')},
                'latest_stable': {k:latest.get(k) for k in ('tag','commit')},
                'status': 'needs_review' if changed or active['integration']['status']!='verified' else 'current'}
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            result[name] = {'integrated': {k:selected.get(k) for k in ('tag','commit')},
                            'status': 'check_failed', 'error': str(exc)}
    return {'applied': False, 'network': True, 'upstreams': result,
            'note': 'Fetched/latest is distinct from integrated; use the repository update_upstreams workflow'}


def _migration_states(root):
    states = {}
    for name in LEGACY_COMPONENTS:
        target = root/name
        safe_path(target)
        if not target.exists(): continue
        old = inventory(target); marker = manifest_for(old, name)
        extras = set(old)-set(marker['files'])-{MANIFEST}
        extras = {p for p in extras if '__pycache__' not in Path(p).parts and not p.endswith('.pyc')}
        if edited(old, marker) or extras:
            raise InstallError('Edited/extra files block migration; nothing replaced: '+name)
        states[name] = old
    return states


def install_selected(root, names=COMPONENTS, mode=None, force=False, apply=False, source=None,
                     project=None, update=False, upstream_only=False, upstream_ref=None):
    root = abs_path(root); safe_path(root)
    states = _migration_states(root)
    target = root/'kotonoha'
    old_marker = manifest_for(states['kotonoha'], 'kotonoha') if 'kotonoha' in states else None
    if upstream_only:
        if not old_marker or not update or mode is not None or force:
            raise InstallError('Upstream-only requires an existing installation and --update without mode/force')
        checked = check_updates(root, names, upstream_ref)
        checked['status'] = 'current' if all(x['status']=='current' for x in checked['upstreams'].values()) else 'UPSTREAM_REVIEW_REQUIRED'
        return checked
    if upstream_ref and upstream_ref != integrated_sources()['sources']['yomiyasu']['tag']:
        raise InstallError('Requested source needs review; use update_upstreams.py prepare')
    if source:
        meta, _ = source_upstream(source)
        if meta['commit'] != integrated_sources()['sources']['yomiyasu']['commit']:
            raise InstallError('Local source needs reviewed integration before installation')
    previous_mode = old_marker['mode'] if old_marker else manifest_for(states['yomiyasu'],'yomiyasu')['mode'] if 'yomiyasu' in states else 'auto'
    effective = mode or previous_mode
    if states and not old_marker and not (update or force):raise InstallError('Use --update to migrate legacy entries')
    if old_marker and (old_marker['version'] != VERSION or old_marker['mode'] != effective) and not (force or update):
        raise InstallError('Use --update for an existing version or mode')
    conflicts = conflict_scan(target, project)
    if conflicts['duplicate_skill']: raise InstallError('Duplicate kotonoha: '+str(conflicts['duplicate_skill']))
    retired = [name for name in states if name != 'kotonoha']
    same = bool(old_marker and old_marker['version']==VERSION and old_marker['mode']==effective and not retired)
    result = {'component': 'kotonoha', 'target': str(target), 'version': VERSION, 'mode': effective,
              'action': 'skip' if same and not update and not force else 'update' if states else 'install',
              'applied': False, 'network': False, 'conflicts': conflicts, 'retire': retired,
              'changes_other_settings': False}
    if not apply or result['action']=='skip': return result
    expected = own_bundle('kotonoha', effective)
    lock_data = json.loads(expected['UPSTREAMS.json'])
    if lock_data['integration']['status'] != 'verified':
        raise InstallError('Source integration has not passed capability verification')
    # Runtime preparation follows all ownership preflights, before switching any Skill.
    runtime = prepare_writing_runtime(root)
    marker = {'owner': OWNERS['kotonoha'], 'component': 'kotonoha', 'schema': 1,
              'version': VERSION, 'mode': effective, 'files': {k:sha(v) for k,v in expected.items()},
              'publisher_signature_verified': False}
    prepared = {**expected, MANIFEST: (json.dumps(marker, ensure_ascii=False, indent=2)+'\n').encode()}
    root.mkdir(parents=True, exist_ok=True)
    stages = []
    def unchanged():
        if _migration_states(root) != states: raise InstallError('Installation changed during preparation')
        if conflict_scan(target, project)['duplicate_skill']: raise InstallError('Duplicate added during preparation')
    with lock(target):
        try:
            unchanged()
            stage = Path(tempfile.mkdtemp(prefix='.kotonoha-stage-', dir=root))
            stages.append((stage, target))
            for rel, raw in prepared.items():
                path = stage/safe_rel(rel); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
            result['backups'] = {name:str(backup(root/name, old)) for name,old in states.items()}
            unchanged()
            replace_directories(stages+[(None, root/name) for name in retired])
        finally:
            for stage, _ in stages:
                if stage.exists(): shutil.rmtree(stage)
    result.update(applied=True, implicit_invocation=effective=='auto', writing_runtime=runtime['versions'])
    return result


def uninstall_selected(root, names=COMPONENTS, apply=False):
    return legacy_uninstall_selected(root, COMPONENTS, apply)


def doctor(target, project=None, component='kotonoha'):
    target = target.parent/'kotonoha'
    result, code = legacy_doctor(target, project, 'kotonoha')
    if code: return result, code
    try:
        values = inventory(target)
        upstream_contract(values)
        index = json.loads(values['resources.json'])
        if any(name not in values or sha(values[name]) != digest for name,digest in index['files'].items()):
            raise InstallError('Source resources changed')
        result['upstreams'] = json.loads(values['UPSTREAMS.json'])
        runtime_path = target.parent.parent/'.kotonoha-runtime'
        helper = target/'scripts/writing_runtime.py'
        if (runtime_path/'settings.json').is_file():
            scope={'__name__':'kotonoha_health','__file__':str(helper)}
            exec(compile(helper.read_text('utf-8'),str(helper),'exec'),scope)
            result['writing_runtime'] = scope['diagnose'](runtime_path)
        result['retired_entries_present'] = [name for name in LEGACY_COMPONENTS if name!='kotonoha' and (target.parent/name).exists()]
        if result['retired_entries_present']: raise InstallError('Legacy entries need migration')
        return result, 0
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        result.update(status='NOT_READY', error=str(exc)); return result, 2
