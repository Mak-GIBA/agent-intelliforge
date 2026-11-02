"""Missing/cross-version observations must never turn into paid blind ratings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('visual_benchmark_test',ROOT/'tools/codex-ux-stack/evals/visual_benchmark.py')
benchmark=importlib.util.module_from_spec(spec);spec.loader.exec_module(benchmark)


class VisualEvaluationTests(unittest.TestCase):
    def test_requested_measurement_is_required_before_any_rating_call(self):
        for mode in ['settled','stable']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                runner=benchmark.Benchmark(directory)
                with patch.object(runner,'call') as call:
                    with self.assertRaisesRegex(ValueError,'Missing requested observations'):
                        runner.ratings(settled=mode=='settled',stable=mode=='stable')
                    call.assert_not_called()

    def test_static_rating_cannot_use_an_older_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            runner=benchmark.Benchmark(directory)
            for case in runner.conditions['cases']:
                for trial in range(1,runner.conditions['trials']+1):
                    for label in ['baseline','candidate']:
                        p=Path(directory)/'generation'/f'{label}-{case}-{trial}'/'operations-stable.json'
                        p.parent.mkdir(parents=True);p.write_text(json.dumps({'revision':3}))
            with patch.object(runner,'call') as call:
                with self.assertRaisesRegex(ValueError,'Wrong observation revision'):
                    runner.ratings(stable=True)
                call.assert_not_called()


if __name__=='__main__':unittest.main()
