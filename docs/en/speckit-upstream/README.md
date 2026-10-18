# SpecKit Upstream

**English** | [日本語](../../speckit-upstream/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md) · [Reassessment](reassessment.md)

Clarify user goals, concerns, use cases, and requirements before implementation, then create overall design and verification plans using technical research. This guide covers Workbench 2.0.6 in [install_speckit_upstream.sh](../../../install_speckit_upstream.sh), which verifies a pinned base and applies embedded upgrades.

## Read these documents first

New projects use three primary documents, plus one report per executed research theme. Lead each with conclusions, requested decisions, and unknowns before detail.

| Question | Primary document | Content |
|---|---|---|
| What to build/preserve? | `docs/upstream/requirements.md` | Goals, users, concerns, use cases, features, quality, constraints, current/desired state, unknowns |
| How to implement it? | `docs/upstream/design.md` | Research mapping, architecture/detail/flows, choices, impact |
| What has been verified? | `docs/upstream/verification.md` | Acceptance criteria, methods, integration checks, actual results/gaps/evidence |
| What did research establish? | `docs/design-research/<slug>/report.md` | Conclusions, comparison, proposed method, verification, limits; only if executed |

Review snapshots, JSON indexes, approval ledgers, and raw logs remain internal records. Updates alone do not migrate old documents; see [optional migration](usage.md#migrate-existing-material-to-three-documents). Official feature `spec.md`, `plan.md`, and `tasks.md` remain detailed references.

Polish Japanese drafts once using available kotonoha or yomiyasu, not both, before review/approval. Preserve claims, numbers, IDs, conditions, results, evidence, and certainty. Missing writing tools do not block work; editing approved content requires review again.

## Components

| Component | Source | Role |
|---|---|---|
| SpecKit CLI (`specify`) | GitHub Spec Kit | Project initialization, templates, agent integration |
| `speckit-workbench` | This repository | Upstream templates, traceability, structure checks, reviews/approvals |
| `upstream-*` Skills | This repository | Goal-specific new/existing/change/bug/refactor procedures |
| `speckit-workbench` Skill | This repository | Shared/legacy compatibility entry |
| Design Research | [Separate installer](../design-research/installation.md) | Technical questions, comparisons, PoCs, theme evidence/reports |

[Spec Kit](https://github.com/github/spec-kit) connects specifications to planning/tasks. Workbench adds linked goal-to-design/verification procedures. It is not an official SpecKit, OpenAI, or ECC distribution or a guarantee of complete standards compliance.

## When to use it

Clarify a new app from goals/concerns; distinguish implementation from agreed requirements and proposals; trace change impact; integrate technical research; or detect changes to approved documents.

```text
$upstream-new I want an app that searches internal documents and answers with supporting evidence.
```

```text
$upstream-change Reduce missed search results while revisiting latency and cost constraints.
```

Proceed through story → concerns → use cases → requirements → technical questions → theme research → integrated design → verification. New/changed mechanisms require relevant research before design finalization. Standard implementation uses evidence-backed `standard`; As-Is/typos do not mandate global research. Missing research permits requirements/As-Is progress but prevents finalizing the dependent design. Use actual available UI/UX Skills for screen examples.

See [usage](usage.md) for entries, diagrams, screens, reviews, and approval; [reassessment](reassessment.md) for workstreams and existing decisions. Research completion is not adoption approval; implementation needs its own request.

## Two-stage installation

First install shared CLI/assets/Skills; then `attach` project documents/settings. Missing `specify` is fetched as `specify-cli==1.0.8` into a dedicated venv. Existing compatible CLI is reused, never silently upgraded. Upstream and Research are installed separately: building both scripts does not install both. See [installation](installation.md) and [validation (Japanese)](../../design-research/validation.md).

## What checks establish

`check` / `gate` inspect structure, references, required content, research/design mapping, and approvals. New/change v2 contracts tie requirement/plan/theme-run/integration state; v1 remains readable. Checks do not establish semantic adequacy, source/test truth, or reviewer identity. Skills are instructions, not access controls or universal enforcement. App tests/CI gates are not configured automatically.

## Inspect detailed references

Installed `releases/2.0.6/README_COMMANDS.md` and `assets/references/` contain commands and guidance, including `RESEARCH_FIRST.md` / `RESEARCH_WORKSTREAMS.md`. `--extract-bundle` exposes upgrade sources offline; `--extract` exposes assembled assets. See [installation](installation.md) and [output locations](reassessment.md#output-locations-and-review-targets).

The guide follows bundled upgrades/pinned implementation. General Spec Kit information was checked on 2026-09-29; do not assume latest upstream operations apply unchanged to the pinned version.
