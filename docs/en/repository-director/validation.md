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

## Limits

Live GitHub/GitLab writes, native Windows and actual Claude model behavior are outside these local checks.
Structural checks do not prove requirements completeness, semantic agreement with code or truthful test claims. Generation samples are not statistical evidence of general reader satisfaction.
