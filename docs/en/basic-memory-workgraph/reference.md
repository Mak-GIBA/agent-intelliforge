# Workgraph: policy, layout, and mechanisms

**English** | [日本語](../../basic-memory-workgraph/reference.md)

[Overview](README.md) · [Installation](installation.md) · [Usage](usage.md) · [Sharing](sharing.md) · [Troubleshooting](troubleshooting.md) · [Documentation](../README.md)

Run commands at the repository root unless specified otherwise; requests go in Codex.

<a id="details"></a>

## Policy, layout, and mechanisms

### Capture quality

The maintained policy is [memory-policy.md (Japanese)](../../../tools/basic-memory-workgraph/memory-policy.md). Automatic abstract Memory requires all five criteria:

| Criterion | Requirement |
|---|---|
| Transfer | A concrete use beyond the originating task |
| Utility | Improve a future decision/procedure, avoiding a named mistake or investigation |
| Evidence | Actual verification supports the claim; one sufficient check can qualify |
| Durability | Conditions, exceptions, and recheck triggers are clear |
| Added value | Not duplicated or easily recovered common knowledge |

Explicit ongoing preferences can also qualify with scope/exceptions. Diaries, completion reports, output inventories, generic advice, and unsupported guesses do not qualify automatically.

Progressive Cases may include successes without corrections, keeping inferred adoption separate from observed behavior. `acceptance` is explicit approval, `assessments` inferred adoption, and `verification` the tested property. Unknown acceptance does not prevent otherwise qualified capture/reuse; verification-only Cases leave adoption empty. Searchable Observations summarize context, useful traits, evidence type, and limits. Interaction retains actual sequence and counterevidence. See [evidence design (Japanese)](../../basic-memory-workgraph/evidence-design.md). No new knowledge means no timestamp-only update. Failed duplicate search means skip automatic capture.

`smart` uses Japanese/English correction, adjustment, success, adoption/reversal, finding/workaround signals and candidates Codex recognizes semantically. Detection is neither complete nor permission to write; Codex evaluates content.

### Workflow review and prompt length

Review attempts, obstacles, remedies, verification, and next applicability as an operational summary, not private reasoning. A verified remedy does not establish its cause. Hooks supply common admission criteria once; detailed Case/Correction/audit/Skill procedures are read only before relevant operations.

Hook length is checked against a [fixed baseline](../../../tests/fixtures/workgraph-prompt-baseline.json) under the same four configurations, normalizing environment paths only. Common policy, reference guidance, and arming commands count. This is character measurement, not real input-token or decision-quality measurement. Tests require at least 20% shorter full prompts, deployed references, mode/config preservation, and one evaluation. Semantic choices use [fictional scenarios (Japanese)](../../../tests/POLICY_SCENARIOS.md).

On 2026-10-12, `auto=smart / correction=scoped / case=progressive / skill=review` gave:

| Full hook, characters | Before | After | Reduction |
|---|---:|---:|---:|
| Start | 20,120 | 13,604 | 32.4% |
| Stop | 18,282 | 13,310 | 27.2% |

Default, Case/registration-enabled, and automation-off settings also met the reduction threshold. Automation off does not start Stop capture evaluation. Common policy shrank from 16,628 to 12,718 characters. Workgraph's 38 tests, existing-install update's 14 tests, and Bash syntax checks passed.

### Read in Plan; evaluate writes in implementation mode

The start hook supplies recall guidance and a session/turn-specific arming command. Codex runs it before answering only after confirming current implementation mode and write availability. Users normally need not run it. Plan/read-only and Stop continuations must not arm. The Stop hook requests one evaluation only for armed turns.

Plan can recall Memory. A short Stop gating process still runs, but not an extra capture turn. Missing/stale tokens, another turn, invalid setup, or `auto=off` suppress evaluation; turns begun before update have no token.

Codex 0.157.1's `permission_mode` reflects approval settings, not collaboration mode ([implementation](https://github.com/openai/codex/blob/rust-v0.157.1/codex-rs/core/src/hook_runtime.rs#L1031)). Arming therefore depends on Codex checking mode; omission skips evaluation. Explicit `permission_mode=plan` is also refused. Policy forbids writing after a later switch to Plan, even if armed. This is not direct host-mode verification or an MCP-wide write enforcement boundary.

