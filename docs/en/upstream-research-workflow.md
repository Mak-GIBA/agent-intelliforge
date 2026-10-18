# Upstream and Design Research: outputs and review order

**English** | [日本語](../upstream-research-workflow.md)

Start with the target app's `docs/upstream/README.md`. This generated overview lists the current stage, documents and IDs to review, pending approval, research status, and next action. Upstream 2.1.0 / Design Research 2.6.0 refresh it after document, research, review, and approval updates. Projects with a custom `docs_dir` use its `README.md` instead.

Run these commands in the target app. The default and JSON views do not write files.

```bash
speckit-workbench overview --project .
speckit-workbench overview --project . --json
# Refresh the saved overview after changing documents
speckit-workbench overview --project . --write
```

An existing, unmanaged README is preserved. `--write` reports the conflict; retain and move or integrate its contents before generating the overview. Inspection-only requests do not save a new overview.

## Where files belong

Read the primary requirements, design, and verification documents first, then follow the relevant research report and fixed evidence. These files serve different purposes.

| Location | Contents | What to review | Git handling |
|---|---|---|---|
| `docs/upstream/README.md` | Generated overview | Stage, IDs, unresolved issues, next action | May be committed as shared navigation |
| `docs/upstream/requirements.md` | Goals, use cases, stories, functional/quality requirements, constraints | Outcomes, acceptance criteria, observed/agreed/proposed status | Commit as the primary requirements document |
| `docs/upstream/design.md` | Architecture, selected approaches, impact, research mapping | Requirement coverage, rationale, IDs, integration constraints | Commit as the primary design document |
| `docs/upstream/verification.md` | Verification plan, criteria, execution results | Planned versus executed checks, design mapping | Commit as the primary verification document |
| `specs/<feature>/` | Official SpecKit `spec.md`, `plan.md`, `tasks.md`, and related detail | Feature specification and implementation tasks | Commit needed feature detail |
| `docs/design-research/<topic>/report.md`, `figures/` | Latest research report and figures | Comparison conditions, conclusions, measurements, limitations | Commit human-facing reports |
| `docs/design-research/<topic>/evidence/<run-id>/` | Selected run's fixed report, inputs, outputs, required records, manifest | Supporting evidence, missing or modified files | Commit evidence used for design decisions |
| `.artifacts/design-research/<topic>/` | New topic's complete runs, state, trials, working copies, detailed logs | Resumption, reassessment, failure diagnosis | Ignored when a new topic is created; normally local |
| `.specify/workbench/` | Research plan, fixed reviews, trace indexes, approval ledger, gate | Approval scope, consistency, workflow diagnosis | Commit records needed to trace plans and agreement |

The topic-level `report.md` changes as work progresses. Bind adopted design rationale to a fixed report under an explicit run ID in `evidence/`. Publish a new run for a new adopted result; existing evidence packages are immutable.

Existing topics retain their locations. Old `docs/design-research/<topic>/runs/` records are neither moved nor deleted, and remain readable, resumable, and usable as reassessment input. Adding the ignore rule does not untrack existing records.

## What to check for each command

These are Skills selected in Codex's conversation interface. Every entry ends by identifying the overview and relevant IDs. Creating a document, reviewing it, recording approval, and verifying an app are separate outcomes.

| Entry | Outputs or updates | Reader's review target | Completion and next action |
|---|---|---|---|
| `$upstream-new` | Requirements, design, verification; feature specs and research if needed | User goals, stories, acceptance criteria, architecture, verification approach | Scoped documents and unknowns are recorded; proceed to review |
| `$upstream-existing` | Existing primary documents, separating observation/agreement/proposal | Implementation sources, differences from agreement, unsupported assumptions | Confirm current/proposed boundaries and review intended changes |
| `$upstream-change` | Affected requirements, design, verification | Rationale, affected IDs, compatibility, migration | Review the defined change and reapproval scope |
| `$upstream-bug` | Expected behavior, reproduction evidence, design/regression plan | Reproduction, expected/actual difference, proposed fix | Review findings and approach; request fixes separately |
| `$upstream-refactor` | Invariants, quality goals, design/migration plan | Preserved behavior, measurement, rollback | Review preservation and improvement criteria |
| `$upstream-check` | Findings; document edits only when requested | Ambiguity, contradictions, missing evidence, stale approval | Identify fixes and necessary review; inspection alone does not edit |
| `$upstream-review` | Fixed packet under `.specify/workbench/reviews/` | Prose, shared conditions, IDs, unresolved issues | Specify IDs to approve or revise; packet creation is not approval |
| `$upstream-approve` | Approval record for explicitly approved IDs | Review ID, item IDs, current approval state | Verify recording and consistency; stale items return to review |

