# GitHub Project Director

**English** | [日本語](../../codex-github-pm/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md) · [Recording policy and validation](behavior.md)

A custom Skill for investigating, organizing, and updating GitHub Issues, PRs, and Projects through Codex conversation. Issues track work and defects, PRs propose code changes, and Projects organize ownership and progress. Reports explain purpose, changes, verification, and next actions for both developers and non-developers.

Requests such as “check progress” or “organize remaining tasks” activate the relevant procedure when the repository or conversation identifies GitHub. **Activating a Skill is separate from posting an Issue comment.** Record important new information rather than every intermediate step. Missing authentication or target information triggers focused connection support.

[install_codex_github_pm.sh](../../../install_codex_github_pm.sh), version **v1.3.1**, is self-contained. No helper checkout is needed. This is a repository-specific Skill, not an official GitHub, OpenAI, or ECC distribution.

## Installed assets

| Asset | Purpose |
|---|---|
| `github-project-director`, references, and display metadata | Writing, posting decisions, task breakdown, ownership, deadlines, priorities, and Codex display settings |
| `github_inspect.py` | Read Issues, PRs, Projects, dependencies, and recurring updates; no writes |
| User-wide AGENTS guidance | Direct GitHub requests to the Skill |

The default Skill location is `~/.agents/skills/github-project-director/`. Guidance is normally added to `~/.codex/AGENTS.md`, preserving existing content. Project AGENTS files, Codex configuration/hooks, and remote GitHub data are unchanged. See [placement and updates](installation.md).

Operations use official `gh` or an available GitHub MCP. Existing `gh` is reused; downloading it requires `--install-gh`. Installation does not log in, add a GitHub MCP, or register tokens. Codex must already be installed. Basic Memory, ECC, and SpecKit are neither installed nor required.

## After installation

1. Open a new Codex session in the project you want to manage and make a normal request.
2. Codex identifies the target and connection, investigates what is needed, and asks only for missing information or permission.
3. Results/proposals return in conversation. Authorized remote changes are fetched again to verify their result.

```text
Check this project's progress and organize remaining tasks and blockers. Start with findings and proposals only.
```

See [usage](usage.md) for connection support and Issue/PR examples. Selection relies on Codex instructions rather than a program that guarantees activation in every conversation. Use `$github-project-director` explicitly when needed.

## Capabilities and records

Create/review Issues and PRs, investigate Actions failures, summarize releases, propose tasks from requirements, detect gaps/duplicates, and organize hierarchy, dependencies, ownership, deadlines, and priorities. Use only relevant steps for a small request rather than auditing the whole project.

GitHub Issues / Projects are the source of truth for work status. Recurring records require an explicit request or agreed process and summarize significant changes. No separate management database or background scheduler is installed. See [policy and validation](behavior.md).
