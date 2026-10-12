"""Opt-in, non-model boundary probe using temporary fixtures only."""
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile

from .catalog import ForgeError
from .portable import capture


def smoke(agent, state=None):
    with tempfile.TemporaryDirectory(prefix='intelliforge-isolation-') as temporary:
        root=Path(temporary);project=root/'project';project.mkdir()
        allowed=project/'allowed.txt';allowed.write_text('allowed')
        outside=root/'outside.txt';outside.write_text('outside')
        # The write must be denied, and the original must remain byte-for-byte.
        program='import pathlib,json; p=pathlib.Path('+repr(str(allowed))+'); result={"read":p.read_text()=="allowed","write_denied":False};\ntry:p.write_text("changed")\nexcept OSError:result["write_denied"]=True\nprint(json.dumps(result));raise SystemExit(0 if all(result.values()) else 3)'
        if agent=='codex':
            executable=shutil.which('codex')
            if not executable:raise ForgeError('Codex CLI is missing')
            command=[executable,'-c','sandbox_mode="read-only"','sandbox','--',sys.executable,'-c',program]
        else:
            from .provider import isolated_command
            command=isolated_command([sys.executable,'-c',program],project,[],False,timeout=15,state=state)
        result=capture(command,cwd=project,env=os.environ.copy(),timeout=20)
        intact=allowed.read_text()=='allowed' and outside.read_text()=='outside'
        return {'agent':agent,'isolation_ready':result['exit_code']==0 and intact and not result['timed_out'],
                'exit_code':result['exit_code'],'fixtures_intact':intact,
                'stdout':result['stdout'][-1000:],'stderr':result['stderr'][-1000:],
                'scope':'Temporary read-only filesystem boundary only; no model or browser quality assertion.'}
