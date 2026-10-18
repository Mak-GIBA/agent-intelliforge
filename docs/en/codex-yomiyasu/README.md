# kotonoha — clear, natural Japanese writing

**English** | [日本語](../../codex-yomiyasu/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md)

kotonoha helps write and revise Japanese technical documents, specifications, Issues/PRs, and reports without changing meaning. It preserves numbers, terminology, conditions, and certainty while untangling syntax and repetition. Where an important claim is too abstract, it explains mechanisms and practical changes supported by the source material.

kotonoha 3.0.0 is a custom workflow combining meiseki's syntactic clarity, paragraph structure, explanatory depth, hedge reduction, and yomiyasu's natural style. It uses relevant references on the same draft rather than repeatedly loading whole upstream Skills. Upstream originals, versions, and licenses remain separately recorded.

Use `$kotonoha` normally. `$yomiyasu` is a compatibility entry; paragraph-writing and japanese-direct-writing handle narrower requests. Short emails and already adequate drafts do not receive unnecessary explanation.

`--apply` prepares missing Python, Node.js, textlint, and markdownlint in a user-local environment. Compatible existing tools are reused; system defaults and shell settings stay unchanged. Maintained assets and dependency versions are under `tools/codex-yomiyasu/`.

The standalone [Bash](../../../install_kotonoha.sh) and [PowerShell](../../../install_kotonoha.ps1) scripts preview without arguments and install with `--apply`. The old [install_codex_yomiyasu.sh](../../../install_codex_yomiyasu.sh) remains supported.

## Components

| Asset | Source | Purpose |
|---|---|---|
| meiseki originals, syntax rules, lint configuration | [bamboo-nova/meiseki](https://github.com/bamboo-nova/meiseki) | Negation, modifier relationships, nominalization, redundant wording |
| yomiyasu originals, lint, diff | [nanaism/yomiyasu](https://github.com/nanaism/yomiyasu) | Japanese revision and static checks |
| kotonoha entry/common workflow | This repository | Audience, paragraphs, wording, hedges, meaning preservation |
| paragraph-writing | Repository revision of an earlier Gist-derived Skill | Paragraph-only requests and integrated structure review |
| japanese-direct-writing | Repository revision of an earlier supplied ZIP | Hedge-only requests and integrated review |
| `scripts/check.py` | This repository | Requester-facing residue, paragraph openings, numeric/code differences, upstream checks |

meiseki originals are stored as `meiseki-upstream/SKILL.upstream.md` plus settings, dictionaries, and MIT license. yomiyasu uses `upstream/SKILL.upstream.md` plus references/scripts/licenses. Auxiliary Skill bodies are maintained here with provenance/change records in `UPSTREAM.json` / `SOURCE.json`; this differs from installing the untouched 1.3.0 ZIP. They update from bundled assets without contacting the original Gist/ZIP location.

ECC, Basic Memory, Office Workbench, and GitHub Project Director are optional, not required dependencies. Existing hooks, MCP, AGENTS, and other Skill settings are unchanged.

## From installation to use

1. [Install and update](installation.md), checking placement and protection.
2. [Specify the draft and preserved facts](usage.md).

[Validation (Japanese)](../../codex-yomiyasu/kotonoha-validation.md) reports prompt size, examples, failures, and limits. Limited automated comparisons do not establish general quality superiority; installer tests are separate from writing evaluation. Earlier [validation history (Japanese)](../../codex-yomiyasu/validation.md) and [explanation design (Japanese)](../../codex-yomiyasu/explanation-design.md) remain available.
