# Install, update, and remove GitHub Project Director

**English** | [日本語](../../codex-github-pm/installation.md)

[Documentation](../README.md) · [Overview](README.md) · [Usage](usage.md) · [Policy and validation](behavior.md)

## Requirements

Requires Linux / WSL2 / macOS, Bash, Python 3.10 or later, Codex CLI, and write access to Skill and user-wide guidance destinations. Default paths need no administrator privileges. GitHub operations require network access and an authenticated CLI or existing MCP that can access the target.

Follow the [repository download instructions](../../../README.md#quick-start) and run from the root, or run a standalone script from its saved location. Placing Skill files works offline. Codex itself is separate.

## First installation

**No arguments performs installation.** Add `--dry-run` to preview.

```bash
bash install_codex_github_pm.sh --dry-run
bash install_codex_github_pm.sh
```

This places the user-wide Skill and an AGENTS rule directing relevant requests to it. Defaults are `~/.agents/skills/github-project-director/` and usually `~/.codex/AGENTS.md`. Existing text and project files remain intact. See [placement](#placement-and-shared-guidance).

### Also install GitHub CLI

If `gh` is missing and you want it installed:

```bash
bash install_codex_github_pm.sh --install-gh
```

Only if `gh` is absent from PATH, download an official release, verify its published checksum, and place it in `~/.local/bin` by default. Linux/macOS amd64 and arm64 are supported. Existing `gh` is not upgraded. Add the directory to PATH if needed; see [troubleshooting](#troubleshooting) for adding it after Skill installation.

## Start using it

Open a **new Codex session in the project to manage**.

```text
Check this project's progress and organize remaining tasks. Start with investigation and proposals only.
```

Codex checks available connections and suggests only missing setup or target information. It asks before preparations that need authorization and identifies authentication actions only you can complete. An existing usable MCP can be reused. See [examples](usage.md#missing-authentication-or-target-information).

The installer does not log in, add MCP, register tokens, or add permissions. To log in yourself, select the intended host:

```bash
gh auth login --hostname github.com
```

Do not paste credentials into conversation. Permission to prepare a connection is separate from permission to post Issues or comments.

## Verify installation

```bash
bash install_codex_github_pm.sh --doctor
```

Diagnosis is read-only.

| Output | Meaning |
|---|---|
| `installed: true`, `version: "1.3.1"` | Current Skill files exist |
| `modified: []` | No managed files edited/missing; user-added files are outside this check |
| `guidance.valid: true` | User-wide guidance is valid |
| `gh: true`, `authenticated: true` | CLI works and authentication for the selected host succeeded |
| `projects_cli: true` | Projects help is available; individual access is separate |
| `codex: true` | Codex is on PATH |
| `mcp_server_names` | Registered names, not proof of authentication or capabilities |

Exit 0 requires the Skill, unchanged managed files, valid guidance, and CLI authentication. Missing prerequisites return 2; invalid ownership or execution errors return 1. **MCP-only use may still work when missing CLI authentication produces exit 2.** Verify access and permissions for the intended operation. Try `$github-project-director` explicitly if automatic selection fails; activation does not itself post anything.

## Update or rerun

Normal reruns skip existing managed Skills and preserve local edits. Obtain the new script and select `--force` for an update.

```bash
bash install_codex_github_pm.sh --force --dry-run
bash install_codex_github_pm.sh --force
bash install_codex_github_pm.sh --doctor
```

The previous Skill and common AGENTS are separately backed up as ZIPs. This also adds guidance when updating v1.1.0; a normal rerun does not update that version. Distributed files' local edits are overwritten during forced updates. User-added files remain unless they conflict with distribution paths, which stops processing. Same-name directories without ownership records are never overwritten, including with `--force`.

## Remove

```bash
bash install_codex_github_pm.sh --uninstall --dry-run
bash install_codex_github_pm.sh --uninstall
```

Uninstall backs up the Skill and removes managed files, ownership metadata, and the managed guidance block. Existing/later AGENTS text, added files, `gh`, authentication, and backups remain. An AGENTS file created by this installer is deleted only when nothing outside the managed block remains. Edits stop removal; if you deliberately want edited managed files removed, use `--uninstall --force` after backup.

## Placement and shared guidance

| Asset | Default |
|---|---|
| Skill, references, UI metadata, helper | `~/.agents/skills/github-project-director/`, from the embedded ZIP |
| Shared guidance | `$CODEX_HOME/AGENTS.md`, or nonempty `AGENTS.override.md` |
| Ownership record | `.github-pm-install.json` inside the Skill; records hashes and guidance path |
| Optional GitHub CLI | `~/.local/bin/gh`, from official `cli/cli` releases |
| Skill backup | `.github-project-director.backup-<ID>.zip` in the Skill parent |
| Guidance backup | `.github-project-director.backup-guidance-<ID>.zip` in the guidance directory |

The Codex home precedence is `--codex-home`, `CODEX_HOME`, then `~/.codex`. The block records the Skill's actual absolute path and is not duplicated on reruns. Updates/removal use the recorded guidance destination; uninstall and reinstall to move it. Another Skill directory cannot overwrite the same guidance. Preview `global_guidance` with `--dry-run`.

Normal installation downloads no dependencies and verifies embedded SHA-256 before extraction. It does not alter Codex `config.toml`, hooks, Basic Memory, ECC, SpecKit, or GitHub data.

### Update and removal protection

Symlinks, including destination parents, are refused. Locks on the Skill and guidance prevent simultaneous installers. Failed writes/replacements restore prior assets. Concurrent edits to guidance cause a stop with recovery backups retained. Forced termination or disk failures during restoration cannot be guaranteed recoverable. A downloaded `gh` may remain if later Skill installation fails. Inspect errors and paths rather than repeatedly forcing operations or deleting locks.

## Detailed options

| Option / variable | Default | Effect |
|---|---|---|
| `--help` / `-h` | — | Help |
| `--dry-run` | Off | Preview without persistent writes or dependency fetches |
| `--force` | Off | Back up and update existing assets; with uninstall, remove edited managed files |
| `--doctor` | Off | Read-only files, guidance, CLI, and authentication checks |
| `--uninstall` | Off | Remove managed assets |
| `--install-gh` | Off | Download official `gh` only if missing from PATH |
| `--gh-version X.Y.Z` | Latest official version when downloaded | Pin optional `gh`; `vX.Y.Z` also accepted |
| `--skills-dir PATH` | `~/.agents/skills` | Skill parent directory |
| `--codex-home PATH` | `CODEX_HOME`, else `~/.codex` | Guidance home; recorded path reused later |
| `--bin-dir PATH` | `~/.local/bin` | Optional `gh` destination |
| `--hostname HOST` | `github.com` | Authentication diagnosis host, not a change to normal operation targets |
| `--self-test` | — | Offline tests in temporary environment |
| `--extract DIRECTORY` | — | Extract to unused/empty directory |
| `PYTHON_BIN` | Auto-detect compatible Python | Python 3.10+ command/path |

`--gh-version` requires `--install-gh`. Do not combine `--doctor` with `--force`, `--uninstall`, or `--install-gh`, or `--uninstall` with `--install-gh`. Use `--self-test` and `--extract` alone. Reuse custom `--skills-dir` for diagnosis, updates, and removal.

## Inspect distribution contents

Extraction writes files but does not install anything. Use an unused or empty directory.

```bash
bash install_codex_github_pm.sh --extract /tmp/github-pm-review
```

Inspect `README_EXTRACTED.md`, `scripts/install_github_pm.py`, `skills/github-project-director/`, `tests/test_github_project_director.py`, and `tests/behavioral-scenarios.md`. Skill references cover operations, planning, and writing. See [test distinctions](behavior.md).

## Troubleshooting

| Symptom | Action |
|---|---|
| Python requirement | Provide Python 3.10+ and optionally `PYTHON_BIN` |
| Embedded checksum mismatch | Check damage/modification and download the script again |
| `Unmanaged path exists` | Preserve and reconcile the same-name existing Skill |
| Symlink error | Select real directories and check Codex discovery |
| `gh` outside PATH | Add its directory |
| `--install-gh` skipped for an existing Skill | Use `--force --install-gh` if also updating; otherwise install CLI separately |
| `authenticated: false` | Check CLI authentication and host separately from MCP |
| Project access fails | Check target and authentication permissions; failed retrieval is not an empty list |
| Edited guidance | Deliberate replacement/removal can use `--force` with backup |
| Missing/malformed guidance block | Restore from backup; malformed markers are not ignored even with `--force` |
| Guidance shadowed by another AGENTS | Uninstall and reinstall to the effective common instruction file |
| Skill missing in Codex | Start a new session and check destination / `SKILL.md` |

See official [Projects](https://cli.github.com/manual/gh_project) and [authentication status](https://cli.github.com/manual/gh_auth_status) documentation. These explanations use the implementation and official material checked on 2026-09-30.
