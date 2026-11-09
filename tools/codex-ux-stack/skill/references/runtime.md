# Runtime guide

`audit` writes evidence and reports without editing application source. `run` captures a baseline and iterates up to five times. `resume RUN_ID` keeps the original baseline and evidence; it refuses unrelated source changes. Interrupted or unvalidated fixes preserve the diff and require a new audit/run. `doctor` checks CLI capabilities, the host's Codex sandbox and Chromium by actually launching the local browser bridge on a blank page.

Common flags: `--project PATH`, `--url URL`, `--start-command COMMAND`, repeatable `--test-command COMMAND`, `--review PATH`, repeatable `--reference-url URL`, `--max-iterations N`, `--phase-timeout SECONDS`, `--idle-timeout SECONDS`, `--model MODEL`, `--browser auto|local-playwright`. The normal browser order is Browser plugin, configured Playwright MCP, then the bundled local Playwright bridge after a recorded failure. Explicit `local-playwright` chooses that bridge directly.

Version 1.3.0 adds opt-in `--profile focused --focus '<screen and operation>'`. Full remains the default.
Focused defaults to desktop/mobile and first_time/mistake; repeat `--viewport` to select widths.
Reference comparison is required only when reference URLs are supplied. Reports declare the scope and cannot certify the whole app.
Resume retains its recorded profile; missing legacy profile means full. Focused planning maps the target without repeating the reviewer's operation matrix.
`ux_inspect.recent_frames` exposes the latest twelve browser-generated frame records. Use their actual URL after redirects,
viewport, path and hash after viewing the image. Mismatches remain failures; diagnostics name the evidence/fields instead of weakening checks.

New runs from 1.2.0 use workspace-write for all roles. `--role-sandbox read-only|workspace-write` controls non-fixer roles; fixers always use workspace-write. Audit remains source-preserving by instruction and before/after checks, rather than OS write prevention. Unexpected edits stop the run and remain for inspection. Resume retains saved policy (legacy missing policy means read-only); an explicit override is recorded separately from frozen config and affects future invocations only.

`doctor --check-mcp` tests the bundled local MCP without a model: initialization, tool discovery, three real browser operations and hashes of saved images/receipts, in a disposable workspace under the selected command sandbox. This does not establish native Plugin/MCP or model authentication readiness. The role's invocation records effective sandbox/network settings; missing structured output also leaves classified diagnostics. Only observed browser failures can switch to the local fallback. HOME/CODEX_HOME remain unchanged, transient caches live inside the role, and installed Playwright browser discovery is preserved.

The private browser bridge is required at child startup and its tools are approved only in that invocation, as part of the explicit audit/run. Existing user/native MCP approval policies remain in force. An approval refusal is recorded as `tool_approval` and does not trigger a browser fallback. A direct MCP doctor probe cannot establish the child Codex client's tool-approval readiness; an actual role invocation checks that boundary.

## Completion, checkpoints and stopping

New planner/reference/reviewer executions use `--phase-timeout 0`: no fixed wall deadline while verified work advances. `--idle-timeout` defaults to 900 seconds. Only new verified observations/evidence or distinct successful browser operations advance the monitor; log chatter, changed wording and repeated operations do not. Once a role enters reporting, further browser exploration cannot extend it. A positive `--phase-timeout` is an explicit deadline and does not trigger automatic recovery. Readiness remains 60 seconds; browser actions retain their own limits. Fixer executions and required check commands retain a 1800-second limit when no positive phase limit is supplied.

Workspace-write planner/references/reviewer roles atomically save partial original-schema results using the supplied `role_checkpoint.py` helper after each completed flow/viewport/candidate. Final completion uses a small envelope; the host verifies the saved full result and still writes the existing `result.json` and reports. Checkpoint context binds the run, role, iteration, source, scope and backend. Browser paths, receipts, hashes and coverage references are checked; earlier findings and evidence identities cannot be dropped. The helper waits for host acknowledgement; schema/evidence/coverage errors are returned to the role for correction before final output. Reporting requires the full original schema, and immutable evidence hashes are checked again on recovery and completion. A checkpoint is never a pass. Explicit OS read-only roles retain direct full-result output without broadening permissions; resumed saved findings and evidence still pass the same preservation checks.

