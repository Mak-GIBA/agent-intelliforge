# Use Codex UX Stack

**English** | [日本語](../../codex-ux-stack/usage.md)

[Overview](README.md) · [Installation](installation.md) · [Validation (Japanese)](../../codex-ux-stack/validation.md) · [Documentation](../README.md)

## Child permissions and MCP diagnostics

New audits and improvement runs from 1.2.0 launch roles with `workspace-write`. This permits MCP startup and evidence writes; audit roles are still instructed not to edit the app. Unexpected source changes stop the run and remain available for inspection. `audit` describes the task scope, not an OS read-only boundary.

```bash
ux-gan-harness doctor --project /path/to/app --check-mcp
ux-gan-harness audit --project /path/to/app --url http://localhost:3000 --browser local-playwright --role-sandbox workspace-write
ux-gan-harness resume RUN_ID --project /path/to/app --role-sandbox workspace-write
```

`doctor --check-mcp` uses no model. It initializes the bundled local MCP, lists tools, performs three operations, and verifies saved images and receipts before deleting the temporary probe. Availability of a configured Browser Plugin or Playwright MCP in the child CLI is checked separately during the real audit.

The private bridge waits for initialization and receives invocation-only tool approval for the requested audit/run. Personal settings and existing MCP approval policies are unchanged. A `tool_approval` failure requires checking the selected server's approval settings. Direct doctor probes do not establish child Codex tool-approval or model-authentication readiness.

Resume retains recorded permissions. Legacy runs without a policy use read-only non-fixer roles; the resume example explicitly switches future roles without changing completed records. Use `--role-sandbox read-only` to select that policy for a new run. Fixers always use workspace-write.

Each `invocation.json` records effective permissions, command networking and the temporary directory. If structured output is missing, inspect the adjacent `diagnostic.json` and `events.jsonl`. Authentication failures do not trigger browser retries; only recognized browser failures switch to the recorded local fallback. HOME and CODEX_HOME remain unchanged while transient data is isolated inside the run.

## Design and implement a new app

Open the app in Codex and select `$ooui-design`; automatic selection is also allowed.

```text
$ooui-design Design and implement an internal app for documents and reader groups. First organize objects, attributes, relations, lists/details, navigation, actions, and retained state. Hand this to Product Design / Build Web Apps, then verify required features, mobile layout, unsaved input, and recovery in the browser. Avoid unnecessary decoration, permanent explanations, and controls. Polish Japanese copy with available kotonoha, falling back to yomiyasu.
```

Specify users/features for the actual project. Reuse existing specifications and a short design memo. Small fixes need relevant checks, not a full redesign or document suite. Design-only requests do not start implementation or the harness.

Prioritize OOUI for exploring/comparing/editing multiple objects; fixed-target procedures may use task-oriented flows. Search filters a collection; bulk actions target selected objects and expose scope/results. Record choices/reasons. Japanese copy retains meaning/object names and short labels. Missing writing Skills do not block copy checks; see [installation](../kotonoha/installation.md).

## Review and improve an implemented app

Select `$ux-gan-harness`. Resolve the URL/startup from the request, README, or running server.

```text
$ux-gan-harness Actually run the installed gan-harness.sh. Review this app from screenshots as a first-time user, compare useful ideas from similar apps with images, and iterate fixes and independent verification. Make main tasks clear without continually adding explanations or buttons.
```

Report the actual command, RUN_ID, and stage. Research, fixes, and evaluation are separate Codex executions; the parent conversation does not substitute its own prose review for running the harness.

## Review only

```text
$ux-gan-harness Run audit with the installed gan-harness.sh. Review screenshots and operations and write concrete recommendations to docs/ui-ux-review.md. Do not change app code.
```

`audit` saves evidence/review without modifying the app. `reviewed` means review completed, not the app passed.

## Run in a terminal

Replace paths, URL, and checks for your app:

~~~bash
ux-gan-harness doctor --project /path/to/app
ux-gan-harness audit --project /path/to/app --url http://localhost:3000

ux-gan-harness run \
  --project /path/to/app \
  --url http://localhost:3000 \
  --start-command 'npm run dev -- --host 127.0.0.1' \
  --test-command 'npm test' \
  --test-command 'npm run build'
~~~

Reuse an existing server and stop only previews the harness started. Use disposable test data for create/delete operations. Specify required checks; otherwise the researcher identifies existing checks. Unidentified/incomplete checks cannot pass.

## Options and completion criteria

