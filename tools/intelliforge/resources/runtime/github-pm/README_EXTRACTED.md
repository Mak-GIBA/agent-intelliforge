# GitHub Project Director v1.3.1 embedded sources

These are the readable resources embedded in `install_codex_github_pm.sh`.
The repository only needs the single installer file; normal installation extracts these resources to a temporary directory and installs the Skill into the user-level Codex skill directory, plus a managed block in the effective global AGENTS file. Project AGENTS files are not changed.

Key behavior:
- Explicit invocation: `$github-project-director` followed by the user's request.
- Natural-language/implicit selection remains enabled; global guidance routes GitHub requests to the installed Skill.
- `--codex-home` selects global guidance; otherwise CODEX_HOME or ~/.codex is used.
- Existing instructions outside the owned block are preserved; force updates back up both resources.
- Issue/PR/review/progress writing follows references/writing-and-tracking.md.
- Business goal / user story / requirements are considered when proposing Issues.
- Important GitHub writes follow analysis -> proposal -> user confirmation -> write -> read-back.
- Progress/remaining-task/priority/blocker requests activate the Skill when context identifies GitHub, even without its name.
- When setup or target information is missing, offer specific help and ask only for the missing permission/details; resume the original task once ready.
- Activation does not imply posting: check shared value, existing evidence and authorization before drafting a comment.
- Record important blockers, agreed scope decisions and handoffs only when they add information; do not echo retries, individual tests or field changes.
- Recurring updates require an explicit request or agreed policy. No material change means no comment unless explicitly requested.
- Read `tests/behavioral-scenarios.md` for live behavior and writing checks, separate from static contract tests.
- GitHub Issues/Projects remain the source of truth; no background scheduler or extra task database is installed.

Run the outer installer with `--self-test` to execute the embedded offline tests.
