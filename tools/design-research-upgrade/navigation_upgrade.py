"""Final maintained layer: split research records, curated evidence and navigation."""
from pathlib import Path
import shutil


def replace(path,before,after):
    text=path.read_text('utf-8')
    if text.count(before)!=1:
        raise ValueError(f'Navigation upgrade anchor changed in {path}: {before[:90]}')
    path.write_text(text.replace(before,after),encoding='utf-8')


def apply(repo):
    research=repo/'tools/design-research/skill';scripts=research/'scripts'
    upstream=repo/'tools/speckit-upstream';workbench=upstream/'workbench'
    replace(scripts/'harness.py','    parent = regular_path(project / "docs/design-research")',
            '    from workspace_paths import topic_workspace, state_paths\n    parent = regular_path(project / "docs/design-research")')
    replace(scripts/'harness.py','matches = list(parent.glob("*/runs/" + args.run_id + "/state.json"))',
            'matches = state_paths(project, args.run_id)')
    replace(scripts/'harness.py','workspace = regular_path(parent / args.slug)',
            'workspace = regular_path(topic_workspace(project, args.slug, create=True))')
    replace(scripts/'harness.py','    atomic_json(role_dir / "invocation.json",',
            '    atomic_bytes(role_dir / "prompt.txt", scrub(prompt).encode("utf-8"))\n    atomic_json(role_dir / "invocation.json",')
    replace(scripts/'harness.py','                shutil.copy2(source, dest)\n            env = test_environment(scratch)',
            '                shutil.copy2(source, dest)\n                archived = regular_path(directory / "inputs" / name)\n                archived.parent.mkdir(parents=True, exist_ok=True)\n                shutil.copy2(source, archived)\n                add_record(state, workspace, archived, kind="experiment_input", description=f"Frozen experiment input: {name}")\n            env = test_environment(scratch)')
    # Both role input builders must point at the actual, resolved workspace.
    text=(scripts/'harness.py').read_text('utf-8')
    import re
    text,n=re.subn(r'Path\(state\["config"\]\["project"\]\) / "docs/design-research" /\s*state\["config"\]\["slug"\]',
                  'topic_workspace(state["config"]["project"], state["config"]["slug"])',text)
    if n!=4:raise ValueError('Role workspace builders changed')
    text=text.replace('from __future__ import annotations','from __future__ import annotations\nfrom workspace_paths import topic_workspace\nfrom runtime import atomic_bytes')
    (scripts/'harness.py').write_text(text,encoding='utf-8')
    replace(scripts/'gan-harness.sh','if [[ "${1:-}" == "reassess" ]]; then',
            'if [[ "${1:-}" == "export-evidence" || "${1:-}" == "verify-evidence" ]]; then\n  exec "${PYTHON_BIN:-python3}" -B "$DR_GAN_SCRIPT_DIR/published_evidence.py" "$@"\nfi\nif [[ "${1:-}" == "reassess" ]]; then')
    replace(scripts/'harness.py','def main(argv=None):\n    args = parser().parse_args(argv)',
            'def main(argv=None):\n    argv=list(sys.argv[1:] if argv is None else argv)\n    if argv[:1] and argv[0] in {"export-evidence","verify-evidence"}:\n        from published_evidence import main as evidence_main\n        return evidence_main(argv)\n    args = parser().parse_args(argv)')
    replace(scripts/'report.py','def publish(state, workspace, run_dir):',
            'def publish(state, workspace, run_dir):\n    _publish_local(state, workspace, run_dir)\n    from workspace_paths import publish_public\n    publish_public(state, workspace)\n\ndef _publish_local(state, workspace, run_dir):')
    replace(scripts/'runtime.py','        if name.startswith(excluded) or name == "docs/design-research/.gan.lock":',
            '        from workspace_paths import split, public_topic\n        public_excluded = public_topic(output).relative_to(project).as_posix()+"/" if split(output) else excluded\n        from workspace_paths import generated_navigation\n        if name.startswith((excluded, public_excluded)) or name == "docs/design-research/.gan.lock" or generated_navigation(project, name):')
    path=scripts/'codex_interface.py'
    replace(path,"    if len(rel) != 6 or rel[:2] != ('docs', 'design-research') or rel[3] != 'runs' or rel[5] != 'state.json':\n        raise ValueError('Use docs/design-research/<topic>/runs/<run-id>/state.json')",
            '    from workspace_paths import state_identity\n    state_identity(root,path)')
    replace(path,"    for path in sorted(base.glob('*/runs/*/state.json')):",
            '    from workspace_paths import state_paths\n    for path in state_paths(root):')
    replace(path,"rows = [state_record(root, str(p)) for p in safe(root, 'docs/design-research').glob('*/runs/'+args.run_id+'/state.json')]",
            'from workspace_paths import state_paths\n            rows = [state_record(root,str(p)) for p in state_paths(root,args.run_id)]')
    replace(path,"if not safe(root, 'docs/design-research/'+slug).exists():",
            "if not safe(root, 'docs/design-research/'+slug).exists() and not safe(root,'.artifacts/design-research/'+slug).exists():")
    text=path.read_text('utf-8').replace("if safe(root, 'docs/design-research/'+slug).exists():",
                "if safe(root, 'docs/design-research/'+slug).exists() or safe(root,'.artifacts/design-research/'+slug).exists():")
    text=text.replace("if not SLUG.fullmatch(slug) or safe(root, 'docs/design-research/'+slug).exists():",
                "if not SLUG.fullmatch(slug) or safe(root, 'docs/design-research/'+slug).exists() or safe(root,'.artifacts/design-research/'+slug).exists():")
    path.write_text(text,encoding='utf-8')
    replace(scripts/'reassessment.py','    if workspace.parent != project / "docs/design-research":\n        raise ValueError("Previous run must be within docs/design-research/<topic>")',
            '    from workspace_paths import state_identity\n    state_identity(project,path)')
    replace(scripts/'reassessment.py','if (project / "docs/design-research" / slug).exists():',
            'if (project / "docs/design-research" / slug).exists() or (project / ".artifacts/design-research" / slug).exists():')
    # Shared, standalone verifier ships with both tools; no dependency on installed research.
    shutil.copy2(scripts/'published_evidence.py',workbench/'published_evidence.py')
    shutil.copy2(scripts/'workspace_paths.py',workbench/'workspace_paths.py')
    shutil.copy2(research/'references/published-evidence.md',upstream/'assets/references/PUBLISHED_EVIDENCE.md')
    replace(upstream/'assets/templates/design.md','RESEARCH_WORKSTREAMS.mdのv2 bindingに従い、',
            'RESEARCH_WORKSTREAMS.mdの計画・統合契約とPUBLISHED_EVIDENCE.mdのv3 bindingに従い、')
    patch_binding(workbench/'design_quality.py')
    replace(workbench/'trace.py','    return sorted(files)',
            '    from .overview import owned_navigation\n    return sorted(p for p in files if not owned_navigation(root,p))')
    replace(workbench/'trace.py','    return items,findings',
            '    from .overview import evidence_hashes\n    hashes=evidence_hashes(root,path,text)\n    if hashes is not None:\n        for item in items:\n            if item.get("type") in {"design","decision"}:item["_evidence_hashes"]=hashes\n    return items,findings')
    replace(workbench/'approval_core.py',"    return 3 if row.get('_section') is not None else HASH_VERSION",
            "    if '_evidence_hashes' in row:return 4\n    return 3 if row.get('_section') is not None else HASH_VERSION")
    replace(workbench/'approval_core.py',"    if hash_version(row) == 3:","    if row.get('_section') is not None:")
    replace(workbench/'approval_core.py',"    body = json.dumps(payload, ensure_ascii=False, sort_keys=True,",
            "    if '_evidence_hashes' in row:payload['evidence']=row['_evidence_hashes']\n    body = json.dumps(payload, ensure_ascii=False, sort_keys=True,")
    replace(workbench/'workflow.py','def flow(root: Path, mode: str) -> str:',
            'def flow(root: Path, mode: str, brief: bool=False) -> str:\n    if brief:\n        from .overview import brief_flow\n        return brief_flow(root,mode)')
    cli=workbench/'cli.py'
    replace(cli,"    q=sub.add_parser('gate',help=", "    q.add_argument('--brief',action='store_true')\n    q=sub.add_parser('overview',help='確認対象・状態・次の操作を表示。既定は読み取りのみ')\n    q.add_argument('--project',default='.')\n    q.add_argument('--json',action='store_true');q.add_argument('--write',action='store_true')\n    q=sub.add_parser('gate',help=")
    replace(cli,"        if a.cmd=='flow':print(flow(root,a.mode));return 0",
            "        if a.cmd=='flow':print(flow(root,a.mode,a.brief));return 0\n        if a.cmd=='overview':\n            from .overview import overview, render, write\n            data=overview(root)\n            if a.write:write(root,data)\n            print(json_text(data) if a.json else render(data));return 0")
    # Refresh only after a mutating operation actually requested a write/apply.
    text=cli.read_text('utf-8')
    text=text.replace("                print(json_text(migrate(root,a.apply,a.include_doc)));return 0",
                      "                data=migrate(root,a.apply,a.include_doc)\n                if a.apply:\n                    from .overview import refresh\n                    refresh(root)\n                print(json_text(data));return 0")
    anchor='    except (WorkbenchError,OSError,ValueError) as exc:'
    text=text.replace(anchor,"        if root and (getattr(a,'apply',False) or getattr(a,'write',False)) and a.cmd!='uninstall':\n            from .overview import refresh\n            refresh(root)\n"+anchor)
    # Early-return write branches need their own refresh.
    text=text.replace("            return 0 if result['passed'] else 1", "            if a.write:\n                from .overview import refresh\n                refresh(root)\n            return 0 if result['passed'] else 1")
    text=text.replace("            return 1 if result['errors'] else 0", "            if getattr(a,'write',False):\n                from .overview import refresh\n                refresh(root)\n            return 1 if result['errors'] else 0")
    cli.write_text(text,encoding='utf-8')
    replace(workbench/'approval.py','def _packet_markdown(packet:dict)->str:',
            'def _packet_markdown(packet:dict)->str:\n    from .overview import review_markdown\n    return review_markdown(packet)\n\ndef _technical_packet_markdown(packet:dict)->str:')


