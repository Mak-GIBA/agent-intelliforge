# Use Design Research

**English** | [日本語](../../design-research/usage.md)

[Documentation](../README.md) · [Overview](README.md) · [Installation](installation.md) · [Validation (Japanese)](../../design-research/validation.md)

## Report structure, reading and adoption

New 2.8.1 runs organize the main report as conclusion, background/problem/assumptions, candidate comparison, recommended approach and adoption, verification/results, and limitations/next actions. Proposed-method diagrams and formulas belong with adoption details. Unused sections are omitted; process tables, reading records and detailed stops move to the appendix. In-progress reports are explicitly drafts.

After scientific review, a writer reads the whole Japanese draft and uses installed kotonoha, otherwise yomiyasu. The parent locks numbers, IDs, references, formulas, code and structure; a separate reader checks meaning, negation, conditions, causality and certainty. Available offline lint results are retained without requiring zero findings. If neither Skill exists, research can finish with an explicit unpolished notice; no Skill is installed during a run.

Version 2.8.1 resolves references and checkers inside self-contained kotonoha 4.0.0 without a sibling yomiyasu Skill. The older kotonoha/yomiyasu combination remains supported.

Promising papers require complete main-text reading and relevant supplementary material, with actual sections/pages, findings and missing coverage. Partial/unavailable reading defers adoption of that candidate while other comparisons continue. Retrieval and a `full_text` label do not certify understanding.

Fetched full text and relevant sections are retained with hashes under the local run's `sources/` directory. Failed retrieval or storage cannot count as complete reading. These response bodies are excluded from automatic Evidence exports; reports contain analysis and references to originals.

OSS choices document the exact version/ref, implementation and tests, API, dependencies, license conditions and integration. Prefer suitable reuse; compare direct use, wrapping, adaptation and custom implementation. Unknown/incompatible conditions defer adoption. Recommendations do not authorize app dependency or source changes. A stopped writing phase resumes without repeating completed experiments. Historical runs retain their saved contracts/layouts.

## Child write permissions

New runs from 2.7.0 launch research, proposal and review roles with `workspace-write`. Transient tool data lives inside the run while HOME and CODEX_HOME retain authentication and configuration. Research and audit keep their existing task scope: unexpected source edits by non-fixer roles stop the run.

Use `--role-sandbox read-only` for read-only non-fixer roles. Resume retains recorded policy, with read-only as the legacy default when no policy was saved. `resume RUN_ID --role-sandbox workspace-write` changes future invocations and records the override outside frozen research config, preserving completed checkpoint hashes. The single-entry `codex_interface.py prepare/run` commands also accept this option.

Role `invocation.json` records effective permissions and command networking; failed child CLI execution also writes `diagnostic.json`. Existing `--allow-network` / `--offline` research limits remain, separately from MCP-specific networking. Offline is not a firewall for all MCP traffic. PoC and test isolation remains separate from model-role permissions.

## Focus on the project's core logic

2.8.1 uses one `$design-research` entry. Open the target project and state the goal without enumerating mode names, candidate counts, figures, or CLI flags.

```text
$design-research Investigate ways to improve this project's search accuracy.
```

The Skill checks objectives, metrics, preserved constraints, current approaches, and prior research, then scopes the questions that affect outcomes: retrieval/ranking, extraction, classification, reasoning, decision rules, or business processing. Ambiguous targets/prior work require clarification.

<a id="codex画面でbashの実行を指示する"></a>

## State the purpose in Codex

| Request | Work |
|---|---|
| Compare this project's document extraction approaches | Comparison, bounded PoC as needed, report |
| Split these requirements into research themes; plan only | Requirement mapping, dependencies/order; no experiment |
| Study candidate generation and ranking separately, including integration | Theme studies and integration handoff |
| Reevaluate earlier search findings with new data | Separate new research referencing prior work |
| Continue interrupted research under the same conditions | Verified run resumption |
| Summarize results and remaining work | Read records only |