State contains only a random control token, candidate/armed flags, and format version, not conversation content. Tokens are consumed at Stop to prevent duplicate/concurrent evaluation. Raw transcripts are not read.

### Note locations

| Directory | Content |
|---|---|
| `rules/` | Conditional rules and explicit ongoing preferences |
| `workflows/` | Reusable procedures and Skill packaging rationale |
| `validations/` | Reusable verification methods |
| `cases/` | Concrete interactions and existing freeform Cases |
| `corrections/` | Explicit requests or `correction=scoped` contextual corrections |
| `artifacts/` | References to outputs / registered Skills |
| `projects/` | Explicitly requested long-lived scope |
| `schemas/` | Structural definitions |

Existing note types remain; new fields are optional and notes are not batch-converted. A structured `type: case` note contains versioned JSON while keeping normal Observations/Relations. Link independently admitted notes with relations such as `generalized_to` and `learned_from`; see [CAPTURE (Japanese)](../../../tools/basic-memory-workgraph/templates/CAPTURE.md).

[Skill packaging (Japanese)](../../../tools/basic-memory-workgraph/templates/SKILL_REVIEW.md) requires an Artifact with `kind: skill` and `skill:<name>` only after registration, linked from Workflow via `packaged_as`. Execution belongs in the Skill, background/evidence/conditions in Workgraph. Do not create companion notes merely to populate relations.

### Sharing and training metadata

| Field | Default | Meaning |
|---|---|---|
| `sharing_scope` | `private` | Explicit `team` / `public` designation |
| `training_use` | `excluded` | Explicit `approved` designation |
| `privacy_review` | `pending` | Content-review state |
| `review_sha256` | Absent | Fingerprint tied to content/metadata |
| `integrity_status` | Treat as `unreviewed` | `needs_review` blocks sharing/training export |

Missing fields on old notes mean private/excluded. These fields select export eligibility; they are not file access controls or encryption.

### Installed files

Paths below are relative to `${CODEX_HOME:-$HOME/.codex}`.

| Path | Content |
|---|---|
| `basic-memory.json` | Project and policy; `checkpointOnCompact=false` |
| `basic-memory-workgraph/config.json` | Capture, Case, and Skill modes |
| `basic-memory-workgraph/memory-policy.md` | Common hook criteria |
| `basic-memory-workgraph/templates/` | Case, Skill review, schemas |
| `basic-memory-workgraph/workgraph_tools.py` | Share, JSONL, audit, registration CLI |
| `basic-memory-workgraph/workgraph_sequence.py` | Case v2 sequence/evidence validation |
| `basic-memory-workgraph/workgraph_github.py` | Private GitHub PR/pull/update CLI |
| `basic-memory-workgraph/github-sharing.json` | Setup profiles |
| `basic-memory-workgraph/github-state/` | Import fingerprints, commits, locks; no note bodies |
| Managed `AGENTS.md` block | Route memory-sharing requests; retain other instructions |
| `hooks/basic_memory_workgraph.py` | Recall/policy/evaluation prompts |
| `hooks.json` | Hook registrations |

The installed CLI also works outside the repository:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/workgraph_tools.py" --help
```

Its Python still needs PyYAML; GitHub sharing needs git/gh. Existing authentication is reused and not saved in sharing state. There is no recurring/hook-driven send; see [GitHub sharing](github-sharing.md).

Official Plugin configuration discovery follows its own rules; project `.codex/basic-memory.json` can take precedence. Existing `captureEvents` is preserved (default true when absent). Official event recording differs from these hooks, which do not record bodies. Automatic compaction checkpoints remain disabled.

`connect` / `sync` store repository connections under `connections` in `github-sharing.json`.
Received sources and preserved edits live under `shared-memory/<repo-id>/` beside the personal memory project.
Receiving projects are appended to the user's `secondaryProjects`; existing publishing profiles, writing projects, and unrelated settings are preserved.
