# Visual UX design and collaborative editing

[Overview](README.md) · [Installation and OAuth](installation.md) · [日本語](../../codex-ux-stack/visual-design.md)

`ux-visual-design` turns requirements and existing behavior into Journeys, screens, states,
actions, recovery paths, editable diagrams and implementable UI designs. It reuses the OOUI
model and design system; fixed procedures can use task-oriented flows. Minor CSS/copy changes
do not require a complete redesign or a new document set.

```text
$ux-visual-design
Visualize search → document → related document → collection for this existing app.
Preserve filters, selection and notes. Include save failure and retry. Keep the canonical
contract at docs/ux/design-contract.json, provide editable diagrams/wireframes, then implement
and verify in a real browser. Use local artifacts if design MCP is unavailable.
```

New or substantial changes have a reviewable design stage. An explicit implementation request
does not require another approval wait. Unapproved artifacts never become approved automatically.

## Canonical contract and editable sources

Local JSON stores user goals, Journey/Screen IDs, screen purpose, routes, states, actions,
transition conditions/destinations, errors, retained fields, required features and acceptance
assertions. It maps external file/node IDs and URLs to implementation component paths.
See the [schema](../../../tools/codex-ux-stack/ux-visual-design/assets/contract.schema.json) and
[document example](../../../tools/codex-ux-stack/ux-visual-design/assets/document-example.json).

Journey IDs become harness flow IDs. Screen IDs remain screen IDs. Assertions support visibility,
exact text/value/selection, focus, accessible name and URL. `approval.status/source` records actual
approval/delegation evidence. Valid JSON does not prove UX quality.

For approved designs, artifacts can include `revision` and `snapshot: {path, sha256}` pointing to
a project-local PNG. The host freezes that image with the contract and supplies it to independent
review. An approved design without a reference remains unverified and cannot pass a run. The
presence of an image alone never proves visual agreement; actual comparison remains necessary.

```bash
python3 <skill-dir>/scripts/ux_contract.py validate --contract docs/ux/design-contract.json
python3 <skill-dir>/scripts/ux_contract.py export --contract docs/ux/design-contract.json --design docs/ux/visual
python3 <skill-dir>/scripts/ux_contract.py import --contract docs/ux/design-contract.json --design docs/ux/visual/wireframes.svg
```

Export produces editable Mermaid, SVG, interactive HTML and an ownership manifest. Mermaid retains
state/transition/error bindings; SVG retains screen/action IDs. HTML is a structural prototype with
branches and retained inputs, without real sending or payment. Develop main screens further:
hierarchy, density, typography, spacing, CTA priority, forms, navigation, feedback, responsive layouts
and reusable components/tokens.

## Reconcile human changes

Edit supported SVG titles/actions/layout/color or Mermaid labels/state edges/conditions while retaining
IDs and the embedded baseline. Unsupported deletion or rebound error edges stop explicitly.
Use canonical JSON or a `{base, contract}` JSON exchange for screen/requirement additions and deletions.
Import compares the baseline, current local contract and human edits. Independent edits merge;
same-field conflicts are preserved and reported. No-op imports do not increase the revision.

Import previews by default; append `--apply` for changes within the authorized scope. Edited outputs
are protected from re-export. Changes to approved designs return them to `needs_review`.
Unmapped annotations/styles remain in the source and report `preserved_unmapped_edits`.
Export to another directory or reconcile those edits explicitly. No-op apply also preserves JSON formatting.
For external canvases, rediscover read tools, reread the specific file/version and node IDs, normalize
observed edits using `artifacts.bindings`, and use the same three-way exchange. There is no background sync.
Scope writes to requested files/frames/nodes. Code-based Figma editing uses the official host Skill;
generic arbitrary-JavaScript execution is unavailable.

## Implementation and browser conformance

Pass the contract, IDs, screens, components/tokens, responsive decisions and unresolved conditions
to available Product Design / Build Web Apps workflows. Add `--project .` to validation after
implementation to check actual component paths; omit it during design-only work.

```bash
ux-gan-harness run --project . --url http://localhost:3000 \
  --ux-contract docs/ux/design-contract.json --journey J-doc --test-command 'npm test'
```

The host freezes the contract and selects the bundled browser for screenshot-bound assertions.
`ux_check_contract` observes routes, state-specific acceptance conditions, action targets, transitions
and retained values. If an input unmounts, its value remains unverified until it reappears.
Missing screens, wrong actions/routes, lost inputs, failed assertions and missing evidence prevent a pass.
Human design changes invalidate a frozen run and require reconciliation. Do not weaken the design to
match broken code. Review current screenshots for appearance, contrast, cognitive load and consistency.
Automated checks and AI ratings are distinct from human usability testing.

Additional distribution users run helpers with
`intelliforge kit-run ux-stack --agent codex --tool ux_contract.py -- <arguments>` and the harness
with `intelliforge kit-run ux-stack --agent codex -- <arguments>`.
