# Share Memory and export training data

**English** | [日本語](../../basic-memory-workgraph/sharing.md)

[Overview](README.md) · [Installation](installation.md) · [Usage](usage.md) · [Reference](reference.md) · [Troubleshooting](troubleshooting.md) · [Documentation](../README.md)

Run terminal commands at the repository root unless stated otherwise. Requests go in Codex.

<a id="share"></a>

## Share Memory

[GitHub sharing](github-sharing.md) handles export/PR creation and receipt of merged updates through conversation. Below is file-based export/import. `workgraph_tools.py` writes locally; `workgraph_github.py` sends through GitHub.

Activate the [Python environment](installation.md#python-tools). Replace `rules/example.md` with an actual path relative to Memory storage and quote paths with spaces. Replace `--memory-dir` for custom storage.

### Review the note and authorize sharing

Inspect body, title, metadata, and links; remove credentials, confidential data, and unnecessary personal information before marking team sharing reviewed.

```bash
python3 tools/basic-memory-workgraph/workgraph_tools.py review \
  --memory-dir "$HOME/knowledge/codex-memory" \
  --note "rules/example.md" --sharing team
```

`review` records a completed content review and output authorization; it does not anonymize content. Automated checks also refuse common secret patterns.

### Export the share directory

```bash
python3 tools/basic-memory-workgraph/workgraph_tools.py export-share \
  --memory-dir "$HOME/knowledge/codex-memory" \
  --scope team --output ./team-memory
```

This writes reviewed `team` notes and a manifest. `--include-cases` also requires each Case's team designation and review. `--scope public` selects only public notes; team and public are separate categories.

Unshared notes are not pulled in through links. Links to excluded/ambiguous wiki or local Markdown targets are removed in exported copies, leaving originals untouched. Attachments, executables, and Skill bodies are excluded.

### Import on the receiving side

```bash
python3 tools/basic-memory-workgraph/workgraph_tools.py import-share \
  --memory-dir "$HOME/knowledge/imported-memory" --bundle ./team-memory
```

This example uses a new directory. For an existing Basic Memory project, use its registered location; register a new location separately:

```bash
bm project add imported-memory "$HOME/knowledge/imported-memory"
```

Identical imports make no changes. Different content at the same path stops the entire import without overwriting. Imported notes retain provenance but reset to `private` and excluded from training. Imported instructions are not executed and Skills are not registered. After registration, use normal Basic Memory sync/search.

<a id="training"></a>

## Export training JSONL

**Case capture, sharing permission, and training permission are independent.** A saved Case is not automatically training data. Inspect/anonymize a Case in [CAPTURE format (Japanese)](../../../tools/basic-memory-workgraph/templates/CAPTURE.md) and explicitly authorize training. Old freeform Cases are not automatically completed or converted.

Activate [Python](installation.md#python-tools) and replace `cases/example.md`:

```bash
# Authorize local training use; keep sharing private
python3 tools/basic-memory-workgraph/workgraph_tools.py review \
  --memory-dir "$HOME/knowledge/codex-memory" \
  --note "cases/example.md" --training approved

python3 tools/basic-memory-workgraph/workgraph_tools.py export-cases \
  --memory-dir "$HOME/knowledge/codex-memory" --output ./cases.jsonl
```

Output is generic JSONL, one Case per line.

| Field | Meaning |
|---|---|
| `format_version` | Export version |
| `source_id` | Identifier based on original note path |
| `interaction` | v1 legacy content; v2 context, ordered steps, assessments, evidence, correction history |
| `integrity_status` | v2 only; Cases needing review are excluded |
| `relations` | Typed target identifiers, without related note bodies |

The outer `format_version` remains 1; `interaction.version` distinguishes v1/v2. Preserve summaries versus excerpts, verification versus acceptance, inferred adoption versus confirmed labels, and unknown/unfinished outcomes. Later processing can select records and convert requests/corrections plus improved outputs to SFT-like formats, but must not treat summaries as original quotations or unknown outcomes as success. This tool exports generic JSONL only; SFT conversion, LoRA training, and model ingestion are outside its scope.

### Authorize both sharing and training

Omitted `review` permissions default to private/excluded. Specify both in a single call when authorizing both:

```bash
python3 tools/basic-memory-workgraph/workgraph_tools.py review \
  --memory-dir "$HOME/knowledge/codex-memory" \
  --note "cases/example.md" --sharing team --training approved
```

Body/metadata edits invalidate the content fingerprint and require a new review. Automatic capture never grants sharing/training authorization.