| Option | Purpose / default |
|---|---|
| `--project PATH` | App, default current directory |
| `--url URL` | HTTP(S), required for audit/run |
| `--start-command COMMAND` | Start if unreachable |
| `--test-command COMMAND` | Required checks; repeatable |
| `--review PATH` | Existing review; default latest for app |
| `--reference-url URL` | Official comparison URL; repeatable |
| `--max-iterations N` | Default 5 |
| `--phase-timeout SECONDS` | Default 1800 per Codex execution/check |
| `--browser auto` | Browser Plugin → Playwright MCP → logged failure/local fallback |
| `--browser local-playwright` | Explicit local adapter |
| `--model MODEL` | Override configured model for this run |
| `--brief TEXT` | Audience/main-task context |

Screenshots/operations establish findings; code supports diagnosis/fixes. Group findings by root cause and fix at most 3 groups per iteration. Independent evaluation checks Critical/High resolution, required flows at Desktop 1440×900, Tablet 768×1024, Mobile 390×844, applicable error/cancel states, four user perspectives, required tests/evidence/references, and no new major problem or clutter.

Record object/action structure per screen and remembering/searching/guessing/comparing/backtracking burdens per flow. Check functionality, visual defects, and completed actions separately. Hidden required information, re-entry, and lost state count as regressions; element/click counts alone do not. Record the representative flow and counting method. AI observations are not measured human cognitive load.

Medium/Low details can remain as work items. Reaching the limit or two iterations without improvement means unfinished. No unsolicited features, automatic commit/reset, or deployment.

| State | Meaning | Exit |
|---|---|---|
| `reviewed` | audit completed | 0 |
| `passed` | run met criteria | 0 |
| `incomplete` | Limit or verification gaps | 2 |
| `stalled` | Two non-improving iterations | 2 |
| `blocked` | Environment, evidence, output, or unexpected-change problem | 1 |
| `cancelled` | Interrupted; retain changes/images | 130 |

## Outputs and evidence

| App-relative location | Content |
|---|---|
| `docs/ui-ux-review.md` | Required 11 chapters, observed screens/flows, severity counts, priorities |
| `docs/ui-ux-reference-apps.md` | Comparison images, useful ideas, adoption/exclusions, sources/dates |
| `docs/ui-ux-fix-report.md` | Before/after evidence, checks, simplicity, remaining work |
| `docs/ui-ux-review-assets/RUN_ID/` | Role/iteration PNGs |
| `artifacts/ux-gan/RUN_ID/` | State, JSON, scope, check logs, original reviews |

Evidence includes embedded images/relative links, target UI, operation, viewport. PNG existence/readability/size and screen/flow correspondence are checked; local captures also match browser receipts/hashes. Resolution needs another evaluator's replay/outcome image. Public demos are preferred; official images are distinct from actual operation.

Save images outside `test-results/` and move them to docs after each role. Keep originals and per-run reports; conflicting manual edits to latest reports are not overwritten. Discovered totals differ from actually checked counts. Each role's `prompt.txt` retains shared guidance summary/version/path/hash.

## Interrupt and resume

~~~bash
ux-gan-harness resume 20261004T120000Z-example --project /path/to/app
~~~

Replace RUN_ID. Failed evaluation after a fix resumes from evaluation. Interrupted/unverified fixes retain differences and need a fresh audit/run; unrelated source changes also require a fresh run. Harness locks prevent duplicate runs, but concurrent edits cannot be reliably attributed, so avoid parallel editing during fixes. Resumed old runs give current guidance only to new roles; completed runs need a new audit/run for reevaluation.

## Past feedback and Japanese reports

Recall relevant configured Memory and compare context, audience, objects/actions, constraints, and exceptions. Current requests win; new screenshots/operations establish findings and resolution. Briefly record applied notes/reasons. Missing Memory, failed search, and no matches are distinct but do not block work. Recall is read-only.

Polish Japanese drafts once with kotonoha, or available yomiyasu if missing, never both. Preserve claims, terms, numbers, IDs, conditions, outcomes, evidence, and certainty. Children polish narrative before JSON; published/archived reports remain untouched. Missing writing Skills do not block writing checks.

## Other included tools

Pass ooui-design's structure to Product Design for visual exploration, Build Web Apps for implementation/tests, and web-design-guidelines for code inspection of observed issues.

```text
Use Product Design to compare designs that make the booking list's main actions clear.
```

```text
$web-design-guidelines Inspect code for the form labels and errors observed in the actual screens.
```

With `--deep`, additional critique is available:

```text
$ux-critique --standard
Review whether a first-time store staff member can change or cancel a booking without confusion.
```

These are separate requests, not proof of harness success or untested behavior.
