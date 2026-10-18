# Use SpecKit Upstream

**English** | [日本語](../../speckit-upstream/usage.md)

[Overview](README.md) · [Installation](installation.md) · [Reassessment](reassessment.md) · [Documentation](../README.md)

## First request

Use the target app's `docs/upstream/README.md` as the entry point. `speckit-workbench overview --project .` reads the latest state; add `--write` after editing documents to refresh the saved page. Custom projects use their configured `docs_dir`. See [outputs and review order](../upstream-research-workflow.md).

After user-wide installation, open the app in Codex. New development starts with `$upstream-new`; existing apps with `$upstream-existing`. Missing project setup triggers [attach guidance](installation.md).

```text
$upstream-new I want a booking app where store staff can see today's and unattended bookings, change them, and cancel them.
```

```text
$upstream-existing Organize the booking functionality in this repository.
```

Describe user/purpose rather than CLI flags. New design develops concerns, use cases, verifiable requirements, research, architecture, and verification. Existing analysis separates observed As-Is, sourced agreed specifications, and proposed To-Be. App implementation needs another instruction.

<a id="8つのコマンド"></a>

## Select a Skill by purpose

| Entry | Outcome |
|---|---|
| `$upstream-new` | Goals, requirements, stories, design, verification plan |
| `$upstream-existing` | Current state, agreed specifications, desired state |
| `$upstream-change` | Change rationale, requirement IDs, design/test impact |
| `$upstream-bug` | Expected behavior, reproduction, related requirements, fix/regression plan |
| `$upstream-refactor` | Preserved behavior, improvement goals, design/migration plan |
| `$upstream-check` | Content review and structural checks |
| `$upstream-review` | Fixed next-checkpoint review packet |
| `$upstream-approve` | Record explicit approval for a specified review/item ID |

These custom Skills are explicit-only conversation entries, distinct from shell commands or official `$speckit-*`. Bug analysis is not automatic fix authorization. List commands with `speckit-workbench commands`.

## From stories through research to design

```mermaid
flowchart LR
  S["Stories and goals"] --> C["Concerns and constraints"]
  C --> U["Use cases"]
  U --> R["Verifiable requirements"]
  R --> P["Research questions by theme"]
  P --> D["Approach research and PoCs"]
  D --> I["Integration and whole-system checks"]
  I --> A["Design and verification plan"]
  A --> V["Review and explicit approval"]
```

Arrows show handoff order, not automatic execution or approval. Upstream handles goals/experience/requirements/design; Research handles approaches, PoCs, and evidence. Complete required requirement review/approval and freeze requirements/plan before research. Changed requirements or approval metadata do not make an old run evidence under the new inputs.

New/changed mechanisms need theme research before finalizing. Standard CRUD can be `standard` with implementation/specification/test evidence. As-Is/typos need no global research. Unavailable Research allows requirements/As-Is work but leaves necessary research unexecuted and design unfinalized. No automatic Research installation or app fixes are implied.

### Turn concerns into use cases

Read existing material first; resolve unknowns affecting value, behavior, or usability. Connect concerns such as irreversible cancellation or trust in results to operations and success criteria. Keep unanswered points hypothetical/undecided; high-impact unresolved concerns prevent finalization.

Use cases state actor, goal, trigger, prerequisites, initial state, steps/feedback, and success. Include relevant empty/error/loading/permission/duplicate/interruption/recovery/undo/input-preservation/accessibility states. Propose success rate, hesitation, rework, or timing checks without claiming unmeasured usability. Trace story → use case → requirement → design → verification IDs. Use-case IDs are body identifiers referencing existing metadata, not a new `type`.

### Read overall design before details

`design.md` explains purpose/example, themes, boundary/architecture, components, representative flow, data/API/failure behavior, checks/limits. Match diagram names/IDs, identify expanded components and arrow payloads, and explain each diagram's question/reading in text. Framework selection records layer/name/role/version/status/reason/alternatives/evidence; distinguish implemented/proposed/unverified. Link research archives rather than duplicating full reports.

### Include screen examples

Actually apply available UI/UX Skills such as ooui-design, Product Design, or Build Web Apps when suitable. Identify objects/attributes/actions/states/navigation and relevant primary/empty/loading/success/failure/recovery screens. Distinguish static images, working prototypes, and actual app operations. If no suitable Skill is available, defer screen-example completion; design-only requests do not authorize app implementation.

## Revisit existing requirements and designs

Use existing/check to establish current state and ambiguous requirements/evaluation, then change for behavior/acceptance/quality-contract changes, or refactor for internal changes preserving external behavior.

```text
$upstream-change Reduce missed search results and revisit the current approach and quality requirements.
```

Use `reassess` for completed research under changed conditions and `resume` for interrupted unchanged work. See [scenarios](reassessment.md).

## Create and inspect documents

Confirm goals/unknowns and write supported content. Run terminal commands in the **attached app root**, not the installer checkout:

```bash
# Check placement, CLI startup, and project configuration
speckit-workbench doctor --project .

# Check draft document structure
speckit-workbench check --project . --phase draft

# Write the internal traceability index
speckit-workbench trace --project . --write
```

