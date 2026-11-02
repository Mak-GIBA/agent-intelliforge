# Codex UX Stack

Use **`$ux`** as the common entry for consultation, review, redesign, implementation and improvement.
It selects and combines the specialist workflows according to the goal and permitted changes.
Reviews may include structural analysis and redesign proposals without applying them to app code or approved designs.
The visual workflow creates editable flows/wireframes, reconciles human edits into a local UX contract,
and checks implementation through browser-owned evidence. Whimsical and Figma Remote MCP
are explicitly selected options; Mermaid, SVG and HTML work without them.
See [visual design and collaboration](visual-design.md).
The [1.4.0 verification report (Japanese)](../../codex-ux-stack/verification-1.4.0.md)
separates local regression tests, actual browser operations, model comparisons and unverified SaaS authentication.
See the [1.5.0 entrypoint checks (Japanese)](../../codex-ux-stack/verification-1.5.0.md) for installation,
scope decisions, the single seven-case model trial and its limits.

**English** | [日本語](../../codex-ux-stack/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md) · [Validation (Japanese)](../../codex-ux-stack/validation.md)

Design screens around the objects users work with: object-oriented UI, or OOUI. In a booking app, for example, connect the booking list/detail to actions on the selected booking. After implementation, screenshots and real browser operations check discoverability and completion of main tasks.

[install_codex_ux_stack.sh](../../../install_codex_ux_stack.sh) is standalone; Workgraph and SpecKit are optional.

## Components

| Component | Source / format | Purpose | Selection |
|---|---|---|---|
| ux | Repository Skill | Common entry selecting analysis, design, implementation and verification | Standard |
| ooui-design | Repository Skill/references | Object/view/action design, cognitive-load checks, implementation handoff | Standard |
| ux-visual-design | Repository Skill/contract/helpers | Editable flows and wireframes, co-edit reconciliation, implementation conformance | Standard |
| UI/UX GAN Harness | Repository Bash/Python/Skill | Screenshot reviews, reference comparisons, fixes, independent verification | Standard |
| Product Design | OpenAI Plugin | Design ideas, prototypes, existing-flow review | Standard |
| Build Web Apps | OpenAI Plugin | Frontend implementation/browser tests | Standard |
| web-design-guidelines | Vercel Skill | Code checks for observed UI issues | Standard |
| Playwright MCP | Microsoft MCP | Browser operations from Codex | Standard |
| Local Playwright | Microsoft library/custom adapter | Screenshot/action fallback when normal routes fail | Standard |
| Whimsical / Figma Remote MCP | Official provider endpoints | Editable flows, wireframes, UI design and collaboration | Explicit `--visual-tools` selection |
| ux-critique | Thecsiz Skill | Additional knowledge-base critique | `--deep` |
| kotonoha / yomiyasu compatibility | Separate writing kit | Japanese copy and report revision | Recommended, not installed here |
| Basic Memory | Existing Memory tools | Contextually relevant past feedback | Read-only when available |

New apps follow **OOUI design → visual design/implementation → browser verification**. ooui-design organizes users, objects, attributes, relations, lists/details, actions, and retained state into a short handoff for Product Design / Build Web Apps, keeping required features and priorities through image generation and implementation.

Search, bulk actions, fixed-target operations, and meaningful wizards depend on the task. Keep major tasks clear without adding unnecessary decoration, permanent explanations, or controls. Do not remove required actions or hide information in ways that increase search/backtracking.

At design/review/fix start, recall available Basic Memory feedback and compare original context/exceptions with current users, goals, and constraints. Current screenshots/actions establish findings and resolution. Record applied notes/reasons briefly in existing findings. Missing Memory/search failure/no matches do not block work; this does not install/configure/write Memory.

Japanese drafts can be polished once with kotonoha, falling back to yomiyasu; do not apply both. Preserve claims, numbers, conditions, results, and evidence, and keep short labels short. See the [separate installer](../kotonoha/installation.md).

The custom existing-app harness references [ECC's iteration structure](https://github.com/affaan-m/ECC/blob/ef648e01899ba3e8dc6371642deaaf64b4477775/scripts/gan-harness.sh). It runs separate researcher/fixer/reviewer Codex executions, not model training. Use the requested audience, with first-time, mistaken, hurried, and explanation-skipping perspectives as additional checks. Prefer consolidation, removal, ordering, and precise copy before adding UI. Recheck steps, decisions, mobile density, and before/after screenshots. Reference research normally seeks 3 apps, distinguishing public interactions from official images.

## First request

```text
$ux Design and implement this app around the objects users work with. Organize screens and actions before visual design; verify required features and retained state in the browser. Avoid unnecessary decoration, explanation, and permanent controls. Polish Japanese copy with available kotonoha, or yomiyasu if missing.
```

For an implemented app:

```text
$ux Review this app using screenshots and operations. Include structural or navigation redesign proposals when useful. Stop at proposals; do not change app code.
```

Specify no code changes for review-only. Installation itself does not modify an app; execution needs the target, URL, and test environment. AI observations are separate from human usability testing. See [usage](usage.md) and [validation limits (Japanese)](../../codex-ux-stack/validation.md).

## Design references

The workflow uses [Emuni](https://zenn.dev/emuni/articles/ooui-agent-skill) for process/verification scope, [Star Festival](https://zenn.dev/stafes_blog/articles/shota1995m-ooui) for contextual choices, [Sociomedia's OOUI material](https://www.sociomedia.co.jp/7279), and the supplied cognitive-load tips. [Cognitive-load guidance (Japanese)](../../../tools/codex-ux-stack/ooui-design/references/cognitive-load.md) and [sources (Japanese)](../../../tools/codex-ux-stack/ooui-design/references/sources.md) are bundled, so normal use/installation does not require reaching the articles. OOUI structure and functional/visual/interaction completeness are checked separately.
