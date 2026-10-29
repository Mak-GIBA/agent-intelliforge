# Workgraph: troubleshooting and integrity review

**English** | [日本語](../../basic-memory-workgraph/troubleshooting.md)

[Overview](README.md) · [Installation](installation.md) · [Usage](usage.md) · [Sharing](sharing.md) · [Reference](reference.md) · [Documentation](../README.md)

Run commands at the repository root; requests go in Codex.

<a id="troubleshooting"></a>

## Troubleshooting

| Symptom | Check / action |
|---|---|
| New behavior unavailable | Start a new Codex session; inspect `/plugins` and `/hooks` |
| Retrieval says `unavailable` | Not a no-match result. Check registered projects and PyYAML in the retrieval Python; for Cloud, check CLI version and connectivity |
| Retrieval says `needs_context` | Add sanitized purpose, output, and constraint terms; “implement the plan” alone lacks context |
| CLI cannot locate a DB revision | Check CLI/DB compatibility before rebuilding or deleting anything. [Bind a compatible runtime](installation.md#recall-runtime); local retrieval reads registered Markdown |
| Stop asks for application verification | Compare adopted conditions with artifacts and run `check`; report unresolved conditions as unverified. Only one reminder is requested |
| Many pending lifecycle events | Events are not knowledge notes. `hook flush` archives event envelopes; it does not extract corrections or create notes |
| Lesson not saved | Check mode, evidence, reuse value, duplicates; no value correctly means no capture |
| Correction not saved | Check `correctionMode=scoped`, implementation mode, duplication, privacy |
| No Stop evaluation | Normal in Plan; implementation still needs this turn armed. Start a new session after update |
| No Cases | Default `caseMode=off`; use explicit requests, `reusable`, or `progressive` |
| No Skill created | Default `skillMode=review`; `auto` still needs creator, validation, and added value |
| PyYAML missing | Prepare [the environment](installation.md#python-tools) and use the same Python |
| Update exit 2 | Inspect `preserved`; retained custom files do not mean total failure |
| Storage missing/mismatched | Inspect `primaryProject` and registration; see [update details](installation.md#update-details) |
| Chronology/interpretation wrong | [Audit](#audit), then compare actual conversation evidence |
| `needs_review` blocks export | Resolve evidenced concerns and redo content review; do not just clear the flag |
| Zero exports | Check intended use, permissions, review, and post-edit fingerprints |
| `Missing or stale privacy review` | Inspect content and rerun `review`; specify both permissions if both intended |
| `Output already exists` | Use a new `--output`; existing exports are not overwritten |
| Import `conflicts` | Compare same-name notes or choose separate storage; no overwrite |
| Secret check rejects content | Anonymize and re-review; passing checks does not prove privacy |

Sharing/training `--dry-run` performs checks without persistent writes, but normal input constraints still apply, including existing output destinations. Exit 0 is success, 1 input/processing error, 2 skipped items or import conflicts. Export writes eligible items and reports exclusion reasons in `skipped`.

<a id="audit"></a>

### Review saved memory

Review after necessary writes, before reuse, on contradictory evidence, or by request. No scheduled sweep is added. Start with read-only structural checks:

```bash
# Audit the complete storage without changing notes or review metadata
python3 tools/basic-memory-workgraph/workgraph_tools.py audit --memory-dir "$HOME/knowledge/codex-memory"

# Audit one Case; replace the example path with a real note
python3 tools/basic-memory-workgraph/workgraph_tools.py audit \
  --memory-dir "$HOME/knowledge/codex-memory" --note "cases/example.md"
```

JSON identifies issue type, location, possible remedy, and potentially affected derived notes up to 2 levels away. Exit 0 means no structural finding, 2 findings, 1 input/processing error. `audit` is always read-only, including with `--dry-run`. Unsupported existing freeform Cases are reported rather than discarded.

CLI checks detect duplicate IDs, broken references, contradictory sequence/targets, and unsupported adoption assessments. **Structural success does not establish correct real chronology or interpretation.**

```text
Compare this Case's correction sequence and evaluation targets against available conversation evidence. Correct only established errors with reasons and history; mark unknown concerns for review. Check dependent Rules and Workflows too.
```

In implementation mode, repair only established errors, retaining sanitized before/after, reasons, and evidence. Real failed attempts and changed instructions are history, not record errors to erase. Unknown concerns become `integrity_status=needs_review`; do not use the Case as a positive precedent or export it. Check dependent evidence without bulk deletion/rewriting. Plan/read-only permits reporting and avoiding suspect claims only.

States `unreviewed`, `checked`, and `needs_review` are separate from sharing/training permission. Restore `checked` only after evidence review, structural recheck, and read-back. Content/state changes invalidate privacy review and require a new export review. No-change reviews do not append timestamps. Imported `checked` resets to `unreviewed`, while `needs_review` remains. See [AUDIT (Japanese)](../../../tools/basic-memory-workgraph/templates/AUDIT.md).
