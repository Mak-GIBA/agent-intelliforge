# Write and revise with kotonoha

**English** | [日本語](../../codex-yomiyasu/usage.md)

[Overview](README.md) · [Installation](installation.md)

## Specify the text and constraints

Open a new Codex session and request the Skill:

```text
$kotonoha Revise docs/usage.md in Japanese for a first-time user. Preserve commands, settings, defaults, and exceptions; fix unclear explanations.
```

```text
$kotonoha Write this PR description in Japanese so developers and non-developers can follow it. Preserve purpose, verified results, and unverified scope.
```

New writing starts with a draft, then one revision. For existing files, specify scope and compare original/diff. Verbatim legal text and quotations must remain unchanged.

| Invocation | Purpose |
|---|---|
| `$kotonoha` | Whole-document Japanese writing/revision |
| `$yomiyasu` | Same workflow, explicit compatibility entry |
| `$paragraph-writing` | Paragraph structure only |
| `$japanese-direct-writing` | Excessive caveats, defensive wording, and hedges only |

`auto` allows relevant automatic selection. Code-only changes, simple fact lookup, and verbatim quotation are excluded. Normal requests do not need every auxiliary name listed.

## Explain mechanisms and practical changes

```text
$kotonoha Revise this technical explanation in Japanese for a new team member. Use only the draft and supplied material to explain missing reasons, processing steps, and differences. Do not assert uninvestigated causes or unmeasured effects.
```

Use extra explanation only where important abstract claims leave the mechanism unclear. Show what processes what and under which conditions behavior changes, using evidence in the material. Claim, explanation, concrete illustration, and consequence are roles, not a fixed four-sentence template. Do not add what the reader already knows.

Revision must not invent methods, causes, or numbers. New explanatory writing can use clearly hypothetical examples, never disguised measurements. Unknown causes remain unknown; connector/example counts are not targets. Short emails and word edits do not need the heavy explanatory workflow. See [comparisons and examples (Japanese)](../../codex-yomiyasu/kotonoha-validation.md).

## Organize paragraphs and reasoning

```text
$paragraph-writing Reorganize this Japanese report for the person deciding whether to adopt the approach. Connect conclusions and evidence while retaining numbers, conditions, and unmeasured scope.
```

Clarify each paragraph's point, supporting evidence, and relationship to the next. Reports/PRs lead with decision-relevant status; technical explanations introduce necessary premises in order. kotonoha reads the real paragraph-writing asset during its structure stage, using the same draft, without requiring an extra user invocation. Local wording/order-preserving requests do not trigger rearrangement. Preserve code, tables, procedures, IDs, comparison conditions, negation, and uncertainty. The auxiliary also works independently; see [history (Japanese)](../../codex-yomiyasu/validation.md).

## Remove unnecessary caveats

```text
$japanese-direct-writing Remove unnecessary disclaimers and defensive caveats from this Japanese explanation. Preserve evidence, explanatory depth, important conditions, and unverified scope.
```

Remove notes that do not affect understanding/judgment, retaining necessary uncertainty next to its claim. Keep quotations, numbers, protected notes, and concrete safety conditions. kotonoha reads the real auxiliary once in its hedge stage; multiple Skill names do not repeat the work. If auxiliaries are missing, bundled references provide fallback; disclose that outside the finished text.

## Review AI-like patterns and audience boundaries

Review formulaic contrasts, unsupported significance, repeated paragraph shapes, and abstract padding in context. Do not invent feelings/experience or artificially vary sentence lengths/endings.

Separate the final reader from the requester. “I made this clear as requested” belongs outside the finished draft; apply the instruction to the writing itself. Legitimate recipient requests, research objectives, procedures, and quoted expressions remain. Inspect titles, tables, captions, notes, and HTML comments too.

Read once as someone without the production conversation. Fix only actual residue, omissions, inventions, or formulaic wording, with at most one targeted revision. Review notes/self-scores stay outside the final text.

## Check saved files

Keep an original UTF-8 copy outside the delivery location. Run textlint before/after and markdownlint for Markdown. Findings are candidates, not targets for arbitrary shortening or zero scores. The checker does not edit files.

```bash
# The managed Python path is recorded in .kotonoha-runtime/settings.json
<python-path> <skills-dir>/yomiyasu/scripts/writing_lint.py after.md --before before.md
# For a Plugin installation
intelliforge kit-run yomiyasu --agent codex --tool writing_lint.py -- after.md --before before.md
```

JSON distinguishes checked from unavailable. If tools fail, continue revision and disclose omitted checks outside the text. No external text-rating API, Jev, or automatic hooks are added.

### Compare meaning and paragraph structure

Replace `before.md` and `after.md` with your original/revised files:

```bash
python3 ~/.agents/skills/yomiyasu/scripts/check.py lint after.md --genre manual
python3 ~/.agents/skills/yomiyasu/scripts/check.py outline after.md
python3 ~/.agents/skills/yomiyasu/scripts/check.py compare before.md after.md --protect=--apply --stance 説明
```

`--genre` accepts `report / research / email / manual / article / template`; repeat `--protect` for multiple terms. Inspect numeric/ID/code/link changes and lint candidates. `outline` extracts paragraph openings, not a judgment of reasoning. These local checks neither change files nor send text outside. Zero findings do not establish equivalent meaning: read negation, conditions, causality, and certainty yourself.

GitHub posting permission and Office layout checks follow their own workflows. Using kotonoha alone does not authorize posting, sharing, commit, or push.
