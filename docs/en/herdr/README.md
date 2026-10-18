# Herdr — open a terminal by working directory

**English** | [日本語](../../herdr/README.md)

[Documentation](../README.md) · [Installation](installation.md) · [Usage](usage.md)

After moving into a project, run `herdr` to open its workspace: a group of terminals for that project. An existing workspace for the same directory is reused; otherwise one is created. [install_herdr.sh](../../../install_herdr.sh) works as a standalone script and **installs and configures the integration without arguments**.

## Components

| Component | Source | Role |
|---|---|---|
| Herdr | [Herdr](https://herdr.dev/) | Terminal and workspace application; fetched from its official installer only if missing |
| `herdr-open` | This repository | Find, select, or create a workspace using the directory's real path |
| Bash `herdr` function | This repository | Route calls without arguments to `herdr-open`, and calls with arguments to Herdr's own CLI |

Matching uses a recorded association with the real directory path, rather than a workspace name or label alone. No Git worktree is created, and no Codex Skill, Plugin, MCP, or hook is registered.

The wrapper uses the CLI and `session.json` format checked with Herdr 0.9.3. Unknown formats stop processing rather than creating a guessed workspace. See [installation](installation.md) and [daily usage](usage.md).
