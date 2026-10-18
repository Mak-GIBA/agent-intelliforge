# Codex UX Stack

**English** | [日本語](../../codex-ux-stack/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md) · [Validation (Japanese)](../../codex-ux-stack/validation.md)

Design screens around the objects users work with: object-oriented UI, or OOUI. In a booking app, for example, connect the booking list/detail to actions on the selected booking. After implementation, screenshots and real browser operations check discoverability and completion of main tasks.

[install_codex_ux_stack.sh](../../../install_codex_ux_stack.sh) is standalone; Workgraph and SpecKit are optional.

## Components

| Component | Source / format | Purpose | Selection |
|---|---|---|---|
| ooui-design | Repository Skill/references | Object/view/action design, cognitive-load checks, implementation handoff | Standard |
| UI/UX GAN Harness | Repository Bash/Python/Skill | Screenshot reviews, reference comparisons, fixes, independent verification | Standard |
| Product Design | OpenAI Plugin | Design ideas, prototypes, existing-flow review | Standard |
| Build Web Apps | OpenAI Plugin | Frontend implementation/browser tests | Standard |
| web-design-guidelines | Vercel Skill | Code checks for observed UI issues | Standard |
| Playwright MCP | Microsoft MCP | Browser operations from Codex | Standard |
| Local Playwright | Microsoft library/custom adapter | Screenshot/action fallback when normal routes fail | Standard |
| ux-critique | Thecsiz Skill | Additional knowledge-base critique | `--deep` |
| kotonoha / yomiyasu compatibility | Separate writing kit | Japanese copy and report revision | Recommended, not installed here |
| Basic Memory | Existing Memory tools | Contextually relevant past feedback | Read-only when available |

New apps follow **OOUI design → visual design/implementation → browser verification**. ooui-design organizes users, objects, attributes, relations, lists/details, actions, and retained state into a short handoff for Product Design / Build Web Apps, keeping required features and priorities through image generation and implementation.

Search, bulk actions, fixed-target operations, and meaningful wizards depend on the task. Keep major tasks clear without adding unnecessary decoration, permanent explanations, or controls. Do not remove required actions or hide information in ways that increase search/backtracking.

At design/review/fix start, recall available Basic Memory feedback and compare original context/exceptions with current users, goals, and constraints. Current screenshots/actions establish findings and resolution. Record applied notes/reasons briefly in existing findings. Missing Memory/search failure/no matches do not block work; this does not install/configure/write Memory.

Japanese drafts can be polished once with kotonoha, falling back to yomiyasu; do not apply both. Preserve claims, numbers, conditions, results, and evidence, and keep short labels short. See the [separate installer](../codex-yomiyasu/installation.md).

The custom existing-app harness references [ECC's iteration structure](https://github.com/affaan-m/ECC/blob/ef648e01899ba3e8dc6371642deaaf64b4477775/scripts/gan-harness.sh). It runs separate researcher/fixer/reviewer Codex executions, not model training. Use the requested audience, with first-time, mistaken, hurried, and explanation-skipping perspectives as additional checks. Prefer consolidation, removal, ordering, and precise copy before adding UI. Recheck steps, decisions, mobile density, and before/after screenshots. Reference research normally seeks 3 apps, distinguishing public interactions from official images.

## First request

```text
$ooui-design Design and implement this app around the objects users work with. Organize screens and actions before visual design; verify required features and retained state in the browser. Avoid unnecessary decoration, explanation, and permanent controls. Polish Japanese copy with available kotonoha, or yomiyasu if missing.
```

For an implemented app:

```text
$ux-gan-harness Run the installed gan-harness.sh to review this app using screenshots, then iterate fixes and independent rechecks. Prioritize clear main actions without adding excessive explanations or buttons.
```

Specify no code changes for review-only. Installation itself does not modify an app; execution needs the target, URL, and test environment. AI observations are separate from human usability testing. See [usage](usage.md) and [validation limits (Japanese)](../../codex-ux-stack/validation.md).

## Design references

The workflow uses [Emuni](https://zenn.dev/emuni/articles/ooui-agent-skill) for process/verification scope, [Star Festival](https://zenn.dev/stafes_blog/articles/shota1995m-ooui) for contextual choices, [Sociomedia's OOUI material](https://www.sociomedia.co.jp/7279), and the supplied cognitive-load tips. [Cognitive-load guidance (Japanese)](../../../tools/codex-ux-stack/ooui-design/references/cognitive-load.md) and [sources (Japanese)](../../../tools/codex-ux-stack/ooui-design/references/sources.md) are bundled, so normal use/installation does not require reaching the articles. OOUI structure and functional/visual/interaction completeness are checked separately.
