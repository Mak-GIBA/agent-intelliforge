# Design Research

**English** | [日本語](../../design-research/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md) · [Validation (Japanese)](../../design-research/validation.md)

See [Upstream and Research: outputs and review order](../upstream-research-workflow.md) for the project overview, primary documents, reports, and selected evidence.

Compare approaches for core logic—search, extraction, classification, reasoning—and report improvements grounded in sources and verification. This guide covers [install_design_research.sh](../../../install_design_research.sh) 2.7.0.

For effectiveness/accuracy/performance claims, freeze metrics, scoring, comparison conditions, and adoption criteria before experiments. Save baseline/candidate final outputs for the same inputs and recalculate reported scores from execution records. Unmeasured main effects leave effectiveness evaluation incomplete; design/literature studies may complete with explicitly conditional, unmeasured conclusions.

Execution progresses through minimal design/experiment assets, measurements/scoring, original-source checks, explanation, and review. Saved stages support reuse under unchanged conditions; required unfinished stages prevent overall completion.

<a id="codex画面から使う"></a>
<a id="目的に合わせた3つの使い方"></a>

## Choose by purpose

Open the target project in Codex and use the single `$design-research` entry:

```text
$design-research Improve search accuracy.
```

```text
$design-research Consider another approach using the previous research results.
```

```text
$design-research What has been completed, and which checks remain?
```

The Skill checks requirements, implementation, plan, and prior runs, then selects the relevant stage. You need not enumerate theme counts, candidate counts, figures, or CLI flags. Planning-only stops at planning; status-only does not experiment. Ambiguous targets/prior results require selection.

| Purpose | Entry | Main output |
|---|---|---|
| Compare a technique/algorithm | `$design-research` | Theme report |
| Organize research themes only | `$design-research` with “plan only” | Plan/dependencies |
| Reassess completed research | `$design-research` | New report and differences |
| Create/change overall requirements/design | `$upstream-new` / `$upstream-change` | Requirements/design/verification |

These are conversation Skill names, not terminal commands. Automatic selection depends on Codex; specify the entry when needed.

## Research expectations

Per theme, aim for about 5 methods including the current baseline and approaches with different principles. This is not a fixed theme count or permission to pad candidates. Read key primary sources through methods, conditions, results, and limits; use bounded experiments to compare or falsify claims. Distinguish literature values, earlier measurements, current measurements, hypotheses, and unmeasured claims.

The human report is normally `docs/design-research/<slug>/report.md`. Explain purpose/examples/terms/figures, and give any proposed method its own architecture, inputs/outputs, equations/pseudocode, differences, costs, and limits. Keep raw JSON/logs/archived reports; see [outputs](usage.md#evidence-and-outputs).

Japanese drafts may use kotonoha or available yomiyasu once, not both. Preserve claims, numbers, IDs, conditions, evidence, and certainty; absence does not block writing.

## Relationship with Upstream

[Upstream](../speckit-upstream/README.md) handles stories, use cases, requirements, overall design, and verification; Research handles technical comparisons/evidence. New or changed mechanisms need relevant themes researched/integrated before design finalization. Standard implementation needs existing evidence, while As-Is transcription/typos do not require global research.

Return each theme's contract/results to Upstream to check combined quality, latency, resources, and design. Independent themes in a plan do not imply parallel execution: same-project runs serialize under a lock. See [usage](usage.md) and [reassessment](../speckit-upstream/reassessment.md).

<a id="指摘を増やすより解決を優先する"></a>
<a id="uiuxキットとの関係"></a>

## Audit, fixes, and UI/UX

`audit` verifies core/backend behavior; `run` performs requested local fixes and independent rechecks, focusing on at most 3 important root causes. Research/design requests do not automatically authorize app fixes. See [terminal usage](usage.md#run-directly-in-a-terminal).

[UX Stack](../codex-ux-stack/README.md) handles screens, actions, state, and navigation. Apply available UI Skills to Upstream screen examples and distinguish static images, prototypes, and real operations. Existing UX reviews can be inputs, but screenshots alone cannot establish server architecture.

<a id="収録内容と前提"></a>

## Install and verify

Requires Bash and Python 3.11+. Distribution scripts normally fetch/check a pinned base before building; offline use requires two specific original installers. Harness execution additionally needs authenticated Codex, a working command sandbox, and project test prerequisites. See [installation](installation.md).

Updates retire only unchanged, verifiably owned old shortcut Skills; edited/unmanaged folders and old research material remain. Optional [migration](usage.md#migrate-older-material-into-one-report) consolidates reports.

Configured [Workgraph](../basic-memory-workgraph/README.md) may retain useful detailed experiment records under existing policy/permissions; see [capture](usage.md#retain-useful-experiment-details-in-workgraph). Research completion, adoption approval, and whole-system performance are separate checks. [Validation (Japanese)](../../design-research/validation.md) distinguishes assembly, lifecycle, and model limitations.
