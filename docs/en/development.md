# Development, verification, and documentation

**English** | [日本語](../development.md)

[Documentation](README.md) · [Repository overview](../../README.md)

Maintained sources and required checks depend on the change. Edit the source and regenerate rather than directly editing Plugins or embedded payloads.

| Change | Procedure |
|---|---|
| README / guides | [Documentation-only checks](#documentation-only-checks) |
| Kit implementation / rules | [Source layout](#source-and-asset-layout), [kit validation](#validation-by-installer) |
| Shared CLI / OS-host distributions | [Distribution development](cross-platform-development.md) |
| New kit guide | [Adding documentation](#add-an-installer-guide) |

For archived run records, integrity checks and restoration, see [research evidence archives](research-archives.md). Normal tests do not fetch these archives.

## Source and asset layout

Root `install_*.sh` are entry points; helpers/assets/removal scripts live under `tools/<installer-id>/`, guides in `docs/<installer-id>/`, tests in `tests/`. No empty helper directory is needed for a standalone script. Bulk entry is `install_all.sh`; guide is `docs/installation.md`.

Research 2.5.0 / Upstream 2.0.6 distributions assemble a pinned base plus embedded upgrades. Root `tools/design-research/` / `tools/speckit-upstream/` alone are not the current whole implementation. `tools/design-research-upgrade/` applies layers and final overlays to assemble Skills, harness, and evaluation contracts.

```bash
python3 -B tools/design-research-upgrade/build_bootstraps.py
python3 -B tools/design-research-upgrade/build_bootstraps.py --check
bash install_design_research.sh --bundle-self-test
```

With original installers at the specified commit in `--base-dir`, `--offline --build-only` assembles/verifies both without network. Tests target final assembled sources; model quality is separate.

Workgraph code/hooks/policy/templates/schema history/dependencies live under `tools/basic-memory-workgraph/`. Historical schemas/hashes are managed migration inputs and remain tracked. Helpers resolve their own file location, not current directory.

```bash
python3 tools/basic-memory-workgraph/workgraph_tools.py --help
```

Old root CLI wrappers are absent; installed user paths/commands remain. `.vscode/`, caches, bytecode, and virtual environments are excluded from Git.

<a id="development"></a>

## Development checks

Prepare [Python](basic-memory-workgraph/installation.md#python-tools), then run:

```bash
python3 -m unittest discover -s tests -v
bash -n install_all.sh
bash -n install_basic_memory_workgraph.sh
bash -n install_codex_ux_stack.sh
bash -n install_speckit_upstream.sh
bash -n install_codex_github_pm.sh
bash -n install_design_research.sh
bash -n install_codex_ecc.sh
bash -n install_codex_office.sh
bash -n install_kotonoha.sh
bash -n install_herdr.sh
bash -n tools/basic-memory-workgraph/remove_workgraph_hooks.sh
```

Tests use temporary directories/fictional cases rather than personal Memory/Skills. They cover settings, migrations, capture modes, sharing, JSONL, import conflicts, registration protection, preview/rerun/recovery. External installations are mocked. [Policy scenarios (Japanese)](../../tests/POLICY_SCENARIOS.md) review semantic decisions separately; mechanical tests do not prove abstraction quality or creator judgment.

Before changing distributed templates, preserve the previous version under `tools/basic-memory-workgraph/schema-history/<version>/`; runtime migration uses local history, not Git/network. Edit policy in `tools/basic-memory-workgraph/memory-policy.md` and apply via `--configure-only` / `--update`.

## Validation by installer

| Target | Checks / scope |
|---|---|
| Bulk | `python3 -m unittest discover -s tests -p 'test_install_all.py' -v`, Bash syntax: temporary HOME/mock installers; selection, preview, setting-preserving updates, failure aggregation, interruption; not real all-kits download |
| Workgraph | Python tests for local settings/formats/sharing/update; not real external installs |
| UX | Python/Skill/distribution checks, optional real Chromium; references, protection, iteration/stop, state/navigation/evidence. Real model iteration and GUI invocation remain outside these tests; see [validation (Japanese)](../codex-ux-stack/validation.md) |
| SpecKit | `bash install_speckit_upstream.sh --bundle-self-test`, pinned assembly, embedded tests; assembly and 166 upstream tests plus recorded machine update/diagnosis; see [results (Japanese)](../design-research/validation.md) |
| GitHub PM | `bash install_codex_github_pm.sh --self-test`: temporary lifecycle/helpers/static rules, not real GitHub writes or writing quality |
| Research | `bash install_design_research.sh --bundle-self-test`, assembly: 2.5.0 bundled 330 tests and both distributions' self-tests; [model scope (Japanese)](../design-research/validation.md) separate |
| ECC | `python3 -m unittest discover -s tests -p 'test*ecc*.py' -v`, Bash: mocked Codex lifecycle, retry/recovery/settings/original resolution; real fresh downloads separate |
| Office | `bash install_codex_office.sh --self-test`: temporary lifecycle/edit protection/document processing; mocked network/Codex, unavailable PDF libraries skipped; real OfficeCLI/rendering E2E separate |
| kotonoha | `bash install_kotonoha.sh --self-test`: temporary mocked lifecycle/lint; real runtime/network/writing comparisons in [validation (Japanese)](../kotonoha/kotonoha-validation.md) |
| Herdr | `python3 -m unittest discover -s tests -p 'test_install_herdr.py' -v`: temporary HOME/mock download/Bash/workspace checks; not real downloads/sessions |

Existing Research/Upstream checks may target ordinary 2.0.1 installers; do not apply their regeneration-equivalence checks unchanged to current assembly bootstraps. Distinguish base, upgrades, assembled tests, and real model evaluation.

Do not run normal installers just to review documentation/syntax. Workgraph, UX, GitHub PM, Research, and Herdr install without arguments. `--extract` writes files. Research/Upstream `--extract-bundle` is offline, whereas `--extract`, `--doctor`, and `--self-test` may first assemble and contact sources.

## Add an installer guide

1. Copy the [template (Japanese)](../_templates/installer/README.md) files to `docs/<installer-id>/`; choose a lowercase alphanumeric/hyphen ID and place needed helper assets under the matching `tools/` directory.
2. Replace TODOs/placeholders with implementation-backed descriptions and script links.
3. Update the root kit table, [bulk guide](installation.md), and [index](README.md).
4. Check commands, links, anchors, and code/docs together.

Bulk integration also requires ID/script/description/arguments in `install_all.sh`, its guide table, and `tests/test_install_all.py`. Preview-only individual installers need their apply flag in the wrapper. Do not default to reset or force-overwrite paths.

```bash
mkdir -p docs/example-tool
cp docs/_templates/installer/*.md docs/example-tool/
```

| Page | Content |
|---|---|
| `README.md` | Purpose, components/providers/relationships, reading order |
| `installation.md` | Prerequisites, install/verify/update/remove, flags, sources/destinations/changes, troubleshooting |
| `usage.md` | First operation, examples, outputs, limits |

Split long subjects into linked pages, as with Workgraph sharing/reference/troubleshooting. Link common tool explanations and describe this combination's differences.

## Documentation maintenance rules

Use argument parsing and execution as the authority; identify discrepancies with help/comments. Distinguish tool capabilities, installer actions, and user preparation. Do not invent preview/update/uninstall options. Check sources, fixed/latest selection, existing settings, and reruns. Confirm external claims from official/bundled material with dates/versions as relevant. Use placeholders rather than personal paths/secrets. Keep policy/schema/template sources under their maintained locations, not copies in docs. Preserve links/anchors when moving material.

## SpecKit embedded assets

Research and Upstream embed the same upgrade ZIP. Both original installers are checked against `d3f46e0d591b45cb2423317030a489b91566e891`, upgraded/generated/tested temporarily, and emitted as standalone installers.

```bash
bash install_speckit_upstream.sh --extract-bundle /tmp/codex-research-upgrade
bash install_speckit_upstream.sh --bundle-self-test
```

Extracted `codex_interface_upgrade/` includes the following maintained layers; their contract tests are separate from model evaluation.

| Source | Responsibility |
|---|---|
| `bootstrap.py`, `build_installers.py`, `pinned_base.py` | Entry, pinned-base retrieval/verification, assembly |
| `integrate.py`, `installer_commands.py`, `command_assets.py` | Apply upgrades, unified entry, retire owned shortcuts |
| `overlay/tools/design-research/skill/` | Codex dispatch, status, preparation |
| `core_upgrade/`, `previous_report_upgrade/` | Workstreams, reassessment, proposed-method reports, v2 integration |
| Layer `tests/` | Independent contracts |

```bash
bash install_speckit_upstream.sh \
  --base-dir /absolute/path/pinned-base --offline --build-only /absolute/path/empty-output
```

Use genuine unchanged base installers, not current wrappers. Successful assembly emits both installers, `build-summary.json`, validation logs, and `sources/`. Match layers/versions across both distributions. Old `tools/speckit-upstream/build_single.py` and `tools/design-research/build_installer.py` generate intermediate ordinary installers; do not overwrite current root bootstraps with them.

Bundled and assembled tests differ. On 2026-10-10 the initial 249 bundled tests passed while upstream 166 tests stopped with 2 failures / 6 errors. After fixes, assembly/self-tests/machine updates passed; 2.4.0 bundled 287 passed, and 2.5.0 bundled 330 plus upstream 166 passed. See [conditions/results (Japanese)](../design-research/validation.md).

Compare `RESEARCH_FIRST.md` / `RESEARCH_WORKSTREAMS.md` and guides: goals/concerns/use cases precede requirements; required review/approval precedes research; new or changed mechanisms need research/integration before design finalization; standard choices need evidence. Unavailable research leaves it unexecuted while As-Is/requirements can progress. v2 ties hashes, theme runs, archived reports, integration, and UX evidence; do not rewrite v1. Apply real UX Skills to screen examples and distinguish images/prototypes/actual operations. Skill instructions, CLI contracts, and observed model behavior are separate evidence.

## GitHub Project Director embedded assets

Extract with `bash install_codex_github_pm.sh --extract /tmp/github-pm-review` into empty/unused storage. Inspect `README_EXTRACTED.md`, `scripts/install_github_pm.py`, and `skills/github-project-director/`. Maintain user documentation in the [guide](codex-github-pm/README.md), rather than duplicating extracted helper assets.

## Design Research embedded assets

Use the shared [assembly procedure](#speckit-embedded-assets). Compare `workflow-guide.md`, `readable-documents.md`, `reassessment.md`, and `workstreams.md` against `codex_interface.py`, `workflow_overview.py`, and `research_workstreams.py`. `$design-research` dispatches by purpose; planning does not experiment, status reads records. `prepare` resolves inputs and `run --expect-dispatch` verifies matching hashes before running.

Per-theme comparisons normally use about 5 candidates. Proposed methods need their own section, overall/detail/difference diagrams, equations/pseudocode, assumptions, limits. Reassessment uses an archived complete report with a new slug/run; same-condition resumption is different. Dependency plans are not an implemented parallel scheduler: same-project runs serialize under a lock. Mock/file-existence checks do not establish scientific validity, reading quality, or model judgment.

See [installation](design-research/installation.md) and [validation (Japanese)](../design-research/validation.md) for operations, local HTTP/PoC/evidence/recovery tests. Outer Skills handle Memory under existing policy/permissions; harness children do not write it.

## Office Workbench and kotonoha embedded assets

Both embed custom assets/tests and support `--extract DIRECTORY`. Office exposes `README_JA.md` and `install.py`. kotonoha retains `tools/kotonoha/` as its maintained path. `python3 tools/kotonoha/build_installer.py` generates `install_kotonoha.sh`, `install_kotonoha.ps1`, and compatible `install_kotonoha.sh`; `--check` verifies all.

Extracted kotonoha includes `installer.py`, `SKILL.md`, `kotonoha/`, `meiseki-upstream/`, `references/`, `scripts/`, `paragraph-writing/`, `japanese-direct-writing/`, `tests/`, and `evals/`. Evaluation material is not installed as Skills. Separate custom/upstream/runtime versions and verify upstream-only updates preserve custom rules. Since 2.0.0-proposal.1, auxiliaries are partial-task Skills, with hashes/provenance in `UPSTREAM.json` / `SOURCE.json` and metadata generated for `auto` / `explicit`. Source replacements need provenance/hash/revision updates, regeneration, and tests. Extract for review only; maintain user guides separately.

Historical 1.1.0 / 1.2.0 comparisons use explicit `tools/kotonoha/evaluate_writing.py` with preserved `tools/kotonoha/evaluation-v130/` entries/references/four drafts, Python 3.11+, authenticated Codex, and upstream originals. It makes real model calls and never runs from installation/self-tests.

```bash
python3 tools/kotonoha/evaluate_writing.py --out /tmp/paragraph-writing-comparison
```

Save conditions/input hashes/full outputs/blind ratings and manually compare facts/conditions/certainty. Current generation setup uses `evals/prepare_generation_eval.py` and [protocol (Japanese)](../../tools/kotonoha/evals/PROTOCOL.md). `evals/evaluate.py` tests the detector on 60 synthetic cases; `evals/review_examples.py` checks examples without models. Generation, selection, and reader comprehension are separate evaluations.

### Revise Japanese documentation

Use kotonoha with before/after UTF-8 copies, textlint/markdownlint, and `check.py compare`; see [examples](kotonoha/usage.md#check-saved-files). Preserve commands, settings, numbers, conditions, negation, and certainty. Keep useful tables/procedures; do not change meaning merely to silence findings.

## Documentation-only checks

Follow overview/install/usage links in both directions; check local files and heading/explicit anchors. Verify command names, flags, defaults, destinations, versions, and network scope against implementation without real installation. Check Mermaid syntax and arrow meanings without inferring execution/success. Ensure moved content has a destination and run `git diff --check`; untracked new docs need separate inspection. Documentation-only work needs no new functional tests/CI. Test any actual implementation changes separately.

## Maintain both languages

`README.md` is the English entry; `README.ja.md` is Japanese. Japanese guides remain in `docs/`, with corresponding English pages at the same hierarchy under `docs/en/`. Update both counterparts in the same change when procedures or specifications change.

Place a language switch at the top of each page and link to same-language guides. Leave evaluation/design records, history, execution logs, and upstream originals unchanged; identify Japanese-only references from English pages. Compare commands, settings, conditions, and unverified scope across languages, then check links, anchors, and Markdown. No automatic translator or new dependency is required.