An idle role or recognized model disconnect may resume its verified checkpoint at most twice, in the same role directory/run. Remaining work and observation/reporting stage are carried forward; already performed create/send/delete actions are not blindly replayed after browser state resets. The host persists recovery consumption, including explicit resume of any already-invoked role, so `resume` cannot reset an exhausted budget. Without an accepted checkpoint, explicit resume first inspects prior images/receipts and blocks if actions cannot be reconstructed safely; automatic recovery still requires a verified checkpoint. A rejected draft is retained with its validation reason for targeted repair; accepted observations and current-role images are reused instead of repeating the review. Application coverage starts after resizing: its old-width before-image cannot prove a target-width operation. Authentication, approval, explicit deadlines, user interruption and interrupted fixer edits never auto-retry. Recognized native browser failures retain the existing recorded local-browser fallback.

`--max-iterations` still counts fixer → independent reviewer cycles (default five). Two consecutive non-improving reviews stop as `stalled`; resumed pending reviews use the same calculation. Reaching the iteration limit with unresolved conditions is `incomplete`, without resetting counts. These limits are not screenshot or click quotas and do not change full/focused coverage or pass gates.

Resume preserves saved settings. `resume RUN_ID --phase-timeout 0 --idle-timeout 900` explicitly overrides future execution limits and records the change without rewriting frozen config or completed results. Old runs without checkpoints restart only their unfinished role. On failure, the run retains `partial-review.md` with verified observations, remaining work and the stop reason; it does not overwrite the project's previous complete review before a new audit exists.

There is no automatic dependency installation in a target project. Source changes stay as a diff; there are no automatic commits, resets or deployments. Unexpected source changes stop the run and remain available for inspection. Simultaneous edits to the same file cannot be attributed reliably: avoid concurrent target editing while running fixes.

Results: `reviewed` means a review completed, not that the app passed. `passed` means the scoped improvement gates passed. `incomplete` or `stalled` exits 2; `blocked` exits 1; interrupt exits 130. Missing screenshots, malformed output and blocked required flows cannot pass.

Per-run artifacts live in `artifacts/ux-gan/RUN_ID/`, with JSON role results, redacted JSONL logs, coverage, tests and status. Images are archived under `docs/ui-ux-review-assets/RUN_ID/` after each role; they are not kept in `test-results`. The latest report is `docs/ui-ux-review.md`; comparison and before/after results are `docs/ui-ux-reference-apps.md` and `docs/ui-ux-fix-report.md`. Previous reports and their linked local images are copied into the run's `input/` directory before replacement. Each run also holds its own report copies.

Structured results and screenshot existence checks support reproducibility; they do not prove that an AI's severity judgement matches an actual novice's experience. Native Browser/MCP screenshots must be copied into the run's `screenshots/` directory and referenced in the role's evidence list. The local bridge additionally records tool-generated frame hashes and before/after action history. Public reference screenshots and live target screenshots remain distinct.

Version 1.1.0 bundles its own `references/design/` copy of the canonical ooui-design guidance,
including an index, shared review policy, modeling decisions, all 29 cognitive-load tips,
quality checks and sources. It does not depend on a sibling skill or the target app to supply
these files. Source checkouts/extracted distributions read the canonical files in the same
distribution. `doctor` and execution preflight reject missing, empty or invalid bundles.
Each role's `prompt.txt` includes the policy summary, version, reference paths and hashes;
read the detailed references only when relevant. Role result schemas and CLI flags are unchanged.

Version 1.1.2 adds read-only recall of related past feedback from the existing Basic Memory
project to that shared policy. Each role checks the note's original context and exceptions
against the current brief; current screenshots and operations still establish findings and
resolution. Already-read supplied notes may be reused. Missing Memory, failed lookup or no
matching notes does not block execution, and the harness does not install/configure/write Memory.
Read available kotonoha (fall back to yomiyasu) once, without applying both. Polishing
Japanese UI drafts and report narrative fields before
returning JSON is recommended. Preserve evidence, IDs, numbers, conditions, outcomes, keys/enums
and certainty; published reports and archived results remain parent-owned generated artifacts.

OOUI observations go into screen information/interaction; remembering, searching, comparing,
guessing, backtracking and re-entry go into flow friction and simplicity. The representative
flow and counting method belong in simplicity's rationale. Required information, appropriate
confirmations and state recovery matter alongside density. These are AI observations supported
by operations and images, not measured cognitive workload or human satisfaction.
When resuming older runs, prior evidence remains intact; newly executed roles receive the
current policy. An already completed older run is not re-evaluated by `resume`; start a new
audit/run to assess it under the new guidance.
