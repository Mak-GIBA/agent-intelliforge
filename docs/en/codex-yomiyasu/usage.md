# Use kotonoha

[Overview](README.md) · [Installation](installation.md) · [Validation](../../codex-yomiyasu/validation.md)

```text
$kotonoha Revise this Japanese report so a new engineer can follow the mechanism. Preserve facts, numbers, conditions and certainty.
$kotonoha Edit this email only where necessary; return the body only.
$kotonoha Diagnose the paragraph structure without rewriting it.
```

One entry handles full writing/revision and narrower tasks. Preserve terminology, quotations, code, numeric values, negation, conditions, actors, causality and certainty. Do not invent evidence or actors. Brevity and lint scores alone are not the goal.

SKILL.md carries the core workflow. Read references/long-form.md for substantial structure or technical explanations, references/file-review.md for file edits, and maintenance/provenance only when relevant.

```bash
python ~/.agents/skills/kotonoha/scripts/writing_lint.py before.md
python ~/.agents/skills/kotonoha/scripts/writing_lint.py after.md --before before.md
python ~/.agents/skills/kotonoha/scripts/check.py outline after.md
python ~/.agents/skills/kotonoha/scripts/check.py compare before.md after.md --protect=--apply
```

Use the dedicated Python configured by installation when needed. New upstream run/verify checks are exposed through check.py source-check with an explicit --state-dir outside the original resources. See the bundled file-review.md. Helpers do not rewrite documents. Missing execution is distinct from findings, and equal hashes or tokens do not establish semantic correctness or human approval.

The shared CLI accepts `intelliforge kit-run kotonoha --tool writing_lint.py -- after.md --before before.md`; yomiyasu remains a kit alias. Ordinary writing performs no upstream updates.