Internal `plan`, `research`, `workstream`, `reassess`, `resume`, and status are not separate user-facing Skills. Owned unchanged 2.3.0 shortcuts were retired from 2.3.1; see [updates](installation.md#update-an-existing-version).

```text
$design-research Audit the API and storage for invalid input, duplicate submissions, and recovery after failures. Do not use production data or modify code.
```

```text
$design-research Fix duplicate saves in this project. Preserve existing edits and report before/after verification and independent review.
```

`audit` preserves app source; `run` handles explicitly requested local fixes. Research/status alone does not authorize app changes. Confirm actual commands/run IDs/state rather than treating prose as execution. Skills resolve their own paths in new or legacy installations; record missing prerequisites and stop reasons if unavailable.

## Combine with SpecKit requirements and design

Start with `$upstream-new` / `$upstream-change` for overall system work. Upstream 2.1.0 handles stories, concerns, use cases, requirements, and integrated design; Research handles core questions, candidates, PoCs, and evidence. They install separately; standalone Research needs no SpecKit documents.

```text
$upstream-new I want an app that searches internal documents and answers with supporting evidence.
```

New/changed mechanisms require relevant research before finalization. Standard CRUD can be `standard` with evidence; As-Is transcription/typos do not require global research. Fix each theme's inputs/outputs, evaluation, dependencies, budgets, and integration conditions. Same-project execution serializes under a lock even when the plan identifies independent themes. See [workstreams](../speckit-upstream/reassessment.md#split-core-logic-into-research-themes).

Handoff includes requirement IDs, candidates/alternatives, contracts, measurements/gaps, costs/constraints, run ID, archived report, and proposed `design.md` changes. Upstream reviews combined tradeoffs and verification. Research completion is not adoption approval, document approval, or implementation authorization; see [entry choices](../speckit-upstream/reassessment.md).

## Compare primary sources in depth

Aim for about 5 candidates per theme: current baseline plus roughly 4 differing approaches, reducing unsupported candidates with reasons rather than padding. Default `comparison` is broad comparison; choose `proposed-method` for detailed proposed-method design.

Before effectiveness tests, fix purpose-aligned metrics, scoring, inputs, controlled conditions, and adoption criteria. For reasoning tools, solve actual tasks under the same model/budget and score final answers; response availability, accepted reasoning text, or returned length is not reasoning accuracy. Save expected values and baseline/candidate actual outputs; the harness recomputes scores. Distinguish task count from repeated trials, report failures/limits, and accept no-gain/equal findings. Unmeasured main effects mean incomplete effectiveness evaluation; design/literature studies may complete conditionally with that limitation.

Internal `--evaluation-purpose` is `auto / effectiveness / design / literature`, selected from the request and fixed in plan/dispatch hash; changing purpose cannot resume the old run. New runs save minimal design, experiment assets, measurement/scoring, per-candidate original-source review, explanations/figures, and itemized review. Required detail/review must finish before overall completion. Initial child input, including instructions, is at most 16 KiB; large materials are archived with hashes and passed by reference. Role receipts distinguish timeout from validation failure. Format/citation/history repair is allowed once within the original time budget.

Normally read at least 2 independent primary sources for approach/accuracy research, through relevant methods, experiments, and discussion. Compare mechanism/assumptions, data/model/version/metrics/resources, baselines/ablations/results, failure conditions/conflicting findings, and project fit/additional measurement. Preprint/published versions or mirrors of one study are not independent. Abstracts/search snippets/downloads alone do not prove deep reading. Record supporting sections/pages/figures and unread material; defer unsupported judgments within existing budget. Small known bugs do not automatically need literature review.

## Run directly in a terminal

These paths are for new user-wide installs; use actual reported paths for project, custom, or legacy locations.

```bash
DR_GAN="$HOME/.agents/skills/design-research/scripts/gan-harness.sh"
bash "$DR_GAN" doctor --project /path/to/project
bash "$DR_GAN" research --project /path/to/project --slug search-options \
  --brief "Compare baseline and candidates for correctness, latency, and operational cost using necessary local experiments" \
  --reader-friendly --report-profile proposed-method --target-methods 5 \
  --allow-network
```

`--allow-network` enables academic/public-source retrieval and Codex live web research. Otherwise these are disabled; `--offline` makes that explicit. This governs kit research networking, not model connectivity or all existing MCP traffic. Do not expose private code/constraints as search terms.

Replace example test commands with safe existing checks and prepare dependencies yourself; the harness does not install them.

```bash
bash "$DR_GAN" audit --project /path/to/project --slug api-review \
  --brief "Check storage correctness for invalid input and duplicate submissions" \
  --test-command "python3 -m pytest tests/test_api.py"

bash "$DR_GAN" run --project /path/to/project --slug api-fix \
  --brief "Fix invalid-input and duplicate-save issues with minimal changes" \
  --test-command "python3 -m pytest tests/test_api.py"
```

Repeat `--test-command` for mandatory checks, including in research mode. Verify responses, stored state, permissions, and retries, not exit code alone. Do not test nonexistent features.

## Local services and test data

Checks and PoCs run in temporary project copies, retaining results before cleanup. Personal HOME/env and project `.env` are not automatically inherited. Existing `node_modules` / `.venv` may be reused through sandbox read-only links.

```bash
bash "$DR_GAN" audit --project /path/to/project --slug service-review \
  --brief "Check test API input, storage, and recovery" \
  --start-command "python3 test_server.py" \
  --url "http://127.0.0.1:8099/health" \
  --test-command "python3 check_api.py" \
  --test-env-file /path/to/private/test.env
```

Replace commands and choose a free port. `--url` must be credential-free loopback. A URL already responding alongside `--start-command` causes a stop. Only started child services are terminated, never unrelated services. Checks receive `DR_GAN_TEST_URL`.

`--test-env-file` reads explicit `KEY=VALUE` only, without shell execution/expansion, refusing production modes/system variables. It cannot determine whether every connection is really a test database: use dedicated dummy data and safely initialized tests. Explicit test-service connections may enable network inside the test sandbox.

## Optional UX review and reference implementations

The kits work independently; an existing review is optional via `--review /path/to/ui-ux-review.md`. Save it as input and reproduce backend concerns. Add actual public references with `--reference-url https://example.org/actual-source` and `--allow-network`. Distinguish inaccessible/unread/irrelevant material; appearance alone cannot establish architecture. Look for useful examples when needed, explaining adopted ideas and simpler alternatives rather than maximizing candidates.

## Execution and completion

Separate Codex executions plan criteria, perform research/checks, then evaluate evidence, failure/recovery, and complexity. `run` fixes at most 3 significant root causes and repeats checks/review. Save evidence, before/after, gaps, and stop reasons. Initial criteria cannot be relaxed.

Default maximum is 5 iterations including first evaluation; `--max-iterations` accepts 1–5. Two non-improving iterations stop as `plateau`; default `--phase-timeout` is 1800 seconds per stage/check. Required successful receipts must match iteration/source, and failure of the same check cannot be hidden by another success. Fixer claims alone cannot resolve findings.

| State | Meaning | Exit |
|---|---|---|
| `research_complete` | Required research/evidence/execution criteria met, conditional recommendation | 0 |
| `passed` | Required checks, no unresolved Critical/High, complexity criteria met | 0 |
| `reviewed` | Audit report finished; findings/check failures may remain | 0 |
| `blocked` / `cancelled` | Missing prerequisites, inconsistent evidence, failure, interruption | 2 |
| `plateau` / `limit_reached` | Stagnation/limit; completion not achieved | 2 |

Completion is neither universal effectiveness nor human adoption approval; `run` success is limited to recorded checks.

## Evidence and outputs

A new topic has one human-facing `docs/design-research/<slug>/report.md`: conclusion/status/run ID/recommendation/decisions/gaps, problem/constraints/comparison, proposed-method detail, actual experiments, fixes/rechecks where applicable, and remaining work/receipts. A proposed method needs a separate section with mechanism, overall/module/difference diagrams, equations/pseudocode as needed, assumptions/limits. Choosing an existing method does not require invented novelty. Explain diagram questions and reading; preserve measurements versus literature, inference, hypotheses, and unknowns. A finished report/figure is not experimental evidence.

Final conversation centers on conclusions and the report link, adding JSON/logs when diagnosing. Japanese drafts prefer available kotonoha, falling back to the yomiyasu compatibility entry; use one entry per draft and preserve meaning/certainty. Child narrative is polished before JSON, never by rewriting published ledgers/logs/archives. With SpecKit, put adoption rationale/conditions into `design.md` and measurements into `verification.md`, linking rather than copying research.

From 2.6.0, new topics keep complete execution records in `.artifacts/design-research/<slug>/` and publish human reports/figures under `docs/design-research/<slug>/`. Existing topics retain their original locations. [Outputs and review order](../upstream-research-workflow.md) explains what to commit.

Inside the workspace, machine records are `.internal/status.json`, `.internal/evidence.json`, and `.internal/research-log.json`. Evidence has IDs/hashes/iterations/source and is checked before review/resumption. Receipts expose stdout/stderr/outputs. `runs/<run-id>/` retains state, roles, PoC, logs, evidence, and archived `reports/report.md`. Initial material goes in `inputs/`. Latest `report.md` also reflects start/stop state to avoid presenting a prior success as current. Declare generated JSON/figures/images in `artifact_paths`, save real files, and embed images in reports.

For long-lived design rationale, preview `export-evidence` with the selected topic/run ID, then add `--apply` to publish the fixed report and dependencies under `docs/design-research/<slug>/evidence/<run-id>/`. `verify-evidence --package <path>` checks completeness and hashes in a clone without local execution records. Old `runs/<run-id>/reports/` references remain readable.

## Migrate older material into one report

```bash
bash <skill-dir>/scripts/gan-harness.sh migrate --project . --slug TOPIC
# Inspect merged text, link changes, and backups before applying
bash <skill-dir>/scripts/gan-harness.sh migrate --project . --slug TOPIC --apply
```

Merge the old five Markdown outputs into `report.md` and machine JSON into `.internal/`, backing up originals under `.internal/migrations/`. Preserve IDs/source/evidence links and all old runs/receipts/archives. First fix links from retained custom docs. Running studies, broken JSON/evidence, or destination conflicts stop migration. Failures roll back; repeated completed migration is unchanged. It neither reruns research nor approves adoption. Updating alone leaves old layouts; inspect old root `status.json` and report run ID.

## Retain useful experiment details in Workgraph

Configured [Workgraph](../basic-memory-workgraph/README.md) lets the outer Skill select detailed records useful for later decisions, comparison, reproduction, or resumption, including scoped project results/failed approaches. Do not save every success log. One selected experiment record contains purpose/utility, version/run/evidence/iteration, inputs/data/environment/model/resources/baseline/controls, metrics/expectations/criteria, executed commands/preparation/reproduction, actual outcomes/errors/truncation, interpretation/limits/recheck triggers, and archived evidence links.

Link long logs/data/code/papers rather than copying them. Unexecuted work is not measured. Save under configured Memory `artifacts/design-research/<slug>/<run-id>/<evidence-id>.md`, separate from project docs; search duplicates and read back. Report actual project/note references, reason, and state.

```text
$design-research Compare and measure this project's search approaches. Save useful experiment conditions, metrics, commands, outcomes, failure evidence, and reproduction steps in configured Memory Workgraph, with execution and archived-report links. Show the saved note references.
```

Existing permission/modes apply: no writes in Plan/read-only, explicit capture bans, or automatic capture with `auto=off`. Abstract Rules/Workflows/Validations require separate admission. Missing/unavailable Memory, failed search, or failed save must be reported while local artifacts remain. Direct Bash alone and harness children do not write Memory; installation does not change Workgraph settings.

## Stop and resume

Use `resume` for interrupted same-input/same-condition work; `reassess` for completed research under new conditions. Natural requests let the Skill verify records.

### Resume unchanged conditions

```bash
bash "$DR_GAN" resume ACTUAL_RUN_ID --project /path/to/project
```

Replace `ACTUAL_RUN_ID` from report, state, or result JSON. Source/record hashes and explicit test settings must match. Waiting evaluation resumes without duplicate tests. New 2.5.0 runs verify completed-stage input/output/source/receipt hashes and reuse completed execution. Commands with only start records and unknown outcomes are not repeated automatically. Verified failures remain, with fixes/new review in another iteration.

Old-contract interruption may restart experiment/checks in a new iteration/workspace; test data must reset safely. No remaining budget requires a new run. Interrupted fixes retain differences but refuse resume; inspect them and start a fresh audit/run. Completed, plateau, or exhausted runs also need new work. Never reset user edits to force a resume.

### Reassess a completed study

Require completed prior state and archived report. Record earlier question/recommendation/constraints and changed conditions in a new slug/run, including the prior approach and at least 1 differing principle. Do not rewrite old evidence or directly compare numbers from unmatched conditions; evaluate the current approach under new conditions too. Ambiguous prior runs need selection; unfinished runs are not completed reassessment inputs.

### Status only

```bash
DR_SCRIPTS="$HOME/.agents/skills/design-research/scripts"
python3 -B "$DR_SCRIPTS/workflow_overview.py" --project /path/to/project
python3 -B "$DR_SCRIPTS/codex_interface.py" runs --project /path/to/project
python3 -B "$DR_SCRIPTS/codex_interface.py" workstreams --project /path/to/project
```

These read records without experiments. Stages such as unpartitioned/prepared/in-progress/integration-pending do not establish validity, successful experiments, or approval.

### Internal execution dispatch

Normally let the Skill dispatch. Manual inspection uses matching `prepare` and `run` arguments:

```bash
python3 -B "$DR_SCRIPTS/codex_interface.py" prepare research \
  --project /path/to/project --slug search-options \
  --brief "Compare search approaches under matched conditions" --allow-network
# Inspect resolved inputs/target/scope and substitute the actual dispatch_sha256
python3 -B "$DR_SCRIPTS/codex_interface.py" run research \
  --project /path/to/project --slug search-options \
  --brief "Compare search approaches under matched conditions" --allow-network \
  --expect-dispatch ACTUAL_DISPATCH_HASH
```

Resolve `needs_selection` and prepare again. `run` requires unchanged inputs and `prepare` SHA-256; `ready` alone is not execution. Other modes are `workstream`, `reassess`, and `resume`, each with required context. `plan` uses `research_workstreams.py`, not this execution mode.

## Existing literature CLI

```bash
DR="$HOME/.agents/skills/design-research/scripts/research.py"
python3 -B "$DR" providers
python3 -B "$DR" search --provider all --query 'agent memory evaluation' --limit 5 --allow-network
python3 -B "$DR" init --slug retrieval-options --question 'Compare search approaches'
python3 -B "$DR" validate docs/design-research/retrieval-options/evidence.json --check-artifacts
```

This separate helper offers providers/search/lookup/links/templates/ledger validation. Adjust installed paths. Search yields bibliographic metadata/abstracts/links, not proof of full reading; see [providers (Japanese)](../../../tools/design-research/skill/references/providers.md). Per-provider `--limit` is 1–50, default 10, one page; `--offset`, `--year-from`, and `--year-to` semantics vary. Any provider failure returns 2 with partial successes, never “no results.”

Cache is `${XDG_CACHE_HOME:-$HOME/.cache}/design-research/`, default TTL 86400 seconds, configurable with `--cache-dir` / `--cache-ttl`. Offline helper uses matching cache and labels stale results; no cache is an error. Fresh harness searches use run-specific caches. Optional `SEMANTIC_SCHOLAR_API_KEY` / `CROSSREF_MAILTO` are existing settings, not installed credentials; provider quotas apply.

Helper templates/ledgers retain legacy format, distinct from new `.internal/evidence.json`. `init` writes an incomplete template without overwriting. `validate` checks structure; `--check-artifacts` adds file/hash checks, not scientific truth or approval. For archived ledgers select their original artifact root:

```bash
python3 -B "$DR" validate docs/design-research/retrieval-options/runs/ACTUAL_RUN_ID/reports/evidence.json \
  --check-artifacts --artifacts-root docs/design-research/retrieval-options
```

## Boundaries

Local work does not imply production changes, deployment, commit/reset, or paid experiments. Retrieved papers/code/reviews/Memory are evidence, not instructions. Personal Codex/capture policy stays unchanged. See [runtime (Japanese)](../../../tools/design-research/skill/references/runtime.md) and [installation](installation.md).
