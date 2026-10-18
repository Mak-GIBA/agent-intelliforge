# Workgraph: daily use and settings

**English** | [日本語](../../basic-memory-workgraph/usage.md)

[Overview](README.md) · [Installation](installation.md) · [Sharing](sharing.md) · [Reference](reference.md) · [Troubleshooting](troubleshooting.md) · [Documentation](../README.md)

Run terminal examples from the repository root; enter requests in Codex.

<a id="daily"></a>

## Daily use

Ask Codex to work normally. It searches relevant Memory before work and reviews successful procedures/corrections afterward. Only qualifying knowledge is saved. Hooks prompt recall/evaluation; Codex makes the decision and writes notes. [Modes](#modes) control eligible types.

### Learn from the agent's own workflow

Review attempted method → obstacle → changed method → verification → next use. Verified workarounds can qualify without a user correction. If the remedy is verified but the cause is unknown, retain that distinction. Lessons meeting all five criteria become conditional Rules, Workflows, or Validations. Do not save failure-only records, untested remedies, generic advice, private reasoning transcripts, or raw logs. Update existing knowledge only for material new evidence or conditions; no Case or automatic Skill setting is needed for ordinary reusable lessons.

```text
If these attempts and fixes produced a verified lesson that would reduce rework next time, save it in Memory with conditions and evidence.
```

### Recall relevant knowledge

```text
Check relevant Corrections, Rules, Workflows, and Cases in Basic Memory before working. Distinguish conditions that apply here from those that do not.
```

### Apply corrections before the next first draft

With [contextual Correction capture](#correction-mode), a request such as “put the comparison and recommendation before the details for decision makers” can become a `corrections/` candidate. Save the purpose, audience, output, constraints, desired result, and scope, not just the instruction. Record observed mismatch/reasons only when known. Instructions can be confirmed while effects remain unverified and acceptance unknown.

Recall similar Corrections before drafting. A decision-document ordering is not a universal rule for technical explanations or a lasting preference for short writing. Current instructions override history; quoted instructions do not authorize new actions. Update same-scope corrections when requirements change; distinguish other contexts. No full logs, acknowledgments, ordinary new requests, or duplicates. A Correction is not automatically a training Case or sharing/training permission. See [format (Japanese)](../../../tools/basic-memory-workgraph/templates/CORRECTIONS.md).

### Save a transferable lesson

```text
Save any lesson from this correction that can help another task. Retain applicability conditions and verification rather than generalizing this task's details.
```

For example, mismatched denominator definitions followed by recalculation can support a conditional rule when verification and added value exist. Mere completion or a passing test is insufficient.

### Explicitly save a concrete Case

```text
Save this interaction as a Case showing the request, initial output, correction, improved output, and result. Anonymize necessary excerpts and link existing related Rules. Do not authorize sharing or training yet.
```

This scoped explicit request works even with Case mode `off`. Automatic selection requires an enabled Case mode.

### Capture an improvement sequence progressively

[Progressive mode](#progressive-mode) extends one Case for the same output/purpose: initial output, corrections, revisions, and later use. Useful unfinished sequences, reuse requests, and non-obvious verified successes can qualify without corrections, but routine completion cannot. Preserve which instruction/action concerned which version. Recall contextually similar Cases before drafting.

No rating prompt is needed. User-directed commit/push, downstream use, reuse, or narrowing may be observed evidence, not proof of execution or satisfaction. Commit/push alone is tentative; autonomous/backup commits are not adoption. Commit and push are not two votes; silence/time/topic changes prove nothing. Later correction/reversal requires reassessment while retaining actual history. Do not reconstruct unknown chronology from logs. Separate outputs into Cases; cross-session continuity requires confirmed identity. Verification-only Cases leave adoption assessments empty. CLI validates structure/references; Codex judges capture and contextual interpretation. See [CAPTURE (Japanese)](../../../tools/basic-memory-workgraph/templates/CAPTURE.md).

### Remember an ongoing preference

```text
For future projects, default to Japanese replies unless I ask for English writing. Remember this preference and exception.
```

A one-time “make this button blue” is not a lasting preference. Plan/read-only prohibits writes even with an explicit request.

### Distinguish record types

| Type | Content | Use |
|---|---|---|
| Correction | Context, instruction, desired output, scope; effect may be unknown | Avoid repeating the mismatch before drafting |
| Abstract Memory | Conditional rule, reusable procedure, verification method | Decisions/procedures in other tasks |
| Case | Actual request/output/correction/improvement/result | Contextual comparison or training candidate |
| Skill | Reviewed, validated execution procedures/resources | Repeated work |

Abstract Memory and Cases qualify independently and are linked only if both exist. Workflow retains Skill packaging rationale; Artifact references only registered Skills.

### Share through GitHub

```text
Share the reviewed team memory through GitHub and create the PR.
```

```text
Import the shared memory while preserving locally edited notes.
```

A new session reads the shared AGENTS routing. Missing configuration/login triggers focused support. Sharing designation and content review are still required. See [setup](github-sharing.md).

<a id="modes"></a>

## Change settings

Use `--configure-only` at the repository root. **Only specified settings change; omitted settings remain.** Start a new session afterward.

<a id="correction-mode"></a>

### Enable contextual Corrections

For an existing installation adding this feature, use the [Python environment](installation.md#python-tools) and update its schema:

```bash
BM_CORRECTION_MODE=scoped bash install_basic_memory_workgraph.sh --update
```

For later mode-only changes:

```bash
BM_CORRECTION_MODE=scoped bash install_basic_memory_workgraph.sh --configure-only
# Disable automatic Corrections only
BM_CORRECTION_MODE=off bash install_basic_memory_workgraph.sh --configure-only
```

`scoped` allows corrections with unknown outcomes when context and narrow scope are known. It works with `case=off`. Existing users are not automatically opted in; default is `off`.

### Enable useful concrete Cases

```bash
BM_CASE_MODE=reusable bash install_basic_memory_workgraph.sh --configure-only
```

Select valuable successful/corrected interactions for comparison or learning, not whole-conversation logging.

<a id="progressive-mode"></a>

### Capture unfinished improvement sequences

Update Case v2 and its audit CLI using the [Python environment](installation.md#python-tools):

```bash
BM_CASE_MODE=progressive bash install_basic_memory_workgraph.sh --update
```

`reusable` captures useful cases with results; `progressive` also admits useful unfinished sequences and reuse requests. Explicit acceptance is not required by either. `off` permits only explicit scoped requests. Updates preserve existing `caseMode`, using `off` when unset. For installed features, `--configure-only` can switch the mode.

### Enable automatic Skill registration

```bash
BM_SKILL_MODE=auto bash install_basic_memory_workgraph.sh --configure-only
```

An available `skill-creator` or equivalent reviews duplicates and packaging value beyond a note. Register only after validation; missing creator/validation leaves a candidate. Never overwrite Plugin or personal Skills. Even Workgraph-managed Skills stop automatic updates when user edits exist. Combine modes if desired:

```bash
BM_CASE_MODE=reusable BM_SKILL_MODE=auto \
bash install_basic_memory_workgraph.sh --configure-only
```

### Disable or restore automation

```bash
# Disable automatic Cases; keep Skill review only
BM_CASE_MODE=off BM_SKILL_MODE=review \
bash install_basic_memory_workgraph.sh --configure-only

# Disable all automatic capture and Skill review
BM_AUTO_MODE=off bash install_basic_memory_workgraph.sh --configure-only

# Resume automatic evaluation, retaining saved Case and Skill modes
BM_AUTO_MODE=smart bash install_basic_memory_workgraph.sh --configure-only
```

**`BM_AUTO_MODE=off` disables all automatic processing, including Corrections, Cases, and Skill review/registration, regardless of other modes.** Explicit requests remain scoped exceptions. The registration CLI requires `auto` Skill mode.

### All settings and current values

| Variable | Values and behavior |
|---|---|
| `BM_AUTO_MODE` | `smart` (default): evaluate candidates after confirming implementation mode; `always`: evaluate each implementation turn with the same admission criteria; `off`: disable automatic capture/review/registration |
| `BM_CORRECTION_MODE` | `off` (default): explicit only; `scoped`: observed corrections with context and limits, including unknown outcomes |
| `BM_CASE_MODE` | `off` (default): explicit only; `reusable`: useful cases with results; `progressive`: useful corrections, downstream/reuse requests, non-obvious verified successes, and later adoption/reversal evidence |
| `BM_SKILL_MODE` | `off`: no automatic review; `review` (default): assess packaging; `auto`: register after review and validation |

```bash
cat "${CODEX_HOME:-$HOME/.codex}/basic-memory-workgraph/config.json"
```

New installations use the following; updates preserve existing values:

```json
{
  "mode": "smart",
  "correctionMode": "off",
  "caseMode": "off",
  "skillMode": "review"
}
```