`check` is read-only; `trace --write` creates generated records. Structure success does not prove semantic or implementation correctness.

## Record review and approval

Use `$upstream-review`, inspect review/item IDs, content, and unresolved points; fix content first if needed; explicitly identify approved IDs; then record with `$upstream-approve`. Repeat for each checkpoint.

```bash
speckit-workbench approval-plan --project .
speckit-workbench review --project . --checkpoint next --write
```

Use actual review/item IDs; example values are placeholders. `--by` identifies approver and `--reference` actual explicit approval evidence.

```bash
# Preview approval only
speckit-workbench approve --project . \
  --review rev-YYYYMMDDTHHMMSSZ-xxxxxxxxxx --id APP-FR-001 \
  --by "user" --reference "Reference to confirmed explicit approval"
```

Add `--apply` only after actual explicit approval and target verification. Saving a review does not approve it; a name is not identity authentication. Approval binds item content, ordinary Markdown body, and direct dependency hashes. Changes cause `STALE_APPROVAL` / `STALE_DEPENDENCY_APPROVAL`; re-review. Record mistakes/withdrawal with:

```bash
# Preview first; add --apply to record the change
speckit-workbench revoke-approval --project . --id APP-FR-001 \
  --by "user" --reference "Actual evidence for approval withdrawal"
```

### Approval profiles

Attach defaults to `normal`. Change with `approval-profile --set` and apply with `--apply`.

| Profile | Stages |
|---|---|
| `small` | scope → solution |
| `normal` | intent → requirements → solution |
| `critical` | purpose → stories → requirements → design → verification |

```bash
speckit-workbench approval-profile --project .
speckit-workbench approval-profile --project . --set critical
```

## Check document state before implementation

```bash
# Check current structure only
speckit-workbench gate --project .

# Record passing document/configuration hashes
speckit-workbench gate --project . --write

# Verify targets have not changed since the snapshot
speckit-workbench gate --project . --verify
```

Gate checks required upstream items, requirements/design/verification plans, and selected approval stages. Goals alone or empty/heading-only required docs cannot be READY. A complete verification **plan** may still have `not_run` test results; this is not app test success.

New/change design retains `upstream-design-contract:v2` for workstream requirements and uses a schema-version-3 binding to selected published evidence: requirements/plan SHA-256, fixed run state/report/manifest, choices, standard evidence, integration, and UI Skill application. Distinguish `planned`, `verified`, and `inconclusive`; files alone cannot establish valid measurement. Existing v1/v2 bindings remain readable. Semantic review is separate from CLI checks, which fail nonzero without automatically configuring CI/merge rules. `gate --verify` detects stale snapshots, not malicious same-user tampering.

<a id="成果物の保存先"></a>

## Output locations and review targets

Defaults below follow configured `--docs-dir`:

| Document | Content |
|---|---|
| `docs/upstream/README.md` | Generated stage, review targets/IDs, pending decisions, next action |
| `docs/upstream/requirements.md` | Goals/users/scope/features/quality/constraints/current/desired state/unknowns |
| `docs/upstream/design.md` | Architecture/behavior/data/API/operations/choices/impact |
| `docs/upstream/verification.md` | Acceptance/methods/results/unexecuted checks/evidence |
| `docs/design-research/<slug>/report.md` | Executed research comparison/results/changes/gaps |
| `docs/design-research/<slug>/evidence/<run-id>/` | Fixed report and required evidence for a selected run |
| `.artifacts/design-research/<slug>/` | New topic's local execution records and working copies |

Internal reviews/approval summaries/indexes live in `.specify/workbench/`; Research JSON lives in `.internal/` within the local workspace, or the original workspace for existing topics. Read the overview, then primary sections/conclusions and fixed evidence. Pending approval also links one fixed review packet and item IDs. Official `specs/<feature>/spec.md`, `plan.md`, and `tasks.md` remain detailed references.

Content sections use unique `<!-- upstream:section ID -->` / `<!-- /upstream:section -->` markers. Section edits require that section reviewed; shared conditions outside sections affect the whole document; upstream dependency changes affect related lower items. Old unsectioned documents bind the whole body. Updates alone do not invalidate otherwise valid old approvals.

## Migrate existing material to three documents

```bash
# Inspect bodies, moves, link changes, review scope, and backups without writing
speckit-workbench migrate --project .
# Apply the reviewed migration
speckit-workbench migrate --project . --apply
# Explicitly include a custom upstream document only if intended
speckit-workbench migrate --project . --include-doc docs/upstream/custom.md --apply
```

Consolidate the old 19 standard docs and legacy CLI item files. Mixed-type documents remain one section to preserve body scope. Keep official SpecKit and custom additions; first repair retained links or explicitly include a custom document. Back up body/settings in `.specify/workbench/migrations/` and preserve IDs/sources/evidence/approval history. Changed placement/binding needs review; old approvals are not automatically rebound. Duplicate IDs, corrupt records, unresolved links, or conflicts stop. Failed application restores documents/settings; completed reruns are unchanged. See [Research migration](../design-research/usage.md#migrate-older-material-into-one-report).