## Example 1: standard booking design

Tell `$upstream-new` that staff need to view today's bookings, change them, and cancel them. Codex turns user goals, use cases, and concerns such as duplicate bookings into requirements. For parts covered by standard CRUD and transactions, it records the existing basis and determines whether research is necessary.

For example, `BOOK-FR-001` could require one saved booking change, `BOOK-DES-001` could specify a transaction, and `BOOK-TEST-001` could check the saved count during concurrent changes. These are illustrative IDs, not executed test results.

From the overview, review the requirement's acceptance criteria, the design approach and IDs, then the verification procedure and pass criteria. Use `specs/<feature>/` for needed feature detail. If no research was executed, there is no research report or evidence export. Fix the reviewed IDs in a packet and record only explicitly approved IDs. Approval of the verification plan does not mean the app tests have run.

## Example 2: research to improve search accuracy

Tell `$upstream-change` that search should miss fewer relevant documents while preserving response time. Codex reviews requirements and decomposes uncertain logic into questions such as candidate generation and ranking. `.specify/workbench/research-plan.json` records requirement IDs, questions, frozen inputs/evaluation conditions, and dependencies.

After each theme's research, follow the overview to `docs/design-research/ranking/report.md`. Review comparison conditions, actual baseline/candidate outputs, primary metrics, failure cases, and limitations. A `research_complete` state alone establishes neither adoption into the overall design nor measurement of the desired effect.

For a selected run named `RUN-EXAMPLE`, Codex previews and fixes the evidence as follows. Replace the topic and run ID with actual values.

```bash
bash <design-research-skill>/scripts/gan-harness.sh export-evidence \
  --project . --topic ranking --run-id RUN-EXAMPLE --related-id SEARCH-DES-001
# Apply the same selection after inspecting the preview
bash <design-research-skill>/scripts/gan-harness.sh export-evidence \
  --project . --topic ranking --run-id RUN-EXAMPLE --related-id SEARCH-DES-001 --apply
```

The package is written to `docs/design-research/ranking/evidence/RUN-EXAMPLE/`. Its manifest records the run ID, source revision, related IDs, and file hashes. Required stdout/stderr, evaluation inputs/outputs, execution receipts, and frozen requirements/research-plan inputs are retained. Missing or changed dependencies prevent export.

Codex adds the selected candidate, design IDs, and rationale to the returned binding and records it in the design document's v3 binding. Review requirement coverage, fixed-report links, and whole-system quality/latency/cost checks. Individual study success does not establish integration success. Return integration verification plans to `verification.md` before review.

## Verify evidence after cloning

Commit human-facing reports, figures, and the evidence used for adopted design decisions. Keep interim trials and working copies locally. Inspect the Git diff before committing and pushing.

A separate clone can read the overview, primary documents, fixed reports, and figures. Verification does not require the original `.artifacts/` workspace:

```bash
bash <design-research-skill>/scripts/gan-harness.sh verify-evidence \
  --package docs/design-research/ranking/evidence/RUN-EXAMPLE
```

This verifies recorded dependency existence and hashes. It does not certify scientific validity, identity, or user approval. Full resumption needs the original local run records and environment. Changed requirements or conditions require fresh research or reassessment rather than resuming the same frozen run.

## Short entries and detailed procedures

The eight Upstream entries retain essential routing and use `flow --brief` plus the relevant stage in `PHASES.md`. Default `flow` still prints the detailed procedure. Design Research loads execution/evaluation/evidence contracts when running research; status inspection does not require those long references.

Measure entry length and mandatory startup reading separately. Moving instructions into another file is not itself a reduction in reading: the workflow should load the references needed for the current stage.
