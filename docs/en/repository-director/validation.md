# Repository Director validation

**English** | [日本語](../../repository-director/validation.md)

[Overview](README.md) · [Installation](installation.md) · [Usage](usage.md)

## Reference structure

LISTBOX's actual AGENTS, README, document index and six functional, screen, API, data, architecture/operations and testing specifications were read.
Their short entrypoints, links, separated responsibilities and explicit unknowns informed this kit. Framework and project-specific test restrictions were not generalized.
A read-only initialization preview reused its existing functional, architecture/operations and testing documents and proposed only missing purpose, policy and core-logic documents. The reference repository was not modified.

## Functional checks

On 2026-10-31, an isolated copy of tracked/new source files passed 506 tests with 5 skips and no failures/errors.
The focused kit suite passed 32 tests; standalone self-test passed 25. Statement coverage was 88% across the five new engine/migration files, not the whole application.
All 636 generated files matched; wheel/sdist builds, temporary wheel installation, both host previews, retired-ID rejection and 39 documentation pages were checked.
The environment used Python 3.12.13 and PyYAML 6.0.3, excluding ignored local archives/caches.
See [hashes and results](../../repository-director/evidence/test-results.json).


```bash
python3 -B -m unittest discover -s tests -p test_repository_director.py -v
bash install_repository_director.sh --self-test
python3 tools/repository-director/build_installer.py --check
```

Isolated tests cover lifecycle, ownership/edit protection, migration and rollback; existing code with missing/partial/custom documents; monorepo boundaries; preserved source/dependency files; links/Unicode anchors; staged/unstaged/untracked changes.
Mock CLI responses cover pagination, subgroup encoding, failures, bounded/incomplete results and MR note reads.

## Generated writing

The explicit `tools/repository-director/evals/run.py` comparison uses the same fictional inputs and CLI settings for old/new instructions.
It generates commits, PR/MR descriptions, reviews, handoff comments and existing-code document proposals. Review the actual prose against the supplied facts, uncertainty and existing rules.
Installation/self-test never call a model. Lint/string matches alone do not establish quality. No posts, commits or pushes are requested.
The [Japanese results](../../repository-director/validation.md) record the observed outcome and limitations.

## Branch and PR/MR workflow

Version 1.1.0 adds scoped initial agreement and the branch → verify → commit → push → create/update
PR/MR procedure, with the human deciding merge. On 2026-11-02, the repository suite ran 565 tests
with 16 skips and no failures or errors; five isolated Git/forge fixture checks passed.

Four actual model cases ran once each. Initial setup reached a mock PR using a work copy, including
reconciliation after a simulated creation timeout. Other cases retained existing rules and uncertainty,
but protected Git metadata or model capacity prevented some steps from completing. These are not four
end-to-end passes. The [Japanese review](../../repository-director/evidence/workflow-review.md) records
the actual prose, observer corrections, incomplete steps and later changes that were not model-retested.
No live GitHub/GitLab writes were performed.

## Compact documents and implementation flows

Version 1.2.0 defaults to purpose, architecture and development docs, with README as the repository entrypoint.
On 2026-11-02, the repository suite ran 572 tests with 16 skips and no failures/errors. The kit's 32 tests
and the five Git/forge fixture tests passed. One actual-model trial each for a CLI and Web/API produced
three docs, preserved source/rules, and included business context, file responsibilities and source-matching flows.
Prose review found excessive detail and task-only conditions leaking into permanent docs. Instructions were
corrected, without additional model trials. See the [review and edited example](../../repository-director/evidence/document-layout-review.md).

## Read-only branch evidence

Version 1.3.0 adds `work-status`. All 45 kit tests passed on Git 2.34.1 and Python 3.11.12.
The repository suite passed 589 tests with 16 skips and no failures/errors; standalone and 677 generated files matched.
The 13 added cases cover pending changes, renames, Unicode/newline filenames, divergent histories,
linked worktrees, gitlinks, detached/unborn HEAD, failed reads and refs moving during inspection.
Before/after snapshots verified unchanged working files, index and refs, including the filter case.
Git fixtures use a private empty global config and ignore system config; scenario-specific filters remain local.
A reproduced clean-filter callback during status led to callback suppression and explicit uncertainty,
followed by related regression checks. The Skill stays at 89 lines with fewer bytes; the existing
workflow reference grows from 66 to 76 lines. No additional model trial of task separation, conflict
resolution or merging was run. Shared paths do not prove conflicts or behavioral compatibility;
remote freshness and submodule working files remain unchecked.

## Limits

Live GitHub/GitLab writes, native Windows and actual Claude model behavior are outside these local checks.
Structural checks do not prove requirements completeness, semantic agreement with code or truthful test claims. Generation samples are not statistical evidence of general reader satisfaction.
