# Recording policy and validation

**English** | [日本語](../../codex-github-pm/behavior.md)

[Overview](README.md) · [Usage](usage.md) · [Installation](installation.md)

## Current policy

v1.3.1 handles natural GitHub management requests, offers focused connection support, and records only important new information.

| Decision | Policy |
|---|---|
| Activate the Skill? | Use progress, task, priority, and blocker workflows when context identifies GitHub |
| Offer connection support? | Address confirmed missing login, connection, or target, then resume the task |
| Leave a comment? | Check shared value, existing records, and scope; unnecessary comments need neither a draft nor approval prompt |
| How to write? | Explain purpose, changes, verification, next action, completion criteria, and important constraints |

Aggregate blockers needing judgment, agreed scope changes, and handoffs. Do not stream starts, retries, or test successes, or copy adequate PR outcomes into another comment. Recurring reporting requires explicit instruction/agreement and normally no post without changes; explicit no-change reporting is an exception. Missing destinations alone do not justify creating recurring Issues.

The maintained writing/posting policy is `references/writing-and-tracking.md`, shared by the main Skill and operation/meeting procedures. See [usage](usage.md).

## Changes

- **v1.3.0:** stronger natural activation, posting-necessity checks, and readable writing guidance.
- **v1.3.1:** support for confirmed connection gaps; reuse known information/authorization and provide concrete user-side steps when unable to act.

Connection support is neither automatic login nor an independent setup feature. Setup permission does not extend to posting, and setup progress is not posted.

## Design references

These articles were read on 2026-10-03. The integration adopts limited ideas suited to this purpose, not their complete mechanisms or claimed effects.

| Source | Adopted idea |
|---|---|
| [Software factory without reading code](https://zenn.dev/coji/articles/solo-software-factory-without-reading-code) | Limit management overhead and attention-consuming reports while preserving purpose, exclusions, and acceptance criteria |
| [AI code review with PR-Agent](https://zenn.dev/babyjob/articles/ai-review-process-with-pr-agent) | Separate activation from output necessity to avoid repeated-review comment duplication |
| [Revisiting SRE agents after three months](https://zenn.dev/canly/articles/419c622e1ac2db) | Improve Skills and AGENTS within existing work tools |
| [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Resume from Issues, PRs, and Git history rather than posting every intermediate step |

## Validation methods

### Offline tests

```bash
bash install_codex_github_pm.sh --self-test
```

Temporary isolated tests cover installation, update, removal, read helpers, and static instruction consistency. They do not prove real GitHub writes, model selection, or readability.

### Model conversation checks

Extracted `tests/behavioral-scenarios.md` contains 17 fixed inputs/expected behaviors for selection, posting, writing, and connection support using fictional read-only/drafting tasks. `--self-test` does not execute them on a model.

Test selection in fresh sessions without including Skill names or expected behavior. Check that unnecessary records are omitted while blockers and scope changes remain. Read outputs for preserved information, duplication, and invented unagreed details rather than exact wording. Connection support should ask only about gaps and reuse known information and authorization.

## Recorded results

Results checked on 2026-10-03:

| Target | Result |
|---|---|
| v1.3.0 / v1.3.1 distributions | 99 offline tests each, Bash syntax, local links, and whitespace checks passed |
| Installed assets | Distribution match, existing AGENTS text retained, ordinary rerun left content/mtime unchanged, diagnosis checked |
| v1.3.0 activation | 5 independent sessions: Skill read for 3 Japanese/English management requests, not for 2 local typo/citation-only requests |
| v1.3.0 posting B05–B10 | Omitted progress, duplicate outcomes, no-change, and extra field-update comments; kept blockers/scope changes and did not request ongoing authorization again |
| v1.3.0 writing B11/B12 | Guidance strengthened after repetition and invented schedules; final checks preserved expiration, owner-only resumption, denial of others' reads, and save-failure conditions without asserting unagreed methods/dates |
| v1.3.1 connection support | 7 fictional fresh-session cases covered login/CLI suggestions, target questions, immediate investigation when connected, MCP reuse, authorization reuse, and user-side steps |

Model checks used Codex CLI 0.160.0. Environment restrictions prevented OS-level read-only sandbox tests; in normal execution, completed tool calls were confirmed to read local material only. Existing writing Skills were also consulted, so this is not isolated quality measurement of this Skill.

No real login, CLI installation, GitHub posting/mutation, or bulk Issue organization occurred in these conversation tests. Activation rate, posting reduction, and real-world writing gains remain unmeasured. These examples do not guarantee successful authentication or universally correct judgment.
