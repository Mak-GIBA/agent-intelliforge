# Report-only native validation

`report_native.py` is an explicit, opt-in model study. It composes the supplied local report from fixed study records, then tests two synthetic cases: unmeasured design findings and equal measured results. It does not rerun research, tests, source access or paid research experiments.

```bash
python3.11 tools/design-research-upgrade/evals/report_native.py \
  --source /path/to/assembled/sources \
  --case-report /private/project/report.md \
  --case-state /private/project/state.json \
  --output .artifacts/report-native-new
```

The output directory must be new and private. Original inputs are checked for changes. The study freezes the configured model/effort and shares 900 seconds and at most 13 executions across all three uses and a blinded old/new comparison. Each use permits one repair; calls time out after at most 180 seconds. Incomplete/rejected cases remain incomplete, without automatic extension or forced passing.

Review the receipts and actual manuscripts, including observed reads of the selected writing Skill. The independent review rubric covers question, methods, results, support, adoption, limits and readability. A shared model reviewer can miss errors; its acceptance does not establish human acceptance or general quality. Do not commit private reports, frozen records or receipts. Public automated tests use synthetic records only.
