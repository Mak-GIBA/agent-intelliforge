#!/usr/bin/env python3
"""Bounded read-only review recovery; never overwrite the original failure records."""
import argparse
import concurrent.futures
import functools
import hashlib
import http.server
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import threading
from urllib.parse import urlsplit
from local_workflow import LocalWorkflow
from visual_benchmark import Benchmark, ROOT, Quiet, write

RULES = Path(__file__).with_name('local-recovery-contract.json')


class Recovery:
    def __init__(self, output):
        self.bench = Benchmark(output)
        self.rules = json.loads(RULES.read_text())

    def resume(self):
        name = self.rules['resume_case']
        original = self.bench.out / 'local-workflow' / name
        job = self.bench.out / self.rules['output_subdir'] / name
        if (job / 'result.json').exists():
            return json.loads((job / 'result.json').read_text())
        job.mkdir(parents=True, exist_ok=True)
        previous = json.loads((original / 'result.json').read_text())
        app = original / 'app'
        state_file = app / 'artifacts/ux-gan' / previous['run_id'] / 'state.json'
        state = json.loads(state_file.read_text())
        if not state.get('pending_review') or state.get('fix_in_progress') or state['iteration'] != 1:
            raise ValueError('Recovery requires exactly the original validated fixer and pending review')
        write(job / 'resume-input.json', {'protocol': self.rules, 'original_result': previous,
              'state_sha256': hashlib.sha256(state_file.read_bytes()).hexdigest()})
        source = job / 'source'
        source.mkdir()
        archive = subprocess.run(['git', 'archive', self.rules['source_commit'], 'tools/codex-ux-stack'],
                                 cwd=ROOT, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(source, filter='data')
        # Keep the original URL and test command; do not rewrite the frozen state.
        target = urlsplit(state['config']['url'])
        server = http.server.ThreadingHTTPServer((target.hostname, target.port), functools.partial(Quiet, directory=str(app)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        argv = [sys.executable, str(original / 'launch.py'), sys.executable, '-B',
                str(source / 'tools/codex-ux-stack/skill/scripts/harness.py'), 'resume', previous['run_id'],
                '--project', str(app), '--role-sandbox', self.rules['role_sandbox']]
        try:
            result = self.bench.call(argv, app, original / 'codex-home', job / 'harness.log',
                                     self.rules['phase_seconds'] + 80, child=False)
        finally:
            server.shutdown()
            server.server_close()
        state = json.loads(state_file.read_text())
        result.update(case=name, harness_status=state['status'], reason=state['reason'],
                      iteration=state['iteration'], run_id=state['run_id'],
                      contract_report=state.get('ux_contract_report'))
        write(job / 'result.json', result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return result

    def run(self):
        frozen = self.bench.out / 'local-readonly-conditions.json'
        if frozen.exists() and json.loads(frozen.read_text()) != self.rules:
            raise ValueError('Recovery conditions differ from their frozen copy')
        write(frozen, self.rules)
        workflow = LocalWorkflow(self.bench.out)
        workflow.bench = self.bench  # One budget lock for both concurrent operations.
        workflow.rules = self.rules
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(workflow.job, self.rules['fresh_case']), pool.submit(self.resume)]
            for job in jobs:
                job.result()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    Recovery(parser.parse_args().output).run()
