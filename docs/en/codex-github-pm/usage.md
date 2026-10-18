# Use GitHub Project Director

**English** | [日本語](../../codex-github-pm/usage.md)

[Documentation](../README.md) · [Overview](README.md) · [Installation](installation.md) · [Policy and validation](behavior.md)

## Make a normal request

Start a **new Codex session in the project you want to manage**, which may differ from this installer's checkout. Enter requests in conversation:

```text
Check this project's progress. Organize remaining tasks and blockers, and suggest priorities for this week. Investigation and proposals only for now.
```

```text
Create an Issue for this bug. Make its purpose and completion criteria clear to a first-time reader.
```

```text
Create a PR for this change. Explain behavior changes, verification, related Issues, and remaining work.
```

PR review and Actions failure investigation are also supported. The target can be inferred from a GitHub URL, prior conversation, or repository remote. Requests about progress, remaining tasks, priorities, or blockers need not contain “GitHub” when context identifies it. A citation-only GitHub reference or local-only work does not activate this management workflow.

Use `$github-project-director` explicitly when needed. It is not a terminal command, and project AGENTS files need no edits. If selection fails, try explicit invocation and check [guidance](installation.md#verify-installation).

## Missing authentication or target information

Codex first inspects conversation, repository, and available connections, then addresses only confirmed gaps. It can offer to initiate login, install CLI when no usable connection exists, ask for `OWNER/REPO`, or provide commands for your own machine when execution is restricted. An authenticated MCP is reused without requiring `gh`. Known information and authorized setup are not asked for again; Issue-only work does not require selecting a Project board. Passwords/tokens need not be pasted into chat.

After setup, read-only access is checked and the original request resumes. Connection setup permission is not posting permission, and setup progress is not recorded in Issues. This is assistance during a task, not automatic installer login or a separate setup feature.

## From investigation to remote changes

1. Identify the target and inspect the body, diff, code, tests, and other evidence needed for this request.
2. Return findings/proposals with known limits and unresolved points.
3. Apply authorized changes, fetch their state again, and verify results and URLs.

Do not add writes to investigation-only requests or ask again for an already authorized concrete change. Confirm unresolved ownership, dates, or scope before applying them. If target state changed, explain the difference. Distinguish successful changes from uncompleted ones.

## When to record a comment

Check shared value, duplication, and scope before suggesting a comment.

| Situation | Default |
|---|---|
| Start, intermediate progress, retry, individual test success | Report in conversation as needed; do not post |
| Status/owner field update | Update authorized fields without another explanatory comment |
| Blocker needing human judgment | Summarize impact and decision; propose in conversation if posting is unauthorized |
| Agreed scope/policy change | Record change and reason; avoid duplicate comments if body edits suffice |
| Completion/handoff | Summarize outcome, verification, remaining work; avoid duplicating an adequate PR |
| Recurring update | Only explicit/agreed operation; aggregate important changes |

No change or sufficient existing records need no draft or approval prompt. An explicit “record no change” request is an exception. Avoid identical parent/child/recurring comments or proposing a recurring Issue merely because no destination exists.

## Write readable Issues and PRs

Lead Issues with need, work, and completion criteria; lead PRs with purpose, behavior change, and validation. Explain necessary terms on first use and label link relationships. Respect existing templates/languages rather than forcing headings into short updates. Moving long detail elsewhere must retain purpose, acceptance conditions, and major constraints in the body.

For example, describe the observable behavior rather than only an “auth hook race”: the fix prevents returning to login on refresh by waiting for saved login data before switching screens. Do not infer unagreed mechanisms, owners, or dates from examples. Separate confirmed results from future work.

## Request examples

### Propose tasks from requirements

```text
Check business goals, user stories, requirements, implementation, and existing Issues. Propose nonduplicate tasks with purpose, scope, completion criteria, and evidence. Proposals only.
```

Propose verifiable outcomes rather than mechanically splitting by file or creating a parent Issue for every task. Do not invent user stories for maintenance. Existing SpecKit documents can support requirements.

### Plan ownership, deadlines, and priorities

```text
Propose work for the next two weeks. Check the existing Project and dependencies; organize priority, candidate owners, proposed dates, and unconfirmed capacity. Show changes before applying them.
```

Check dates, time zones, and capacity; use existing Project fields. Parent/child hierarchy differs from prerequisite dependencies. Individual Issue deadlines use Project date fields rather than milestone dates.

### Update an agreed recurring Issue

Replace example `#42` with the actual Issue or URL.

```text
Draft a short update for recurring Issue #42 with important changes since the last report: outcomes, decisions, and next actions. Do not change owners or dates; show the draft first.
```

Keep prior text/comments. A recording-only request does not change status or owners. Check earlier comments and retry markers before posting to avoid duplication after network failures; this does not prevent simultaneous posts.

## Results and boundaries

Findings, proposals, and pre-application checks return in conversation. Authorized tasks/plans go to Issues / Projects, recurring updates to the specified Issue. Request a local destination explicitly if needed. No separate ledger database, scheduler, or routine snapshots are created.

Production deployment, PR merging, Issue deletion/transfer, and administrative permission changes are outside this Skill. If connection cannot be prepared, report insufficient evidence and offer provisional analysis from local material; never infer remote state or successful writes. See [validation limits](behavior.md).

## Read-only helper

Manual use needs Python 3.10+ and authenticated `gh` with target access. Replace `OWNER/REPO`, owner, Project, and Issue numbers with real values.

```bash
python3 ~/.agents/skills/github-project-director/scripts/github_inspect.py snapshot --repo OWNER/REPO
python3 ~/.agents/skills/github-project-director/scripts/github_inspect.py project --owner OWNER --owner-type user --number 1
python3 ~/.agents/skills/github-project-director/scripts/github_inspect.py relations --repo OWNER/REPO --issue 42
python3 ~/.agents/skills/github-project-director/scripts/github_inspect.py meeting --repo OWNER/REPO --issue 42
```

Use `--owner-type organization` for organization Projects. Put `--hostname HOST --max-pages N` before subcommands. `meeting --entry-key KEY` checks retry markers. Output goes to stdout only: no files or GitHub writes. Check `complete`, `pages`, and `error`; partial retrieval or denied access is not “no results.” Snapshot Projects are linked repository Projects; inspect other required Projects explicitly.
