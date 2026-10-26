"""Narrow runtime bindings for generated copies; all domain validators stay intact."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
import shutil
import signal
import time

from . import portable
from .subprocess_bridge import adapt


class WhichAdapter:
    def __getattr__(self, name):
        return getattr(shutil, name)

    def which(self, command, *args, **kwargs):
        return shutil.which("claude" if command == "codex" else command, *args, **kwargs)


def portable_link(destination, target, target_is_directory=False):
    if os.name == "nt":
        # No elevation/developer mode or writable link outside the staged copy.
        if target_is_directory: shutil.copytree(target, destination)
        else: shutil.copy2(target, destination)
    else:
        destination.symlink_to(target, target_is_directory=target_is_directory)


def apply_ports(namespace: dict) -> None:
    """Run after definitions, before main; scoped to this generated module only."""
    if os.environ.get("INTELLIFORGE_AGENT") == "claude":
        if "shutil" in namespace: namespace["shutil"] = WhichAdapter()
        if "select_backend" in namespace:
            def select_backend(config):
                if config.get("browser") not in (None, "auto", "local-playwright"):
                    raise namespace["Blocked"]("The selected vendor browser is unavailable in the Claude portable runtime")
                return "local-playwright", "Explicit Claude runtime uses the bundled local Playwright bridge"
            namespace["select_backend"] = select_backend
    if os.environ.get('INTELLIFORGE_KIT_HOME') and Path(namespace.get('__file__','')).name=='check.py' and 'upstream' in namespace and not (Path(namespace['__file__']).parent.parent/'resources.json').is_file():
        def upstream(name, args):
            from .ownership import verify
            from .runtime import owner
            import subprocess, sys, json
            agent=os.environ['INTELLIFORGE_AGENT']; root=Path(os.environ['INTELLIFORGE_KIT_HOME'])/'upstream'
            verify(root,owner('yomiyasu-upstream',agent))
            if name not in ('yomiyasu_lint.py','yomiyasu_diff.py'): raise ValueError('Unknown upstream helper')
            script=root/'scripts'/name
            if not script.is_file(): raise ValueError('Missing verified upstream helper')
            # Exact upstream bytes, isolated Python, sibling imports, same output contract.
            command='import runpy,sys; p=sys.argv.pop(1); sys.path.insert(0,str(__import__("pathlib").Path(p).parent)); sys.argv[0]=p; runpy.run_path(p,run_name="__main__")'
            result=portable.capture([sys.executable,'-X','utf8','-I','-B','-c',command,str(script),*args],cwd=script.parent,env=None,timeout=30,limit=5_000_000)
            if result['exit_code'] not in (0,1) or result['timed_out'] or result['truncated']: raise RuntimeError('Verified upstream check failed or exceeded its limit')
            report=json.loads(result['stdout'])
            if not isinstance(report,dict): raise ValueError('Upstream JSON contract changed')
            return {'status':'EXECUTED','exit_code':result['exit_code'],'report':report}
        namespace['upstream']=upstream
    if os.environ.get('INTELLIFORGE_KIT_HOME') and 'OfficeError' in namespace and 'paths' in namespace:
        from .office_port import bindings
        bindings(namespace)
    if os.environ.get('INTELLIFORGE_KIT_HOME') and 'WorkbenchError' in namespace and 'locations' in namespace:
        home = Path(os.environ['INTELLIFORGE_KIT_HOME'])
        namespace['locations'] = lambda: {'home': Path.home(), 'data': home / 'data', 'config': home / 'config',
                                          'bin': home / 'bin', 'skill': home / 'bundle/skill'}
    if os.name != "nt":
        return
    if 'preflight_commands' in namespace:
        def preflight_commands(project, commands):
            import base64
            import subprocess
            import shutil
            shell = shutil.which('pwsh') or shutil.which('powershell')
            if not shell: raise namespace['Blocked']('PowerShell is required for Windows check commands')
            project = Path(project)
            for name in ('node_modules', '.venv', 'venv'):
                from .ownership import check_path
                if (project / name).exists(): check_path(project / name)
            for row in commands:
                command = row.get('command')
                if not isinstance(command, str) or not command.strip(): raise namespace['Blocked']('Preparation: empty check command')
                # Parse without execution. Do not translate arbitrary Bash text into PowerShell.
                script = "try { [void][scriptblock]::Create('" + command.replace("'", "''") + "'); exit 0 } catch { exit 2 }"
                encoded = base64.b64encode(script.encode('utf-16-le')).decode()
                result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded], cwd=project, capture_output=True, timeout=5)
                if result.returncode: raise namespace['Blocked']('Preparation: Windows checks require valid PowerShell syntax')
            return {'status':'ready', 'scope':'PowerShell syntax/dependency layout only; commands are not executed'}
        namespace['preflight_commands'] = preflight_commands
    if "terminate_owned" in namespace: namespace["terminate_owned"] = portable.terminate
    if "terminate" in namespace: namespace["terminate"] = portable.terminate
    if "capture" in namespace:
        def capture(argv, *, cwd, env, directory, timeout, label, heartbeat=20, input_text=None):
            directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
            started = dt.datetime.now(dt.timezone.utc).isoformat()
            stamp = time.monotonic()
            result = portable.capture(adapt(argv), cwd=cwd, env=env, timeout=timeout, input_text=input_text)
            paths = {}
            for stream in ("stdout", "stderr"):
                text = result.pop(stream)
                scrub = namespace.get("scrub", lambda value, extra=None: value)
                try: text = scrub(text, env)
                except TypeError: text = scrub(text)
                path = directory / (stream + ".log"); path.write_text(text, encoding="utf-8")
                paths[stream] = str(path)
            result.update(paths=paths, started_at=started, finished_at=dt.datetime.now(dt.timezone.utc).isoformat())
            result['duration_seconds'] = round(time.monotonic() - stamp, 3)
            return result
        namespace["capture"] = capture
    if "stream_process" in namespace:
        def stream_process(argv, cwd, env, log_path, timeout):
            result = portable.capture(adapt(argv), cwd=cwd, env=env, timeout=timeout)
            Path(log_path).write_text(namespace["scrub"](result["stdout"] + result["stderr"]), encoding="utf-8")
            if result["timed_out"] or result["truncated"]:
                raise namespace["Blocked"]("Role exceeded its time/output limit")
            return result["exit_code"]
        namespace["stream_process"] = stream_process