def patch_binding(path):
    text=path.read_text('utf-8').replace("not in {1, 2}","not in {1, 2, 3}")
    text=text.replace("data.get('schema_version') == 2","(data.get('schema_version') == 2 or (data.get('schema_version') == 3 and 'workstream_plan' in data))")
    text=text.replace("data.get('schema_version') != 2","data.get('schema_version') not in {2, 3}")
    anchor="        raw = load(binding.get('state'))"
    text=text.replace(anchor,"""        if data.get('schema_version') == 3:
            from .published_evidence import verify
            manifest_path = local_file(root,binding.get('evidence_manifest'))
            manifest_raw = load(binding['evidence_manifest'])
            if sha(manifest_raw) != binding.get('evidence_manifest_sha256'):
                raise ValueError('Published manifest binding changed')
            package = verify(manifest_path.parent)
            prefix = manifest_path.parent/'files'
            if local_file(root,binding.get('state')) != prefix/package['state'] or local_file(root,binding.get('report')) != prefix/package['report']:
                raise ValueError('Binding does not identify the published run')
            deps.update(prefix/name for name in package['files'])
"""+anchor)
    text=text.replace("or state_path.parents[2].parent != Path('docs/design-research')):",
                      "or (data.get('schema_version') != 3 and state_path.parents[2].parent not in {Path('docs/design-research'),Path('.artifacts/design-research')})):")
    # Include every published proof dependency in the gate hash, even an invalid one.
    text=text.replace("            for row in data.get('runs', []):", """            for row in data.get('runs', []):
                if data.get('schema_version') == 3:
                    manifest=local_file(root,row['evidence_manifest'])
                    paths.add(manifest)
                    package=json.loads(read(root,row['evidence_manifest']))
                    paths.update(local_file(root,(manifest.parent/'files'/name).relative_to(root).as_posix()) for name in package['files'])""")
    path.write_text(text,encoding='utf-8')
